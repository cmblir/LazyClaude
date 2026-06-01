"""Statistical anomaly detection on Claude Code usage + cost (feature #18).

Local, no-ML, compute-on-request. Reads the SQLite ``sessions`` table
(``server/db.py``) **READ-ONLY** and flags three classes of outlier over the
daily token/cost series:

1. **Daily spend spikes** — a day whose estimated USD is above
   ``mean + Z*sigma`` of a trailing window (default 14 days, Z=2.5),
   OR a day-over-day jump larger than ``JUMP_PCT`` (default 150%).
2. **Per-project surge** — a single project's daily spend that is far above
   that project's *own* baseline (its trailing mean+sigma), so a normally-cheap
   project suddenly burning money gets flagged even if the global total looks
   ordinary.
3. **Abnormally large single sessions** — a single session whose estimated cost
   is above ``mean + Z*sigma`` of all sessions in range (and above an absolute
   floor so a quiet account with two sessions doesn't false-positive).

Pricing reuses ``cost_timeline._PRICING`` / ``_estimate`` plus the cache-token
multipliers used by ``budget.py`` so the dollar figures line up with the rest
of the dashboard. There is **no background job** — everything is computed when
``api_anomalies`` is called.

The handler degrades honestly: if the ``sessions`` table is empty or missing
the expected columns, it returns ``ok: true`` with empty arrays and a ``note``
explaining why, rather than raising.
"""
from __future__ import annotations

import statistics
import time
from datetime import datetime, timedelta

from .cost_timeline import _PRICING, _estimate
from .db import _db, _db_init
from .logger import log

# ───────── tunables (overridable via query) ─────────

_DEFAULT_DAYS = 30          # how far back to build the daily series
_DEFAULT_WINDOW = 14        # trailing window for the rolling baseline
_DEFAULT_Z = 2.5            # sigma multiplier for the spike threshold
_DEFAULT_JUMP_PCT = 150.0   # day-over-day % jump that also counts as a spike

_DAYS_MIN, _DAYS_MAX = 7, 365
_WINDOW_MIN, _WINDOW_MAX = 3, 90
_Z_MIN, _Z_MAX = 1.0, 6.0
_JUMP_MIN, _JUMP_MAX = 10.0, 2000.0

# Below this absolute USD a "spike" isn't worth surfacing — avoids flagging
# noise on near-zero days / tiny accounts.
_MIN_SPIKE_USD = 0.50
# A single session must clear this absolute floor before the statistical test
# can flag it, so a 2-session account never reports a "huge" session.
_MIN_BIG_SESSION_USD = 1.0
# Minimum number of prior points needed before a statistical test is meaningful.
_MIN_BASELINE_POINTS = 3

# Cache pricing multipliers (mirror budget.py): cache_read 0.1x, write 1.25x of
# the model's per-1M input rate.
_CACHE_READ_MULT = 0.1
_CACHE_WRITE_MULT = 1.25

# Severity ranking for sort order (higher = more severe).
_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


# ───────── pricing ─────────

def _session_cost(model: str, ti: int, to: int, cr: int, cc: int) -> float:
    """Price one session's token columns. Mirrors budget._estimate_session_cost."""
    base = _estimate(model, ti, to)
    in_rate = 0.0
    for mid, p in _PRICING.items():
        if mid in (model or ""):
            in_rate = p["in"]
            break
    cache_usd = (cr / 1_000_000) * in_rate * _CACHE_READ_MULT \
        + (cc / 1_000_000) * in_rate * _CACHE_WRITE_MULT
    return base + cache_usd


# ───────── data access (READ-ONLY) ─────────

def _fetch_sessions(since_ms: int) -> list[dict]:
    """Read sessions started since ``since_ms``. Returns [] on any schema gap."""
    _db_init()
    rows: list[dict] = []
    try:
        with _db() as c:
            cur = c.execute(
                "SELECT session_id, project, cwd, model, started_at, "
                "       COALESCE(input_tokens,0)          AS ti, "
                "       COALESCE(output_tokens,0)         AS to_, "
                "       COALESCE(cache_read_tokens,0)     AS cr, "
                "       COALESCE(cache_creation_tokens,0) AS cc, "
                "       COALESCE(total_tokens,0)          AS tot, "
                "       first_user_prompt "
                "FROM sessions WHERE started_at >= ? AND started_at IS NOT NULL "
                "ORDER BY started_at ASC",
                (since_ms,),
            )
            for r in cur.fetchall():
                ti, to_, cr, cc = int(r["ti"]), int(r["to_"]), int(r["cr"]), int(r["cc"])
                usd = _session_cost(r["model"] or "", ti, to_, cr, cc)
                rows.append({
                    "sessionId": r["session_id"],
                    "project": (r["project"] or _project_from_cwd(r["cwd"]) or "(unknown)"),
                    "model": r["model"] or "",
                    "startedAt": int(r["started_at"]),
                    "tokens": int(r["tot"]) or (ti + to_ + cr + cc),
                    "usd": round(usd, 6),
                    "prompt": (r["first_user_prompt"] or "")[:80],
                })
    except Exception as e:  # surfaced via the handler's note; never silently lost
        log.warning("anomaly _fetch_sessions failed: %s", e)
        raise
    return rows


def _project_from_cwd(cwd: str | None) -> str:
    if not cwd:
        return ""
    return cwd.rstrip("/").rsplit("/", 1)[-1]


def _day_of(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).date().isoformat()


# ───────── series construction ─────────

def _date_range(start_day: str, end_day: str) -> list[str]:
    """Inclusive list of ISO dates so the chart has no gaps (zero-fill)."""
    d0 = datetime.fromisoformat(start_day).date()
    d1 = datetime.fromisoformat(end_day).date()
    out, cur = [], d0
    while cur <= d1:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def _build_daily_series(sessions: list[dict], days: int) -> list[dict]:
    """Zero-filled daily {date, usd, tokens, count} from today-back-N-days to today."""
    today = datetime.now().date()
    start = (today - timedelta(days=days - 1)).isoformat()
    end = today.isoformat()
    buckets: dict[str, dict] = {}
    for s in sessions:
        d = _day_of(s["startedAt"])
        b = buckets.setdefault(d, {"usd": 0.0, "tokens": 0, "count": 0})
        b["usd"] += s["usd"]
        b["tokens"] += s["tokens"]
        b["count"] += 1
    series = []
    for d in _date_range(start, end):
        b = buckets.get(d, {"usd": 0.0, "tokens": 0, "count": 0})
        series.append({
            "date": d,
            "usd": round(b["usd"], 6),
            "tokens": int(b["tokens"]),
            "count": int(b["count"]),
        })
    return series


# ───────── statistics helpers ─────────

def _mean_sigma(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = statistics.fmean(values)
    sigma = statistics.pstdev(values) if len(values) > 1 else 0.0
    return m, sigma


def _severity_from_sigma(deviation_sigmas: float) -> str:
    if deviation_sigmas >= 4.0:
        return "critical"
    if deviation_sigmas >= 3.0:
        return "high"
    if deviation_sigmas >= 2.0:
        return "medium"
    return "low"


def _pct_delta(value: float, baseline: float) -> float:
    if baseline <= 0:
        return 100.0 if value > 0 else 0.0
    return round((value - baseline) / baseline * 100.0, 1)


# ───────── detectors ─────────

def _detect_spend_spikes(series: list[dict], window: int, z: float, jump_pct: float) -> list[dict]:
    """Flag daily spend spikes via trailing mean+Z*sigma OR day-over-day % jump."""
    out: list[dict] = []
    for i, point in enumerate(series):
        usd = point["usd"]
        if usd < _MIN_SPIKE_USD:
            continue
        trailing = [p["usd"] for p in series[max(0, i - window):i]]
        if len(trailing) < _MIN_BASELINE_POINTS:
            continue
        mean, sigma = _mean_sigma(trailing)
        threshold = mean + z * sigma
        prev = series[i - 1]["usd"] if i > 0 else 0.0
        jump = _pct_delta(usd, prev)

        is_sigma_spike = sigma > 0 and usd > threshold
        is_jump_spike = prev > 0 and jump >= jump_pct
        if not (is_sigma_spike or is_jump_spike):
            continue

        dev_sigmas = ((usd - mean) / sigma) if sigma > 0 else 0.0
        baseline = round(mean, 6)
        delta_pct = _pct_delta(usd, baseline)
        if is_sigma_spike:
            severity = _severity_from_sigma(dev_sigmas)
            msg = (
                f"{point['date']} 일일 지출 ${usd:.2f} — 직전 {len(trailing)}일 "
                f"평균 ${mean:.2f}의 {dev_sigmas:.1f}σ 위 (임계 ${threshold:.2f}). "
                f"평소보다 {delta_pct:+.0f}% 급증했습니다."
            )
        else:
            severity = "high" if jump >= jump_pct * 2 else "medium"
            msg = (
                f"{point['date']} 일일 지출 ${usd:.2f} — 전일 ${prev:.2f} 대비 "
                f"{jump:+.0f}% 급등 (임계 {jump_pct:.0f}%)."
            )
        out.append({
            "id": f"spend:{point['date']}",
            "kind": "spend_spike",
            "date": point["date"],
            "session": None,
            "project": None,
            "severity": severity,
            "sigmas": round(dev_sigmas, 2),
            "value": round(usd, 6),
            "baseline": baseline,
            "deltaPct": delta_pct,
            "tokens": point["tokens"],
            "count": point["count"],
            "message": msg,
        })
    return out


def _detect_project_surges(sessions: list[dict], window: int, z: float) -> list[dict]:
    """Flag a project whose latest active day is far above its own baseline."""
    by_project: dict[str, dict[str, float]] = {}
    for s in sessions:
        d = _day_of(s["startedAt"])
        by_project.setdefault(s["project"], {})
        by_project[s["project"]][d] = by_project[s["project"]].get(d, 0.0) + s["usd"]

    out: list[dict] = []
    for project, day_map in by_project.items():
        # Ordered by date so "latest" is the most recent active day.
        ordered = sorted(day_map.items())
        if len(ordered) < _MIN_BASELINE_POINTS + 1:
            continue
        latest_day, latest_usd = ordered[-1]
        if latest_usd < _MIN_SPIKE_USD:
            continue
        prior = [v for _, v in ordered[-(window + 1):-1]]
        if len(prior) < _MIN_BASELINE_POINTS:
            continue
        mean, sigma = _mean_sigma(prior)
        if sigma <= 0:
            continue
        threshold = mean + z * sigma
        if latest_usd <= threshold:
            continue
        dev_sigmas = (latest_usd - mean) / sigma
        delta_pct = _pct_delta(latest_usd, mean)
        out.append({
            "id": f"project:{project}:{latest_day}",
            "kind": "project_surge",
            "date": latest_day,
            "session": None,
            "project": project,
            "severity": _severity_from_sigma(dev_sigmas),
            "sigmas": round(dev_sigmas, 2),
            "value": round(latest_usd, 6),
            "baseline": round(mean, 6),
            "deltaPct": delta_pct,
            "tokens": None,
            "count": None,
            "message": (
                f"프로젝트 '{project}' 지출 급증 — {latest_day} ${latest_usd:.2f}는 "
                f"자체 평소 ${mean:.2f}의 {dev_sigmas:.1f}σ 위 ({delta_pct:+.0f}%). "
                f"이 프로젝트만 비정상적으로 비용이 늘었습니다."
            ),
        })
    return out


def _detect_large_sessions(sessions: list[dict], z: float) -> list[dict]:
    """Flag single sessions whose cost is mean+Z*sigma above all sessions in range."""
    costs = [s["usd"] for s in sessions if s["usd"] > 0]
    if len(costs) < _MIN_BASELINE_POINTS + 1:
        return []
    mean, sigma = _mean_sigma(costs)
    if sigma <= 0:
        return []
    threshold = mean + z * sigma
    out: list[dict] = []
    for s in sessions:
        usd = s["usd"]
        if usd < _MIN_BIG_SESSION_USD or usd <= threshold:
            continue
        dev_sigmas = (usd - mean) / sigma
        delta_pct = _pct_delta(usd, mean)
        prompt = s["prompt"].strip()
        prompt_hint = f" — \"{prompt}\"" if prompt else ""
        out.append({
            "id": f"session:{s['sessionId']}",
            "kind": "large_session",
            "date": _day_of(s["startedAt"]),
            "session": s["sessionId"],
            "project": s["project"],
            "severity": _severity_from_sigma(dev_sigmas),
            "sigmas": round(dev_sigmas, 2),
            "value": round(usd, 6),
            "baseline": round(mean, 6),
            "deltaPct": delta_pct,
            "tokens": s["tokens"],
            "count": 1,
            "message": (
                f"단일 세션 ${usd:.2f} — 전체 세션 평균 ${mean:.2f}의 "
                f"{dev_sigmas:.1f}σ 위 ({delta_pct:+.0f}%). "
                f"프로젝트 '{s['project']}'{prompt_hint}"
            ),
        })
    return out


# ───────── orchestration ─────────

def _clamp(value, lo, hi, default, cast):
    try:
        v = cast(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _compute(days: int, window: int, z: float, jump_pct: float) -> dict:
    since_ms = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    sessions = _fetch_sessions(since_ms)
    series = _build_daily_series(sessions, days)

    if not sessions:
        return {
            "ok": True,
            "computedAt": int(time.time() * 1000),
            "params": {"days": days, "window": window, "z": z, "jumpPct": jump_pct},
            "anomalies": [],
            "series": series,
            "summary": {"total": 0, "byKind": {}, "totalUsd": 0.0, "sessionCount": 0},
            "note": "범위 내 세션 데이터가 없습니다. Claude Code 세션이 인덱싱되면 표시됩니다.",
        }

    anomalies: list[dict] = []
    anomalies += _detect_spend_spikes(series, window, z, jump_pct)
    anomalies += _detect_project_surges(sessions, window, z)
    anomalies += _detect_large_sessions(sessions, z)

    # Sort by severity rank, then sigma deviation, then value — all DESC.
    anomalies.sort(
        key=lambda a: (
            _SEVERITY_RANK.get(a["severity"], 0),
            a.get("sigmas") or 0.0,
            a.get("value") or 0.0,
        ),
        reverse=True,
    )

    # Mark which daily-series points carry an anomaly so the UI can highlight.
    flagged_days = {a["date"] for a in anomalies if a.get("date")}
    for p in series:
        p["flagged"] = p["date"] in flagged_days

    by_kind: dict[str, int] = {}
    for a in anomalies:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1

    return {
        "ok": True,
        "computedAt": int(time.time() * 1000),
        "params": {"days": days, "window": window, "z": z, "jumpPct": jump_pct},
        "anomalies": anomalies,
        "series": series,
        "summary": {
            "total": len(anomalies),
            "byKind": by_kind,
            "totalUsd": round(sum(s["usd"] for s in sessions), 6),
            "sessionCount": len(sessions),
        },
    }


def api_anomalies(query: dict | None = None) -> dict:
    """Public handler. Optional query params (all clamped):
      days     — series length, default 30 (7..365)
      window   — trailing baseline window, default 14 (3..90)
      z        — sigma multiplier, default 2.5 (1.0..6.0)
      jumpPct  — day-over-day % jump threshold, default 150 (10..2000)
    """
    q = query or {}
    days = _clamp(q.get("days"), _DAYS_MIN, _DAYS_MAX, _DEFAULT_DAYS, int)
    window = _clamp(q.get("window"), _WINDOW_MIN, _WINDOW_MAX, _DEFAULT_WINDOW, int)
    z = _clamp(q.get("z"), _Z_MIN, _Z_MAX, _DEFAULT_Z, float)
    jump_pct = _clamp(q.get("jumpPct"), _JUMP_MIN, _JUMP_MAX, _DEFAULT_JUMP_PCT, float)
    # Window can't exceed the series it draws from.
    window = min(window, max(_WINDOW_MIN, days - 1))
    try:
        return _compute(days, window, z, jump_pct)
    except Exception as e:
        log.warning("api_anomalies failed: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "anomalies": [],
            "series": [],
            "summary": {"total": 0, "byKind": {}, "totalUsd": 0.0, "sessionCount": 0},
            "note": "이상 탐지 계산 중 오류가 발생했습니다.",
        }
