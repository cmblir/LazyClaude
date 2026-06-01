"""Context Window Inspector — the dashboard's own ``/context``.

Estimates how the LATEST turn of a Claude Code session fills the model's
context window, broken down by category:

  - system prompt        (estimated — not stored verbatim in the JSONL)
  - tool definitions     (estimated from the distinct tools the turn used)
  - MCP server tools     (estimated from ~/.claude.json mcpServers config)
  - CLAUDE.md / memory   (measured by chars/4 over the real files on disk)
  - conversation history (the remainder of the real prompt-token total)
  - free space           (context window minus used)

GROUND TRUTH vs ESTIMATE
------------------------
Claude Code's session JSONL does NOT contain the system prompt or the tool
schema definitions — those are injected by the CLI at request time and never
written to disk. What IS recorded, per assistant turn, is ``message.usage``
with ``input_tokens`` + ``cache_read_input_tokens`` +
``cache_creation_input_tokens``. The SUM of those three is the real number of
prompt tokens the model saw that turn, i.e. the true "used context". We anchor
on that real total and estimate only how it splits across the static
categories. ``conversation history`` is computed as the residual so the parts
always sum to the measured total.

This module is strictly READ-ONLY. It reads session JSONL transcripts,
``~/.claude.json``, the project + global ``CLAUDE.md`` and any imported memory
files, and the model catalogue in ``ai_providers``. It writes nothing and
touches no shared module. If a data source is missing it degrades to a clear,
honest empty state rather than fabricating numbers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .config import (
    CLAUDE_HOME,
    CLAUDE_JSON,
    CLAUDE_MD,
    PROJECTS_DIR,
    _cwd_to_slug,
)
from .logger import log

# ── token estimation constants ────────────────────────────────────────────
# Chars-per-token heuristic for static text (matches the cost_timeline /
# sessions chars/4 convention used elsewhere in this codebase).
_CHARS_PER_TOKEN = 4

# A bare Claude Code system prompt (identity, behavioural rules, environment
# block, no tools, no memory) is on the order of a few thousand tokens. This is
# a fixed baseline estimate; the JSONL never stores it verbatim so it cannot be
# measured. Documented in the returned `note`.
_SYSTEM_PROMPT_BASE_TOKENS = 2_800

# Rough per-tool definition cost. A built-in tool schema (name + description +
# JSON-schema input) lands in the ~400–700 token range; 550 is a mid estimate.
# Used only for tools whose schema we cannot read (i.e. all of them — schemas
# are not on disk), so this is explicitly an estimate.
_TOKENS_PER_BUILTIN_TOOL = 550

# MCP tools tend to carry larger descriptions / schemas than built-ins.
_TOKENS_PER_MCP_TOOL = 700

# When a server's tool count is unknown we assume this many tools per MCP
# server for the estimate.
_ASSUMED_TOOLS_PER_MCP_SERVER = 8

# Cap on how many JSONL lines we scan from the tail when looking for the last
# assistant usage block (these files can be tens of MB).
_TAIL_SCAN_BYTES = 4_000_000


def _model_catalog() -> dict:
    """Return ``{model_id: ModelInfo}`` from the Claude CLI provider catalogue.

    Read-only access to ``ai_providers``. Falls back to an empty dict if the
    import fails for any reason (keeps this module independently importable).
    """
    try:
        from .ai_providers import ClaudeCliProvider

        return {m.id: m for m in ClaudeCliProvider._MODELS}
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("context_inspector: model catalog unavailable: %s", exc)
        return {}


def _resolve_context_window(model: str) -> tuple[int, str]:
    """Map a session's model string to (context_window, normalized_id).

    Handles dated/snapshot ids (``claude-haiku-4-5-20251001``) by prefix match
    against the catalogue. Falls back to a conservative 200k window for unknown
    models so a missing entry never reports an absurd amount of "free" space.
    """
    catalog = _model_catalog()
    if not model:
        return 200_000, ""
    # Exact id match first.
    info = catalog.get(model)
    if info:
        return int(info.context_window or 200_000), info.id
    # Prefix match for dated snapshots (e.g. claude-haiku-4-5-20251001).
    for mid, mi in catalog.items():
        if model.startswith(mid):
            return int(mi.context_window or 200_000), mi.id
    # Heuristic fallback by family keyword.
    low = model.lower()
    if "opus" in low or "sonnet" in low:
        return 1_000_000, model
    return 200_000, model


def _est_tokens_from_text(text: str) -> int:
    """chars/4 token estimate for a static text blob."""
    if not text:
        return 0
    return max(0, len(text) // _CHARS_PER_TOKEN)


def _read_text_safe(p: Path, limit: int = 2_000_000) -> str:
    try:
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        pass
    return ""


def _collect_memory_files(cwd: str) -> tuple[int, list[dict]]:
    """Estimate CLAUDE.md / memory file tokens for the given working dir.

    Reads (READ-ONLY):
      - global ~/.claude/CLAUDE.md
      - project <cwd>/CLAUDE.md and <cwd>/.claude/CLAUDE.md if present
      - any @import-referenced *.md in the global CLAUDE.md that resolve under
        ~/.claude (e.g. RTK.md) — one level deep only, to avoid surprises.

    Returns (total_tokens, [{path, tokens}]).
    """
    files: list[dict] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        rp = str(p)
        if rp in seen:
            return
        seen.add(rp)
        txt = _read_text_safe(p)
        if not txt:
            return
        files.append({"path": rp, "tokens": _est_tokens_from_text(txt)})

    # Global memory.
    global_md = _read_text_safe(CLAUDE_MD)
    if global_md:
        _add(CLAUDE_MD)
        # One level of @import resolution against ~/.claude (e.g. "@RTK.md").
        for line in global_md.splitlines():
            line = line.strip()
            if line.startswith("@") and line[1:].endswith(".md"):
                ref = (CLAUDE_HOME / line[1:]).resolve()
                try:
                    if CLAUDE_HOME in ref.parents or ref.parent == CLAUDE_HOME:
                        _add(ref)
                except Exception:
                    pass

    # Project memory.
    if cwd:
        cwd_path = Path(cwd)
        _add(cwd_path / "CLAUDE.md")
        _add(cwd_path / ".claude" / "CLAUDE.md")

    total = sum(f["tokens"] for f in files)
    return total, files


def _load_claude_json() -> dict:
    """Parse ~/.claude.json READ-ONLY. Returns {} on any failure."""
    try:
        if CLAUDE_JSON.is_file():
            return json.loads(CLAUDE_JSON.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        log.warning("context_inspector: ~/.claude.json parse failed: %s", exc)
    return {}


def _mcp_server_names(cwd: str) -> list[str]:
    """Distinct MCP server names active for the given cwd (global + project)."""
    cfg = _load_claude_json()
    names: set[str] = set()
    g = cfg.get("mcpServers")
    if isinstance(g, dict):
        names.update(k for k in g.keys() if isinstance(k, str))
    projects = cfg.get("projects")
    if cwd and isinstance(projects, dict):
        entry = projects.get(cwd)
        if isinstance(entry, dict):
            pm = entry.get("mcpServers")
            if isinstance(pm, dict):
                names.update(k for k in pm.keys() if isinstance(k, str))
    return sorted(names)


def _find_session_jsonl(
    cwd: Optional[str], session_id: Optional[str]
) -> Optional[Path]:
    """Resolve which session JSONL to inspect.

    Priority:
      1. explicit session_id  -> first matching <id>.jsonl under any project
      2. explicit cwd         -> most-recently-modified jsonl in that project slug
      3. default              -> globally most-recently-modified session jsonl
    """
    if not PROJECTS_DIR.is_dir():
        return None

    if session_id:
        # Constrain the name to a filename component (no path traversal).
        safe = Path(session_id).name
        for proj in PROJECTS_DIR.iterdir():
            if not proj.is_dir():
                continue
            cand = proj / f"{safe}.jsonl"
            if cand.is_file():
                return cand
        return None

    candidates: list[Path] = []
    if cwd:
        slug = _cwd_to_slug(Path(cwd))
        proj_dir = PROJECTS_DIR / slug
        if proj_dir.is_dir():
            candidates = list(proj_dir.glob("*.jsonl"))
        if not candidates:
            return None
    else:
        for proj in PROJECTS_DIR.iterdir():
            if proj.is_dir():
                candidates.extend(proj.glob("*.jsonl"))

    if not candidates:
        return None
    try:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    except Exception:
        return candidates[0]


def _parse_session(jsonl: Path) -> dict:
    """Single READ-ONLY pass over a session JSONL.

    Extracts, for the LATEST assistant turn that carries ``message.usage``:
      - usage breakdown (input / cache_read / cache_create / output)
      - the model id of that turn
    Plus, across the whole transcript:
      - cwd
      - distinct tool names used (built-in vs mcp__ prefixed)

    Streams line-by-line so multi-MB transcripts stay memory-bounded.
    """
    cwd = ""
    last_usage: Optional[dict] = None
    last_model = ""
    builtin_tools: set[str] = set()
    mcp_tools: set[str] = set()

    try:
        with jsonl.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    m = json.loads(raw)
                except Exception:
                    continue
                if not cwd:
                    c_val = m.get("cwd")
                    if isinstance(c_val, str) and c_val:
                        cwd = c_val
                if m.get("type") != "assistant":
                    continue
                msg = m.get("message") or {}
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            name = b.get("name") or ""
                            if not name:
                                continue
                            if name.startswith("mcp__"):
                                mcp_tools.add(name)
                            else:
                                builtin_tools.add(name)
                usage = msg.get("usage")
                if isinstance(usage, dict) and (
                    usage.get("input_tokens")
                    or usage.get("cache_read_input_tokens")
                    or usage.get("cache_creation_input_tokens")
                ):
                    last_usage = usage
                    model_val = msg.get("model")
                    if isinstance(model_val, str) and model_val:
                        last_model = model_val
    except Exception as exc:
        log.warning("context_inspector: failed to parse %s: %s", jsonl, exc)

    return {
        "cwd": cwd,
        "usage": last_usage,
        "model": last_model,
        "builtinTools": sorted(builtin_tools),
        "mcpTools": sorted(mcp_tools),
    }


def _empty_result(note: str, session_id: str = "", cwd: str = "") -> dict:
    """Honest empty/unsupported state — no fabricated numbers."""
    return {
        "ok": True,
        "model": "",
        "contextWindow": 0,
        "used": 0,
        "free": 0,
        "byCategory": [],
        "sessionId": session_id,
        "cwd": cwd,
        "note": note,
    }


def api_context_inspect(query: dict) -> dict:
    """Estimate the latest turn's context composition for a session.

    Query params (routes ``{key: [value]}`` shape):
      - ``session_id`` : inspect a specific session by id
      - ``cwd``        : inspect the most recent session of a project
      (neither) -> globally most-recently-modified session

    Returns::

        {
          ok, model, contextWindow, used, free,
          byCategory: [{name, tokens, pct}, ...],
          sessionId, cwd, note
        }

    ``pct`` is each category's share of the full context window (0–100),
    so the donut/bar segments + free space sum to ~100%.
    """
    session_id = (query.get("session_id", [""])[0] or "").strip()
    cwd_q = (query.get("cwd", [""])[0] or "").strip()

    jsonl = _find_session_jsonl(cwd_q or None, session_id or None)
    if jsonl is None:
        if not PROJECTS_DIR.is_dir():
            return _empty_result(
                "~/.claude/projects not found — no Claude Code sessions on this "
                "machine to inspect.",
                session_id,
                cwd_q,
            )
        return _empty_result(
            "No matching session found. Pick a session, or run a Claude Code "
            "session in this project first.",
            session_id,
            cwd_q,
        )

    parsed = _parse_session(jsonl)
    resolved_session_id = jsonl.stem
    cwd = parsed["cwd"] or cwd_q
    raw_model = parsed["model"]
    usage = parsed["usage"]

    context_window, model_id = _resolve_context_window(raw_model)

    if not usage:
        # The session has no assistant turn with usage yet (brand-new session,
        # or a transcript that only holds user prompts). Report honestly.
        return {
            "ok": True,
            "model": model_id or raw_model,
            "contextWindow": context_window,
            "used": 0,
            "free": context_window,
            "byCategory": [
                {"name": "free space", "tokens": context_window, "pct": 100.0}
            ],
            "sessionId": resolved_session_id,
            "cwd": cwd,
            "note": (
                "This session has no assistant turn with token usage yet, so "
                "there is nothing to measure. Showing the empty window for "
                f"{model_id or raw_model or 'the detected model'}."
            ),
        }

    # ── REAL total used (ground truth from message.usage) ──────────────────
    u_in = int(usage.get("input_tokens") or 0)
    u_cache_read = int(usage.get("cache_read_input_tokens") or 0)
    u_cache_create = int(usage.get("cache_creation_input_tokens") or 0)
    used = u_in + u_cache_read + u_cache_create
    used = min(used, context_window)  # never report > window
    free = max(0, context_window - used)

    # ── ESTIMATED static parts ─────────────────────────────────────────────
    system_prompt_tokens = _SYSTEM_PROMPT_BASE_TOKENS

    builtin_tools = parsed["builtinTools"]
    tool_def_tokens = len(builtin_tools) * _TOKENS_PER_BUILTIN_TOOL

    # MCP tools: prefer the count actually observed in the transcript; if none
    # were called, fall back to the configured servers × assumed tools/server.
    observed_mcp = parsed["mcpTools"]
    mcp_servers = _mcp_server_names(cwd)
    if observed_mcp:
        mcp_tool_tokens = len(observed_mcp) * _TOKENS_PER_MCP_TOOL
        mcp_detail = {"servers": mcp_servers, "observedTools": len(observed_mcp)}
    elif mcp_servers:
        mcp_tool_tokens = (
            len(mcp_servers) * _ASSUMED_TOOLS_PER_MCP_SERVER * _TOKENS_PER_MCP_TOOL
        )
        mcp_detail = {
            "servers": mcp_servers,
            "assumedToolsPerServer": _ASSUMED_TOOLS_PER_MCP_SERVER,
        }
    else:
        mcp_tool_tokens = 0
        mcp_detail = {"servers": []}

    memory_tokens, memory_files = _collect_memory_files(cwd)

    # ── conversation history = residual so parts sum to the measured total ──
    static_sum = (
        system_prompt_tokens + tool_def_tokens + mcp_tool_tokens + memory_tokens
    )
    if static_sum > used:
        # Static estimate exceeds the real measured total (common when the turn
        # is small / heavily cached). Scale the static parts down proportionally
        # so they never overflow the real `used`, and leave 0 for history.
        scale = used / static_sum if static_sum else 0.0
        system_prompt_tokens = int(system_prompt_tokens * scale)
        tool_def_tokens = int(tool_def_tokens * scale)
        mcp_tool_tokens = int(mcp_tool_tokens * scale)
        memory_tokens = int(memory_tokens * scale)
        history_tokens = max(
            0,
            used
            - (system_prompt_tokens + tool_def_tokens + mcp_tool_tokens + memory_tokens),
        )
        scaled_note = (
            " Static estimates exceeded the measured total for this (likely "
            "small/cached) turn and were scaled down proportionally."
        )
    else:
        history_tokens = used - static_sum
        scaled_note = ""

    def _pct(tokens: int) -> float:
        if context_window <= 0:
            return 0.0
        return round(tokens / context_window * 100, 1)

    by_category = [
        {
            "name": "system prompt",
            "tokens": system_prompt_tokens,
            "pct": _pct(system_prompt_tokens),
            "estimated": True,
        },
        {
            "name": "tool definitions",
            "tokens": tool_def_tokens,
            "pct": _pct(tool_def_tokens),
            "estimated": True,
            "detail": {"tools": builtin_tools},
        },
        {
            "name": "MCP server tools",
            "tokens": mcp_tool_tokens,
            "pct": _pct(mcp_tool_tokens),
            "estimated": True,
            "detail": mcp_detail,
        },
        {
            "name": "CLAUDE.md / memory",
            "tokens": memory_tokens,
            "pct": _pct(memory_tokens),
            "estimated": True,
            "detail": {"files": memory_files},
        },
        {
            "name": "conversation history",
            "tokens": history_tokens,
            "pct": _pct(history_tokens),
            "estimated": False,
        },
        {
            "name": "free space",
            "tokens": free,
            "pct": _pct(free),
            "estimated": False,
        },
    ]
    # Drop zero-token estimated rows except the always-present categories so the
    # chart stays readable, but keep system prompt / history / free always.
    by_category = [
        c
        for c in by_category
        if c["tokens"] > 0
        or c["name"] in ("system prompt", "conversation history", "free space")
    ]

    note = (
        "Total used is REAL (message.usage: input + cache_read + cache_create "
        "for the latest assistant turn). System prompt, tool definitions, and "
        "MCP tools are ESTIMATES — Claude Code does not store those in the "
        "transcript. CLAUDE.md / memory is measured by chars/4 over the files "
        "on disk. 'conversation history' is the residual so the parts sum to "
        "the measured total." + scaled_note
    )

    return {
        "ok": True,
        "model": model_id or raw_model,
        "contextWindow": context_window,
        "used": used,
        "free": free,
        "usageBreakdown": {
            "input": u_in,
            "cacheRead": u_cache_read,
            "cacheCreate": u_cache_create,
            "output": int(usage.get("output_tokens") or 0),
        },
        "byCategory": by_category,
        "sessionId": resolved_session_id,
        "cwd": cwd,
        "note": note,
    }


def api_context_sessions(query: dict) -> dict:
    """Lightweight session picker for the inspector UI (READ-ONLY).

    Lists recent session JSONL files (id, cwd-derived project name, mtime),
    most-recent first, so the tab can offer a dropdown without depending on the
    SQLite index being warm. Capped to keep the response small.
    """
    try:
        limit = int(query.get("limit", ["50"])[0])
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(200, limit))

    if not PROJECTS_DIR.is_dir():
        return {"ok": True, "sessions": [], "note": "~/.claude/projects not found."}

    rows: list[dict] = []
    home_slug = _cwd_to_slug(Path.home())
    for proj in PROJECTS_DIR.iterdir():
        if not proj.is_dir():
            continue
        proj_dir = proj.name
        if proj_dir.startswith(home_slug + "-"):
            project_name = proj_dir[len(home_slug) + 1 :].replace("-", "/")
        else:
            project_name = proj_dir.lstrip("-").replace("-", "/")
        for jsonl in proj.glob("*.jsonl"):
            try:
                mtime = int(jsonl.stat().st_mtime * 1000)
            except Exception:
                mtime = 0
            rows.append(
                {
                    "sessionId": jsonl.stem,
                    "project": project_name,
                    "projectDir": proj_dir,
                    "mtime": mtime,
                }
            )

    rows.sort(key=lambda r: r["mtime"], reverse=True)
    return {"ok": True, "sessions": rows[:limit]}
