"""Memory load-boundary AUDIT — read-only scan of context-injected memory files.

This module does NOT manage memory CRUD (that already lives in
``server/system.py`` as ``api_memory_list`` / ``api_memory_get`` /
``api_memory_put`` / ``api_memory_delete``). Here we only *measure* the
context-load cost of the files Claude Code injects into every conversation:

  - the global ``~/.claude/CLAUDE.md``                  → loaded into EVERY session
  - each project's ``<cwd>/CLAUDE.md``                  → loaded into every session in that project
  - each ``~/.claude/projects/<slug>/memory/*.md``      → project-scoped memory store

For each file we compute bytes, line count and an estimated token load
(chars / 4 — the standard rough heuristic used by Anthropic/OpenAI for
English text; non-Latin scripts like Korean run hotter, so the estimate is
deliberately conservative and labelled as such). We then flag files that
exceed sane load boundaries, because oversized memory inflates the context
window of every conversation in that scope and quietly drives up cost.

Everything here is filesystem read-only. Paths are sandboxed under ``$HOME``
before any read, and reads degrade to empty strings on failure rather than
raising — an absent ``~/.claude`` yields an honest empty report.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from .config import CLAUDE_HOME, CLAUDE_MD, PROJECTS_DIR
from .logger import log
from .projects import _resolve_cwd_from_jsonl, _slug_to_cwd_map
from .utils import _safe_read

# ───────── load-boundary thresholds ─────────
# A memory file is "flagged" when it crosses EITHER boundary. These are
# deliberately conservative: a ~25 KB / ~200-line CLAUDE.md is already a
# meaningful slice of context that is re-paid on every turn of every session
# in that scope.
WARN_BYTES = 25 * 1024          # 25 KB
WARN_LINES = 200                # ~200 lines
# Token-load heuristic: ~4 chars per token (rough, English-biased). Korean and
# other multi-byte scripts tokenise denser, so true load is usually higher.
CHARS_PER_TOKEN = 4
# Cap how much of each file we read for line counting / sizing. Real CLAUDE.md
# and memory files are well under this; the cap just bounds pathological cases.
_READ_LIMIT = 2_000_000


def _est_tokens(char_count: int) -> int:
    """Rough token estimate from character count (chars / 4)."""
    if char_count <= 0:
        return 0
    return (char_count + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def _under_home(p: Path) -> bool:
    """True iff the resolved path is the home dir or strictly under it."""
    try:
        rp = os.path.realpath(str(p))
    except Exception:
        return False
    home = os.path.realpath(str(Path.home()))
    return rp == home or rp.startswith(home + os.sep)


def _scan_file(p: Path, scope: str, label: str, project: str) -> dict | None:
    """Measure one memory-bearing file. Returns None when it doesn't exist
    or sits outside the home sandbox.

    ``scope``   : 'global' | 'projectClaudeMd' | 'projectMemory'
    ``label``   : human label (file name or 'CLAUDE.md (global)')
    ``project`` : project display name this file loads into ('' for global)
    """
    try:
        if not p.exists() or not p.is_file():
            return None
    except Exception:
        return None
    if not _under_home(p):
        return None

    try:
        st = p.stat()
        size_bytes = int(st.st_size)
        mtime_ms = int(st.st_mtime * 1000)
    except Exception:
        size_bytes = 0
        mtime_ms = None

    raw = _safe_read(p, _READ_LIMIT)
    char_count = len(raw)
    # Count lines from the (possibly truncated) read; truncation only happens
    # for absurdly large files, which are flagged regardless.
    line_count = raw.count("\n") + (1 if raw and not raw.endswith("\n") else 0)
    est_tokens = _est_tokens(char_count)

    reasons: list[str] = []
    if size_bytes > WARN_BYTES:
        reasons.append(f">{WARN_BYTES // 1024}KB ({size_bytes / 1024:.1f}KB)")
    if line_count > WARN_LINES:
        reasons.append(f">{WARN_LINES} lines ({line_count})")

    return {
        "path": str(p),
        "name": label,
        "scope": scope,
        "project": project,
        "bytes": size_bytes,
        "lines": line_count,
        "chars": char_count,
        "estTokens": est_tokens,
        "modifiedAt": mtime_ms,
        "flagged": bool(reasons),
        "reasons": reasons,
        "truncated": char_count >= _READ_LIMIT,
    }


def _project_label(slug: str, cwd: str) -> str:
    if cwd:
        name = Path(cwd).name
        if name:
            return name
    return slug


def api_memory_audit(query: dict | None = None) -> dict:
    """GET /api/memory/audit — read-only memory load-boundary report.

    Scans (a) the global ~/.claude/CLAUDE.md, (b) each project's
    <cwd>/CLAUDE.md, and (c) ~/.claude/projects/<slug>/memory/*.md, then
    returns totals, a per-project breakdown, flagged files with reasons, and
    the biggest offenders ranked by estimated token load.

    The ``query`` argument is accepted for the GET-handler calling convention
    but is currently unused — the audit always scans the full tree.
    """
    started = time.time()
    files: list[dict] = []
    projects: dict[str, dict] = {}

    def _proj_bucket(key: str, name: str, cwd: str) -> dict:
        b = projects.get(key)
        if b is None:
            b = {
                "key": key,
                "projectName": name,
                "cwd": cwd,
                "files": [],
                "totalBytes": 0,
                "totalLines": 0,
                "totalEstTokens": 0,
                "flaggedCount": 0,
                "hasClaudeMd": False,
                "memoryFileCount": 0,
            }
            projects[key] = b
        return b

    # ── 1) global CLAUDE.md — loaded into EVERY session in EVERY project ──
    global_entry = _scan_file(
        CLAUDE_MD, "global", "CLAUDE.md (global)", ""
    )
    global_present = global_entry is not None
    if global_entry:
        files.append(global_entry)

    # ── 2) per-project: <cwd>/CLAUDE.md  +  memory/*.md ──
    projects_dir_exists = False
    try:
        projects_dir_exists = PROJECTS_DIR.exists()
    except Exception:
        projects_dir_exists = False

    slug_map: dict = {}
    try:
        slug_map = _slug_to_cwd_map()
    except Exception as e:
        log.warning("memory_audit: slug map failed: %s", e)

    if projects_dir_exists:
        try:
            proj_dirs = sorted(p for p in PROJECTS_DIR.iterdir() if p.is_dir())
        except Exception:
            proj_dirs = []
        for proj in proj_dirs:
            slug = proj.name
            cwd = slug_map.get(slug) or _resolve_cwd_from_jsonl(proj)
            name = _project_label(slug, cwd)
            bucket = _proj_bucket(slug, name, cwd or "")

            # 2a) per-project CLAUDE.md at the resolved cwd (best-effort).
            if cwd:
                cmd_path = Path(cwd) / "CLAUDE.md"
                cmd_entry = _scan_file(
                    cmd_path, "projectClaudeMd", "CLAUDE.md", name
                )
                if cmd_entry:
                    files.append(cmd_entry)
                    bucket["files"].append(cmd_entry)
                    bucket["hasClaudeMd"] = True
                    bucket["totalBytes"] += cmd_entry["bytes"]
                    bucket["totalLines"] += cmd_entry["lines"]
                    bucket["totalEstTokens"] += cmd_entry["estTokens"]
                    if cmd_entry["flagged"]:
                        bucket["flaggedCount"] += 1

            # 2b) memory store *.md files.
            mem_dir = proj / "memory"
            try:
                mem_exists = mem_dir.exists()
            except Exception:
                mem_exists = False
            if mem_exists:
                try:
                    md_files = sorted(mem_dir.glob("*.md"))
                except Exception:
                    md_files = []
                for md in md_files:
                    entry = _scan_file(md, "projectMemory", md.name, name)
                    if not entry:
                        continue
                    files.append(entry)
                    bucket["files"].append(entry)
                    bucket["memoryFileCount"] += 1
                    bucket["totalBytes"] += entry["bytes"]
                    bucket["totalLines"] += entry["lines"]
                    bucket["totalEstTokens"] += entry["estTokens"]
                    if entry["flagged"]:
                        bucket["flaggedCount"] += 1

    # Drop projects that ended up with no scanned files (no CLAUDE.md, no memory).
    project_list = [b for b in projects.values() if b["files"]]
    project_list.sort(key=lambda b: b["totalEstTokens"], reverse=True)

    flagged = [f for f in files if f["flagged"]]
    flagged.sort(key=lambda f: f["estTokens"], reverse=True)

    # Biggest offenders across ALL files, ranked by estimated token load.
    offenders = sorted(files, key=lambda f: f["estTokens"], reverse=True)[:15]

    total_bytes = sum(f["bytes"] for f in files)
    total_lines = sum(f["lines"] for f in files)
    total_est_tokens = sum(f["estTokens"] for f in files)
    global_load = global_entry["estTokens"] if global_entry else 0

    return {
        "ok": True,
        "computedAt": int(started * 1000),
        "elapsedMs": int((time.time() - started) * 1000),
        "claudeHome": str(CLAUDE_HOME),
        "globalClaudeMdPath": str(CLAUDE_MD),
        "projectsDirExists": projects_dir_exists,
        "thresholds": {
            "warnBytes": WARN_BYTES,
            "warnLines": WARN_LINES,
            "charsPerToken": CHARS_PER_TOKEN,
        },
        "totals": {
            "fileCount": len(files),
            "projectCount": len(project_list),
            "bytes": total_bytes,
            "lines": total_lines,
            "estTokens": total_est_tokens,
            "flaggedCount": len(flagged),
            # The global CLAUDE.md is re-paid on EVERY conversation, so we
            # surface its standalone load separately as the "always-on" cost.
            "globalLoadEstTokens": global_load,
        },
        "global": {
            "present": global_present,
            "path": str(CLAUDE_MD),
            "entry": global_entry,
        },
        "projects": project_list,
        "flagged": flagged,
        "offenders": offenders,
        "note": (
            "estTokens는 문자수/4 추정치 (영어 기준 휴리스틱). 한국어 등 "
            "멀티바이트 문자는 실제 토큰이 더 많을 수 있어 보수적 하한입니다. "
            "글로벌 CLAUDE.md는 모든 프로젝트의 모든 대화에 주입되며, 프로젝트 "
            "CLAUDE.md는 해당 프로젝트의 모든 대화에 주입됩니다."
        ),
    }
