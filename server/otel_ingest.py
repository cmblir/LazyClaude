"""OTLP/HTTP JSON metrics ingest — make LazyClaude a Claude Code telemetry backend.

Claude Code can export OpenTelemetry metrics to any OTLP collector. This module
implements a minimal OTLP/HTTP **JSON** metrics receiver so users can point
Claude Code straight at this dashboard with zero extra infrastructure.

Why JSON only: this server is pure-stdlib Python. OTLP/HTTP protobuf would require
a protobuf runtime we deliberately don't ship, so users must set
``OTEL_EXPORTER_OTLP_PROTOCOL=http/json`` (verified valid value, see the official
Claude Code monitoring docs). The standard OTLP metrics path is ``/v1/metrics``;
here we accept the export at ``POST /otlp`` and instruct users to set
``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://127.0.0.1:19500/otlp``.

OTLP/HTTP JSON metrics payload shape (subset we parse):

    {
      "resourceMetrics": [{
        "resource": {"attributes": [{"key": "...", "value": {"stringValue": "..."}}]},
        "scopeMetrics": [{
          "scope": {"name": "com.anthropic.claude_code"},
          "metrics": [{
            "name": "claude_code.token.usage",
            "unit": "tokens",
            "sum": {"dataPoints": [{
              "asDouble": 1234,            # or "asInt": "1234"
              "timeUnixNano": "1717200000000000000",
              "attributes": [{"key": "type", "value": {"stringValue": "input"}}, ...]
            }]}
            # gauge metrics use "gauge" instead of "sum"
          }]
        }]
      }]
    }

Verified Claude Code metric names (official monitoring docs, 2026-06):
  claude_code.session.count, claude_code.lines_of_code.count,
  claude_code.pull_request.count, claude_code.commit.count,
  claude_code.cost.usage, claude_code.token.usage,
  claude_code.code_edit_tool.decision, claude_code.active_time.total

Persisted into the ``otel_metrics`` table:
  (ts, metric, value, model, agent, session_id, attrs_json)

The table is created here (idempotently) since db.py is shared and not edited by
this feature. We reuse db._db() for the connection factory + busy_timeout so we
inherit WAL and lock-contention handling.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from .db import _db
from .logger import log

# Verified canonical Claude Code metric names — the official monitoring docs.
# We don't reject unknown names (forward-compat), but this is what the summary
# endpoint knows how to surface.
_KNOWN_METRICS = {
    "claude_code.session.count",
    "claude_code.lines_of_code.count",
    "claude_code.pull_request.count",
    "claude_code.commit.count",
    "claude_code.cost.usage",
    "claude_code.token.usage",
    "claude_code.code_edit_tool.decision",
    "claude_code.active_time.total",
}

# Table-init guard — _ensure_table() is cheap but only the first call works.
_TABLE_READY = False
_TABLE_LOCK = threading.Lock()

# Defensive cap: a single OTLP export should never carry an absurd number of
# data points. Protects the DB from a malformed/hostile payload.
_MAX_ROWS_PER_REQUEST = 50_000


def _ensure_table() -> None:
    """Create the otel_metrics table + indexes. Idempotent, first call only."""
    global _TABLE_READY
    if _TABLE_READY:
        return
    with _TABLE_LOCK:
        if _TABLE_READY:
            return
        with _db() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS otel_metrics (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts INTEGER NOT NULL,           -- epoch seconds (from timeUnixNano)
                  metric TEXT NOT NULL,          -- e.g. claude_code.token.usage
                  value REAL NOT NULL DEFAULT 0, -- data point numeric value
                  model TEXT,                    -- attribute: model
                  agent TEXT,                    -- attribute: agent.name / query_source
                  session_id TEXT,               -- attribute: session.id
                  attrs_json TEXT,               -- full merged attribute set as JSON
                  ingested_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_otel_ts ON otel_metrics(ts);
                CREATE INDEX IF NOT EXISTS idx_otel_metric_ts ON otel_metrics(metric, ts);
                CREATE INDEX IF NOT EXISTS idx_otel_session ON otel_metrics(session_id);
                """
            )
        _TABLE_READY = True


# ───────── OTLP/HTTP JSON parsing ─────────


def _attr_value(v: dict) -> Any:
    """Unwrap an OTLP AnyValue object to a plain Python scalar/list.

    AnyValue is a one-of: stringValue / intValue / doubleValue / boolValue /
    arrayValue / kvlistValue / bytesValue. intValue arrives as a JSON string
    per the OTLP/JSON encoding (int64 is stringified to avoid precision loss).
    """
    if not isinstance(v, dict):
        return v
    if "stringValue" in v:
        return v["stringValue"]
    if "intValue" in v:
        try:
            return int(v["intValue"])
        except (TypeError, ValueError):
            return v["intValue"]
    if "doubleValue" in v:
        try:
            return float(v["doubleValue"])
        except (TypeError, ValueError):
            return v["doubleValue"]
    if "boolValue" in v:
        return bool(v["boolValue"])
    if "arrayValue" in v:
        items = (v["arrayValue"] or {}).get("values") or []
        return [_attr_value(it) for it in items]
    if "kvlistValue" in v:
        return _attributes_to_dict((v["kvlistValue"] or {}).get("values") or [])
    if "bytesValue" in v:
        return v["bytesValue"]
    return None


def _attributes_to_dict(attrs: list) -> dict:
    """Convert OTLP KeyValue list → flat {key: scalar} dict."""
    out: dict[str, Any] = {}
    if not isinstance(attrs, list):
        return out
    for kv in attrs:
        if not isinstance(kv, dict):
            continue
        key = kv.get("key")
        if not key:
            continue
        out[key] = _attr_value(kv.get("value") or {})
    return out


def _point_value(dp: dict) -> float:
    """Extract the numeric value from a NumberDataPoint (sum or gauge)."""
    if "asInt" in dp:
        try:
            return float(int(dp["asInt"]))
        except (TypeError, ValueError):
            return 0.0
    if "asDouble" in dp:
        try:
            return float(dp["asDouble"])
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _point_ts(dp: dict) -> int:
    """timeUnixNano (string nanos) → epoch seconds. Falls back to now."""
    nano = dp.get("timeUnixNano") or dp.get("startTimeUnixNano")
    if nano is None:
        return int(time.time())
    try:
        return int(int(nano) // 1_000_000_000)
    except (TypeError, ValueError):
        return int(time.time())


def _data_points(metric: dict) -> list[dict]:
    """Return the data points for a sum or gauge metric (the two Claude Code uses).

    Counters export as `sum`; the active_time gauge-style metrics may export as
    `gauge`. We also tolerate `histogram` by reading its dataPoints `sum` if
    present, though Claude Code does not currently emit histograms for these.
    """
    for kind in ("sum", "gauge"):
        block = metric.get(kind)
        if isinstance(block, dict):
            pts = block.get("dataPoints")
            if isinstance(pts, list):
                return pts
    hist = metric.get("histogram")
    if isinstance(hist, dict):
        return hist.get("dataPoints") or []
    return []


def _parse_resource_metrics(payload: dict) -> list[dict]:
    """Flatten an OTLP ExportMetricsServiceRequest into persistable rows.

    Returns rows shaped for insertion: each has ts, metric, value, model, agent,
    session_id, attrs (merged resource + datapoint attributes).
    """
    rows: list[dict] = []
    resource_metrics = payload.get("resourceMetrics") or []
    if not isinstance(resource_metrics, list):
        return rows
    for rm in resource_metrics:
        if not isinstance(rm, dict):
            continue
        resource_attrs = _attributes_to_dict(
            ((rm.get("resource") or {}).get("attributes")) or []
        )
        for sm in rm.get("scopeMetrics") or []:
            if not isinstance(sm, dict):
                continue
            for metric in sm.get("metrics") or []:
                if not isinstance(metric, dict):
                    continue
                name = metric.get("name")
                if not name:
                    continue
                for dp in _data_points(metric):
                    if not isinstance(dp, dict):
                        continue
                    dp_attrs = _attributes_to_dict(dp.get("attributes") or [])
                    merged = {**resource_attrs, **dp_attrs}
                    rows.append({
                        "ts": _point_ts(dp),
                        "metric": name,
                        "value": _point_value(dp),
                        # session.id is the canonical attribute key; some
                        # collectors flatten to session_id — accept both.
                        "session_id": (
                            merged.get("session.id") or merged.get("session_id")
                        ),
                        "model": merged.get("model"),
                        # query_source ("main"/"subagent"/"auxiliary") or the
                        # named subagent attribute, whichever is present.
                        "agent": (
                            merged.get("agent.name")
                            or merged.get("query_source")
                        ),
                        "attrs": merged,
                    })
                    if len(rows) >= _MAX_ROWS_PER_REQUEST:
                        return rows
    return rows


def _persist(rows: list[dict]) -> int:
    """Bulk-insert parsed rows. Returns count written."""
    if not rows:
        return 0
    _ensure_table()
    now = int(time.time())
    params = [
        (
            int(r["ts"]),
            str(r["metric"]),
            float(r["value"]),
            (str(r["model"]) if r.get("model") is not None else None),
            (str(r["agent"]) if r.get("agent") is not None else None),
            (str(r["session_id"]) if r.get("session_id") is not None else None),
            json.dumps(r.get("attrs") or {}, ensure_ascii=False),
            now,
        )
        for r in rows
    ]
    with _db() as c:
        c.executemany(
            "INSERT INTO otel_metrics "
            "(ts, metric, value, model, agent, session_id, attrs_json, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            params,
        )
    return len(params)


# ───────── Handlers ─────────


def api_otlp_ingest(body: dict | None = None) -> dict:
    """POST /otlp — OTLP/HTTP JSON metrics receiver.

    The dispatcher hands us the already-parsed JSON body. We return an
    OTLP-style ExportMetricsServiceResponse ({} on full success / partialSuccess
    on a soft failure) plus dashboard-friendly counters. A 200 with `{}` is what
    an OTLP/HTTP client expects on success.

    Note: this endpoint is unauthenticated by design (a local telemetry sink on
    127.0.0.1). It only ever writes metric rows; it never executes input.
    """
    try:
        if not isinstance(body, dict):
            # Empty / unparseable body — the dispatcher's _read_body() returns {}
            # for a non-JSON payload, which is the protobuf case. Tell the user.
            return {
                "partialSuccess": {
                    "rejectedDataPoints": 0,
                    "errorMessage": (
                        "OTLP payload was not JSON. Set "
                        "OTEL_EXPORTER_OTLP_PROTOCOL=http/json (protobuf is not "
                        "supported by this pure-stdlib backend)."
                    ),
                },
                "ok": False,
            }
        rows = _parse_resource_metrics(body)
        written = _persist(rows)
        # Per-metric tally so the UI / smoke test can confirm what landed.
        by_metric: dict[str, int] = {}
        for r in rows:
            by_metric[r["metric"]] = by_metric.get(r["metric"], 0) + 1
        log.info("otel ingest: %d data points across %d metrics", written, len(by_metric))
        # OTLP success response is an empty JSON object; we attach extras the
        # OTLP spec permits clients to ignore.
        return {"ok": True, "accepted": written, "byMetric": by_metric}
    except Exception as e:
        log.exception("otel ingest failed")
        return {
            "ok": False,
            "partialSuccess": {"rejectedDataPoints": 0, "errorMessage": str(e)},
            "error": str(e),
        }


def _window_seconds(query: dict | None) -> tuple[int, int]:
    """Parse ?hours=N (default 24, clamp 1..720). Returns (cutoff_epoch, hours)."""
    hours = 24
    if isinstance(query, dict):
        raw = query.get("hours")
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        try:
            if raw is not None:
                hours = int(raw)
        except (TypeError, ValueError):
            hours = 24
    hours = max(1, min(720, hours))
    return int(time.time()) - hours * 3600, hours


def api_otel_summary(query: dict | None = None) -> dict:
    """GET /api/otel/summary — aggregate recently ingested Claude Code telemetry.

    Surfaces: total cost, token totals by type, tool accept/reject decisions,
    lines of code added/removed, commit + PR counts, session count, per-model
    cost/tokens, a recent activity feed, and a daily token series for charting.
    """
    cutoff, hours = _window_seconds(query)
    try:
        _ensure_table()
    except Exception as e:
        log.warning("otel summary: ensure_table failed: %s", e)
        return {"ok": False, "error": str(e), "hasData": False}

    try:
        with _db() as c:
            total_rows = c.execute(
                "SELECT COUNT(*) AS n FROM otel_metrics"
            ).fetchone()["n"]

            # Headline scalar sums per metric within the window.
            def _sum(metric: str) -> float:
                row = c.execute(
                    "SELECT COALESCE(SUM(value), 0) AS s FROM otel_metrics "
                    "WHERE metric = ? AND ts >= ?",
                    (metric, cutoff),
                ).fetchone()
                return float(row["s"] or 0)

            cost_usd = round(_sum("claude_code.cost.usage"), 6)
            commits = int(_sum("claude_code.commit.count"))
            pull_requests = int(_sum("claude_code.pull_request.count"))
            sessions = int(_sum("claude_code.session.count"))
            active_time_s = round(_sum("claude_code.active_time.total"), 1)

            # Tokens split by `type` attribute (input/output/cacheRead/cacheCreation).
            tokens_by_type: dict[str, int] = {}
            for r in c.execute(
                "SELECT json_extract(attrs_json, '$.type') AS t, "
                "COALESCE(SUM(value), 0) AS s FROM otel_metrics "
                "WHERE metric = 'claude_code.token.usage' AND ts >= ? "
                "GROUP BY t",
                (cutoff,),
            ).fetchall():
                tokens_by_type[(r["t"] or "unknown")] = int(r["s"] or 0)
            tokens_total = sum(tokens_by_type.values())

            # Lines of code split by added/removed.
            loc_by_type: dict[str, int] = {}
            for r in c.execute(
                "SELECT json_extract(attrs_json, '$.type') AS t, "
                "COALESCE(SUM(value), 0) AS s FROM otel_metrics "
                "WHERE metric = 'claude_code.lines_of_code.count' AND ts >= ? "
                "GROUP BY t",
                (cutoff,),
            ).fetchall():
                loc_by_type[(r["t"] or "unknown")] = int(r["s"] or 0)

            # Tool edit decisions: accept vs reject, plus per-tool breakdown.
            decisions = {"accept": 0, "reject": 0}
            decisions_by_tool: dict[str, dict[str, int]] = {}
            for r in c.execute(
                "SELECT json_extract(attrs_json, '$.decision') AS d, "
                "json_extract(attrs_json, '$.tool_name') AS tool, "
                "COALESCE(SUM(value), 0) AS s FROM otel_metrics "
                "WHERE metric = 'claude_code.code_edit_tool.decision' AND ts >= ? "
                "GROUP BY d, tool",
                (cutoff,),
            ).fetchall():
                dec = (r["d"] or "").lower()
                n = int(r["s"] or 0)
                if dec in decisions:
                    decisions[dec] += n
                tool = r["tool"] or "unknown"
                bucket = decisions_by_tool.setdefault(tool, {"accept": 0, "reject": 0})
                if dec in bucket:
                    bucket[dec] += n

            # Per-model cost + tokens (only rows that carry a model attribute).
            by_model: list[dict] = []
            for r in c.execute(
                "SELECT model, "
                "COALESCE(SUM(CASE WHEN metric='claude_code.cost.usage' "
                "  THEN value ELSE 0 END), 0) AS cost, "
                "COALESCE(SUM(CASE WHEN metric='claude_code.token.usage' "
                "  THEN value ELSE 0 END), 0) AS tokens "
                "FROM otel_metrics WHERE ts >= ? AND model IS NOT NULL "
                "GROUP BY model ORDER BY cost DESC LIMIT 20",
                (cutoff,),
            ).fetchall():
                by_model.append({
                    "model": r["model"],
                    "costUsd": round(float(r["cost"] or 0), 6),
                    "tokens": int(r["tokens"] or 0),
                })

            # Daily token series for the chart (date string → tokens).
            daily: list[dict] = []
            for r in c.execute(
                "SELECT date(ts, 'unixepoch', 'localtime') AS day, "
                "COALESCE(SUM(CASE WHEN metric='claude_code.token.usage' "
                "  THEN value ELSE 0 END), 0) AS tokens, "
                "COALESCE(SUM(CASE WHEN metric='claude_code.cost.usage' "
                "  THEN value ELSE 0 END), 0) AS cost "
                "FROM otel_metrics WHERE ts >= ? GROUP BY day ORDER BY day",
                (cutoff,),
            ).fetchall():
                daily.append({
                    "day": r["day"],
                    "tokens": int(r["tokens"] or 0),
                    "costUsd": round(float(r["cost"] or 0), 6),
                })

            # Recent activity feed — last N data points across all metrics.
            recent: list[dict] = []
            for r in c.execute(
                "SELECT ts, metric, value, model, agent, session_id, attrs_json "
                "FROM otel_metrics ORDER BY ts DESC, id DESC LIMIT 40"
            ).fetchall():
                try:
                    attrs = json.loads(r["attrs_json"] or "{}")
                except Exception:
                    attrs = {}
                recent.append({
                    "ts": int(r["ts"]),
                    "metric": r["metric"],
                    "value": float(r["value"]),
                    "model": r["model"],
                    "agent": r["agent"],
                    "sessionId": r["session_id"],
                    "type": attrs.get("type"),
                    "decision": attrs.get("decision"),
                    "toolName": attrs.get("tool_name"),
                    "language": attrs.get("language"),
                })

            # Last ingest timestamp (across all time) — drives the "live" badge.
            last = c.execute(
                "SELECT MAX(ingested_at) AS m FROM otel_metrics"
            ).fetchone()
            last_ingest = int(last["m"]) if last and last["m"] else 0

        return {
            "ok": True,
            "hasData": total_rows > 0,
            "windowHours": hours,
            "lastIngestAt": last_ingest,
            "totals": {
                "costUsd": cost_usd,
                "tokensTotal": tokens_total,
                "tokensByType": tokens_by_type,
                "linesOfCode": loc_by_type,
                "commits": commits,
                "pullRequests": pull_requests,
                "sessions": sessions,
                "activeTimeSeconds": active_time_s,
            },
            "decisions": decisions,
            "decisionsByTool": decisions_by_tool,
            "byModel": by_model,
            "daily": daily,
            "recent": recent,
        }
    except Exception as e:
        log.exception("otel summary failed")
        return {"ok": False, "error": str(e), "hasData": False}
