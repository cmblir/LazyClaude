"""Plan rate-limit / quota proximity — best-effort, local-data only.

Anthropic does NOT expose a real-time API for the Claude Code plan usage
caps (the rolling 5-hour window, the weekly cap, or the separate weekly
Opus window). The only authoritative signal a user ever sees is the
`/status` panel in the CLI and the synthetic "You've hit your … limit ·
resets …" message Claude Code writes into the session JSONL when a cap
trips. So this module is explicitly **best-effort**:

  * RESET TIMES  — parsed verbatim from the most recent "limit hit"
    message in the local session JSONL files (`~/.claude/projects/**`).
    These are exact when present (Claude Code printed them).
  * USAGE COUNTS — there is no count in the local data, so we *estimate*
    a usage proxy from the token totals recorded in the dashboard SQLite
    `sessions` table inside each window. This is a rough activity proxy,
    NOT the real quota meter, and is flagged `estimated: True`.
  * LIMITS       — the absolute cap (tokens / compute-hours) is never in
    the local data and Anthropic changes it per plan + over time, so
    `limit` is returned as `None` and flagged `limitKnown: False`.

The proximity %% is therefore derived two ways and the better-known one
wins per window:

  1. TIME proximity — how far through the window's clock we are
     (elapsed / windowSeconds). Always computable once we know a reset
     time. This is what drives the gauges by default.
  2. USAGE proximity — only when a real limit were ever known (it isn't
     today), so it stays null.

Window model (verified against Anthropic help-center + reporting,
2026-06):
  * Rolling 5-hour window  — starts on first message, 300 min, auto-reset.
  * Weekly cap             — 7-day compute-hour budget, resets weekly.
  * Weekly Opus window     — Opus-only weekly sub-limit, tracked
    separately ("resets for Opus only and all other models").

This module is READ-ONLY against `~/.claude` and the sessions DB. It
creates NO tables and writes NO files. It reuses the battle-tested
reset-time / jsonl helpers from `auto_resume` where importable, and
falls back to a self-contained minimal parse otherwise.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path
from typing import Optional

from .config import CLAUDE_HOME
from .logger import log

# Window lengths in seconds.
_FIVE_HOUR_SECONDS = 5 * 3600
_WEEK_SECONDS = 7 * 24 * 3600

# How many of the most-recently-modified session JSONL files to scan for
# limit-hit messages. Limit-hit events are rare so scanning the recently
# active set is plenty and keeps the endpoint fast (each file is
# tail-read only, never fully loaded).
_MAX_JSONL_FILES = 80
# Only bytes from the tail of each file are inspected (limit messages are
# always the last thing written before the session stalls).
_TAIL_BYTES = 32768
# Ignore limit-hit events older than this — a 3-week-old reset time is
# meaningless. Weekly windows are 7 days so 21 days covers staleness.
_MAX_EVENT_AGE_SECONDS = 21 * 24 * 3600


# ───────── reset-time parsing ─────────
#
# Real Claude Code messages observed in the wild (~/.claude/projects):
#   "You've hit your session limit · resets 4:10am (Asia/Seoul)"
#   "You've hit your limit · resets 3pm (Asia/Seoul)"
#   "You've hit your weekly limit · resets 1:30pm (Asia/Seoul)"
#   "5-hour limit reached · resets 3pm"
# Note the bare-hour form ("3pm") with no minutes — the auto_resume parser
# requires HH:MM so it returns None for those. We add a bare-hour fallback.

# "resets <H>[:MM] am/pm" — minutes optional. Matches the CLI wording.
_PAT_RESET_CLOCK = re.compile(
    r"reset[s]?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?",
    re.IGNORECASE,
)
# "resets in N hours/minutes" — relative form (rare for caps but cheap).
_PAT_RESET_IN = re.compile(
    r"reset[s]?\s+in\s+(\d+)\s*(second|sec|s|minute|min|m|hour|hr|h)s?\b",
    re.IGNORECASE,
)

# Classify which window a limit message refers to. Order: weekly/opus
# checked before session/5h because "weekly limit" also contains "limit".
_PAT_OPUS_LIMIT = re.compile(r"\bopus\b.*\b(limit|reset)", re.IGNORECASE)
_PAT_WEEKLY_LIMIT = re.compile(r"\bweek(ly)?\b.*\blimit\b", re.IGNORECASE)
_PAT_SESSION_LIMIT = re.compile(
    r"\b(session\s+limit|5[\s-]?hour\s+limit|hit your limit)\b", re.IGNORECASE
)


def _reset_clock_to_epoch_ms(
    text: str, now_ts: Optional[float] = None
) -> Optional[int]:
    """Parse "resets <H>[:MM][am/pm]" / "resets in N units" → epoch ms.

    Handles the bare-hour form the auto_resume parser misses. The clock
    time is interpreted in the *local* timezone (the CLI prints it in the
    user's tz, e.g. "(Asia/Seoul)"; since this dashboard runs on the same
    machine, local time matches). If the time has already passed today it
    rolls to tomorrow. Returns None when no usable hint is found.
    """
    if not text:
        return None
    now_ts = now_ts if now_ts is not None else time.time()

    m = _PAT_RESET_IN.search(text)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith(("hour", "hr", "h")):
            sec = n * 3600
        elif unit.startswith(("min", "m")):
            sec = n * 60
        else:
            sec = n
        return int((now_ts + sec) * 1000)

    m = _PAT_RESET_CLOCK.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    meridiem = (m.group(3) or "").lower().rstrip(".")
    if meridiem in ("pm", "p", "p.m"):
        if hour < 12:
            hour += 12
    elif meridiem in ("am", "a", "a.m"):
        if hour == 12:
            hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    try:
        target_t = dt_time(hour=hour, minute=minute)
    except ValueError:
        return None
    now_dt = datetime.fromtimestamp(now_ts)
    target = datetime.combine(now_dt.date(), target_t)
    if target <= now_dt:
        target += timedelta(days=1)
    return int(target.timestamp() * 1000)


def _parse_reset_ms(text: str, now_ts: Optional[float] = None) -> Optional[int]:
    """Reset-time parse with auto_resume reuse + bare-hour fallback.

    Tries the shared auto_resume parser first (covers HH:MM + "in N
    units"), then falls back to the local bare-hour parser. Returns the
    earliest plausible future epoch-ms, or None.
    """
    candidates: list[int] = []
    try:
        from .auto_resume import _parse_reset_time as _ar_parse

        v = _ar_parse(text, now_ts)
        if v:
            candidates.append(int(v))
    except Exception:
        pass
    local = _reset_clock_to_epoch_ms(text, now_ts)
    if local:
        candidates.append(local)
    if not candidates:
        return None
    return min(candidates)


# ───────── jsonl scanning ─────────


def _projects_dir() -> Path:
    return CLAUDE_HOME / "projects"


def _read_tail(path: Path, byte_window: int = _TAIL_BYTES) -> str:
    """Tail-read helper. Reuses auto_resume's reader when importable."""
    try:
        from .auto_resume import _read_jsonl_tail as _ar_tail

        return _ar_tail(path, byte_window)
    except Exception:
        try:
            size = path.stat().st_size
            with path.open("rb") as fh:
                fh.seek(max(0, size - byte_window))
                return fh.read().decode("utf-8", errors="replace")
        except Exception:
            return ""


def _iter_recent_jsonl(limit: int = _MAX_JSONL_FILES) -> list[Path]:
    """Most-recently-modified session JSONL files under ~/.claude/projects."""
    pdir = _projects_dir()
    if not pdir.exists():
        return []
    files: list[tuple[float, Path]] = []
    try:
        for proj in pdir.iterdir():
            if not proj.is_dir():
                continue
            for jf in proj.glob("*.jsonl"):
                try:
                    files.append((jf.stat().st_mtime, jf))
                except Exception:
                    continue
    except Exception as e:
        log.warning("ratelimit: project scan failed: %s", e)
        return []
    files.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in files[:limit]]


def _classify_window(text: str) -> str:
    """Return one of: 'opus', 'weekly', 'fiveHour'. Defaults to fiveHour."""
    if _PAT_OPUS_LIMIT.search(text):
        return "opus"
    if _PAT_WEEKLY_LIMIT.search(text):
        return "weekly"
    # "session limit" and bare "hit your limit" are the 5h window.
    return "fiveHour"


def _entry_text(entry: dict) -> str:
    """Extract any human limit text from a JSONL assistant entry."""
    msg = entry.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    txt = block.get("text")
                    if isinstance(txt, str):
                        parts.append(txt)
            if parts:
                return " ".join(parts)
        if isinstance(content, str):
            return content
    for key in ("text", "message"):
        v = entry.get(key)
        if isinstance(v, str):
            return v
    return ""


def _iso_to_epoch_ms(iso: str) -> Optional[int]:
    if not iso or not isinstance(iso, str):
        return None
    try:
        # Claude Code writes UTC "Z" timestamps.
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def _scan_limit_events(now_ts: float) -> dict[str, dict]:
    """Scan recent JSONL tails for the latest limit-hit per window type.

    Returns {windowKey: {hitAtMs, resetAtMs, text, sessionId}} for the
    most recent event found per window ('fiveHour' / 'weekly' / 'opus').
    Best-effort and silent on per-file errors.
    """
    found: dict[str, dict] = {}
    age_floor_ms = int((now_ts - _MAX_EVENT_AGE_SECONDS) * 1000)

    for jf in _iter_recent_jsonl():
        tail = _read_tail(jf)
        if not tail:
            continue
        lower = tail.lower()
        # Cheap pre-filter: skip files with no limit wording at all.
        if "limit" not in lower or "reset" not in lower:
            continue
        for line in reversed(tail.strip().split("\n")):
            line = line.strip()
            if not line or "limit" not in line.lower():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if not isinstance(entry, dict):
                continue
            text = _entry_text(entry)
            if not text or "reset" not in text.lower():
                continue
            # Must look like a usage-cap message, not arbitrary prose
            # that merely contains the word "limit".
            if not (
                _PAT_SESSION_LIMIT.search(text)
                or _PAT_WEEKLY_LIMIT.search(text)
                or _PAT_OPUS_LIMIT.search(text)
            ):
                continue
            hit_at = _iso_to_epoch_ms(entry.get("timestamp") or "")
            if hit_at is None:
                try:
                    hit_at = int(jf.stat().st_mtime * 1000)
                except Exception:
                    hit_at = int(now_ts * 1000)
            if hit_at < age_floor_ms:
                continue
            window = _classify_window(text)
            reset_at = _parse_reset_ms(text, now_ts)
            prev = found.get(window)
            if prev is None or hit_at > prev["hitAtMs"]:
                found[window] = {
                    "hitAtMs": hit_at,
                    "resetAtMs": reset_at,
                    "text": text[:200],
                    "sessionId": entry.get("sessionId") or "",
                }
    return found


# ───────── usage proxy from sessions DB ─────────


def _token_usage_since(since_ms: int, opus_only: bool = False) -> dict:
    """Sum recorded session tokens since `since_ms` (best-effort proxy).

    READ-ONLY query against the dashboard sessions table. Returns
    {tokens, sessions}. Opus filter matches model substring 'opus'.
    The token total is NOT the quota meter — Anthropic meters by a
    compute-hour / message budget we cannot read — it is only an
    activity proxy to give the gauge *some* usage signal.
    """
    try:
        from .db import _db, _db_init

        _db_init()
        with _db() as c:
            if opus_only:
                row = c.execute(
                    "SELECT COALESCE(SUM(total_tokens),0) AS tok, COUNT(*) AS n "
                    "FROM sessions WHERE started_at >= ? "
                    "AND LOWER(COALESCE(model,'')) LIKE '%opus%'",
                    (since_ms,),
                ).fetchone()
            else:
                row = c.execute(
                    "SELECT COALESCE(SUM(total_tokens),0) AS tok, COUNT(*) AS n "
                    "FROM sessions WHERE started_at >= ?",
                    (since_ms,),
                ).fetchone()
        return {"tokens": int(row["tok"] or 0), "sessions": int(row["n"] or 0)}
    except Exception as e:
        log.warning("ratelimit: token usage query failed: %s", e)
        return {"tokens": 0, "sessions": 0}


# ───────── ETA formatting ─────────


def _human_eta(reset_at_ms: Optional[int], now_ts: float) -> str:
    """Human "in 2h 13m" / "now" / "" (unknown)."""
    if not reset_at_ms:
        return ""
    delta_s = int(reset_at_ms / 1000 - now_ts)
    if delta_s <= 0:
        return "지금 (이미 리셋됨)"
    h = delta_s // 3600
    m = (delta_s % 3600) // 60
    if h and m:
        return f"{h}시간 {m}분 후"
    if h:
        return f"{h}시간 후"
    if m:
        return f"{m}분 후"
    return f"{delta_s}초 후"


def _build_window(
    key: str,
    label: str,
    window_seconds: int,
    event: Optional[dict],
    now_ts: float,
    usage: dict,
) -> dict:
    """Assemble one window's public payload.

    Proximity is TIME-based: how far the clock is through the window,
    derived from the reset time and the window length. When no reset
    time is known, proximity is null and `detected` is False.
    """
    now_ms = int(now_ts * 1000)
    reset_at = event.get("resetAtMs") if event else None
    hit_at = event.get("hitAtMs") if event else None
    detected = bool(event)

    pct: Optional[float] = None
    if reset_at:
        # Window started at reset - windowSeconds; elapsed/window → pct.
        window_start_ms = reset_at - window_seconds * 1000
        span = reset_at - window_start_ms
        if span > 0:
            elapsed = now_ms - window_start_ms
            pct = max(0.0, min(100.0, round((elapsed / span) * 100, 1)))

    return {
        "key": key,
        "label": label,
        "windowSeconds": window_seconds,
        "detected": detected,
        # Reset time — exact when a limit message was found locally.
        "resetAt": reset_at,
        "resetEta": _human_eta(reset_at, now_ts) if reset_at else "",
        "lastHitAt": hit_at,
        "lastHitText": (event.get("text") if event else "") or "",
        # Proximity — time-through-window %% (best-effort).
        "pct": pct,
        "proximitySource": "time" if pct is not None else None,
        # Usage proxy from local token totals (NOT the real quota meter).
        "used": usage.get("tokens", 0),
        "usedSessions": usage.get("sessions", 0),
        "usedUnit": "tokens (proxy)",
        "estimated": True,
        # Absolute cap — never available from local data.
        "limit": None,
        "limitKnown": False,
    }


def api_ratelimit_status(query: dict | None = None) -> dict:
    """GET /api/ratelimit/status — best-effort plan quota proximity.

    Returns the three plan windows (rolling 5-hour, weekly cap, weekly
    Opus) each with: detected flag, exact resetAt (when a local limit
    message was found) + human ETA, a TIME-based proximity %%, and a
    token-usage *proxy* from the sessions DB. Absolute limits are always
    `null` / `limitKnown:false` because Anthropic exposes no real-time
    quota meter — this is clearly surfaced so the UI can mark it.
    """
    now_ts = time.time()
    now_ms = int(now_ts * 1000)

    try:
        events = _scan_limit_events(now_ts)
    except Exception as e:
        log.warning("ratelimit: scan failed: %s", e)
        events = {}

    five_start_ms = now_ms - _FIVE_HOUR_SECONDS * 1000
    week_start_ms = now_ms - _WEEK_SECONDS * 1000

    # If a window has a known reset time, anchor the usage proxy to the
    # actual window start (reset - windowSeconds); else trailing window.
    def _usage_for(window_seconds: int, event: Optional[dict], opus: bool) -> dict:
        if event and event.get("resetAtMs"):
            start_ms = int(event["resetAtMs"]) - window_seconds * 1000
        else:
            start_ms = now_ms - window_seconds * 1000
        return _token_usage_since(max(0, start_ms), opus_only=opus)

    ev_five = events.get("fiveHour")
    ev_week = events.get("weekly")
    ev_opus = events.get("opus")

    five = _build_window(
        "fiveHour",
        "롤링 5시간 윈도우",
        _FIVE_HOUR_SECONDS,
        ev_five,
        now_ts,
        _usage_for(_FIVE_HOUR_SECONDS, ev_five, opus=False),
    )
    weekly = _build_window(
        "weekly",
        "주간 쿼터 한도",
        _WEEK_SECONDS,
        ev_week,
        now_ts,
        _usage_for(_WEEK_SECONDS, ev_week, opus=False),
    )
    opus = _build_window(
        "opus",
        "주간 Opus 윈도우",
        _WEEK_SECONDS,
        ev_opus,
        now_ts,
        _usage_for(_WEEK_SECONDS, ev_opus, opus=True),
    )
    # The Opus window is only meaningfully "detected" when an Opus-tagged
    # limit message was actually seen — otherwise the gauge would imply a
    # cap we never observed. Keep token proxy regardless.
    opus["detectable"] = bool(ev_opus)

    # lastResetAt — the most recent reset time across any window (mirrors
    # the auto_resume field name so callers can correlate). None when no
    # limit event was found locally at all.
    reset_candidates = [
        w["resetAt"] for w in (five, weekly, opus) if w.get("resetAt")
    ]
    last_reset_at = max(reset_candidates) if reset_candidates else None

    any_detected = bool(events)

    return {
        "ok": True,
        "computedAt": now_ms,
        "anyDetected": any_detected,
        "fiveHour": five,
        "weekly": weekly,
        "opus": opus,
        "lastResetAt": last_reset_at,
        # Honest caveat surfaced to the UI.
        "note": (
            "Anthropic은 주간/5시간 쿼터의 실시간 잔량 API를 제공하지 않습니다. "
            "리셋 시각은 로컬 세션 로그의 한도 도달 메시지에서 추출한 값이며, "
            "사용량 수치는 세션 토큰 합계 기반 근사치(proxy)입니다. 절대 한도(limit)는 "
            "로컬 데이터에 없어 표시할 수 없습니다."
        ),
        "limitsKnown": False,
    }
