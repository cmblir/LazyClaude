"""Plugin Hub — discover and fetch Claude Code extensions from GitHub.

Claude Code plugins ship in *marketplace* repos: a repo carrying
``.claude-plugin/marketplace.json`` that lists one or more plugins (skills,
agents, hooks, MCP servers, slash-commands). This module lets the dashboard:

    1. search    — rank claude-code plugin repos on GitHub by stars
    2. inspect   — read a repo's marketplace.json + per-plugin risk signals
    3. install   — `claude plugin marketplace add` + `claude plugin install`
    4. installed — list what's already installed

Discovery uses the public GitHub REST search API (unauthenticated 10 req/min;
set ``GITHUB_TOKEN``/``GH_TOKEN`` to lift to 30/min + 5000/hr core). Raw
``marketplace.json`` is fetched from the CDN (raw.githubusercontent.com), which
is NOT part of the REST rate limit, so inspection is cheap.

Security stance (installing a plugin runs third-party code at user privilege):
    - install is GATED behind an explicit ``confirm: true`` — never automatic.
    - repo / plugin / marketplace identifiers are strict-validated against an
      allow-list charset before they ever reach a subprocess (no shell=True,
      arg lists only) so a crafted name cannot inject a command.
    - inspect surfaces "runs code" risk flags (hooks / mcpServers / bin) and
      trust signals (stars, freshness, license, official-marketplace) so the
      user decides with eyes open.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .logger import log

# ───────── constants ─────────

GH_API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
_UA = "LazyClaude-PluginHub"

# Default discovery topics (ANDed by GitHub if combined; we query the most
# specific one). `claude-code-plugin` is the highest-precision signal.
DEFAULT_TOPIC = "claude-code-plugin"

# Reserved/official marketplace owners → shown as a trust badge.
_OFFICIAL_OWNERS = {"anthropics"}

# Identifier validation. owner/repo, plugin, and marketplace names all come
# from user input or fetched JSON and flow into a subprocess; pin them to a
# conservative charset so nothing shell-significant survives.
_RE_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
_RE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_SEARCH_TTL_S = 300  # cache search results 5 min (rate-limit friendly)
_CACHE_LOCK = threading.Lock()
_SEARCH_CACHE: dict[str, tuple[float, dict]] = {}

_HTTP_TIMEOUT = 12


def _gh_headers() -> dict:
    h = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    import os

    tok = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _http_get(url: str, *, accept_json: bool = True) -> tuple[int, object, dict]:
    """GET a URL. Returns (status, parsed_or_text, headers). Never raises —
    network/parse failures degrade to (status_or_0, None, {})."""
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            status = resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            hdrs = {k.lower(): v for k, v in e.headers.items()}
        except Exception:
            hdrs = {}
        return e.code, None, hdrs
    except Exception as e:
        log.warning("plugin_hub: GET %s failed: %s", url, e)
        return 0, None, {}
    if not accept_json:
        return status, raw.decode("utf-8", errors="replace"), hdrs
    try:
        return status, json.loads(raw.decode("utf-8", errors="replace")), hdrs
    except Exception:
        return status, None, hdrs


def _rate_meta(hdrs: dict) -> dict:
    try:
        return {
            "remaining": int(hdrs.get("x-ratelimit-remaining", -1)),
            "reset": int(hdrs.get("x-ratelimit-reset", 0)),
        }
    except Exception:
        return {}


def _claude_bin() -> str | None:
    return shutil.which("claude")


# ───────── search ─────────


def _repo_to_card(item: dict) -> dict:
    owner = ((item.get("owner") or {}).get("login")) or ""
    lic = (item.get("license") or {}) or {}
    return {
        "fullName": item.get("full_name") or "",
        "owner": owner,
        "name": item.get("name") or "",
        "stars": int(item.get("stargazers_count") or 0),
        "description": (item.get("description") or "")[:300],
        "htmlUrl": item.get("html_url") or "",
        "defaultBranch": item.get("default_branch") or "main",
        "pushedAt": item.get("pushed_at") or "",
        "license": lic.get("spdx_id") or "",
        "topics": list(item.get("topics") or [])[:12],
        "archived": bool(item.get("archived")),
        "official": owner.lower() in _OFFICIAL_OWNERS,
    }


def api_plugin_hub_search(query: dict) -> dict:
    """GET /api/plugin_hub/search?q=&topic=&limit=

    Ranks Claude Code plugin/marketplace repos by stars. Empty ``q`` falls back
    to a topic search (``claude-code-plugin``). Results are cached 5 min.
    """
    q = (query.get("q", [""])[0] or "").strip()
    topic = (query.get("topic", [""])[0] or "").strip() or DEFAULT_TOPIC
    try:
        limit = int(query.get("limit", ["30"])[0])
    except Exception:
        limit = 30
    limit = max(1, min(50, limit))

    # Build the GitHub search expression. Free text is scoped to the
    # claude-code domain so unrelated repos don't dominate; empty text uses
    # the topic, which is the precise plugin signal.
    if q:
        if not _RE_TOPIC_OK(topic):
            topic = DEFAULT_TOPIC
        search_q = f"{q} claude code in:name,description,readme"
    else:
        search_q = f"topic:{topic}"

    cache_key = f"{search_q}|{limit}"
    now = time.time()
    with _CACHE_LOCK:
        hit = _SEARCH_CACHE.get(cache_key)
        if hit and (now - hit[0]) < _SEARCH_TTL_S:
            return hit[1]

    url = (
        f"{GH_API}/search/repositories?q="
        + urllib.parse.quote(search_q)
        + f"&sort=stars&order=desc&per_page={limit}"
    )
    status, body, hdrs = _http_get(url)
    if status == 403:
        return {
            "ok": False,
            "error": "GitHub rate limit hit (search: 10/min unauthenticated). "
            "Set GITHUB_TOKEN to raise it, or retry shortly.",
            "rate": _rate_meta(hdrs),
        }
    if status != 200 or not isinstance(body, dict):
        return {"ok": False, "error": f"GitHub search failed (HTTP {status})"}

    items = body.get("items") or []
    cards = [_repo_to_card(it) for it in items if isinstance(it, dict)]
    # Drop archived/disabled; keep stars order (GitHub already sorted).
    cards = [c for c in cards if not c["archived"]]
    result = {
        "ok": True,
        "query": search_q,
        "total": int(body.get("total_count") or 0),
        "repos": cards,
        "rate": _rate_meta(hdrs),
        "authenticated": "authorization" in _gh_headers(),
    }
    with _CACHE_LOCK:
        _SEARCH_CACHE[cache_key] = (now, result)
    return result


def _RE_TOPIC_OK(topic: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9-]{0,49}$", topic))


# ───────── inspect ─────────


def _fetch_marketplace_json(repo: str, branch: str) -> tuple[object, str]:
    """Fetch + parse .claude-plugin/marketplace.json from the CDN. Returns
    (parsed|None, branch_used)."""
    for br in [branch, "main", "master"]:
        if not br:
            continue
        url = f"{RAW}/{repo}/{br}/.claude-plugin/marketplace.json"
        status, body, _ = _http_get(url)
        if status == 200 and isinstance(body, (dict, list)):
            return body, br
    return None, branch


def _assess_plugin_risk(repo: str, branch: str, source) -> dict:
    """Best-effort: read a plugin's plugin.json to flag executable components.
    `source` is the marketplace plugins[].source (str path or dict). Only local
    relative-path sources are probed (remote git/npm sources can't be cheaply
    inspected via the CDN). Failures degrade to unknown (no flags)."""
    rel = None
    if isinstance(source, str):
        rel = source
    elif isinstance(source, dict) and source.get("source") in (None, "local"):
        rel = source.get("path") or source.get("source")
    if not isinstance(rel, str) or not rel:
        return {"runsCode": None, "components": [], "probed": False}
    rel = rel.lstrip("./").strip("/")
    base = f"{repo}/{branch}/" + (rel + "/" if rel else "")
    status, pj, _ = _http_get(f"{RAW}/{base}.claude-plugin/plugin.json")
    components: list[str] = []
    runs_code = False
    if status == 200 and isinstance(pj, dict):
        for key, risky in (
            ("hooks", True),
            ("mcpServers", True),
            ("commands", False),
            ("agents", False),
            ("skills", False),
        ):
            if pj.get(key):
                components.append(key)
                if risky:
                    runs_code = True
    return {"runsCode": runs_code if status == 200 else None,
            "components": components, "probed": status == 200}


def api_plugin_hub_inspect(query: dict) -> dict:
    """GET /api/plugin_hub/inspect?repo=owner/repo

    Reads the repo's marketplace.json and returns the install metadata for each
    plugin plus best-effort risk flags. This is the confirm-before-install view.
    """
    repo = (query.get("repo", [""])[0] or "").strip()
    if not _RE_REPO.match(repo):
        return {"ok": False, "error": "repo must be 'owner/name'"}

    # Resolve default branch (1 core REST call; cheap, cached implicitly by GH).
    status, meta, _ = _http_get(f"{GH_API}/repos/{repo}")
    branch = "main"
    repo_meta = {}
    if status == 200 and isinstance(meta, dict):
        branch = meta.get("default_branch") or "main"
        repo_meta = _repo_to_card(meta)
    elif status == 404:
        return {"ok": False, "error": "repo not found"}

    mkt, branch = _fetch_marketplace_json(repo, branch)
    if mkt is None:
        return {
            "ok": False,
            "error": "no .claude-plugin/marketplace.json found — not an installable "
            "marketplace repo (it may be a plain skills repo or just an agents list).",
            "repo": repo_meta,
        }

    mkt_name = (mkt.get("name") if isinstance(mkt, dict) else "") or ""
    raw_plugins = (mkt.get("plugins") if isinstance(mkt, dict) else None) or []
    plugins = []
    # Probe risk for up to 8 plugins in parallel (CDN, not rate-limited).
    def _one(p):
        if not isinstance(p, dict):
            return None
        name = (p.get("name") or "").strip()
        if not name:
            return None
        risk = _assess_plugin_risk(repo, branch, p.get("source"))
        return {
            "name": name,
            "description": (p.get("description") or "")[:300],
            "category": p.get("category") or p.get("tags") or "",
            "source": p.get("source"),
            "version": p.get("version") or "",
            "risk": risk,
            "installCmd": f"claude plugin install {name}@{mkt_name}" if mkt_name else "",
        }

    cap = 100
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(_one, raw_plugins[:cap]):
            if r:
                plugins.append(r)
    truncated = max(0, len(raw_plugins) - cap)

    return {
        "ok": True,
        "repo": repo_meta or {"fullName": repo, "defaultBranch": branch},
        "marketplaceName": mkt_name,
        "marketplaceDescription": (mkt.get("description") if isinstance(mkt, dict) else "") or "",
        "plugins": plugins,
        "truncated": truncated,
        "addCmd": f"claude plugin marketplace add {repo}",
    }


# ───────── install ─────────


def _run_claude(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    cb = _claude_bin()
    if not cb:
        return 127, "", "`claude` CLI not on PATH"
    try:
        p = subprocess.run(
            [cb, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return p.returncode, (p.stdout or "")[-4000:], (p.stderr or "")[-4000:]
    except subprocess.TimeoutExpired:
        return 124, "", f"`claude {' '.join(args)}` timed out after {timeout}s"
    except Exception as e:
        return 1, "", f"spawn failed: {e}"


def api_plugin_hub_install(body: dict) -> dict:
    """POST /api/plugin_hub/install

    Body: {repo, plugin, marketplace, confirm:true, scope?='user'}

    Runs `claude plugin marketplace add <repo>` then
    `claude plugin install <plugin>@<marketplace> --scope <scope>`. GATED:
    refuses unless ``confirm`` is true (installing runs third-party code).
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    if not body.get("confirm"):
        return {
            "ok": False,
            "error": "confirm:true required — installing a plugin runs third-party "
            "code (hooks/MCP/bin) at your user privilege. Review it first.",
            "needsConfirm": True,
        }
    repo = (body.get("repo") or "").strip()
    plugin = (body.get("plugin") or "").strip()
    marketplace = (body.get("marketplace") or "").strip()
    scope = (body.get("scope") or "user").strip().lower()
    if scope not in ("user", "project", "local"):
        scope = "user"
    if not _RE_REPO.match(repo):
        return {"ok": False, "error": "repo must be 'owner/name'"}
    if not _RE_NAME.match(plugin):
        return {"ok": False, "error": "invalid plugin name"}
    if not _RE_NAME.match(marketplace):
        return {"ok": False, "error": "invalid marketplace name"}
    if _claude_bin() is None:
        return {"ok": False, "error": "`claude` CLI not on PATH"}

    steps = []
    add_rc, add_out, add_err = _run_claude(["plugin", "marketplace", "add", repo])
    steps.append({"step": "marketplace add", "rc": add_rc, "out": add_out, "err": add_err})
    # `marketplace add` failing because it already exists is non-fatal; only a
    # genuine failure (network/bad repo) should abort before install.
    already = "already" in (add_err + add_out).lower()
    if add_rc != 0 and not already:
        return {"ok": False, "error": f"marketplace add failed: {add_err or add_out}", "steps": steps}

    inst_rc, inst_out, inst_err = _run_claude(
        ["plugin", "install", f"{plugin}@{marketplace}", "--scope", scope]
    )
    steps.append({"step": "install", "rc": inst_rc, "out": inst_out, "err": inst_err})
    if inst_rc != 0:
        return {"ok": False, "error": f"install failed: {inst_err or inst_out}", "steps": steps}

    log.info("plugin_hub: installed %s@%s from %s (scope=%s)", plugin, marketplace, repo, scope)
    return {"ok": True, "installed": f"{plugin}@{marketplace}", "scope": scope, "steps": steps}


# ───────── installed list ─────────


def api_plugin_hub_installed(query: dict) -> dict:
    """GET /api/plugin_hub/installed — `claude plugin list --json`."""
    if _claude_bin() is None:
        return {"ok": True, "plugins": [], "note": "`claude` CLI not on PATH"}
    rc, out, err = _run_claude(["plugin", "list", "--json"], timeout=30)
    if rc != 0:
        # Older CLIs may not support --json; surface gracefully rather than 500.
        return {"ok": True, "plugins": [], "raw": (out or err)[:2000], "note": "could not list plugins"}
    try:
        data = json.loads(out)
    except Exception:
        return {"ok": True, "plugins": [], "raw": out[:2000]}
    return {"ok": True, "plugins": data if isinstance(data, list) else data}
