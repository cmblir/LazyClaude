"""'Today' cockpit — single-screen daily overview aggregator.

Read-only roll-ups over the `sessions` SQLite table (see `server/db.py` /
`server/system.py` for the canonical column list). Every figure on the
cockpit comes from data already indexed by the background session indexer:

- today's token total + estimated USD (and the delta vs yesterday),
- today's session count + the most-recently-active project,
- the top 3 projects by tokens today,
- tokens grouped by model today,
- a 14-day token spark series (oldest → newest),
- a recent-activity list (latest sessions across all projects).

`sessions.started_at` is epoch **milliseconds**. Day bucketing uses SQLite's
`date(..., 'unixepoch', 'localtime')` so "today" matches the user's wall
clock, not UTC.

Pricing reuses `cost_timeline._PRICING` for the per-MTok input/output rates
and applies the standard cache multipliers (cache_read 0.1x of input,
cache_write/creation 1.25x of input) so the USD figure lines up with the
project's other cost estimates.
"""
from __future__ import annotations

import time
from pathlib import Path

from .cost_timeline import _PRICING
from .db import _db, _db_init
from .logger import log

# Cache token multipliers relative to the model's input price.
# Verified against the official prompt-caching pricing model (2026): a cache
# read is billed at 0.1x the base input rate, a 5-minute cache write at 1.25x.
_CACHE_READ_MULT = 0.1
_CACHE_WRITE_MULT = 1.25


def _price_for(model: str) -> dict | None:
    """Resolve the per-MTok price row for a model id (substring match)."""
    m = model or ""
    for mid, p in _PRICING.items():
        if mid in m:
            return p
    return None


def _estimate_usd(model: str, ti: int, to: int, cr: int, cc: int) -> float:
    """Estimate USD for one session's token breakdown.

    ti/to/cr/cc are input / output / cache_read / cache_creation token counts.
    Unknown models contribute $0 (no guessing) — same policy as
    cost_timeline._estimate.
    """
    price = _price_for(model)
    if not price:
        return 0.0
    in_rate = price["in"]
    out_rate = price["out"]
    usd = (
        (ti / 1_000_000) * in_rate
        + (to / 1_000_000) * out_rate
        + (cr / 1_000_000) * in_rate * _CACHE_READ_MULT
        + (cc / 1_000_000) * in_rate * _CACHE_WRITE_MULT
    )
    return usd


def _row_tokens(r) -> tuple[int, int, int, int, int]:
    """(input, output, cache_read, cache_creation, total) from a sessions row."""
    return (
        int(r["ti"] or 0),
        int(r["to_"] or 0),
        int(r["cr"] or 0),
        int(r["cc"] or 0),
        int(r["tot"] or 0),
    )


# Column projection shared by the per-day aggregate queries.
_TOKEN_COLS = (
    "COALESCE(SUM(input_tokens),0) AS ti, "
    "COALESCE(SUM(output_tokens),0) AS to_, "
    "COALESCE(SUM(cache_read_tokens),0) AS cr, "
    "COALESCE(SUM(cache_creation_tokens),0) AS cc, "
    "COALESCE(SUM(total_tokens),0) AS tot, "
    "COUNT(*) AS n"
)

# Local-time day expression for a started_at column in ms.
_DAY_EXPR = "date(started_at/1000, 'unixepoch', 'localtime')"


def _project_name(cwd: str, project: str, project_dir: str) -> str:
    """Best-effort human label for a project, mirroring system.py's logic."""
    if cwd:
        return Path(cwd).name or cwd
    if project:
        return project
    if project_dir:
        return Path(project_dir).name or project_dir
    return "—"


def _summary() -> dict:
    _db_init()
    now = time.time()
    # Trailing 14-day window (inclusive of today) in ms for the spark series.
    spark_since_ms = int((now - 13 * 86400) * 1000)

    with _db() as c:
        today_key = c.execute(
            "SELECT date('now', 'localtime') AS d"
        ).fetchone()["d"]
        yest_key = c.execute(
            "SELECT date('now', '-1 day', 'localtime') AS d"
        ).fetchone()["d"]

        def _day_totals(day_key: str):
            return c.execute(
                f"SELECT {_TOKEN_COLS} FROM sessions "
                f"WHERE {_DAY_EXPR} = ?",
                (day_key,),
            ).fetchone()

        today_tot = _day_totals(today_key)
        yest_tot = _day_totals(yest_key)

        t_ti, t_to, t_cr, t_cc, t_total = _row_tokens(today_tot)
        y_ti, y_to, y_cr, y_cc, y_total = _row_tokens(yest_tot)
        today_sessions = int(today_tot["n"] or 0)
        yest_sessions = int(yest_tot["n"] or 0)

        # Top 3 projects today by tokens.
        top_rows = c.execute(
            "SELECT COALESCE(NULLIF(cwd,''), project_dir) AS key, "
            "       MAX(cwd) AS cwd, MAX(project) AS project, "
            "       MAX(project_dir) AS project_dir, "
            "       COUNT(*) AS sessions, "
            "       COALESCE(SUM(total_tokens),0) AS tokens "
            f"FROM sessions WHERE {_DAY_EXPR} = ? "
            "GROUP BY COALESCE(NULLIF(cwd,''), project_dir) "
            "ORDER BY tokens DESC LIMIT 3",
            (today_key,),
        ).fetchall()
        top_projects = [
            {
                "key": r["key"] or "",
                "cwd": r["cwd"] or "",
                "name": _project_name(r["cwd"] or "", r["project"] or "", r["project_dir"] or ""),
                "sessions": int(r["sessions"] or 0),
                "tokens": int(r["tokens"] or 0),
            }
            for r in top_rows
        ]

        # Tokens by model today (with per-model USD estimate).
        model_rows = c.execute(
            "SELECT COALESCE(NULLIF(model,''), '(unknown)') AS model, "
            "       COUNT(*) AS sessions, "
            "       COALESCE(SUM(input_tokens),0) AS ti, "
            "       COALESCE(SUM(output_tokens),0) AS to_, "
            "       COALESCE(SUM(cache_read_tokens),0) AS cr, "
            "       COALESCE(SUM(cache_creation_tokens),0) AS cc, "
            "       COALESCE(SUM(total_tokens),0) AS tot "
            f"FROM sessions WHERE {_DAY_EXPR} = ? "
            "GROUP BY COALESCE(NULLIF(model,''), '(unknown)') "
            "ORDER BY tot DESC",
            (today_key,),
        ).fetchall()
        by_model = []
        for r in model_rows:
            mi, mo, mcr, mcc, mtot = _row_tokens(r)
            by_model.append({
                "model": r["model"],
                "sessions": int(r["sessions"] or 0),
                "tokens": mtot,
                "usd": round(_estimate_usd(r["model"], mi, mo, mcr, mcc), 6),
            })

        # 14-day spark series — one bucket per local day, zero-filled.
        spark_rows = c.execute(
            f"SELECT {_DAY_EXPR} AS d, "
            "       COALESCE(SUM(total_tokens),0) AS tokens, "
            "       COUNT(*) AS sessions "
            "FROM sessions WHERE started_at >= ? "
            f"GROUP BY d",
            (spark_since_ms,),
        ).fetchall()
        spark_map = {r["d"]: r for r in spark_rows}

        # Recent activity — latest sessions across all projects.
        recent_rows = c.execute(
            "SELECT session_id, project, project_dir, cwd, model, "
            "       first_user_prompt, total_tokens, message_count, "
            "       tool_use_count, started_at "
            "FROM sessions "
            "ORDER BY started_at DESC LIMIT 12"
        ).fetchall()

    # Estimate today's / yesterday's USD from the aggregate token mix.
    # NOTE: this uses the aggregate token sums against the dominant model, so
    # it's an approximation when a day mixes models — the per-model `byModel`
    # breakdown above is exact per model. We sum the per-model estimates for
    # today to keep the headline figure consistent with the breakdown.
    today_usd = round(sum(m["usd"] for m in by_model), 6)

    # Yesterday USD — recompute per-model in a lightweight pass for the delta.
    _db_init()
    with _db() as c:
        y_model_rows = c.execute(
            "SELECT COALESCE(NULLIF(model,''), '(unknown)') AS model, "
            "       COALESCE(SUM(input_tokens),0) AS ti, "
            "       COALESCE(SUM(output_tokens),0) AS to_, "
            "       COALESCE(SUM(cache_read_tokens),0) AS cr, "
            "       COALESCE(SUM(cache_creation_tokens),0) AS cc "
            f"FROM sessions WHERE {_DAY_EXPR} = ? "
            "GROUP BY COALESCE(NULLIF(model,''), '(unknown)')",
            (yest_key,),
        ).fetchall()
    yest_usd = 0.0
    for r in y_model_rows:
        mi = int(r["ti"] or 0)
        mo = int(r["to_"] or 0)
        mcr = int(r["cr"] or 0)
        mcc = int(r["cc"] or 0)
        yest_usd += _estimate_usd(r["model"], mi, mo, mcr, mcc)
    yest_usd = round(yest_usd, 6)

    # Build the zero-filled 14-day spark series oldest → newest.
    import datetime as dt
    today_date = dt.date.today()
    spark = []
    for i in range(13, -1, -1):
        d = (today_date - dt.timedelta(days=i)).isoformat()
        row = spark_map.get(d)
        spark.append({
            "date": d,
            "tokens": int(row["tokens"]) if row else 0,
            "sessions": int(row["sessions"]) if row else 0,
        })

    recent = []
    most_recent_project = ""
    most_recent_cwd = ""
    for idx, r in enumerate(recent_rows):
        name = _project_name(r["cwd"] or "", r["project"] or "", r["project_dir"] or "")
        if idx == 0:
            most_recent_project = name
            most_recent_cwd = r["cwd"] or ""
        recent.append({
            "sessionId": r["session_id"],
            "project": name,
            "cwd": r["cwd"] or "",
            "model": r["model"] or "",
            "prompt": (r["first_user_prompt"] or "")[:200],
            "tokens": int(r["total_tokens"] or 0),
            "messages": int(r["message_count"] or 0),
            "tools": int(r["tool_use_count"] or 0),
            "startedAt": int(r["started_at"] or 0),
        })

    def _delta(today_v, yest_v):
        diff = today_v - yest_v
        pct = None
        if yest_v > 0:
            pct = round(diff / yest_v * 100, 1)
        return {"yesterday": yest_v, "diff": diff, "pct": pct}

    return {
        "ok": True,
        "today": today_key,
        "yesterday": yest_key,
        "computedAt": int(now * 1000),
        "tokens": {
            "total": t_total,
            "input": t_ti,
            "output": t_to,
            "cacheRead": t_cr,
            "cacheCreate": t_cc,
        },
        "usd": today_usd,
        "sessions": today_sessions,
        "delta": {
            "tokens": _delta(t_total, y_total),
            "usd": _delta(round(today_usd, 6), yest_usd),
            "sessions": _delta(today_sessions, yest_sessions),
        },
        "mostRecentProject": most_recent_project,
        "mostRecentCwd": most_recent_cwd,
        "topProjects": top_projects,
        "byModel": by_model,
        "spark": spark,
        "recent": recent,
    }


def api_today_summary(_q: dict | None = None) -> dict:
    """GET /api/today/summary — the 'Today' cockpit roll-up.

    Takes no parameters (registered via `lambda q: api_today_summary()`).
    Read-only; never writes. Returns ``{"ok": False, "error": ...}`` on any
    failure rather than raising, so the cockpit can degrade gracefully.
    """
    try:
        return _summary()
    except Exception as e:
        log.warning("today summary failed: %s", e)
        return {"ok": False, "error": str(e)}
