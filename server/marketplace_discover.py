"""Plugin & Skill Marketplace Discover browser.

Read-only discovery layer over Claude Code's local plugin state. It parses the
cached marketplace manifests that the `claude` CLI writes under
``~/.claude/plugins`` and surfaces every advertised plugin with its install
state and the EXACT, verified install command.

Sources (all local, all read-only — we never fetch arbitrary remote URLs):
  - ``~/.claude/plugins/known_marketplaces.json`` : configured marketplaces +
    their cached ``installLocation`` on disk.
  - ``<installLocation>/.claude-plugin/marketplace.json`` : the marketplace
    manifest (``plugins[]`` catalogue). If this cache file is absent we mark
    the marketplace ``needsRefresh`` instead of reaching out to the network.
  - ``~/.claude/plugins/installed_plugins.json`` : installed plugins keyed by
    ``name@marketplace``.
  - ``settings.json`` ``enabledPlugins`` / ``extraKnownMarketplaces`` : enabled
    state + admin-declared marketplaces not yet cloned locally.

Verified against docs.claude.com (code.claude.com/docs/en/discover-plugins,
2026-06-01):
  - add a marketplace : ``claude plugin marketplace add <source>``
  - refresh a cache   : ``claude plugin marketplace update <marketplace>``
  - install a plugin  : ``claude plugin install <name>@<marketplace>``
The ``<name>@<marketplace>`` install form and the ``add``/``update`` verbs are
the documented commands; the slash-command equivalents (``/plugin install`` …)
behave identically inside an interactive session.

Public handlers:
  - api_marketplace_discover(query)        : all marketplaces + their plugins.
  - api_marketplace_browse(query)          : one marketplace's plugin list.
  - api_marketplace_install(body)          : run a CURATED install command in a
    Terminal window (never arbitrary input).
"""
from __future__ import annotations

import json
from pathlib import Path

from .claude_md import get_settings
from .cli_tools import _run_in_terminal, _which
from .config import (
    INSTALLED_PLUGINS_JSON,
    KNOWN_MARKETPLACES_JSON,
    PLUGINS_DIR,
)
from .utils import _safe_read

# The marketplace manifest lives at this relative path inside a cloned/cached
# marketplace repo (verified: code.claude.com/docs/en/plugin-marketplaces).
_MANIFEST_REL = (".claude-plugin/marketplace.json", "marketplace.json")

# A simple identifier guard for values we splice into a shell command. Every
# install command is built from local, server-parsed manifest data — never raw
# user input — but we still validate the shape so a malformed manifest entry
# can never produce an injectable command string.
_SAFE_ID = __import__("re").compile(r"^[A-Za-z0-9_][A-Za-z0-9_.@-]*$")


# ───────── manifest / state loading (read-only) ─────────

def _load_json(p: Path) -> dict:
    """Read a JSON file, returning {} on any error (missing / malformed)."""
    if not p.exists():
        return {}
    try:
        data = json.loads(_safe_read(p))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _known_marketplaces() -> dict:
    """known_marketplaces.json merged with settings.extraKnownMarketplaces.

    known_marketplaces.json wins on key collision because it reflects what is
    actually cloned on disk; extra entries are admin/team declarations that may
    not be cached yet (those surface as ``needsRefresh``).
    """
    km = _load_json(KNOWN_MARKETPLACES_JSON)
    s = get_settings()
    extra = (s.get("extraKnownMarketplaces") if isinstance(s, dict) else None) or {}
    merged: dict = {}
    for name, meta in {**extra, **km}.items():
        if isinstance(meta, dict):
            merged[name] = meta
    return merged


def _installed_map() -> dict:
    """installed_plugins.json → {composite_id: install_records}."""
    data = _load_json(INSTALLED_PLUGINS_JSON)
    plugins = data.get("plugins", {})
    return plugins if isinstance(plugins, dict) else {}


def _enabled_map() -> dict:
    s = get_settings()
    ep = s.get("enabledPlugins") if isinstance(s, dict) else None
    return ep if isinstance(ep, dict) else {}


def _resolve_install_location(name: str, meta: dict) -> Path | None:
    """Where is this marketplace's manifest cached on disk?

    Prefer the ``installLocation`` recorded by the CLI; fall back to the
    conventional ``PLUGINS_DIR/marketplaces/<name>`` layout. Returns the
    directory only if it actually exists on disk (so a stale path becomes
    needs-refresh rather than a crash).
    """
    loc = meta.get("installLocation")
    candidates: list[Path] = []
    if isinstance(loc, str) and loc:
        candidates.append(Path(loc))
    candidates.append(PLUGINS_DIR / "marketplaces" / name)
    for c in candidates:
        try:
            if c.is_dir():
                return c
        except Exception:
            continue
    return None


def _read_manifest(install_dir: Path) -> dict | None:
    """Parse the cached .claude-plugin/marketplace.json under a marketplace dir."""
    for rel in _MANIFEST_REL:
        f = install_dir / rel
        if f.exists():
            try:
                data = json.loads(_safe_read(f))
                if isinstance(data, dict):
                    return data
            except Exception:
                return None
    return None


def _author_name(author) -> str:
    """marketplace.json author is either a string or {name, email, url}."""
    if isinstance(author, dict):
        return author.get("name", "") or author.get("url", "")
    if isinstance(author, str):
        return author
    return ""


def _source_summary(source) -> str:
    """Human-readable one-liner for a plugin/marketplace source descriptor."""
    if isinstance(source, str):
        return source
    if isinstance(source, dict):
        return (
            source.get("repo")
            or source.get("url")
            or source.get("path")
            or source.get("source")
            or ""
        )
    return ""


def _install_command(plugin_name: str, marketplace_name: str) -> str:
    """The VERIFIED install command, or "" if either id is shell-unsafe.

    Form: ``claude plugin install <name>@<marketplace>`` — documented at
    code.claude.com/docs/en/discover-plugins.
    """
    if not (_SAFE_ID.match(plugin_name) and _SAFE_ID.match(marketplace_name)):
        return ""
    return f"claude plugin install {plugin_name}@{marketplace_name}"


def _refresh_command(marketplace_name: str) -> str:
    """``claude plugin marketplace update <marketplace>`` — verified verb."""
    if not _SAFE_ID.match(marketplace_name):
        return ""
    return f"claude plugin marketplace update {marketplace_name}"


def _plugin_card(p: dict, marketplace_name: str, installed: dict, enabled: dict) -> dict | None:
    """One manifest plugin entry → a discovery card with install state."""
    if not isinstance(p, dict):
        return None
    name = (p.get("name") or "").strip()
    if not name:
        return None
    composite_id = f"{name}@{marketplace_name}"
    install_records = installed.get(composite_id)
    is_installed = bool(install_records)
    version = ""
    if isinstance(install_records, list) and install_records:
        last = install_records[-1]
        if isinstance(last, dict):
            version = last.get("version", "") or ""
    if not version:
        version = p.get("version", "") or ""
    keywords = p.get("keywords") or p.get("tags") or []
    if not isinstance(keywords, list):
        keywords = []
    return {
        "id": composite_id,
        "name": name,
        "marketplace": marketplace_name,
        "description": (p.get("description") or "").strip(),
        "author": _author_name(p.get("author")),
        "category": p.get("category", "") or "",
        "keywords": [str(k) for k in keywords if k][:12],
        "version": version,
        "homepage": p.get("homepage", "") or "",
        "source": _source_summary(p.get("source")),
        "installed": is_installed,
        "enabled": bool(enabled.get(composite_id, False)),
        "installCommand": _install_command(name, marketplace_name),
    }


def _build_marketplace(name: str, meta: dict, installed: dict, enabled: dict) -> dict:
    """Assemble one marketplace entry: metadata + cached-manifest plugin list."""
    source = meta.get("source") if isinstance(meta, dict) else {}
    src = source if isinstance(source, dict) else {}
    entry: dict = {
        "id": name,
        "name": name,
        "sourceType": src.get("source", "") if isinstance(src, dict) else "",
        "repo": _source_summary(src) if src else _source_summary(source),
        "lastUpdated": meta.get("lastUpdated", "") if isinstance(meta, dict) else "",
        "needsRefresh": False,
        "refreshCommand": _refresh_command(name),
        "plugins": [],
        "pluginCount": 0,
        "installedCount": 0,
    }

    install_dir = _resolve_install_location(name, meta)
    manifest = _read_manifest(install_dir) if install_dir else None
    if manifest is None:
        # Manifest not cached locally — be honest, do not fetch remotely.
        entry["needsRefresh"] = True
        entry["description"] = ""
        return entry

    entry["description"] = (manifest.get("description") or "").strip()
    entry["owner"] = _author_name(manifest.get("owner"))
    cards: list[dict] = []
    for p in manifest.get("plugins", []) or []:
        card = _plugin_card(p, name, installed, enabled)
        if card:
            cards.append(card)
    cards.sort(key=lambda c: ((not c["installed"]), c["name"].lower()))
    entry["plugins"] = cards
    entry["pluginCount"] = len(cards)
    entry["installedCount"] = sum(1 for c in cards if c["installed"])
    return entry


def _matches(card: dict, needle: str) -> bool:
    if not needle:
        return True
    hay = " ".join([
        card.get("name", ""),
        card.get("description", ""),
        card.get("category", ""),
        card.get("author", ""),
        " ".join(card.get("keywords", [])),
    ]).lower()
    return needle in hay


# ───────── public GET handlers ─────────

def api_marketplace_discover(query: dict | None = None) -> dict:
    """All configured marketplaces + their advertised plugins.

    Query params (routes-style ``{key: [val]}``):
      - ``q`` : optional case-insensitive filter over plugin name/desc/category.

    Returns ``{ok, claudeCliInstalled, marketplaces:[...], counts:{...}}``.
    Degrades honestly: if no marketplaces are configured the list is empty and
    ``counts.marketplaces`` is 0; if a marketplace's manifest is not cached the
    entry carries ``needsRefresh: true`` and an empty plugin list.
    """
    q = query or {}
    needle = (q.get("q", [""])[0] if isinstance(q.get("q"), list) else q.get("q", "")) or ""
    needle = str(needle).strip().lower()

    known = _known_marketplaces()
    installed = _installed_map()
    enabled = _enabled_map()

    marketplaces: list[dict] = []
    for name in sorted(known):
        mp = _build_marketplace(name, known[name], installed, enabled)
        if needle:
            mp["plugins"] = [c for c in mp["plugins"] if _matches(c, needle)]
            mp["pluginCount"] = len(mp["plugins"])
            mp["installedCount"] = sum(1 for c in mp["plugins"] if c["installed"])
        marketplaces.append(mp)

    total_plugins = sum(m["pluginCount"] for m in marketplaces)
    total_installed = sum(m["installedCount"] for m in marketplaces)
    needs_refresh = sum(1 for m in marketplaces if m["needsRefresh"])

    return {
        "ok": True,
        "claudeCliInstalled": bool(_which("claude")),
        "query": needle,
        "marketplaces": marketplaces,
        "counts": {
            "marketplaces": len(marketplaces),
            "plugins": total_plugins,
            "installed": total_installed,
            "needsRefresh": needs_refresh,
        },
    }


def api_marketplace_browse(query: dict | None = None) -> dict:
    """One marketplace's plugin list.

    Query params:
      - ``marketplace`` : required marketplace id/name.
      - ``q``           : optional plugin filter.

    Returns ``{ok, marketplace:{...}}`` or ``{ok: False, error}`` when the
    marketplace id is unknown.
    """
    q = query or {}
    raw_mp = q.get("marketplace")
    if isinstance(raw_mp, list):
        raw_mp = raw_mp[0] if raw_mp else ""
    mp_name = (raw_mp or "").strip()
    if not mp_name:
        return {"ok": False, "error": "marketplace required", "error_key": "err_marketplace_required"}

    known = _known_marketplaces()
    if mp_name not in known:
        return {
            "ok": False,
            "error": "마켓플레이스를 찾을 수 없습니다",
            "error_key": "err_marketplace_not_found",
            "marketplace": mp_name,
        }

    needle = q.get("q")
    if isinstance(needle, list):
        needle = needle[0] if needle else ""
    needle = (needle or "").strip().lower()

    mp = _build_marketplace(mp_name, known[mp_name], _installed_map(), _enabled_map())
    if needle:
        mp["plugins"] = [c for c in mp["plugins"] if _matches(c, needle)]
        mp["pluginCount"] = len(mp["plugins"])
        mp["installedCount"] = sum(1 for c in mp["plugins"] if c["installed"])
    return {"ok": True, "claudeCliInstalled": bool(_which("claude")), "marketplace": mp}


# ───────── public POST handler ─────────

def api_marketplace_install(body: dict) -> dict:
    """Run a CURATED ``claude plugin install`` in a Terminal window.

    body: ``{name, marketplace}`` — both must reference a plugin that actually
    exists in the named marketplace's cached manifest. We rebuild the command
    server-side from the verified manifest entry rather than trusting any
    client-supplied command string, so arbitrary commands can never be run.
    Requires the ``claude`` CLI to be installed.
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body"}
    name = (body.get("name") or "").strip()
    marketplace = (body.get("marketplace") or "").strip()
    if not name or not marketplace:
        return {"ok": False, "error": "name and marketplace required",
                "error_key": "err_marketplace_install_args"}

    if not _which("claude"):
        return {"ok": False, "error": "Claude Code CLI 가 설치되어 있지 않습니다",
                "error_key": "err_claude_cli_missing"}

    known = _known_marketplaces()
    if marketplace not in known:
        return {"ok": False, "error": "마켓플레이스를 찾을 수 없습니다",
                "error_key": "err_marketplace_not_found", "marketplace": marketplace}

    # Verify the plugin is actually advertised by this marketplace's cached
    # manifest before running anything — this is what makes the command curated.
    install_dir = _resolve_install_location(marketplace, known[marketplace])
    manifest = _read_manifest(install_dir) if install_dir else None
    if manifest is None:
        return {"ok": False, "error": "마켓플레이스 매니페스트가 캐시되어 있지 않습니다 — 먼저 새로고침하세요",
                "error_key": "err_marketplace_needs_refresh",
                "refreshCommand": _refresh_command(marketplace)}
    advertised = {
        (p.get("name") or "").strip()
        for p in (manifest.get("plugins", []) or [])
        if isinstance(p, dict)
    }
    if name not in advertised:
        return {"ok": False, "error": "해당 플러그인이 이 마켓플레이스에 없습니다",
                "error_key": "err_plugin_not_in_marketplace",
                "name": name, "marketplace": marketplace}

    cmd = _install_command(name, marketplace)
    if not cmd:
        return {"ok": False, "error": "유효하지 않은 플러그인/마켓플레이스 식별자",
                "error_key": "err_marketplace_install_id_invalid"}

    r = _run_in_terminal(cmd)
    if not r.get("ok"):
        return r
    r.update({"name": name, "marketplace": marketplace, "command": cmd})
    return r
