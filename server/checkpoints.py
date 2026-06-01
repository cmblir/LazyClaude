"""Checkpoints & Rewind Explorer — read-only view of Claude Code's per-prompt
file snapshots (the data behind ``/rewind`` and double-``Esc``).

What Claude Code stores on disk (verified 2026-06-01 against
https://code.claude.com/docs/en/checkpointing and a live ``~/.claude`` inspection):

* Every user prompt creates a checkpoint. Claude Code captures the *before*
  state of any file edited via its file-editing tools (Write/Edit/MultiEdit/
  NotebookEdit). Bash side-effects and external edits are NOT tracked.
* Snapshots live in two correlated places:
  - ``~/.claude/file-history/<session_uuid>/<sha256(abspath)[:16]>@v<N>`` — the
    raw file contents of each backed-up version (plain file bytes, no wrapper).
  - The session transcript ``~/.claude/projects/<slug>/<session>.jsonl`` carries
    ``{"type":"file-history-snapshot","messageId":...,"isSnapshotUpdate":bool,
    "snapshot":{"trackedFileBackups":{<relOrAbsPath>:{"backupFileName":
    "<hash>@vN"|null,"version":N,"backupTime":ISO}}}}`` entries. ``backupFileName``
    is the authoritative on-disk basename inside the ``file-history`` dir.
* Retention: cleaned up together with the session after ~30 days (configurable),
  so older sessions may have a transcript but no surviving ``file-history`` dir.

This module never writes or restores anything — it reconstructs a per-prompt
timeline (timestamp, prompt preview, files touched, whether the backups are
still present on disk so a rewind would be possible). Actual rewind happens
inside the Claude Code CLI via ``/rewind``; this is an explorer, not a restorer.

stdlib only. Read-only.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import CLAUDE_HOME, PROJECTS_DIR, _cwd_to_slug
from .logger import log

# ───────── 경로 ─────────
# Claude Code persists per-prompt file backups here, keyed by session UUID.
# Mirrors server/system.py::FILE_HISTORY_DIR (kept local to avoid cross-module
# coupling — this module owns only its own file).
FILE_HISTORY_DIR = CLAUDE_HOME / "file-history"

# How long Claude Code keeps checkpoints by default (docs: ~30 days, configurable).
_RETENTION_DAYS = 30

# User-turn wrappers that are not genuine human prompts (slash commands, local
# command echoes, task-notification injections, hook reminders). Anything whose
# trimmed text starts with one of these is treated as machinery, not a prompt.
_SYNTHETIC_PREFIXES = (
    "<command-name>",
    "<command-message>",
    "<local-command",
    "<bash-input>",
    "<bash-stdout>",
    "<bash-stderr>",
    "<system-reminder",
    "<task-notification>",
    "<task-",
    "<user-prompt-submit",
    "Caveat: The messages below",
    "<local-command-caveat>",
)

# File-edit tools whose targets count as "files touched" within a turn. Used to
# enrich the snapshot-derived list (a turn may edit a file the snapshot layer
# also records; we union both so the timeline is complete even if one source
# misses an entry).
_EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

_PROMPT_PREVIEW_CHARS = 240


# ───────── 시간 ─────────

def _to_ms(ts: Optional[str]) -> Optional[int]:
    """ISO 8601 → epoch ms. Returns None on failure or empty."""
    if not ts:
        return None
    try:
        return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return None


# ───────── 세션 위치 탐색 ─────────

def _all_session_jsonls() -> list[Path]:
    """Every session transcript across all projects, newest mtime first."""
    if not PROJECTS_DIR.exists():
        return []
    out: list[Path] = []
    try:
        for proj in PROJECTS_DIR.iterdir():
            if not proj.is_dir():
                continue
            out.extend(proj.glob("*.jsonl"))
    except Exception as e:
        log.warning("checkpoints: listing projects failed: %s", e)
        return []
    out.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return out


def _jsonl_for_session(session_id: str) -> Optional[Path]:
    """Locate a transcript by session UUID (search every project dir)."""
    if not session_id or not PROJECTS_DIR.exists():
        return None
    try:
        for proj in PROJECTS_DIR.iterdir():
            if proj.is_dir():
                cand = proj / f"{session_id}.jsonl"
                if cand.exists():
                    return cand
    except Exception:
        return None
    return None


def _jsonls_for_cwd(cwd: str) -> list[Path]:
    """Transcripts for a given working directory (via the slug rule), newest first."""
    try:
        slug = _cwd_to_slug(Path(cwd))
    except Exception:
        return []
    proj = PROJECTS_DIR / slug
    if not proj.is_dir():
        return []
    files = list(proj.glob("*.jsonl"))
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return files


# ───────── 프롬프트 판별 ─────────

def _real_user_prompt_text(entry: dict) -> Optional[str]:
    """Return the genuine human prompt text from a 'user' entry, else None.

    Filters out meta/sidechain turns, tool-result-only turns, and synthetic
    command/notification wrappers so the timeline reflects what a person typed.
    """
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    content = (entry.get("message") or {}).get("content")
    text: Optional[str] = None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = [p for p in content if isinstance(p, dict)]
        # A turn that only carries tool results is not a prompt.
        if any(p.get("type") == "tool_result" for p in parts):
            return None
        for p in parts:
            if p.get("type") == "text":
                text = p.get("text")
                break
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    for prefix in _SYNTHETIC_PREFIXES:
        if stripped.startswith(prefix):
            return None
    return stripped


def _edit_paths_from_assistant(entry: dict) -> list[str]:
    """Absolute file paths targeted by file-edit tool_use blocks in an assistant turn."""
    if entry.get("type") != "assistant":
        return []
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    paths: list[str] = []
    for p in content:
        if not isinstance(p, dict) or p.get("type") != "tool_use":
            continue
        if p.get("name") not in _EDIT_TOOLS:
            continue
        inp = p.get("input") or {}
        fp = inp.get("file_path") or inp.get("notebook_path")
        if isinstance(fp, str) and fp:
            paths.append(fp)
    return paths


# ───────── 백업 존재 확인 ─────────

def _backup_on_disk(session_id: str, backup_file_name: Optional[str]) -> bool:
    """True if the named backup file exists under file-history/<session>/."""
    if not backup_file_name:
        return False
    try:
        return (FILE_HISTORY_DIR / session_id / backup_file_name).exists()
    except Exception:
        return False


def _short_path(path: str, cwd: Optional[str]) -> str:
    """Display path: strip the session cwd prefix when present, else basename-ish."""
    if cwd and path.startswith(cwd.rstrip("/") + "/"):
        return path[len(cwd.rstrip("/")) + 1:]
    return path


# ───────── 핵심 파서 ─────────

def _parse_checkpoints(jsonl: Path) -> dict:
    """Stream a transcript → ordered per-prompt checkpoint timeline.

    Algorithm: walk the file in order, collecting genuine user prompts and all
    file-history-snapshot backup records (with their backupTime). Then attribute
    each backup to the prompt whose time window [prompt_ts, next_prompt_ts) it
    falls in — "every user prompt creates a checkpoint", so a turn's file edits
    belong to the prompt that started that turn.
    """
    session_id = jsonl.stem
    cwd: Optional[str] = None
    git_branch: Optional[str] = None

    prompts: list[dict] = []  # {ts, tms, text}
    backups: list[dict] = []  # {path, version, backupFileName, bms}
    edit_paths: list[dict] = []  # {path, tms} from assistant tool_use

    try:
        with jsonl.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if cwd is None and o.get("cwd"):
                    cwd = o.get("cwd")
                if git_branch is None and o.get("gitBranch"):
                    git_branch = o.get("gitBranch")

                t = o.get("type")
                if t == "user":
                    txt = _real_user_prompt_text(o)
                    if txt is not None:
                        ts = o.get("timestamp")
                        prompts.append({"ts": ts, "tms": _to_ms(ts), "text": txt})
                elif t == "file-history-snapshot":
                    snap = o.get("snapshot") or {}
                    for path, meta in (snap.get("trackedFileBackups") or {}).items():
                        if not isinstance(meta, dict):
                            continue
                        backups.append({
                            "path": path,
                            "version": meta.get("version") or 0,
                            "backupFileName": meta.get("backupFileName"),
                            "bms": _to_ms(meta.get("backupTime")),
                        })
                elif t == "assistant":
                    ats = _to_ms(o.get("timestamp"))
                    for fp in _edit_paths_from_assistant(o):
                        edit_paths.append({"path": fp, "tms": ats})
    except Exception as e:
        log.warning("checkpoints: parse failed for %s: %s", jsonl, e)

    fh_session_dir = FILE_HISTORY_DIR / session_id
    fh_dir_exists = fh_session_dir.is_dir()

    checkpoints: list[dict] = []
    for i, p in enumerate(prompts):
        lo = p["tms"]
        hi = prompts[i + 1]["tms"] if i + 1 < len(prompts) else None

        def _in_window(ms_val: Optional[int]) -> bool:
            if ms_val is None or lo is None:
                return False
            if ms_val < lo:
                return False
            return hi is None or ms_val < hi

        # Files from the snapshot layer (authoritative — these have backups).
        files: dict[str, dict] = {}
        for b in backups:
            if not _in_window(b["bms"]):
                continue
            existing = files.get(b["path"])
            if existing is None or b["version"] >= existing["version"]:
                disp = _short_path(b["path"], cwd)
                files[b["path"]] = {
                    "path": disp,
                    "fullPath": b["path"],
                    "version": b["version"],
                    "backupFileName": b["backupFileName"],
                    "restorable": _backup_on_disk(session_id, b["backupFileName"]),
                }
        # Enrich with edit-tool targets in the same window that the snapshot
        # layer did not record (e.g. a fresh Write with no prior version).
        for e in edit_paths:
            if not _in_window(e["tms"]):
                continue
            if e["path"] in files:
                continue
            files[e["path"]] = {
                "path": _short_path(e["path"], cwd),
                "fullPath": e["path"],
                "version": None,
                "backupFileName": None,
                "restorable": False,
            }

        file_list = sorted(files.values(), key=lambda x: x["path"])
        restorable_files = sum(1 for f in file_list if f["restorable"])
        preview = p["text"].replace("\n", " ").strip()
        if len(preview) > _PROMPT_PREVIEW_CHARS:
            preview = preview[:_PROMPT_PREVIEW_CHARS].rstrip() + "…"

        checkpoints.append({
            "index": i,
            "ts": p["ts"],
            "tsMs": p["tms"],
            "promptPreview": preview,
            "files": file_list,
            "fileCount": len(file_list),
            "restorableFileCount": restorable_files,
            # A checkpoint is rewindable iff the file-history dir survives and at
            # least one referenced backup is still on disk.
            "restorable": bool(fh_dir_exists and restorable_files > 0),
        })

    return {
        "sessionId": session_id,
        "cwd": cwd,
        "project": Path(cwd).name if cwd else "",
        "gitBranch": git_branch,
        "fileHistoryDir": str(fh_session_dir),
        "fileHistoryDirExists": fh_dir_exists,
        "checkpoints": checkpoints,
        "promptCount": len(prompts),
        "totalTrackedFiles": len({b["path"] for b in backups}),
    }


def _session_summary(jsonl: Path) -> dict:
    """Lightweight descriptor for the session picker (id, project, first prompt, mtime)."""
    session_id = jsonl.stem
    cwd = ""
    first_prompt = ""
    try:
        with jsonl.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if not cwd and o.get("cwd"):
                    cwd = o.get("cwd")
                if not first_prompt:
                    txt = _real_user_prompt_text(o)
                    if txt:
                        first_prompt = txt.replace("\n", " ").strip()[:120]
                if cwd and first_prompt:
                    break
    except Exception:
        pass
    try:
        mtime = int(jsonl.stat().st_mtime * 1000)
    except Exception:
        mtime = None
    return {
        "sessionId": session_id,
        "cwd": cwd,
        "project": Path(cwd).name if cwd else "",
        "firstPrompt": first_prompt,
        "mtimeMs": mtime,
        "hasFileHistory": (FILE_HISTORY_DIR / session_id).is_dir(),
    }


# ───────── API ─────────

def api_checkpoints_list(query: dict) -> dict:
    """Per-prompt checkpoint timeline for a session.

    Query params (BaseHTTPRequestHandler parsed form — values are lists):
      - ``session_id``: explicit session UUID.
      - ``cwd``: pick the most-recent session for that working directory.
      - (neither): pick the most-recent session globally.
      - ``sessions=1``: also return the session picker list.

    Always read-only. When Claude Code's checkpoint store is absent (feature
    disabled, never used here, or GC'd after ~30 days) the response carries
    ``available:false`` plus an honest explanation rather than fabricated data.
    """
    def _q(key: str) -> str:
        v = query.get(key)
        if isinstance(v, list):
            return (v[0] or "").strip() if v else ""
        if isinstance(v, str):
            return v.strip()
        return ""

    session_id = _q("session_id")
    cwd = _q("cwd")
    want_sessions = _q("sessions") in ("1", "true", "yes")

    base = {
        "available": False,
        "supported": True,
        "retentionDays": _RETENTION_DAYS,
        "fileHistoryRoot": str(FILE_HISTORY_DIR),
        "fileHistoryRootExists": FILE_HISTORY_DIR.is_dir(),
        # How rewind actually works — surfaced verbatim in the empty state so the
        # UI never has to invent an explanation.
        "rewindInfo": {
            "trigger": "Run /rewind in the Claude Code CLI, or press Esc twice when the prompt input is empty.",
            "captures": "Every user prompt creates a checkpoint capturing the before-state of files edited via Claude's file-editing tools (Write/Edit/MultiEdit/NotebookEdit).",
            "notCaptured": "Files changed by bash commands (rm/mv/cp) and external/manual edits are NOT tracked. Checkpoints are local undo, not a Git replacement.",
            "retention": f"Checkpoints are cleaned up with their session after ~{_RETENTION_DAYS} days (configurable).",
            "actions": [
                "Restore code and conversation",
                "Restore conversation",
                "Restore code",
                "Summarize from here / up to here",
            ],
            "readOnlyNote": "This explorer is read-only. It reads the on-disk snapshot store; perform an actual rewind inside the Claude Code CLI.",
        },
    }

    # Session picker payload (best-effort; capped).
    if want_sessions:
        base["sessions"] = [_session_summary(p) for p in _all_session_jsonls()[:200]]

    # Resolve target transcript.
    jsonl: Optional[Path] = None
    resolved_by = ""
    if session_id:
        jsonl = _jsonl_for_session(session_id)
        resolved_by = "session_id"
        if jsonl is None:
            base["error"] = f"session not found: {session_id}"
            base["resolvedBy"] = resolved_by
            return base
    elif cwd:
        cand = _jsonls_for_cwd(cwd)
        if cand:
            jsonl = cand[0]
            resolved_by = "cwd"
    if jsonl is None:
        recent = _all_session_jsonls()
        if recent:
            jsonl = recent[0]
            resolved_by = resolved_by or "most-recent"

    if jsonl is None:
        base["emptyReason"] = (
            "No Claude Code sessions found under ~/.claude/projects. "
            "Start a session and edit a file to create checkpoints."
        )
        base["resolvedBy"] = resolved_by or "none"
        return base

    result = _parse_checkpoints(jsonl)
    result.update({
        "available": bool(result["checkpoints"]),
        "supported": True,
        "resolvedBy": resolved_by,
        "retentionDays": _RETENTION_DAYS,
        "fileHistoryRoot": str(FILE_HISTORY_DIR),
        "fileHistoryRootExists": FILE_HISTORY_DIR.is_dir(),
        "rewindInfo": base["rewindInfo"],
    })
    if want_sessions:
        result["sessions"] = base.get("sessions", [])

    if not result["checkpoints"]:
        result["emptyReason"] = (
            "This session has no user-prompt checkpoints on disk. "
            "Either no files were edited via Claude's editing tools, or the "
            f"file-history store was cleaned up (retention ~{_RETENTION_DAYS} days)."
        )
    elif not result["fileHistoryDirExists"]:
        result["emptyReason"] = (
            "Prompt timeline reconstructed from the transcript, but the file-history "
            "backups for this session are no longer on disk, so rewind is not possible "
            f"(likely GC'd after ~{_RETENTION_DAYS} days)."
        )
    return result
