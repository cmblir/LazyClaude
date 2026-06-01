"""Team / per-user leaderboard from the Claude Code Analytics Admin API.

Builds a per-actor (per-user / per-API-key) leaderboard of Claude Code activity
— sessions, lines of code, commits, pull requests, tokens, and estimated USD
cost — ranked across a date window.

Data source (verified 2026-06 against
https://platform.claude.com/docs/en/build-with-claude/claude-code-analytics-api
and the reference at .../api/admin-api/claude-code/get-claude-code-usage-report):

  GET https://api.anthropic.com/v1/organizations/usage_report/claude_code
  Auth   : header `x-api-key: <admin key>` + `anthropic-version: 2023-06-01`.
  Params : `starting_at` (YYYY-MM-DD UTC, REQUIRED — returns metrics for THIS
           SINGLE DAY only), `limit` (records/page, default 20, max 1000),
           `page` (opaque cursor from the previous response's `next_page`).
  Returns: {data:[record...], has_more, next_page}. Each record is one actor's
           activity for one day:
             - date              RFC 3339 timestamp
             - actor             {type:"user_actor", email_address} OR
                                 {type:"api_actor",  api_key_name}
             - organization_id, customer_type, terminal_type
             - core_metrics.num_sessions
             - core_metrics.lines_of_code.{added,removed}
             - core_metrics.commits_by_claude_code
             - core_metrics.pull_requests_by_claude_code
             - tool_actions.{edit_tool,multi_edit_tool,write_tool,
                             notebook_edit_tool}.{accepted,rejected}
             - model_breakdown[].{model, tokens:{input,output,cache_read,
                             cache_creation}, estimated_cost:{currency,amount}}
           `estimated_cost.amount` is an INTEGER in CENTS USD (so 1025 == $10.25).

Because the endpoint serves exactly one UTC day per request, a multi-day
leaderboard is built by looping day-by-day over the requested window (capped at
`_MAX_DAYS`), following pagination within each day, then aggregating every
record per actor (matched by email / api_key_name) across all days.

Admin key: reused READ-ONLY from `~/.claude-dashboard-admin.json` (the file that
`server/admin_api.py` owns/writes). We import that module's `_get_admin_key`
getter rather than re-reading the file ourselves, so secret handling stays in
one place. This module never writes that file and never returns the key.

LIVE limits (reported to the user in the UI + integrationNotes):
  - The Admin API is UNAVAILABLE for individual accounts — it requires an
    organization admin key (`sk-ant-admin...`). Without one this module returns
    a clean no-key state; it cannot synthesize real numbers.
  - The endpoint only covers Claude Code usage on the Claude API. Usage via
    Bedrock / Vertex / Microsoft Foundry / Claude Platform on AWS is excluded.
  - Data has up to a ~1 hour freshness delay (only data older than 1h is
    returned for stable pagination).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from .logger import log

# Reuse the admin-key getter READ-ONLY. We do not edit or write admin_api.py.
# `_get_admin_key` honours the ANTHROPIC_ADMIN_KEY env override first, then the
# `~/.claude-dashboard-admin.json` file.
from .admin_api import _get_admin_key, _mask_key


# ───────── constants ─────────

_API_BASE = "https://api.anthropic.com"
_CC_PATH = "/v1/organizations/usage_report/claude_code"
_ANTHROPIC_VERSION = "2023-06-01"
_USER_AGENT = "LazyClaude-Dashboard/1.0 (https://github.com/cmblir/LazyClaude)"

_HTTP_TIMEOUT = 30
# The endpoint serves one UTC day per request; cap how many days we will sweep
# so a single leaderboard build can never fan out into hundreds of HTTP calls.
_MAX_DAYS = 31
_DEFAULT_DAYS = 7
# Per-day pagination guard (records/page * pages). 1000 is the documented max.
_PAGE_LIMIT = 1000
_MAX_PAGES_PER_DAY = 20


# ───────── HTTP ─────────

class _AnalyticsApiError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"claude_code analytics api {status}: {body[:300]}")


def _build_query(params: dict) -> str:
    pairs: list[tuple[str, str]] = []
    for k, v in params.items():
        if v is None or v == "":
            continue
        pairs.append((k, str(v)))
    return urllib.parse.urlencode(pairs)


def _http_get(params: dict, admin_key: str) -> dict:
    """Single GET against the Claude Code Analytics endpoint."""
    url = _API_BASE + _CC_PATH
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
        raise _AnalyticsApiError(e.code, body) from e
    except urllib.error.URLError as e:
        raise _AnalyticsApiError(0, str(e.reason)) from e


def _fetch_day(day: str, admin_key: str) -> list[dict]:
    """Fetch every record for one UTC day, following cursor pagination."""
    records: list[dict] = []
    page_token: str | None = None
    for _ in range(_MAX_PAGES_PER_DAY):
        params: dict[str, Any] = {"starting_at": day, "limit": _PAGE_LIMIT}
        if page_token:
            params["page"] = page_token
        resp = _http_get(params, admin_key)
        data = resp.get("data") or []
        if isinstance(data, list):
            records.extend(data)
        if resp.get("has_more") and resp.get("next_page"):
            page_token = resp["next_page"]
        else:
            break
    return records


# ───────── window helpers ─────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_days(query: dict | None) -> int:
    q = query or {}
    try:
        days = int(q.get("days") or _DEFAULT_DAYS)
    except (TypeError, ValueError):
        days = _DEFAULT_DAYS
    return max(1, min(_MAX_DAYS, days))


def _day_strings(days: int) -> list[str]:
    """The `days` most-recent complete UTC dates (YYYY-MM-DD), oldest→newest.

    We start the window at yesterday because the endpoint only returns data
    older than ~1 hour; today is typically incomplete.
    """
    end = _now_utc().date()  # today UTC
    out: list[str] = []
    for i in range(days, 0, -1):
        out.append((end - timedelta(days=i)).isoformat())
    return out


# ───────── actor key + aggregation ─────────

def _actor_identity(actor: dict | None) -> tuple[str, str, str]:
    """Return (stableKey, displayName, kind) for an actor record.

    kind is 'user' (OAuth email) or 'api' (API key name) or 'unknown'.
    """
    actor = actor or {}
    a_type = actor.get("type") or ""
    if a_type == "user_actor" or actor.get("email_address"):
        email = (actor.get("email_address") or "").strip()
        if email:
            return (f"user:{email.lower()}", email, "user")
    if a_type == "api_actor" or actor.get("api_key_name"):
        name = (actor.get("api_key_name") or "").strip()
        if name:
            return (f"api:{name}", name, "api")
    return ("unknown", "(unknown actor)", "unknown")


def _sum_model_breakdown(model_breakdown: list[dict] | None) -> dict:
    """Sum tokens + estimated cost (cents→USD) across a record's models."""
    tokens_in = tokens_out = cache_read = cache_creation = 0
    cents = 0
    models: set[str] = set()
    for m in (model_breakdown or []):
        toks = m.get("tokens") or {}
        tokens_in += int(toks.get("input") or 0)
        tokens_out += int(toks.get("output") or 0)
        cache_read += int(toks.get("cache_read") or 0)
        cache_creation += int(toks.get("cache_creation") or 0)
        est = m.get("estimated_cost") or {}
        try:
            cents += int(est.get("amount") or 0)
        except (TypeError, ValueError):
            pass
        if m.get("model"):
            models.add(m["model"])
    total_tokens = tokens_in + tokens_out + cache_read + cache_creation
    return {
        "tokensIn": tokens_in,
        "tokensOut": tokens_out,
        "cacheReadTokens": cache_read,
        "cacheCreationTokens": cache_creation,
        "totalTokens": total_tokens,
        "estimatedUsd": round(cents / 100.0, 4),
        "models": models,
    }


def _new_actor_row(stable_key: str, name: str, kind: str) -> dict:
    return {
        "key": stable_key,
        "name": name,
        "kind": kind,  # user | api | unknown
        "activeDays": 0,
        "sessions": 0,
        "linesAdded": 0,
        "linesRemoved": 0,
        "commits": 0,
        "pullRequests": 0,
        "tokensIn": 0,
        "tokensOut": 0,
        "cacheReadTokens": 0,
        "cacheCreationTokens": 0,
        "totalTokens": 0,
        "estimatedUsd": 0.0,
        "toolAccepted": 0,
        "toolRejected": 0,
        "_models": set(),
        "terminals": set(),
    }


def _accumulate(rows: dict[str, dict], record: dict) -> None:
    """Fold one daily analytics record into its actor's running totals."""
    key, name, kind = _actor_identity(record.get("actor"))
    row = rows.get(key)
    if row is None:
        row = _new_actor_row(key, name, kind)
        rows[key] = row

    core = record.get("core_metrics") or {}
    loc = core.get("lines_of_code") or {}
    row["activeDays"] += 1
    row["sessions"] += int(core.get("num_sessions") or 0)
    row["linesAdded"] += int(loc.get("added") or 0)
    row["linesRemoved"] += int(loc.get("removed") or 0)
    row["commits"] += int(core.get("commits_by_claude_code") or 0)
    row["pullRequests"] += int(core.get("pull_requests_by_claude_code") or 0)

    tools = record.get("tool_actions") or {}
    for tool in ("edit_tool", "multi_edit_tool", "write_tool", "notebook_edit_tool"):
        t = tools.get(tool) or {}
        row["toolAccepted"] += int(t.get("accepted") or 0)
        row["toolRejected"] += int(t.get("rejected") or 0)

    mb = _sum_model_breakdown(record.get("model_breakdown"))
    row["tokensIn"] += mb["tokensIn"]
    row["tokensOut"] += mb["tokensOut"]
    row["cacheReadTokens"] += mb["cacheReadTokens"]
    row["cacheCreationTokens"] += mb["cacheCreationTokens"]
    row["totalTokens"] += mb["totalTokens"]
    row["estimatedUsd"] = round(row["estimatedUsd"] + mb["estimatedUsd"], 4)
    row["_models"] |= mb["models"]

    term = (record.get("terminal_type") or "").strip()
    if term:
        row["terminals"].add(term)


def _finalize_row(row: dict) -> dict:
    """Turn internal sets into sorted lists + derived fields."""
    accepted = row["toolAccepted"]
    rejected = row["toolRejected"]
    total_actions = accepted + rejected
    out = {k: v for k, v in row.items() if not k.startswith("_") and k != "terminals"}
    out["linesNet"] = row["linesAdded"] - row["linesRemoved"]
    out["acceptRate"] = round(accepted / total_actions, 4) if total_actions else None
    out["models"] = sorted(row["_models"])
    out["terminals"] = sorted(row["terminals"])
    return out


_SORT_KEYS = {
    "cost": "estimatedUsd",
    "tokens": "totalTokens",
    "sessions": "sessions",
    "lines": "linesAdded",
    "commits": "commits",
    "prs": "pullRequests",
}


def _build_leaderboard(records: list[dict], sort_by: str) -> dict:
    rows: dict[str, dict] = {}
    for rec in records:
        _accumulate(rows, rec)
    finalized = [_finalize_row(r) for r in rows.values()]

    sort_field = _SORT_KEYS.get(sort_by, "estimatedUsd")
    finalized.sort(key=lambda r: (r.get(sort_field) or 0), reverse=True)
    for i, r in enumerate(finalized, start=1):
        r["rank"] = i

    totals = {
        "actors": len(finalized),
        "sessions": sum(r["sessions"] for r in finalized),
        "linesAdded": sum(r["linesAdded"] for r in finalized),
        "linesRemoved": sum(r["linesRemoved"] for r in finalized),
        "commits": sum(r["commits"] for r in finalized),
        "pullRequests": sum(r["pullRequests"] for r in finalized),
        "totalTokens": sum(r["totalTokens"] for r in finalized),
        "estimatedUsd": round(sum(r["estimatedUsd"] for r in finalized), 4),
    }
    return {"rows": finalized, "totals": totals, "sortBy": sort_field}


# ───────── public API handlers ─────────

def api_team_status() -> dict:
    """GET /api/team/status — is an org admin key configured? (masked).

    Mirrors api_admin_status's no-key-friendly contract: returns ok:True with
    configured:False when no key is set, so the frontend can render a clear
    empty state pointing at the Admin Usage tab rather than erroring.
    """
    key = _get_admin_key()
    return {
        "ok": True,
        "configured": bool(key),
        "maskedKey": _mask_key(key),
        "endpoint": _CC_PATH,
        "anthropicVersion": _ANTHROPIC_VERSION,
        "maxDays": _MAX_DAYS,
        "defaultDays": _DEFAULT_DAYS,
        # Honest constraints surfaced to the UI.
        "limits": [
            "Requires an organization admin key (sk-ant-admin...); unavailable on individual accounts.",
            "Covers Claude Code usage on the Claude API only (excludes Bedrock / Vertex / MS Foundry).",
            "Daily-aggregated with ~1h freshness delay; today is excluded until complete.",
        ],
    }


def api_team_leaderboard(query: dict | None = None) -> dict:
    """GET /api/team/leaderboard?days=&sort= — per-actor Claude Code leaderboard.

    Sweeps the last `days` complete UTC days (default 7, max 31) of the Claude
    Code Analytics endpoint, aggregates every record per actor, and ranks them.

    Query:
      days  — window length in days (1..31, default 7)
      sort  — cost | tokens | sessions | lines | commits | prs (default cost)
    """
    q = query or {}
    days = _resolve_days(q)
    sort_by = (q.get("sort") or "cost").strip().lower()

    admin_key = _get_admin_key()
    if not admin_key:
        return {
            "ok": True,
            "configured": False,
            "error": "no_admin_key",
            "hint": "Set an organization admin key (sk-ant-admin...) in the Admin Usage tab.",
            "window": {"days": days},
            "leaderboard": {"rows": [], "totals": {}, "sortBy": _SORT_KEYS.get(sort_by, "estimatedUsd")},
        }

    day_strings = _day_strings(days)
    records: list[dict] = []
    fetched_days: list[str] = []
    failed_days: list[dict] = []
    for day in day_strings:
        try:
            day_records = _fetch_day(day, admin_key)
        except _AnalyticsApiError as e:
            failed_days.append({"date": day, "status": e.status, "detail": e.body[:200]})
            # A hard auth/permission failure (401/403) will recur for every day;
            # bail out immediately rather than hammering the API.
            if e.status in (401, 403):
                return {
                    "ok": False,
                    "configured": True,
                    "error": "api_error",
                    "status": e.status,
                    "detail": e.body[:500],
                    "hint": "Admin key rejected — confirm it is an org admin key (sk-ant-admin...) with analytics access.",
                    "window": {"days": days, "dates": day_strings},
                }
            continue
        except Exception as e:  # noqa: BLE001
            log.warning("team leaderboard day fetch failed (%s): %s", day, e)
            failed_days.append({"date": day, "status": 0, "detail": str(e)[:200]})
            continue
        fetched_days.append(day)
        records.extend(day_records)

    leaderboard = _build_leaderboard(records, sort_by)
    result: dict[str, Any] = {
        "ok": True,
        "configured": True,
        "maskedKey": _mask_key(admin_key),
        "window": {
            "days": days,
            "dates": day_strings,
            "fetchedDates": fetched_days,
            "recordCount": len(records),
        },
        "leaderboard": leaderboard,
    }
    if failed_days:
        result["partial"] = True
        result["failedDays"] = failed_days
        result["warning"] = (
            f"{len(failed_days)} of {len(day_strings)} day(s) failed to fetch; "
            "leaderboard reflects the remaining days."
        )
    return result
