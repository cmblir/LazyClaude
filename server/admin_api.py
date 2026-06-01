"""Anthropic Admin Usage & Cost API connector.

Wraps the organization-level Admin API (requires an admin key starting with
`sk-ant-admin...`, distinct from a standard API key) to fetch *actual billed*
token usage and USD cost, then reconciles them against this dashboard's local
`cost_timeline._estimate()` so users can see estimate-vs-actual drift.

Official endpoints (verified 2026-06 against
https://platform.claude.com/docs/en/manage-claude/usage-cost-api):
  - Usage  : GET https://api.anthropic.com/v1/organizations/usage_report/messages
  - Cost   : GET https://api.anthropic.com/v1/organizations/cost_report
Auth      : header `x-api-key: <admin key>` + `anthropic-version: 2023-06-01`.
Pagination: response carries `has_more` + `next_page`; pass `next_page` back as
            the `page` query param until `has_more` is false.

Usage report buckets (`results[]`) expose token counts split as
`uncached_input_tokens`, `cache_read_input_tokens`,
`cache_creation.{ephemeral_1h_input_tokens,ephemeral_5m_input_tokens}`, and
`output_tokens`. Cost report `results[]` expose `amount` (a decimal STRING in
the lowest currency unit — cents — so `"123.45"` USD == $1.2345) plus
`currency` (always "USD" today), `cost_type`, `description`, `model`.

Polling: Anthropic recommends polling at most once per minute. We cache both
reports in SQLite (table `admin_api_cache`) keyed by report+param hash and
refuse to refetch within the polling window unless `force=true`.

Secrets: the admin key lives in `~/.claude-dashboard-admin.json` with file mode
0600 (mirrors `server/ai_keys.py`). It is never returned to the client in full;
status/handlers only return a masked preview.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import _env_path
from .logger import log
from .utils import _safe_read, _safe_write


# ───────── constants ─────────

ADMIN_CONFIG_PATH = _env_path(
    "CLAUDE_DASHBOARD_ADMIN",
    Path.home() / ".claude-dashboard-admin.json",
)

_API_BASE = "https://api.anthropic.com"
_USAGE_PATH = "/v1/organizations/usage_report/messages"
_COST_PATH = "/v1/organizations/cost_report"
_ANTHROPIC_VERSION = "2023-06-01"
_USER_AGENT = "LazyClaude-Dashboard/1.0 (https://github.com/cmblir/LazyClaude)"

# Anthropic recommends "once per minute" sustained polling. We cache results
# and refuse to refetch within this window unless force=true.
_POLL_WINDOW_SEC = 60

# Defensive caps so a single fetch can never spin forever on pagination.
_MAX_PAGES = 20
_HTTP_TIMEOUT = 30

# Bucket-width default limits (mirror the official "Time granularity limits"
# table). We request the max so a single page covers the whole asked window.
_USAGE_MAX_LIMIT = {"1d": 31, "1h": 168, "1m": 1440}


# ───────── config (admin key) load / save ─────────

_CFG_LOCK = threading.Lock()


def _load_config() -> dict:
    """Load the admin-key config. Returns a default shell when absent."""
    if not ADMIN_CONFIG_PATH.exists():
        return {"version": 1, "adminKey": ""}
    try:
        data = json.loads(_safe_read(ADMIN_CONFIG_PATH))
        if not isinstance(data, dict):
            return {"version": 1, "adminKey": ""}
        data.setdefault("version", 1)
        data.setdefault("adminKey", "")
        return data
    except Exception as e:  # noqa: BLE001
        log.warning("admin config load failed: %s", e)
        return {"version": 1, "adminKey": ""}


def _save_config(data: dict) -> bool:
    """Atomic write + chmod 600 (mirrors ai_keys / slack secret handling)."""
    with _CFG_LOCK:
        ok = _safe_write(ADMIN_CONFIG_PATH, json.dumps(data, ensure_ascii=False, indent=2))
        if ok:
            try:
                os.chmod(ADMIN_CONFIG_PATH, 0o600)
            except OSError as e:
                log.warning("admin config chmod failed: %s", e)
    return ok


def _get_admin_key() -> str:
    """Resolve the admin key. Env var `ANTHROPIC_ADMIN_KEY` overrides the file."""
    env = (os.environ.get("ANTHROPIC_ADMIN_KEY") or "").strip()
    if env:
        return env
    return (_load_config().get("adminKey") or "").strip()


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 16:
        return "••••"
    return key[:12] + "…" + key[-4:]


# ───────── SQLite cache ─────────

def _ensure_cache_table() -> None:
    """Create the cache table on demand. Separate from db._db_init so this
    module owns its own schema and stays decoupled."""
    from .db import _db, _db_init
    _db_init()
    with _db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS admin_api_cache (
              cache_key TEXT PRIMARY KEY,
              report    TEXT NOT NULL,
              params    TEXT NOT NULL,
              payload   TEXT NOT NULL,
              fetched_at INTEGER NOT NULL
            )
        """)


def _cache_key(report: str, params: dict) -> str:
    raw = report + "|" + json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _cache_get(key: str) -> dict | None:
    """Return {payload, fetched_at, age_sec} or None on miss."""
    try:
        _ensure_cache_table()
        from .db import _db
        with _db() as c:
            row = c.execute(
                "SELECT payload, fetched_at FROM admin_api_cache WHERE cache_key=?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return {
            "payload": json.loads(row["payload"]),
            "fetched_at": row["fetched_at"],
            "age_sec": max(0, int(time.time()) - int(row["fetched_at"])),
        }
    except Exception as e:  # noqa: BLE001
        log.warning("admin cache read failed: %s", e)
        return None


def _cache_put(key: str, report: str, params: dict, payload: dict) -> None:
    try:
        _ensure_cache_table()
        from .db import _db
        with _db() as c:
            c.execute(
                "INSERT OR REPLACE INTO admin_api_cache"
                " (cache_key, report, params, payload, fetched_at)"
                " VALUES (?,?,?,?,?)",
                (
                    key, report,
                    json.dumps(params, sort_keys=True, default=str),
                    json.dumps(payload, ensure_ascii=False),
                    int(time.time()),
                ),
            )
    except Exception as e:  # noqa: BLE001
        log.warning("admin cache write failed: %s", e)


# ───────── HTTP ─────────

class _AdminApiError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"admin api {status}: {body[:300]}")


def _build_query(params: dict) -> str:
    """Encode params; list values become repeated `key[]=v` pairs to match the
    Admin API's `group_by[]` / `models[]` array convention."""
    pairs: list[tuple[str, str]] = []
    for k, v in params.items():
        if v is None or v == "":
            continue
        if isinstance(v, (list, tuple)):
            arr_key = k if k.endswith("[]") else f"{k}[]"
            for item in v:
                if item is None or item == "":
                    continue
                pairs.append((arr_key, str(item)))
        else:
            pairs.append((k, str(v)))
    return urllib.parse.urlencode(pairs)


def _http_get(path: str, params: dict, admin_key: str) -> dict:
    """Single GET against the Admin API. Raises _AdminApiError on non-2xx."""
    url = _API_BASE + path
    qs = _build_query(params)
    if qs:
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("x-api-key", admin_key)
    req.add_header("anthropic-version", _ANTHROPIC_VERSION)
    req.add_header("User-Agent", _USER_AGENT)
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise _AdminApiError(e.code, body) from e
    except urllib.error.URLError as e:
        raise _AdminApiError(0, str(e.reason)) from e


def _http_get_paginated(path: str, params: dict, admin_key: str) -> list[dict]:
    """Follow `has_more` / `next_page` until exhausted (capped at _MAX_PAGES).
    Returns the concatenated `data` buckets across all pages."""
    buckets: list[dict] = []
    page_token: str | None = None
    for _ in range(_MAX_PAGES):
        q = dict(params)
        if page_token:
            q["page"] = page_token
        resp = _http_get(path, q, admin_key)
        data = resp.get("data") or []
        if isinstance(data, list):
            buckets.extend(data)
        if resp.get("has_more") and resp.get("next_page"):
            page_token = resp["next_page"]
        else:
            break
    return buckets


# ───────── window helpers ─────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_window(query: dict | None, bucket_width: str) -> tuple[str, str, int]:
    """Resolve (starting_at, ending_at, days) from optional query.

    Defaults: ending_at = start of tomorrow UTC (so today is fully covered),
    starting_at = `days` before that. `days` defaults to 7 for 1d, clamped to
    the bucket-width maximum.
    """
    q = query or {}
    try:
        days = int(q.get("days") or (7 if bucket_width == "1d" else 1))
    except (TypeError, ValueError):
        days = 7
    max_days = {"1d": 31, "1h": 7, "1m": 1}.get(bucket_width, 31)
    days = max(1, min(max_days, days))

    now = _now_utc()
    end_default = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_default = end_default - timedelta(days=days)

    starting_at = (q.get("starting_at") or "").strip() or _rfc3339(start_default)
    ending_at = (q.get("ending_at") or "").strip() or _rfc3339(end_default)
    return starting_at, ending_at, days


# ───────── usage / cost flatten + reconcile ─────────

def _bucket_token_totals(result: dict) -> dict:
    """Sum the four token kinds out of a single usage `results[]` entry."""
    cc = result.get("cache_creation") or {}
    cache_creation = int(cc.get("ephemeral_1h_input_tokens") or 0) + \
        int(cc.get("ephemeral_5m_input_tokens") or 0)
    uncached_in = int(result.get("uncached_input_tokens") or 0)
    cache_read = int(result.get("cache_read_input_tokens") or 0)
    output = int(result.get("output_tokens") or 0)
    return {
        "uncachedInputTokens": uncached_in,
        "cacheReadInputTokens": cache_read,
        "cacheCreationTokens": cache_creation,
        "outputTokens": output,
        # Effective billable input for estimation: uncached at 1x, cache_read at
        # ~0.1x, cache_write at ~1.25x (verified pricing facts).
        "effectiveInputTokens": uncached_in + cache_read + cache_creation,
    }


def _estimate_bucket_usd(result: dict) -> float:
    """Estimate USD for one usage bucket via cost_timeline pricing + the
    verified cache multipliers (cache_read ~0.1x input, cache_write ~1.25x)."""
    from .cost_timeline import _PRICING

    model = result.get("model") or ""
    price = None
    for mid, p in _PRICING.items():
        if mid in model:
            price = p
            break
    if not price:
        return 0.0
    t = _bucket_token_totals(result)
    in_rate = price["in"] / 1_000_000
    out_rate = price["out"] / 1_000_000
    usd = (
        t["uncachedInputTokens"] * in_rate
        + t["cacheReadInputTokens"] * in_rate * 0.1
        + t["cacheCreationTokens"] * in_rate * 1.25
        + t["outputTokens"] * out_rate
    )
    return round(usd, 6)


def _shape_usage(buckets: list[dict]) -> dict:
    """Flatten usage buckets into per-day rows + grand totals + estimate."""
    by_day: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    totals = {
        "uncachedInputTokens": 0, "cacheReadInputTokens": 0,
        "cacheCreationTokens": 0, "outputTokens": 0, "totalTokens": 0,
        "estimatedUsd": 0.0, "webSearchRequests": 0,
    }
    for b in buckets:
        start = b.get("starting_at") or ""
        day = start[:10] if start else "?"
        drow = by_day.setdefault(day, {
            "date": day, "uncachedInputTokens": 0, "cacheReadInputTokens": 0,
            "cacheCreationTokens": 0, "outputTokens": 0, "totalTokens": 0,
            "estimatedUsd": 0.0,
        })
        for r in (b.get("results") or []):
            tok = _bucket_token_totals(r)
            est = _estimate_bucket_usd(r)
            total_tok = (tok["uncachedInputTokens"] + tok["cacheReadInputTokens"]
                         + tok["cacheCreationTokens"] + tok["outputTokens"])
            stu = r.get("server_tool_use") or {}
            web = int(stu.get("web_search_requests") or 0)

            for key in ("uncachedInputTokens", "cacheReadInputTokens",
                        "cacheCreationTokens", "outputTokens"):
                drow[key] += tok[key]
                totals[key] += tok[key]
            drow["totalTokens"] += total_tok
            drow["estimatedUsd"] = round(drow["estimatedUsd"] + est, 6)
            totals["totalTokens"] += total_tok
            totals["estimatedUsd"] = round(totals["estimatedUsd"] + est, 6)
            totals["webSearchRequests"] += web

            model = r.get("model") or "(ungrouped)"
            mrow = by_model.setdefault(model, {
                "model": model, "totalTokens": 0, "outputTokens": 0,
                "estimatedUsd": 0.0,
            })
            mrow["totalTokens"] += total_tok
            mrow["outputTokens"] += tok["outputTokens"]
            mrow["estimatedUsd"] = round(mrow["estimatedUsd"] + est, 6)

    days = sorted(by_day.values(), key=lambda x: x["date"])
    models = sorted(by_model.values(), key=lambda x: x["estimatedUsd"], reverse=True)
    return {"totals": totals, "days": days, "byModel": models, "bucketCount": len(buckets)}


def _shape_cost(buckets: list[dict]) -> dict:
    """Flatten cost buckets. `amount` is a decimal STRING in cents → /100 USD."""
    by_day: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    by_type: dict[str, float] = {}
    total_usd = 0.0
    currency = "USD"

    for b in buckets:
        start = b.get("starting_at") or ""
        day = start[:10] if start else "?"
        drow = by_day.setdefault(day, {"date": day, "actualUsd": 0.0})
        for r in (b.get("results") or []):
            currency = r.get("currency") or currency
            try:
                # amount is in lowest unit (cents) → dollars.
                usd = float(r.get("amount") or 0) / 100.0
            except (TypeError, ValueError):
                usd = 0.0
            drow["actualUsd"] = round(drow["actualUsd"] + usd, 6)
            total_usd = round(total_usd + usd, 6)

            ctype = r.get("cost_type") or "(ungrouped)"
            by_type[ctype] = round(by_type.get(ctype, 0.0) + usd, 6)

            model = r.get("model")
            if model:
                mrow = by_model.setdefault(model, {"model": model, "actualUsd": 0.0})
                mrow["actualUsd"] = round(mrow["actualUsd"] + usd, 6)

    days = sorted(by_day.values(), key=lambda x: x["date"])
    models = sorted(by_model.values(), key=lambda x: x["actualUsd"], reverse=True)
    types = [{"costType": k, "actualUsd": v} for k, v in
             sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)]
    return {
        "currency": currency,
        "totalUsd": total_usd,
        "days": days,
        "byModel": models,
        "byCostType": types,
        "bucketCount": len(buckets),
    }


def _reconcile(usage: dict, cost: dict) -> list[dict]:
    """Build per-day estimate-vs-actual drift rows."""
    by_date: dict[str, dict] = {}
    for d in usage.get("days", []):
        by_date.setdefault(d["date"], {"date": d["date"], "estimatedUsd": 0.0, "actualUsd": 0.0})
        by_date[d["date"]]["estimatedUsd"] = d.get("estimatedUsd", 0.0)
    for d in cost.get("days", []):
        by_date.setdefault(d["date"], {"date": d["date"], "estimatedUsd": 0.0, "actualUsd": 0.0})
        by_date[d["date"]]["actualUsd"] = d.get("actualUsd", 0.0)
    out = []
    for row in sorted(by_date.values(), key=lambda x: x["date"]):
        est = row["estimatedUsd"]
        act = row["actualUsd"]
        drift = round(act - est, 6)
        drift_pct = round((drift / act) * 100, 2) if act else None
        out.append({**row, "driftUsd": drift, "driftPct": drift_pct})
    return out


# ───────── core fetch (cache-aware) ─────────

def _fetch_report(report: str, path: str, params: dict, force: bool) -> dict:
    """Cache-aware fetch. Returns {ok, fromCache, ageSec, data|error}."""
    admin_key = _get_admin_key()
    if not admin_key:
        return {"ok": False, "error": "no_admin_key",
                "hint": "Set an admin key (sk-ant-admin...) in the Admin Usage tab."}
    if not admin_key.startswith("sk-ant-admin"):
        # Warn but still attempt — Anthropic could change the prefix; the API
        # will reject it with a clear 401 we surface verbatim.
        log.warning("admin key does not start with sk-ant-admin; attempting anyway")

    key = _cache_key(report, params)
    cached = _cache_get(key)
    if cached and not force and cached["age_sec"] < _POLL_WINDOW_SEC:
        return {"ok": True, "fromCache": True, "ageSec": cached["age_sec"],
                "fetchedAt": cached["fetched_at"], "data": cached["payload"]}

    try:
        buckets = _http_get_paginated(path, params, admin_key)
    except _AdminApiError as e:
        # On a fresh error, fall back to any stale cache so the UI degrades
        # gracefully instead of going blank.
        if cached:
            return {"ok": True, "fromCache": True, "stale": True,
                    "ageSec": cached["age_sec"], "fetchedAt": cached["fetched_at"],
                    "warning": f"refresh failed (HTTP {e.status}); showing cached",
                    "data": cached["payload"]}
        return {"ok": False, "error": "api_error", "status": e.status,
                "detail": e.body[:500]}
    except Exception as e:  # noqa: BLE001
        if cached:
            return {"ok": True, "fromCache": True, "stale": True,
                    "ageSec": cached["age_sec"], "fetchedAt": cached["fetched_at"],
                    "warning": f"refresh failed ({e}); showing cached",
                    "data": cached["payload"]}
        return {"ok": False, "error": "fetch_failed", "detail": str(e)[:300]}

    _cache_put(key, report, params, buckets)
    return {"ok": True, "fromCache": False, "ageSec": 0,
            "fetchedAt": int(time.time()), "data": buckets}


# ───────── public API handlers ─────────

def api_admin_status() -> dict:
    """GET /api/admin/status — is a key configured? (masked) + cache freshness.

    Key-absent path returns ok:True, configured:False so the frontend can render
    a clear 'no key' empty state without erroring."""
    key = _get_admin_key()
    from_env = bool((os.environ.get("ANTHROPIC_ADMIN_KEY") or "").strip())
    return {
        "ok": True,
        "configured": bool(key),
        "fromEnv": from_env,
        "maskedKey": _mask_key(key),
        "pollWindowSec": _POLL_WINDOW_SEC,
        "endpoints": {"usage": _USAGE_PATH, "cost": _COST_PATH},
        "anthropicVersion": _ANTHROPIC_VERSION,
    }


def api_admin_set_key(body: dict) -> dict:
    """POST /api/admin/set-key — body: {adminKey} to set, or {adminKey:""}/{clear:true} to clear."""
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body"}
    if (os.environ.get("ANTHROPIC_ADMIN_KEY") or "").strip():
        return {"ok": False, "error": "env_locked",
                "hint": "ANTHROPIC_ADMIN_KEY env var is set; unset it to manage the key here."}
    clear = bool(body.get("clear"))
    key = (body.get("adminKey") or "").strip()
    cfg = _load_config()
    if clear or not key:
        cfg["adminKey"] = ""
        ok = _save_config(cfg)
        return {"ok": ok, "configured": False, "maskedKey": ""}
    # Light validation; warn (don't reject) on unexpected prefix so a future
    # prefix change doesn't lock users out.
    cfg["adminKey"] = key
    ok = _save_config(cfg)
    return {
        "ok": ok,
        "configured": True,
        "maskedKey": _mask_key(key),
        "warning": "" if key.startswith("sk-ant-admin")
        else "key does not start with sk-ant-admin — admin keys usually do",
    }


def api_admin_usage(query: dict | None = None) -> dict:
    """GET /api/admin/usage — actual billed token usage from the Usage API.

    Query: days?, starting_at?, ending_at?, bucket_width? (1d|1h|1m), group_by?
           (comma list, default 'model'), force? (bypass cache).
    """
    q = query or {}
    bucket_width = (q.get("bucket_width") or "1d").strip()
    if bucket_width not in ("1d", "1h", "1m"):
        bucket_width = "1d"
    starting_at, ending_at, days = _resolve_window(q, bucket_width)

    raw_group = (q.get("group_by") or "model").strip()
    valid_groups = {"model", "workspace_id", "api_key_id", "service_tier",
                    "context_window", "inference_geo", "account_id",
                    "service_account_id"}
    group_by = [g.strip() for g in raw_group.split(",")
                if g.strip() in valid_groups][:3]

    params = {
        "starting_at": starting_at,
        "ending_at": ending_at,
        "bucket_width": bucket_width,
        "limit": _USAGE_MAX_LIMIT.get(bucket_width, 31),
        "group_by": group_by or ["model"],
    }
    force = str(q.get("force") or "").lower() in ("1", "true", "yes")
    res = _fetch_report("usage", _USAGE_PATH, params, force)
    if not res.get("ok"):
        return res
    shaped = _shape_usage(res["data"])
    return {
        "ok": True,
        "fromCache": res.get("fromCache", False),
        "stale": res.get("stale", False),
        "warning": res.get("warning", ""),
        "ageSec": res.get("ageSec", 0),
        "fetchedAt": res.get("fetchedAt"),
        "window": {"startingAt": starting_at, "endingAt": ending_at,
                   "days": days, "bucketWidth": bucket_width},
        "groupBy": params["group_by"],
        "usage": shaped,
    }


def api_admin_cost(query: dict | None = None) -> dict:
    """GET /api/admin/cost — actual billed USD from the Cost API + reconciliation.

    Query: days?, starting_at?, ending_at?, force?. bucket_width is fixed to 1d
    (the Cost API only supports daily granularity).
    """
    q = query or {}
    starting_at, ending_at, days = _resolve_window(q, "1d")
    params = {
        "starting_at": starting_at,
        "ending_at": ending_at,
        "bucket_width": "1d",
        "limit": 31,
        "group_by": ["description"],  # description exposes model + cost_type
    }
    force = str(q.get("force") or "").lower() in ("1", "true", "yes")

    cost_res = _fetch_report("cost", _COST_PATH, params, force)
    if not cost_res.get("ok"):
        return cost_res
    cost_shaped = _shape_cost(cost_res["data"])

    # Pull matching usage (estimate side) for the same window so the UI gets a
    # single source for the estimate-vs-actual reconciliation table. Usage is
    # cache-aware too, so this is cheap on warm reads.
    usage_params = {
        "starting_at": starting_at,
        "ending_at": ending_at,
        "bucket_width": "1d",
        "limit": 31,
        "group_by": ["model"],
    }
    usage_res = _fetch_report("usage", _USAGE_PATH, usage_params, force)
    usage_shaped = _shape_usage(usage_res["data"]) if usage_res.get("ok") else {"days": [], "totals": {}}

    reconciliation = _reconcile(usage_shaped, cost_shaped)
    est_total = round(sum(r["estimatedUsd"] for r in reconciliation), 6)
    act_total = cost_shaped["totalUsd"]
    drift_total = round(act_total - est_total, 6)

    return {
        "ok": True,
        "fromCache": cost_res.get("fromCache", False),
        "stale": cost_res.get("stale", False),
        "warning": cost_res.get("warning", ""),
        "ageSec": cost_res.get("ageSec", 0),
        "fetchedAt": cost_res.get("fetchedAt"),
        "window": {"startingAt": starting_at, "endingAt": ending_at, "days": days},
        "cost": cost_shaped,
        "reconciliation": {
            "rows": reconciliation,
            "estimatedUsdTotal": est_total,
            "actualUsdTotal": act_total,
            "driftUsd": drift_total,
            "driftPct": round((drift_total / act_total) * 100, 2) if act_total else None,
        },
    }
