"""Spend budgets · threshold alerts · persistent alerts center (feature #6).

Generalizes the narrow per-batch cost guard in ``batch_jobs.py``
(``_load_budget`` / ``_save_budget`` / ``maxPerBatchUsd``) into configurable
**daily** and **monthly** caps — in USD and/or tokens — optionally scoped per
spend source (claude-code sessions vs workflow runs vs playground labs).

Persistence
-----------
- Caps + alert thresholds live in ``~/.claude-dashboard-budget.json``
  (override via ``CLAUDE_DASHBOARD_BUDGET``; falls back next to
  ``DASHBOARD_CONFIG_PATH`` family). Written atomically (tmp + rename) and
  ``chmod 600`` — same hygiene as ``ai_keys`` / ``slack`` secret files even
  though caps are not secrets, so the file is consistent with siblings.
- Threshold breaches are recorded in a lazily-created SQLite table
  ``budget_alerts`` (``id / ts / level / scope / period / message / dismissed``).
  We do **not** edit ``server/db.py`` — the table is created on first use via
  an ``_ensure_alerts_table`` helper, mirroring the lazy-table pattern.

Spend source of truth
----------------------
Current spend is **estimated** from the ``sessions`` table token columns priced
with the same per-1M-token rates as ``cost_timeline`` (``_PRICING`` /
``_estimate``). claude-code sessions are the only source carrying per-row
token + timestamp + model in SQLite; workflow / labs spend is read from the
cost-timeline aggregator so per-source caps can still be evaluated.

NOTE (refinement path): admin/OTel actuals (``admin_api`` / ``otel_ingest``)
can later replace the estimate for the ``claude-code`` source. Until then the
status payload flags ``estimated: true`` so the UI can disclose it.

Handlers
--------
- ``api_budget_status(query)`` — today/month spend vs caps, % used, per source.
- ``api_budget_set(body)``     — persist caps + thresholds; re-evaluate alerts.
- ``api_alerts_list(query)``   — recent alerts (optionally include dismissed).
- ``api_alert_dismiss(body)``  — mark one (or all) alert(s) dismissed.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DASHBOARD_CONFIG_PATH, _env_path
from .cost_timeline import _PRICING, _estimate
from .db import _db, _db_init
from .logger import log
from .utils import _safe_write

# ───────── persistence path ─────────

# Default sits next to the other ~/.claude-dashboard-*.json stores so the whole
# family lives together; overridable via env. DASHBOARD_CONFIG_PATH is imported
# so a deployment that relocates the config family also relocates this file.
_DEFAULT_BUDGET_PATH = DASHBOARD_CONFIG_PATH.parent / ".claude-dashboard-budget.json"


def _budget_path() -> Path:
    return _env_path("CLAUDE_DASHBOARD_BUDGET", _DEFAULT_BUDGET_PATH)


# ───────── cap model ─────────

# Spend sources we can scope caps to. "all" = aggregate of everything.
_SOURCES = ("all", "claude-code", "workflow", "labs")

# Cache pricing multipliers relative to the input (per-1M) rate, per the task
# spec (cache_read 0.1x, cache_write 1.25x). The sessions table carries
# cache_read_tokens / cache_creation_tokens separately from input/output, so we
# price them explicitly rather than folding into the plain input estimate.
_CACHE_READ_MULT = 0.1
_CACHE_WRITE_MULT = 1.25


def _empty_cap() -> dict:
    """A cap entry: 0 / None means "no limit" for that dimension."""
    return {"dailyUsd": 0.0, "monthlyUsd": 0.0, "dailyTokens": 0, "monthlyTokens": 0}


def _default_budget() -> dict:
    return {
        "enabled": False,
        # Threshold fractions (of any active cap) that fire an alert when
        # crossed. Stored as fractions 0..1; UI shows percent.
        "thresholds": [0.8, 1.0],
        # Per-source caps. "all" is the headline aggregate cap; the others are
        # optional sub-caps so e.g. labs spend can be bounded independently.
        "caps": {s: _empty_cap() for s in _SOURCES},
    }


def _coerce_cap(raw: Any) -> dict:
    cap = _empty_cap()
    if not isinstance(raw, dict):
        return cap
    for k, caster in (
        ("dailyUsd", float), ("monthlyUsd", float),
        ("dailyTokens", int), ("monthlyTokens", int),
    ):
        v = raw.get(k)
        if v is None:
            continue
        try:
            cv = caster(v)
        except (TypeError, ValueError):
            continue
        cap[k] = cv if cv > 0 else (0.0 if caster is float else 0)
    return cap


def _load_budget() -> dict:
    p = _budget_path()
    base = _default_budget()
    if not p.exists():
        return base
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("budget load failed (%s): %s", p, e)
        return base
    if not isinstance(data, dict):
        return base
    base["enabled"] = bool(data.get("enabled", False))
    thr = data.get("thresholds")
    if isinstance(thr, list):
        clean = []
        for x in thr:
            try:
                f = float(x)
            except (TypeError, ValueError):
                continue
            if 0 < f <= 2:  # allow >100% (e.g. 1.0, but cap at 200%)
                clean.append(round(f, 4))
        if clean:
            base["thresholds"] = sorted(set(clean))
    caps_in = data.get("caps") or {}
    if isinstance(caps_in, dict):
        for s in _SOURCES:
            base["caps"][s] = _coerce_cap(caps_in.get(s))
    return base


def _save_budget(data: dict) -> bool:
    p = _budget_path()
    ok = _safe_write(p, json.dumps(data, ensure_ascii=False, indent=2))
    if ok:
        try:
            os.chmod(p, 0o600)
        except Exception:
            pass
    return ok


# ───────── period boundaries (local time) ─────────

def _period_start_ms(period: str) -> int:
    """Epoch-ms start of the current local 'day' or 'month'."""
    now = datetime.now()
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # day
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


# ───────── spend computation ─────────

def _estimate_session_cost(model: str, ti: int, to: int, cr: int, cc: int) -> float:
    """Price one session's token columns with cost_timeline rates.

    input/output use cost_timeline._estimate (single-sourced pricing);
    cache_read / cache_write are priced off the model's input rate with the
    spec multipliers (0.1x / 1.25x).
    """
    base = _estimate(model, ti, to)
    # Recover the input per-1M rate for the matched model to price cache tokens.
    in_rate = 0.0
    for mid, p in _PRICING.items():
        if mid in (model or ""):
            in_rate = p["in"]
            break
    cache_usd = (cr / 1_000_000) * in_rate * _CACHE_READ_MULT \
        + (cc / 1_000_000) * in_rate * _CACHE_WRITE_MULT
    return base + cache_usd


def _claude_code_spend(since_ms: int) -> dict:
    """Sum estimated USD + tokens from the sessions table since `since_ms`."""
    _db_init()
    usd = 0.0
    tokens = 0
    with _db() as c:
        rows = c.execute(
            "SELECT model, "
            "       COALESCE(input_tokens,0) ti, COALESCE(output_tokens,0) to_, "
            "       COALESCE(cache_read_tokens,0) cr, COALESCE(cache_creation_tokens,0) cc, "
            "       COALESCE(total_tokens,0) tot "
            "FROM sessions WHERE started_at >= ?",
            (since_ms,),
        ).fetchall()
    for r in rows:
        usd += _estimate_session_cost(
            r["model"] or "", r["ti"] or 0, r["to_"] or 0, r["cr"] or 0, r["cc"] or 0
        )
        tokens += int(r["tot"] or 0)
    return {"usd": round(usd, 6), "tokens": tokens}


def _timeline_spend(since_sec: int) -> dict[str, dict]:
    """Workflow + labs spend since `since_sec` (epoch seconds), via cost_timeline.

    Returns {"workflow": {usd, tokens}, "labs": {usd, tokens}}. The cost
    aggregator entries carry source ids: "workflows" → workflow; every other
    playground source (promptCache, thinkingLab, …) → labs.
    """
    out = {"workflow": {"usd": 0.0, "tokens": 0}, "labs": {"usd": 0.0, "tokens": 0}}
    try:
        from .cost_timeline import _gather_all
        for e in _gather_all():
            if int(e.get("ts") or 0) < since_sec:
                continue
            bucket = "workflow" if e.get("source") == "workflows" else "labs"
            out[bucket]["usd"] = round(out[bucket]["usd"] + float(e.get("usd") or 0), 6)
            out[bucket]["tokens"] += int(e.get("tokensIn") or 0) + int(e.get("tokensOut") or 0)
    except Exception as e:
        log.warning("timeline spend failed: %s", e)
    return out


def _spend_for_period(period: str) -> dict[str, dict]:
    """Per-source {usd, tokens} for the current day or month."""
    start_ms = _period_start_ms(period)
    start_sec = start_ms // 1000
    cc = _claude_code_spend(start_ms)
    tl = _timeline_spend(start_sec)
    workflow = tl["workflow"]
    labs = tl["labs"]
    allsrc = {
        "usd": round(cc["usd"] + workflow["usd"] + labs["usd"], 6),
        "tokens": cc["tokens"] + workflow["tokens"] + labs["tokens"],
    }
    return {"all": allsrc, "claude-code": cc, "workflow": workflow, "labs": labs}


def _pct(spent: float, cap: float) -> float | None:
    if not cap or cap <= 0:
        return None
    return round(spent / cap * 100, 1)


def _build_status(budget: dict) -> dict:
    day = _spend_for_period("day")
    month = _spend_for_period("month")
    caps = budget.get("caps") or {}
    sources = []
    for s in _SOURCES:
        cap = caps.get(s) or _empty_cap()
        d = day.get(s, {"usd": 0.0, "tokens": 0})
        m = month.get(s, {"usd": 0.0, "tokens": 0})
        sources.append({
            "source": s,
            "daily": {
                "spentUsd": d["usd"], "spentTokens": d["tokens"],
                "capUsd": cap["dailyUsd"], "capTokens": cap["dailyTokens"],
                "pctUsd": _pct(d["usd"], cap["dailyUsd"]),
                "pctTokens": _pct(d["tokens"], cap["dailyTokens"]),
            },
            "monthly": {
                "spentUsd": m["usd"], "spentTokens": m["tokens"],
                "capUsd": cap["monthlyUsd"], "capTokens": cap["monthlyTokens"],
                "pctUsd": _pct(m["usd"], cap["monthlyUsd"]),
                "pctTokens": _pct(m["tokens"], cap["monthlyTokens"]),
            },
        })
    return {
        "enabled": bool(budget.get("enabled")),
        "thresholds": budget.get("thresholds") or [0.8, 1.0],
        "estimated": True,
        "computedAt": int(time.time() * 1000),
        "sources": sources,
    }


# ───────── alerts table (lazy) ─────────

_ALERTS_READY = False


def _ensure_alerts_table() -> None:
    """Create budget_alerts lazily. Does NOT touch db.py's schema init."""
    global _ALERTS_READY
    if _ALERTS_READY:
        return
    _db_init()
    with _db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS budget_alerts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts INTEGER,
              level TEXT,
              scope TEXT,
              period TEXT,
              dimension TEXT,
              threshold REAL,
              pct REAL,
              message TEXT,
              dedupe_key TEXT,
              dismissed INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_budget_alerts_ts ON budget_alerts(ts DESC);
            CREATE INDEX IF NOT EXISTS idx_budget_alerts_active ON budget_alerts(dismissed, ts DESC);
            CREATE INDEX IF NOT EXISTS idx_budget_alerts_dedupe ON budget_alerts(dedupe_key);
            """
        )
    _ALERTS_READY = True


def _level_for(threshold: float) -> str:
    return "critical" if threshold >= 1.0 else "warning"


def _alert_message(scope: str, period: str, dimension: str, threshold: float,
                   pct: float, spent: float, cap: float) -> str:
    src_label = {
        "all": "전체", "claude-code": "Claude Code 세션",
        "workflow": "워크플로우", "labs": "플레이그라운드",
    }.get(scope, scope)
    per_label = "월" if period == "month" else "일"
    if dimension == "usd":
        return (f"{src_label} {per_label} 지출이 한도의 {int(round(threshold * 100))}%를 "
                f"넘었습니다 (${spent:.4f} / ${cap:.2f}, {pct:.0f}%).")
    return (f"{src_label} {per_label} 토큰이 한도의 {int(round(threshold * 100))}%를 "
            f"넘었습니다 ({spent:,.0f} / {cap:,.0f}, {pct:.0f}%).")


def _dedupe_key(scope: str, period: str, dimension: str, threshold: float) -> str:
    """One alert per (scope, period, dimension, threshold) per period bucket.

    The bucket is the period start so a fresh day/month re-arms each threshold.
    """
    bucket = _period_start_ms(period)
    return f"{scope}:{period}:{dimension}:{threshold}:{bucket}"


def _evaluate_and_record(budget: dict, status: dict) -> int:
    """Record any newly-breached thresholds. Returns count of new alerts.

    Idempotent within a period via dedupe_key — calling repeatedly (status
    poll, after a save) will not duplicate an alert already on file for the
    same period bucket.
    """
    if not budget.get("enabled"):
        return 0
    thresholds = budget.get("thresholds") or [0.8, 1.0]
    _ensure_alerts_table()
    now = int(time.time() * 1000)
    new_rows: list[tuple] = []

    for src in status.get("sources", []):
        scope = src["source"]
        for period in ("daily", "monthly"):
            blk = src[period]
            period_key = "month" if period == "monthly" else "day"
            for dim, spent_key, cap_key, pct_key in (
                ("usd", "spentUsd", "capUsd", "pctUsd"),
                ("tokens", "spentTokens", "capTokens", "pctTokens"),
            ):
                cap = blk[cap_key]
                if not cap or cap <= 0:
                    continue
                spent = blk[spent_key]
                frac = spent / cap if cap else 0
                for thr in thresholds:
                    if frac >= thr:
                        pct = round(frac * 100, 1)
                        dk = _dedupe_key(scope, period_key, dim, thr)
                        new_rows.append((
                            now, _level_for(thr), scope, period_key, dim, thr, pct,
                            _alert_message(scope, period_key, dim, thr, pct, spent, cap),
                            dk,
                        ))

    if not new_rows:
        return 0
    inserted = 0
    with _db() as c:
        for row in new_rows:
            dk = row[-1]
            exists = c.execute(
                "SELECT 1 FROM budget_alerts WHERE dedupe_key = ? LIMIT 1", (dk,)
            ).fetchone()
            if exists:
                continue
            c.execute(
                "INSERT INTO budget_alerts "
                "(ts, level, scope, period, dimension, threshold, pct, message, dedupe_key, dismissed) "
                "VALUES (?,?,?,?,?,?,?,?,?,0)",
                row,
            )
            inserted += 1
    return inserted


# ───────── public handlers ─────────

def api_budget_status(query: dict | None = None) -> dict:
    """GET /api/budget/status — current spend vs caps + fires due alerts."""
    try:
        budget = _load_budget()
        status = _build_status(budget)
        new_alerts = _evaluate_and_record(budget, status)
        active = 0
        try:
            _ensure_alerts_table()
            with _db() as c:
                r = c.execute(
                    "SELECT COUNT(*) n FROM budget_alerts WHERE dismissed = 0"
                ).fetchone()
                active = int(r["n"] or 0)
        except Exception:
            pass
        return {
            "ok": True,
            "budget": budget,
            "status": status,
            "newAlerts": new_alerts,
            "activeAlerts": active,
        }
    except Exception as e:
        log.exception("budget status failed")
        return {"ok": False, "error": str(e)}


def api_budget_set(body: dict) -> dict:
    """POST /api/budget/set — persist caps + thresholds.

    Body shape (all optional; missing keys keep current values)::

        {
          "enabled": true,
          "thresholds": [0.8, 1.0],
          "caps": {
            "all":         {"dailyUsd": 5, "monthlyUsd": 100, "dailyTokens": 0, "monthlyTokens": 0},
            "claude-code": {...}, "workflow": {...}, "labs": {...}
          }
        }
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    cur = _load_budget()
    if "enabled" in body:
        cur["enabled"] = bool(body.get("enabled"))
    if "thresholds" in body:
        thr = body.get("thresholds")
        if not isinstance(thr, list) or not thr:
            return {"ok": False, "error": "thresholds must be a non-empty list"}
        clean = []
        for x in thr:
            try:
                f = float(x)
            except (TypeError, ValueError):
                return {"ok": False, "error": "thresholds must be numbers (fractions, e.g. 0.8)"}
            if not (0 < f <= 2):
                return {"ok": False, "error": "thresholds must be in (0, 2]"}
            clean.append(round(f, 4))
        cur["thresholds"] = sorted(set(clean))
    caps_in = body.get("caps")
    if caps_in is not None:
        if not isinstance(caps_in, dict):
            return {"ok": False, "error": "caps must be an object"}
        for s in _SOURCES:
            if s in caps_in:
                cur["caps"][s] = _coerce_cap(caps_in.get(s))
    if not _save_budget(cur):
        return {"ok": False, "error": "save failed"}
    # Re-evaluate so lowering a cap immediately surfaces a breach.
    status = _build_status(cur)
    new_alerts = _evaluate_and_record(cur, status)
    return {"ok": True, "budget": cur, "status": status, "newAlerts": new_alerts}


def api_alerts_list(query: dict | None = None) -> dict:
    """GET /api/alerts/list?includeDismissed=1&limit=100"""
    q = query or {}

    def _qs(key: str, default: str = "") -> str:
        v = q.get(key) if isinstance(q, dict) else None
        if isinstance(v, list):
            v = v[0] if v else None
        return v if isinstance(v, str) else default

    include_dismissed = _qs("includeDismissed").lower() in ("1", "true", "yes", "on")
    try:
        limit = int(_qs("limit", "100") or 100)
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(500, limit))
    try:
        _ensure_alerts_table()
        where = "" if include_dismissed else "WHERE dismissed = 0"
        with _db() as c:
            rows = [dict(r) for r in c.execute(
                f"SELECT id, ts, level, scope, period, dimension, threshold, pct, "
                f"       message, dismissed "
                f"FROM budget_alerts {where} ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()]
            active = int(c.execute(
                "SELECT COUNT(*) n FROM budget_alerts WHERE dismissed = 0"
            ).fetchone()["n"] or 0)
        return {"ok": True, "alerts": rows, "activeCount": active}
    except Exception as e:
        log.exception("alerts list failed")
        return {"ok": False, "error": str(e)}


def api_alert_dismiss(body: dict) -> dict:
    """POST /api/alert/dismiss — body {id} or {all: true}."""
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    try:
        _ensure_alerts_table()
        if body.get("all"):
            with _db() as c:
                cur = c.execute("UPDATE budget_alerts SET dismissed = 1 WHERE dismissed = 0")
                n = cur.rowcount
            return {"ok": True, "dismissed": n}
        aid = body.get("id")
        try:
            aid = int(aid)
        except (TypeError, ValueError):
            return {"ok": False, "error": "id required (int) or all=true"}
        with _db() as c:
            cur = c.execute("UPDATE budget_alerts SET dismissed = 1 WHERE id = ?", (aid,))
            n = cur.rowcount
        if not n:
            return {"ok": False, "error": "alert not found"}
        return {"ok": True, "dismissed": n}
    except Exception as e:
        log.exception("alert dismiss failed")
        return {"ok": False, "error": str(e)}
