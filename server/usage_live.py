"""Real-time token usage — incremental JSONL tail parser + today API.

Session JSONL files are append-only, so a per-file byte offset
(jsonl_offsets table) lets the tailer parse only newly appended lines on
each cycle instead of re-reading multi-MB files. Each assistant turn's
usage lands in usage_events keyed by the message timestamp, which makes
"today" aggregation correct even for sessions spanning midnight
(sessions.started_at bucketing attributes everything to the start day).

Dedup: Claude Code writes one assistant line per content block of a
single API response, all carrying the same message.id and an identical
usage object (~2.5x overcount if summed naively). usage_events has a
unique index on message_id, and all inserts go through INSERT OR IGNORE —
duplicate blocks, tail cycles that re-see a message, and resumed-session
history copies all collapse to one row per API response.

Nested transcripts (subagents/, workflows/) are tailed for usage events
only — they are not sessions and must not pollute the session list.
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
from .sessions import INDEX_LOCK, _index_jsonl_unlocked

from .utils import _iso_ms

_TAIL_INTERVAL_SEC = 5.0
# First boot after upgrade: files the tailer has never seen get a full
# back-parse only when modified within this window. Older files start
# tracking from their current end — bounded one-time cost instead of
# re-parsing the user's whole ~/.claude/projects history.
_BACKFILL_WINDOW_MS = 48 * 3600 * 1000

_INSERT_EVENT_SQL = (
    "INSERT OR IGNORE INTO usage_events (session_id,ts,model,message_id,input_tokens,"
    "output_tokens,cache_read_tokens,cache_creation_tokens) VALUES (?,?,?,?,?,?,?,?)"
)

# usage_events rows older than this are pruned (the table only feeds
# recent-window aggregations; unbounded growth was flagged in review).
_RETENTION_DAYS = 90
_CLEANUP_EVERY_CYCLES = 720  # ≈ 1h at the 5s cadence

# Files whose last visit consumed nothing (e.g. a permanently unterminated
# trailing line keeps size > offset) — skip while (size, mtime) unchanged
# instead of re-reading the partial tail every cycle.
_QUIET: dict = {}

_STARTED = False


def _parse_appended(jsonl: Path, session_id: str, offset: int) -> tuple[list[tuple], int]:
    """Parse complete lines appended after byte `offset`.

    Returns (usage_rows, new_offset). A trailing line without a newline
    terminator is a write in progress — left for the next cycle so a
    half-written JSON record is never consumed.
    """
    rows: list[tuple] = []
    seen_mids: set = set()
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
            mid = str(msg_obj.get("id") or "")
            if mid and mid in seen_mids:
                continue
            if mid:
                seen_mids.add(mid)
            # Fallback ts=0 matches _index_jsonl_unlocked — the same physical
            # line must produce the same row whichever path parses it first.
            ts = _iso_ms(m.get("timestamp", "") or "") or 0
            rows.append((session_id, ts, str(msg_obj.get("model") or ""), mid,
                         u_in, u_out, u_cr, u_cc))
    return rows, consumed


def _insert_events(c, rows: list[tuple]) -> list[tuple]:
    """Insert usage rows, returning only those actually inserted (the unique
    message_id index silently drops duplicates)."""
    inserted: list[tuple] = []
    for r in rows:
        if c.execute(_INSERT_EVENT_SQL, r).rowcount:
            inserted.append(r)
    return inserted


def _tail_file(jsonl: Path, mtime_ms: int, update_session: bool) -> int:
    """Consume appended bytes of one known file. Returns events inserted.

    Re-reads the stored offset under INDEX_LOCK because a concurrent full
    reindex (boot / manual) may have advanced it after the cycle snapshot.
    The offset write is a compare-and-swap so a second dashboard process
    sharing the DB can't double-apply the same byte range.
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
            _QUIET[str(jsonl)] = (size, mtime_ms)
            return 0
        _QUIET.pop(str(jsonl), None)
        with _db() as c:
            if row is not None:
                moved = c.execute(
                    "UPDATE jsonl_offsets SET offset=?, mtime=? WHERE jsonl_path=? AND offset=?",
                    (new_offset, mtime_ms, str(jsonl), cur),
                ).rowcount
                if not moved:
                    # Another writer advanced the cursor first — drop batch;
                    # the unique index would drop the rows anyway.
                    return 0
            else:
                c.execute(
                    "INSERT OR REPLACE INTO jsonl_offsets (jsonl_path,session_id,offset,mtime) VALUES (?,?,?,?)",
                    (str(jsonl), jsonl.stem, new_offset, mtime_ms),
                )
            inserted = _insert_events(c, rows)
            updated = 1
            if inserted and update_session:
                d_in = sum(r[4] for r in inserted)
                d_out = sum(r[5] for r in inserted)
                d_cr = sum(r[6] for r in inserted)
                d_cc = sum(r[7] for r in inserted)
                last_ts = max(r[1] for r in inserted)
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
        if inserted and update_session and not updated:
            # Offset row without a sessions row (e.g. partially wiped DB) —
            # rebuild the session from scratch for consistency.
            _index_jsonl_unlocked(jsonl, jsonl.parent.name)
    return len(inserted)


def _ingest_nested(jsonl: Path, mtime_ms: int, truncated: bool) -> int:
    """Full events-only (re-)parse of a nested transcript. Caller-safe:
    acquires INDEX_LOCK itself. Returns events inserted."""
    with INDEX_LOCK:
        rows, consumed = _parse_appended(jsonl, jsonl.stem, 0)
        with _db() as c:
            if truncated:
                c.execute("DELETE FROM usage_events WHERE session_id=?", (jsonl.stem,))
            inserted = _insert_events(c, rows)
            c.execute(
                "INSERT OR REPLACE INTO jsonl_offsets (jsonl_path,session_id,offset,mtime) VALUES (?,?,?,?)",
                (str(jsonl), jsonl.stem, consumed, mtime_ms),
            )
    return len(inserted)


def _tail_once() -> dict:
    """One tail cycle over all session + nested transcript files."""
    stats = {"tailed": 0, "events": 0, "full": 0, "skippedOld": 0}
    if not PROJECTS_DIR.exists():
        return stats
    with _db() as c:
        known = {
            r["jsonl_path"]: (r["offset"] or 0, r["mtime"] or 0)
            for r in c.execute("SELECT jsonl_path, offset, mtime FROM jsonl_offsets")
        }
    now_ms = int(time.time() * 1000)
    stale_seeds: list[tuple] = []
    for project_dir_path in PROJECTS_DIR.iterdir():
        if not project_dir_path.is_dir():
            continue
        for jsonl in project_dir_path.rglob("*.jsonl"):
            # Direct children are sessions; deeper files are subagent /
            # workflow transcripts (usage events only, never sessions rows).
            nested = jsonl.parent != project_dir_path
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
                    stale_seeds.append((str(jsonl), jsonl.stem, size, mtime_ms))
                    stats["skippedOld"] += 1
                    continue
                with INDEX_LOCK:
                    # Re-check under the lock — the boot-time full indexer
                    # may have claimed this file after our cycle snapshot.
                    with _db() as c:
                        claimed = c.execute(
                            "SELECT 1 FROM jsonl_offsets WHERE jsonl_path=?",
                            (str(jsonl),),
                        ).fetchone()
                    if claimed:
                        continue
                    if nested:
                        pass  # handled below, outside this lock scope
                    elif _index_jsonl_unlocked(jsonl, project_dir_path.name):
                        stats["full"] += 1
                        continue
                    else:
                        # Empty/unparseable file — seed the cursor at 0 so it
                        # isn't re-parsed every cycle; appended bytes will be
                        # picked up by the tail path later.
                        with _db() as c:
                            c.execute(
                                "INSERT OR REPLACE INTO jsonl_offsets (jsonl_path,session_id,offset,mtime) VALUES (?,?,?,?)",
                                (str(jsonl), jsonl.stem, 0, 0),
                            )
                        continue
                if nested:
                    n = _ingest_nested(jsonl, mtime_ms, truncated=False)
                    stats["full"] += 1
                    stats["events"] += n
                continue
            offset, _prev_mtime = prev
            if size == offset:
                continue
            if _QUIET.get(str(jsonl)) == (size, mtime_ms):
                continue
            if size < offset:
                # Rewritten/truncated (e.g. compaction) — full re-parse.
                if nested:
                    stats["events"] += _ingest_nested(jsonl, mtime_ms, truncated=True)
                    stats["full"] += 1
                else:
                    with INDEX_LOCK:
                        if _index_jsonl_unlocked(jsonl, project_dir_path.name):
                            stats["full"] += 1
                continue
            n = _tail_file(jsonl, mtime_ms, update_session=not nested)
            if n:
                stats["tailed"] += 1
                stats["events"] += n
    if stale_seeds:
        # One transaction for the whole historical backlog (first run after
        # upgrade can be hundreds of files).
        with INDEX_LOCK, _db() as c:
            c.executemany(
                "INSERT OR IGNORE INTO jsonl_offsets (jsonl_path,session_id,offset,mtime) VALUES (?,?,?,?)",
                stale_seeds,
            )
    return stats


def _cleanup_once() -> None:
    """Prune old events and rows for files deleted from disk."""
    cutoff = int(time.time() * 1000) - _RETENTION_DAYS * 86400 * 1000
    with _db() as c:
        c.execute("DELETE FROM usage_events WHERE ts < ?", (cutoff,))
        paths = [r["jsonl_path"] for r in c.execute("SELECT jsonl_path FROM jsonl_offsets")]
    gone = [(p, Path(p).stem) for p in paths if not Path(p).exists()]
    if gone:
        with _db() as c:
            c.executemany("DELETE FROM jsonl_offsets WHERE jsonl_path=?", [(p,) for p, _ in gone])
            c.executemany("DELETE FROM usage_events WHERE session_id=?", [(s,) for _, s in gone])
        for p, _ in gone:
            _QUIET.pop(p, None)


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
        cycles = 0
        while True:
            try:
                r = _tail_once()
                if r["events"] or r["full"]:
                    log.debug("usage tail: %s", r)
            except Exception as e:
                log.warning("usage tail cycle failed: %s", e)
            cycles += 1
            if cycles % _CLEANUP_EVERY_CYCLES == 1:
                try:
                    _cleanup_once()
                except Exception as e:
                    log.warning("usage cleanup failed: %s", e)
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
