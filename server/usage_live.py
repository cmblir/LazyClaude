"""Real-time token usage — incremental JSONL tail parser + today API.

Session JSONL files are append-only, so a per-file byte offset
(jsonl_offsets table) lets the tailer parse only newly appended lines on
each cycle instead of re-reading multi-MB files. Each assistant turn's
usage lands in usage_events keyed by the message timestamp, which makes
"today" aggregation correct even for sessions spanning midnight
(sessions.started_at bucketing attributes everything to the start day).
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path

from .config import PROJECTS_DIR
from .db import _db, _db_init
from .logger import log
from .sessions import INDEX_LOCK, _index_jsonl, _index_jsonl_unlocked
from .utils import _iso_ms

_TAIL_INTERVAL_SEC = 5.0
# First boot after upgrade: files the tailer has never seen get a full
# back-parse only when modified within this window. Older files start
# tracking from their current end — bounded one-time cost instead of
# re-parsing the user's whole ~/.claude/projects history.
_BACKFILL_WINDOW_MS = 48 * 3600 * 1000

_STARTED = False


def _parse_appended(jsonl: Path, session_id: str, offset: int) -> tuple[list[tuple], int]:
    """Parse complete lines appended after byte `offset`.

    Returns (usage_rows, new_offset). A trailing line without a newline
    terminator is a write in progress — left for the next cycle so a
    half-written JSON record is never consumed.
    """
    rows: list[tuple] = []
    consumed = offset
    with jsonl.open("rb") as f:
        f.seek(offset)
        for braw in f:
            if not braw.endswith(b"\n"):
                break
            consumed += len(braw)
            raw = braw.decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            try:
                m = json.loads(raw)
            except Exception:
                continue
            if m.get("type") != "assistant":
                continue
            msg_obj = m.get("message") or {}
            usage = msg_obj.get("usage") or {}
            u_in = int(usage.get("input_tokens") or 0)
            u_out = int(usage.get("output_tokens") or 0)
            u_cr = int(usage.get("cache_read_input_tokens") or 0)
            u_cc = int(usage.get("cache_creation_input_tokens") or 0)
            if not (u_in or u_out or u_cr or u_cc):
                continue
            ts = _iso_ms(m.get("timestamp", "") or "") or int(time.time() * 1000)
            rows.append((session_id, ts, str(msg_obj.get("model") or ""),
                         u_in, u_out, u_cr, u_cc))
    return rows, consumed


def _tail_file(jsonl: Path, mtime_ms: int) -> int:
    """Consume appended bytes of one known file. Returns events inserted.

    Re-reads the stored offset under INDEX_LOCK because a concurrent full
    reindex (boot / manual) may have advanced it after the cycle snapshot.
    """
    with INDEX_LOCK:
        with _db() as c:
            row = c.execute(
                "SELECT offset FROM jsonl_offsets WHERE jsonl_path=?",
                (str(jsonl),),
            ).fetchone()
        cur = (row["offset"] if row else 0) or 0
        try:
            size = jsonl.stat().st_size
        except OSError:
            return 0
        if size <= cur:
            return 0
        rows, new_offset = _parse_appended(jsonl, jsonl.stem, cur)
        if new_offset == cur:
            return 0
        with _db() as c:
            if rows:
                c.executemany(
                    "INSERT INTO usage_events (session_id,ts,model,input_tokens,output_tokens,"
                    "cache_read_tokens,cache_creation_tokens) VALUES (?,?,?,?,?,?,?)",
                    rows,
                )
                d_in = sum(r[3] for r in rows)
                d_out = sum(r[4] for r in rows)
                d_cr = sum(r[5] for r in rows)
                d_cc = sum(r[6] for r in rows)
                last_ts = max(r[1] for r in rows)
                # Keep the sessions row live for the existing Usage views.
                # sessions.mtime is intentionally NOT bumped so the boot-time
                # full reindex still refreshes message counts / scores later.
                updated = c.execute(
                    "UPDATE sessions SET input_tokens=input_tokens+?, output_tokens=output_tokens+?, "
                    "cache_read_tokens=cache_read_tokens+?, cache_creation_tokens=cache_creation_tokens+?, "
                    "total_tokens=total_tokens+?, ended_at=MAX(ended_at,?) WHERE session_id=?",
                    (d_in, d_out, d_cr, d_cc, d_in + d_out + d_cr + d_cc,
                     last_ts, jsonl.stem),
                ).rowcount
            else:
                updated = 1
            c.execute(
                "INSERT OR REPLACE INTO jsonl_offsets (jsonl_path,session_id,offset,mtime) VALUES (?,?,?,?)",
                (str(jsonl), jsonl.stem, new_offset, mtime_ms),
            )
        if rows and not updated:
            # Offset row without a sessions row (e.g. partially wiped DB) —
            # rebuild the session from scratch for consistency.
            _index_jsonl_unlocked(jsonl, jsonl.parent.name)
    return len(rows)


def _tail_once() -> dict:
    """One tail cycle over all session files. Returns counters."""
    stats = {"tailed": 0, "events": 0, "full": 0, "skippedOld": 0}
    if not PROJECTS_DIR.exists():
        return stats
    with _db() as c:
        known = {
            r["jsonl_path"]: (r["offset"] or 0, r["mtime"] or 0)
            for r in c.execute("SELECT jsonl_path, offset, mtime FROM jsonl_offsets")
        }
    now_ms = int(time.time() * 1000)
    for project_dir_path in PROJECTS_DIR.iterdir():
        if not project_dir_path.is_dir():
            continue
        for jsonl in project_dir_path.glob("*.jsonl"):
            try:
                st = jsonl.stat()
            except OSError:
                continue
            size = st.st_size
            mtime_ms = int(st.st_mtime * 1000)
            prev = known.get(str(jsonl))
            if prev is None:
                if now_ms - mtime_ms > _BACKFILL_WINDOW_MS:
                    # Pre-feature history — start tracking from current end.
                    with INDEX_LOCK, _db() as c:
                        c.execute(
                            "INSERT OR REPLACE INTO jsonl_offsets (jsonl_path,session_id,offset,mtime) VALUES (?,?,?,?)",
                            (str(jsonl), jsonl.stem, size, mtime_ms),
                        )
                    stats["skippedOld"] += 1
                else:
                    if _index_jsonl(jsonl, project_dir_path.name):
                        stats["full"] += 1
                continue
            offset, _prev_mtime = prev
            if size == offset:
                continue
            if size < offset:
                # Rewritten/truncated (e.g. compaction) — full re-parse;
                # _index_jsonl deletes + reinserts this session's events.
                if _index_jsonl(jsonl, project_dir_path.name):
                    stats["full"] += 1
                continue
            n = _tail_file(jsonl, mtime_ms)
            if n:
                stats["tailed"] += 1
                stats["events"] += n
    return stats


def start_usage_tailer() -> None:
    """Spawn the tail-loop daemon thread (idempotent)."""
    global _STARTED
    if _STARTED:
        return
    _STARTED = True

    def _loop() -> None:
        _db_init()
        # Let the boot-time full index claim most changed files first; the
        # INDEX_LOCK + offset re-read keeps overlap correct either way.
        time.sleep(_TAIL_INTERVAL_SEC)
        while True:
            try:
                r = _tail_once()
                if r["events"] or r["full"]:
                    log.debug("usage tail: %s", r)
            except Exception as e:
                log.warning("usage tail cycle failed: %s", e)
            time.sleep(_TAIL_INTERVAL_SEC)

    threading.Thread(target=_loop, daemon=True, name="usage-tail").start()


def api_usage_today() -> dict:
    """Today's token usage (local midnight window) from usage_events."""
    _db_init()
    now = datetime.now()
    start_ms = int(datetime(now.year, now.month, now.day).timestamp() * 1000)
    now_ms = int(time.time() * 1000)
    with _db() as c:
        tot = c.execute(
            "SELECT COALESCE(SUM(input_tokens),0) AS ti, COALESCE(SUM(output_tokens),0) AS to_, "
            "COALESCE(SUM(cache_read_tokens),0) AS cr, COALESCE(SUM(cache_creation_tokens),0) AS cc, "
            "COUNT(*) AS n, COUNT(DISTINCT session_id) AS s, COALESCE(MAX(ts),0) AS last "
            "FROM usage_events WHERE ts >= ?",
            (start_ms,),
        ).fetchone()
        hourly_rows = c.execute(
            "SELECT CAST(strftime('%H', ts/1000, 'unixepoch', 'localtime') AS INTEGER) AS h, "
            "SUM(input_tokens+output_tokens+cache_read_tokens+cache_creation_tokens) AS tokens, "
            "COUNT(*) AS events FROM usage_events WHERE ts >= ? GROUP BY h",
            (start_ms,),
        ).fetchall()
        by_model = [dict(r) for r in c.execute(
            "SELECT model, SUM(input_tokens) AS input, SUM(output_tokens) AS output, "
            "SUM(input_tokens+output_tokens+cache_read_tokens+cache_creation_tokens) AS tokens, "
            "COUNT(*) AS events FROM usage_events WHERE ts >= ? "
            "GROUP BY model ORDER BY tokens DESC",
            (start_ms,),
        ).fetchall()]
        top_sessions = [dict(r) for r in c.execute(
            "SELECT e.session_id, s.cwd, s.first_user_prompt, "
            "SUM(e.input_tokens+e.output_tokens+e.cache_read_tokens+e.cache_creation_tokens) AS tokens, "
            "MAX(e.ts) AS last_ts "
            "FROM usage_events e LEFT JOIN sessions s ON s.session_id = e.session_id "
            "WHERE e.ts >= ? GROUP BY e.session_id ORDER BY tokens DESC LIMIT 5",
            (start_ms,),
        ).fetchall()]
        recent = c.execute(
            "SELECT COALESCE(SUM(input_tokens+output_tokens+cache_read_tokens+cache_creation_tokens),0) AS tokens "
            "FROM usage_events WHERE ts >= ?",
            (now_ms - 5 * 60 * 1000,),
        ).fetchone()

    hourly = [{"hour": h, "tokens": 0, "events": 0} for h in range(24)]
    for r in hourly_rows:
        if 0 <= r["h"] <= 23:
            hourly[r["h"]] = {"hour": r["h"], "tokens": r["tokens"] or 0, "events": r["events"] or 0}
    for s in top_sessions:
        cwd = s.get("cwd") or ""
        s["project"] = Path(cwd).name if cwd else ""

    return {
        "ok": True,
        "date": f"{now.year:04d}-{now.month:02d}-{now.day:02d}",
        "totals": {
            "input": tot["ti"], "output": tot["to_"],
            "cacheRead": tot["cr"], "cacheCreate": tot["cc"],
            "total": tot["ti"] + tot["to_"] + tot["cr"] + tot["cc"],
            "events": tot["n"], "sessions": tot["s"],
        },
        "hourly": hourly,
        "byModel": by_model,
        "topSessions": top_sessions,
        "burnPerMin": (recent["tokens"] or 0) // 5,
        "lastEventTs": tot["last"],
        "serverNow": now_ms,
    }
