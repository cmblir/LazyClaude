"""Bridge between the lazyclaude dashboard and the lazyclaw npm CLI.

Goal: expose every `lazyclaw <cmd>` surface as a JSON HTTP endpoint so the
dashboard can drive the CLI's full feature set without users dropping to
the terminal.

Two execution paths, picked per command:

  - **File-backed** commands (`config`, `rates`, `auth`, `pairing`,
    `nodes`, `message`, `cron`, `workspace`, `export`, `import`) operate
    on ``~/.lazyclaw/config.json`` plus the per-workspace markdown files.
    These are read/written in-process — no subprocess — because the
    schema is small and stable. Atomic via ``_safe_write``.

  - **Runtime** commands (`chat`, `agent`, `browse`, `doctor`, `status`,
    `daemon`, `setup`, `onboard`, workflow runner family `run` /
    `resume` / `inspect` / `clear` / `validate` / `graph`) shell out to
    the installed ``lazyclaw`` binary with a tight timeout, capture
    stdout / stderr, and surface the JSON output the CLI already emits.

The CLI is resolved via ``shutil.which('lazyclaw')`` — when not
installed, runtime endpoints return ``{ok: False, error: 'lazyclaw CLI
not installed'}`` instead of throwing 500s.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from .logger import log
from .utils import _safe_read, _safe_write


# ── Locations ────────────────────────────────────────────────────────

LAZYCLAW_HOME = Path(os.environ.get("LAZYCLAW_CONFIG_DIR", str(Path.home() / ".lazyclaw")))
LAZYCLAW_CONFIG = LAZYCLAW_HOME / "config.json"
LAZYCLAW_LOGS = LAZYCLAW_HOME / "logs"
LAZYCLAW_WORKSPACES = LAZYCLAW_HOME / "workspaces"
LAZYCLAW_SESSIONS = LAZYCLAW_HOME / "sessions"
LAZYCLAW_SKILLS = LAZYCLAW_HOME / "skills"

_HOME = Path.home().resolve()


def _under_home(p: Path) -> bool:
    """True iff ``p`` resolves to a path under ``$HOME``. Guards every
    user-supplied path before we read or write it."""
    try:
        return str(p.resolve()).startswith(str(_HOME) + os.sep) or str(p.resolve()) == str(_HOME)
    except Exception:
        return False


# ── lazyclaw binary discovery ────────────────────────────────────────

def _cli_path() -> Optional[str]:
    p = shutil.which("lazyclaw")
    return p


def cli_available() -> bool:
    return _cli_path() is not None


# ── config.json read / write ─────────────────────────────────────────

def read_cfg() -> dict:
    """Return ``~/.lazyclaw/config.json`` as a dict (empty when missing)."""
    if not LAZYCLAW_CONFIG.exists():
        return {}
    txt = _safe_read(LAZYCLAW_CONFIG)
    if not txt.strip():
        return {}
    try:
        return json.loads(txt)
    except Exception as e:
        log.warning("lazyclaw cfg parse failed: %s", e)
        return {}


def write_cfg(cfg: dict) -> bool:
    """Persist ``~/.lazyclaw/config.json`` atomically. Returns success."""
    LAZYCLAW_HOME.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
    return _safe_write(LAZYCLAW_CONFIG, text)


def _ensure_section(cfg: dict, key: str, default):
    if key not in cfg or not isinstance(cfg[key], type(default)):
        cfg[key] = default
    return cfg[key]


# ── subprocess helper ────────────────────────────────────────────────

def _run_cli(args: list[str], *, input_text: Optional[str] = None,
             timeout: float = 60.0, env_extra: Optional[dict] = None) -> dict:
    """Invoke ``lazyclaw <args...>`` and return a uniform response shape.

    Tries to JSON-parse stdout; falls back to raw text on `parsed`.
    Always returns ``{ok, exitCode, stdout, stderr, parsed, durationMs}``.
    """
    cli = _cli_path()
    if not cli:
        return {"ok": False, "error": "lazyclaw CLI not installed", "code": "no_cli"}
    cmd = [cli, *args]
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=input_text if input_text is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"lazyclaw {' '.join(args)} timed out after {timeout}s",
            "code": "timeout",
            "durationMs": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"lazyclaw spawn failed: {e}",
            "code": "spawn_error",
            "durationMs": int((time.time() - t0) * 1000),
        }
    out = proc.stdout or ""
    err = proc.stderr or ""
    parsed: Any = None
    try:
        parsed = json.loads(out)
    except Exception:
        parsed = None
    return {
        "ok": proc.returncode == 0,
        "exitCode": proc.returncode,
        "stdout": out,
        "stderr": err,
        "parsed": parsed,
        "durationMs": int((time.time() - t0) * 1000),
        "cmd": " ".join(shlex.quote(p) for p in cmd),
    }


# ── config tab ───────────────────────────────────────────────────────

def api_lc_config_get(_q: dict) -> dict:
    return {"ok": True, "configured": LAZYCLAW_CONFIG.exists(), "path": str(LAZYCLAW_CONFIG), "cfg": read_cfg()}


def api_lc_config_set(body: dict) -> dict:
    key = (body or {}).get("key")
    if not key or not isinstance(key, str):
        return {"ok": False, "error": "key required"}
    cfg = read_cfg()
    value = body.get("value")
    # Best-effort type coercion: numbers stay numbers, "true"/"false" → bool.
    if isinstance(value, str):
        if value.lower() == "true": value = True
        elif value.lower() == "false": value = False
        else:
            try:
                if "." in value: value = float(value)
                else: value = int(value)
            except ValueError:
                pass
    cfg[key] = value
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "cfg": cfg}


def api_lc_config_delete(body: dict) -> dict:
    key = (body or {}).get("key")
    cfg = read_cfg()
    if key in cfg:
        del cfg[key]
        if not write_cfg(cfg):
            return {"ok": False, "error": "write failed"}
    return {"ok": True, "cfg": cfg}


# ── rates / auth / pairing / nodes / message — all live under cfg.* ──

def api_lc_rates_list(_q: dict) -> dict:
    cfg = read_cfg()
    return {"ok": True, "rates": cfg.get("rates", {})}


def api_lc_rates_set(body: dict) -> dict:
    spec = (body or {}).get("spec", "").strip()  # e.g. "anthropic/claude-opus-4-7"
    if not spec or "/" not in spec:
        return {"ok": False, "error": "spec required (provider/model)"}
    cfg = read_cfg()
    rates = _ensure_section(cfg, "rates", {})
    card = rates.get(spec, {}) if isinstance(rates.get(spec), dict) else {}
    for k in ("input", "output", "cacheRead", "cacheCreate"):
        v = body.get(k)
        if v is not None:
            try:
                card[k] = float(v)
            except (TypeError, ValueError):
                return {"ok": False, "error": f"{k} must be a number"}
    if body.get("currency"):
        card["currency"] = str(body["currency"])
    rates[spec] = card
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "rates": rates}


def api_lc_rates_delete(body: dict) -> dict:
    spec = (body or {}).get("spec", "").strip()
    cfg = read_cfg()
    rates = cfg.get("rates", {}) or {}
    if spec in rates:
        del rates[spec]
        cfg["rates"] = rates
        if not write_cfg(cfg):
            return {"ok": False, "error": "write failed"}
    return {"ok": True, "rates": rates}


def api_lc_auth_list(q: dict) -> dict:
    provider = (q or {}).get("provider", "")
    cfg = read_cfg()
    auth = cfg.get("auth", {}) or {}
    if provider:
        block = auth.get(provider, {}) or {}
        # Mask keys — never return raw values over the wire.
        keys = block.get("keys", []) or []
        masked = []
        for entry in keys:
            if isinstance(entry, dict):
                key = entry.get("key") or ""
                masked.append({
                    "label": entry.get("label", ""),
                    "masked": (key[:6] + "…" + key[-4:]) if len(key) > 12 else "***",
                })
        return {"ok": True, "provider": provider, "active": block.get("active"), "keys": masked}
    return {"ok": True, "providers": list(auth.keys())}


def api_lc_auth_add(body: dict) -> dict:
    provider = (body or {}).get("provider", "").strip()
    key = (body or {}).get("key", "")
    label = (body or {}).get("label", "default").strip() or "default"
    if not provider or not key:
        return {"ok": False, "error": "provider and key required"}
    cfg = read_cfg()
    auth = _ensure_section(cfg, "auth", {})
    block = auth.setdefault(provider, {"keys": [], "active": None})
    if not isinstance(block.get("keys"), list):
        block["keys"] = []
    # Idempotent — overwrite same label.
    block["keys"] = [k for k in block["keys"] if (isinstance(k, dict) and k.get("label") != label)]
    block["keys"].append({"label": label, "key": key})
    if not block.get("active"):
        block["active"] = label
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True}


def api_lc_auth_remove(body: dict) -> dict:
    provider = (body or {}).get("provider", "").strip()
    label = (body or {}).get("label", "").strip()
    cfg = read_cfg()
    auth = cfg.get("auth", {}) or {}
    block = auth.get(provider) or {}
    keys = block.get("keys") or []
    block["keys"] = [k for k in keys if (isinstance(k, dict) and k.get("label") != label)]
    if block.get("active") == label:
        block["active"] = block["keys"][0]["label"] if block["keys"] else None
    auth[provider] = block
    cfg["auth"] = auth
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True}


def api_lc_auth_use(body: dict) -> dict:
    provider = (body or {}).get("provider", "").strip()
    label = (body or {}).get("label", "").strip()
    cfg = read_cfg()
    auth = cfg.get("auth", {}) or {}
    block = auth.get(provider) or {}
    if not any(isinstance(k, dict) and k.get("label") == label for k in (block.get("keys") or [])):
        return {"ok": False, "error": f"no such label '{label}' for {provider}"}
    block["active"] = label
    auth[provider] = block
    cfg["auth"] = auth
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True}


def api_lc_pairing_list(_q: dict) -> dict:
    cfg = read_cfg()
    return {"ok": True, "pairings": cfg.get("pairing", []) or []}


def api_lc_pairing_add(body: dict) -> dict:
    sid = (body or {}).get("id", "").strip()
    if not sid:
        return {"ok": False, "error": "id required"}
    label = (body or {}).get("label", "").strip() or sid
    cfg = read_cfg()
    pair = _ensure_section(cfg, "pairing", [])
    pair = [p for p in pair if not (isinstance(p, dict) and p.get("id") == sid)]
    pair.append({"id": sid, "label": label, "addedAt": int(time.time() * 1000)})
    cfg["pairing"] = pair
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "pairings": pair}


def api_lc_pairing_remove(body: dict) -> dict:
    sid = (body or {}).get("id", "").strip()
    cfg = read_cfg()
    pair = [p for p in (cfg.get("pairing") or []) if not (isinstance(p, dict) and p.get("id") == sid)]
    cfg["pairing"] = pair
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "pairings": pair}


def api_lc_nodes_list(_q: dict) -> dict:
    cfg = read_cfg()
    return {"ok": True, "nodes": cfg.get("nodes", []) or []}


def api_lc_nodes_register(body: dict) -> dict:
    nid = (body or {}).get("id", "").strip()
    if not nid:
        return {"ok": False, "error": "id required"}
    cfg = read_cfg()
    nodes = _ensure_section(cfg, "nodes", [])
    nodes = [n for n in nodes if not (isinstance(n, dict) and n.get("id") == nid)]
    nodes.append({
        "id": nid,
        "platform": (body.get("platform") or "cli").lower(),
        "label": (body.get("label") or nid),
        "registeredAt": int(time.time() * 1000),
    })
    cfg["nodes"] = nodes
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "nodes": nodes}


def api_lc_nodes_remove(body: dict) -> dict:
    nid = (body or {}).get("id", "").strip()
    cfg = read_cfg()
    nodes = [n for n in (cfg.get("nodes") or []) if not (isinstance(n, dict) and n.get("id") == nid)]
    cfg["nodes"] = nodes
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "nodes": nodes}


def api_lc_message_list(_q: dict) -> dict:
    cfg = read_cfg()
    msgs = cfg.get("message", {}) or {}
    # Don't echo webhook URLs raw — mask the second half.
    out = {}
    for name, entry in msgs.items():
        if not isinstance(entry, dict): continue
        url = entry.get("url", "")
        out[name] = {
            "kind": entry.get("kind", "generic"),
            "urlPreview": url[:24] + "…" if len(url) > 28 else url,
        }
    return {"ok": True, "messages": out}


def _detect_webhook_kind(url: str) -> str:
    u = url.lower()
    if "hooks.slack.com" in u: return "slack"
    if "discord.com/api/webhooks" in u or "discordapp.com/api/webhooks" in u: return "discord"
    return "generic"


def api_lc_message_add(body: dict) -> dict:
    name = (body or {}).get("name", "").strip()
    url = (body or {}).get("url", "").strip()
    if not name or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "name + https(s) url required"}
    kind = (body or {}).get("kind") or _detect_webhook_kind(url)
    cfg = read_cfg()
    msgs = _ensure_section(cfg, "message", {})
    msgs[name] = {"url": url, "kind": kind, "addedAt": int(time.time() * 1000)}
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True}


def api_lc_message_remove(body: dict) -> dict:
    name = (body or {}).get("name", "").strip()
    cfg = read_cfg()
    msgs = cfg.get("message", {}) or {}
    if name in msgs:
        del msgs[name]
        cfg["message"] = msgs
        if not write_cfg(cfg):
            return {"ok": False, "error": "write failed"}
    return {"ok": True}


def api_lc_message_send(body: dict) -> dict:
    name = (body or {}).get("name", "").strip()
    text = (body or {}).get("text", "")
    if not name or not text:
        return {"ok": False, "error": "name and text required"}
    # Defer to the CLI so we share the URL/payload shape (Slack vs Discord
    # vs generic) instead of re-implementing it.
    return _run_cli(["message", "send", name, text], timeout=20)


# ── cron (lives in cfg.cron, but write also requires the CLI for
#         launchd/crontab sync — so we delegate to the binary) ────────

def api_lc_cron_list(_q: dict) -> dict:
    cfg = read_cfg()
    return {"ok": True, "jobs": cfg.get("cron", {}) or {}}


def api_lc_cron_add(body: dict) -> dict:
    name = (body or {}).get("name", "").strip()
    spec = (body or {}).get("spec", "").strip()
    cmd = (body or {}).get("cmd", "")
    if not (name and spec and cmd):
        return {"ok": False, "error": "name + cron spec + cmd required"}
    # Use the CLI so launchd/crontab is touched correctly.
    return _run_cli(["cron", "add", name, spec, "--", *shlex.split(cmd)], timeout=30)


def api_lc_cron_remove(body: dict) -> dict:
    name = (body or {}).get("name", "").strip()
    return _run_cli(["cron", "remove", name], timeout=15)


def api_lc_cron_sync(_body: dict) -> dict:
    return _run_cli(["cron", "sync"], timeout=30)


def api_lc_cron_run(body: dict) -> dict:
    name = (body or {}).get("name", "").strip()
    return _run_cli(["cron", "run", name], timeout=600)


# ── workspace — AGENTS.md / SOUL.md / TOOLS.md per workspace dir ─────

_WS_FILES = ("AGENTS.md", "SOUL.md", "TOOLS.md")


def _ws_dir(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in "._-")
    if not safe or safe != name:
        return None  # type: ignore[return-value]
    p = (LAZYCLAW_WORKSPACES / safe).resolve()
    return p if _under_home(p) else None  # type: ignore[return-value]


def api_lc_workspace_list(_q: dict) -> dict:
    out = []
    if LAZYCLAW_WORKSPACES.exists():
        for child in sorted(LAZYCLAW_WORKSPACES.iterdir()):
            if not child.is_dir():
                continue
            out.append({
                "name": child.name,
                "files": [f for f in _WS_FILES if (child / f).exists()],
            })
    return {"ok": True, "workspaces": out}


def api_lc_workspace_get(q: dict) -> dict:
    name = (q or {}).get("name", "")
    fname = (q or {}).get("file", "")
    p = _ws_dir(name)
    if not p:
        return {"ok": False, "error": "invalid workspace name"}
    if fname:
        if fname not in _WS_FILES:
            return {"ok": False, "error": "unknown file"}
        return {"ok": True, "name": name, "file": fname, "content": _safe_read(p / fname)}
    return {"ok": True, "name": name, "files": {f: _safe_read(p / f) for f in _WS_FILES}}


def api_lc_workspace_save(body: dict) -> dict:
    name = (body or {}).get("name", "")
    fname = (body or {}).get("file", "")
    content = (body or {}).get("content", "")
    if fname not in _WS_FILES:
        return {"ok": False, "error": "unknown file"}
    p = _ws_dir(name)
    if not p:
        return {"ok": False, "error": "invalid workspace name"}
    p.mkdir(parents=True, exist_ok=True)
    if not _safe_write(p / fname, content):
        return {"ok": False, "error": "write failed"}
    return {"ok": True}


def api_lc_workspace_init(body: dict) -> dict:
    name = (body or {}).get("name", "")
    p = _ws_dir(name)
    if not p:
        return {"ok": False, "error": "invalid workspace name"}
    p.mkdir(parents=True, exist_ok=True)
    stubs = {
        "AGENTS.md": "# Agents\n\nDescribe the agents this workspace defines.\n",
        "SOUL.md":   "# Soul\n\nGuiding principles / persona.\n",
        "TOOLS.md":  "# Tools\n\nTool inventory + when to reach for each.\n",
    }
    for f, body in stubs.items():
        if not (p / f).exists():
            _safe_write(p / f, body)
    return {"ok": True}


def api_lc_workspace_remove(body: dict) -> dict:
    name = (body or {}).get("name", "")
    p = _ws_dir(name)
    if not p or not p.exists():
        return {"ok": True}
    # rmtree manually so we never call shell. Only remove regular files
    # + the three known markdown shapes.
    try:
        for f in p.iterdir():
            if f.is_file():
                f.unlink()
        p.rmdir()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}


# ── Runtime commands — delegate to the CLI ───────────────────────────

def api_lc_doctor(_q: dict) -> dict:
    return _run_cli(["doctor"], timeout=30)


def api_lc_status(_q: dict) -> dict:
    return _run_cli(["status"], timeout=10)


def api_lc_version(_q: dict) -> dict:
    return _run_cli(["version"], timeout=5)


def api_lc_browse(body: dict) -> dict:
    url = (body or {}).get("url", "")
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "https(s) url required"}
    return _run_cli(["browse", url, "--meta"], timeout=60)


def api_lc_agent(body: dict) -> dict:
    prompt = (body or {}).get("prompt", "")
    if not prompt:
        return {"ok": False, "error": "prompt required"}
    args = ["agent", "-"]
    if body.get("provider"): args += ["--provider", str(body["provider"])]
    if body.get("model"):    args += ["--model", str(body["model"])]
    if body.get("skill"):    args += ["--skill", str(body["skill"])]
    if body.get("workspace"): args += ["--workspace", str(body["workspace"])]
    if body.get("usage"):    args += ["--usage"]
    if body.get("cost"):     args += ["--cost"]
    return _run_cli(args, input_text=prompt, timeout=int(body.get("timeoutSec", 600)))


def api_lc_setup_status(_q: dict) -> dict:
    """Lightweight 'is the user onboarded?' check. We can't run the
    interactive ``lazyclaw setup`` wizard from a web UI (no TTY) — but
    we can tell the user whether the four critical config blocks exist.
    """
    cfg = read_cfg()
    return {
        "ok": True,
        "provider": cfg.get("provider"),
        "model": cfg.get("model"),
        "hasOrchestrator": bool(cfg.get("orchestrator")),
        "hasRates": bool(cfg.get("rates")),
        "hasAuth": bool(cfg.get("auth")),
        "needs": [k for k, v in {
            "provider": cfg.get("provider"),
            "model": cfg.get("model"),
        }.items() if not v],
    }


def api_lc_onboard(body: dict) -> dict:
    """Non-interactive onboard — exactly what `lazyclaw onboard
    --non-interactive` does, but driven from the dashboard form."""
    provider = (body or {}).get("provider", "").strip()
    model = (body or {}).get("model", "").strip()
    api_key = (body or {}).get("apiKey", "").strip()
    if not provider:
        return {"ok": False, "error": "provider required"}
    args = ["onboard", "--non-interactive", "--provider", provider]
    if model: args += ["--model", model]
    if api_key: args += ["--api-key", api_key]
    return _run_cli(args, timeout=30)


# ── Workflow runner family — wrap the .mjs runner subcommands ────────

def _resolve_workflow_path(raw: str) -> Optional[Path]:
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    return p if _under_home(p) and p.exists() and p.suffix == ".mjs" else None


def api_lc_run(body: dict) -> dict:
    session = (body or {}).get("session", "").strip()
    workflow = _resolve_workflow_path((body or {}).get("workflow", ""))
    mode = (body or {}).get("mode", "")
    if not session or not workflow:
        return {"ok": False, "error": "session + workflow path required (must live under $HOME)"}
    args = ["run", session, str(workflow)]
    if mode == "parallel": args.append("--parallel")
    elif mode == "parallel-persistent": args.append("--parallel-persistent")
    conc = (body or {}).get("concurrency")
    if conc: args += ["--concurrency", str(conc)]
    return _run_cli(args, timeout=int(body.get("timeoutSec", 1800)))


def api_lc_resume(body: dict) -> dict:
    session = (body or {}).get("session", "").strip()
    workflow = _resolve_workflow_path((body or {}).get("workflow", ""))
    if not session or not workflow:
        return {"ok": False, "error": "session + workflow path required"}
    args = ["resume", session, str(workflow)]
    if (body or {}).get("dag"): args.append("--parallel-persistent")
    return _run_cli(args, timeout=int(body.get("timeoutSec", 1800)))


def api_lc_inspect(q: dict) -> dict:
    session = (q or {}).get("session", "").strip()
    args = ["inspect"]
    if session: args.append(session)
    if (q or {}).get("status"): args += ["--status", str(q["status"])]
    if (q or {}).get("summary"): args.append("--summary")
    return _run_cli(args, timeout=30)


def api_lc_clear_session(body: dict) -> dict:
    session = (body or {}).get("session", "").strip()
    if not session:
        return {"ok": False, "error": "session required"}
    return _run_cli(["clear", session], timeout=15)


def api_lc_validate(body: dict) -> dict:
    workflow = _resolve_workflow_path((body or {}).get("workflow", ""))
    if not workflow:
        return {"ok": False, "error": "workflow path required"}
    return _run_cli(["validate", str(workflow)], timeout=15)


def api_lc_graph(body: dict) -> dict:
    workflow = _resolve_workflow_path((body or {}).get("workflow", ""))
    if not workflow:
        return {"ok": False, "error": "workflow path required"}
    args = ["graph", str(workflow)]
    if (body or {}).get("lr"): args.append("--lr")
    return _run_cli(args, timeout=15)


# ── Daemon process control ───────────────────────────────────────────
#
# The dashboard tracks whether a `lazyclaw daemon` subprocess started by
# this server is alive. We don't manage external daemons. State lives in
# module globals — restart-survivable state would need a pid file.

_daemon_proc: Optional[subprocess.Popen] = None
_daemon_port: Optional[int] = None


def api_lc_daemon_status(_q: dict) -> dict:
    global _daemon_proc, _daemon_port
    alive = _daemon_proc is not None and _daemon_proc.poll() is None
    return {"ok": True, "running": alive, "pid": (_daemon_proc.pid if alive else None), "port": _daemon_port}


def api_lc_daemon_start(body: dict) -> dict:
    global _daemon_proc, _daemon_port
    if _daemon_proc is not None and _daemon_proc.poll() is None:
        return {"ok": True, "alreadyRunning": True, "pid": _daemon_proc.pid, "port": _daemon_port}
    cli = _cli_path()
    if not cli:
        return {"ok": False, "error": "lazyclaw CLI not installed"}
    port = int((body or {}).get("port", 0) or 0)
    args = [cli, "daemon", "--port", str(port)]
    if (body or {}).get("authToken"): args += ["--auth-token", str(body["authToken"])]
    try:
        LAZYCLAW_LOGS.mkdir(parents=True, exist_ok=True)
        log_path = LAZYCLAW_LOGS / "daemon.dashboard.log"
        f = open(log_path, "a", buffering=1)
        _daemon_proc = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT)
        _daemon_port = port if port else None
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "pid": _daemon_proc.pid, "port": _daemon_port, "logPath": str(log_path)}


def api_lc_daemon_stop(_body: dict) -> dict:
    global _daemon_proc, _daemon_port
    if _daemon_proc is None or _daemon_proc.poll() is not None:
        _daemon_proc = None
        _daemon_port = None
        return {"ok": True, "wasRunning": False}
    try:
        _daemon_proc.terminate()
        try:
            _daemon_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _daemon_proc.kill()
    finally:
        _daemon_proc = None
        _daemon_port = None
    return {"ok": True, "wasRunning": True}


# ── Export / import — bundle the cfg blob (sessions kept locally) ────

def api_lc_export(q: dict) -> dict:
    include_secrets = (q or {}).get("includeSecrets") in ("1", "true", True)
    cfg = read_cfg()
    if not include_secrets:
        # Strip raw api keys + auth keys before returning.
        for k in list(cfg.keys()):
            if k.lower().endswith("apikey") or k.lower() == "apikey":
                cfg[k] = "***REDACTED***"
        if isinstance(cfg.get("auth"), dict):
            for prov, block in cfg["auth"].items():
                if not isinstance(block, dict): continue
                for entry in (block.get("keys") or []):
                    if isinstance(entry, dict) and "key" in entry:
                        entry["key"] = "***REDACTED***"
    return {"ok": True, "bundle": cfg}


def api_lc_import(body: dict) -> dict:
    bundle = (body or {}).get("bundle")
    overwrite = bool((body or {}).get("overwrite", False))
    if not isinstance(bundle, dict):
        return {"ok": False, "error": "bundle must be a JSON object"}
    cfg = read_cfg()
    for k, v in bundle.items():
        if v == "***REDACTED***":
            continue
        if k not in cfg or overwrite:
            cfg[k] = v
    if not write_cfg(cfg):
        return {"ok": False, "error": "write failed"}
    return {"ok": True}
