"""Cache Diagnostics — pinpoint what broke a prompt-cache hit.

Drives Anthropic's official **cache-diagnosis beta** to find the exact
breakpoint that invalidated a prompt cache between two consecutive
Messages API requests.

Verified facts (Anthropic docs, 2026-06; ZDR-eligible beta feature):
  - Beta header:  ``anthropic-beta: cache-diagnosis-2026-04-07``
  - Opt-in:       top-level request body field
                  ``"diagnostics": {"previous_message_id": <id|null>}``
                  Turn 1 passes ``null`` (nothing to compare against); turn 2
                  passes the ``id`` returned by turn 1.
  - Response:     top-level ``diagnostics`` object on the Message. Four states:
                    * field absent  -> beta header / diagnostics field missing
                    * ``null``      -> first turn, OR comparison found no divergence
                    * ``{"cache_miss_reason": null}`` -> comparison still running
                                       (inconclusive — check next turn)
                    * ``{"cache_miss_reason": {"type": ..., ...}}`` -> a reason
  - ``cache_miss_reason`` is a discriminated union on ``type``:
        model_changed | system_changed | tools_changed | messages_changed
        | previous_message_not_found | unavailable
    The four ``*_changed`` types also carry ``cache_missed_input_tokens``
    (an int estimate, derived from byte lengths — magnitude indicator,
    NOT a billing number; can exceed ``usage.input_tokens``).
  - Usage:        ``cache_creation_input_tokens`` / ``cache_read_input_tokens``
                  / ``input_tokens`` / ``output_tokens`` on ``usage``.
  - Platform:     Claude API ONLY. NOT Amazon Bedrock, NOT Vertex AI.

Endpoint POST ``/api/cache-diag/run`` body:
  {
    "model": "claude-opus-4-8",
    "maxTokens": 1024,
    "base":     {"system": <str|blocks>, "tools": [...], "messages": [...]},
    "modified": {"system": <str|blocks>, "tools": [...], "messages": [...]}
  }
``base`` is sent first (turn 1, ``previous_message_id: null``); ``modified``
is sent second referencing turn 1's id. The returned ``diagnostics`` of the
second call identifies the first breakpoint that diverged.

A local, offline, byte-level structural diff (``_local_diff``) is ALSO
computed so the UI can explain *why* even when ``ANTHROPIC_API_KEY`` is
unset or the API returns ``unavailable`` / a still-pending comparison. The
local diff is a best-effort fallback, never a replacement for the API's
authoritative ``cache_miss_reason``.

History: ``~/.claude-dashboard-cache-diag.json`` (most recent 20).
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .ai_keys import load_api_keys
from .config import _env_path
from .logger import log
from .utils import _safe_read, _safe_write

# ───────── Verified beta constants ─────────

# Anthropic cache-diagnosis beta header value (verified 2026-06).
BETA_HEADER = "cache-diagnosis-2026-04-07"

# Discriminated-union `type` values for `diagnostics.cache_miss_reason.type`
# (verified against the official cache-diagnostics docs page).
#   *_changed       -> a concrete divergence point (carry cache_missed_input_tokens)
#   *_not_found / unavailable -> no comparison was produced
_CHANGED_TYPES = {"model_changed", "system_changed", "tools_changed", "messages_changed"}
_NO_COMPARISON_TYPES = {"previous_message_not_found", "unavailable"}
KNOWN_MISS_TYPES = _CHANGED_TYPES | _NO_COMPARISON_TYPES

# Human-readable explanation + remediation per verified `type`.
# (English mirrored from the docs "Cache miss reason types" table; the UI
#  surfaces the localized copy via t() so these stay as the canonical source.)
_REASON_INFO: dict[str, dict[str, str]] = {
    "model_changed": {
        "what": "The `model` differs from the previous request. The cache is per-model.",
        "fix": "Hold the model constant within a cached conversation.",
        "section": "model",
    },
    "system_changed": {
        "what": "The `system` parameter differs — often a timestamp / request id interpolated into the system prompt.",
        "fix": "Make the system prompt a byte-stable constant; move dynamic data into the first user message after the cache breakpoint.",
        "section": "system",
    },
    "tools_changed": {
        "what": "The `tools` array differs: tools added, removed, reordered, or schemas serialized non-deterministically.",
        "fix": "Send the same tool list every turn in a fixed order with deterministically serialized schemas (sort keys).",
        "section": "tools",
    },
    "messages_changed": {
        "what": "model/system/tools match, but an earlier `messages` entry was altered, reordered, or removed rather than appended to.",
        "fix": "Treat history as append-only; echo assistant content and tool results back verbatim.",
        "section": "messages",
    },
    "previous_message_not_found": {
        "what": "No stored fingerprint exists for the supplied previous_message_id. Not evidence your request changed.",
        "fix": "Send the beta header on every turn and keep consecutive turns close together in time (same workspace).",
        "section": "",
    },
    "unavailable": {
        "what": "Diagnostics not available — another prompt-affecting param (tool_choice / thinking / context_management / output_config / output_format / active beta headers) differs, or the divergence is beyond the comparison horizon.",
        "fix": "Keep all prompt-affecting request params constant for the lifetime of a cached conversation.",
        "section": "",
    },
}

HISTORY_PATH = _env_path(
    "CLAUDE_DASHBOARD_CACHE_DIAG",
    Path.home() / ".claude-dashboard-cache-diag.json",
)
_MAX_HISTORY = 20

_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


# ───────── Default examples (UI first-load templates) ─────────
#
# Each example carries a base + a modified request that intentionally breaks
# the cache at a specific block, so the user can see the diagnosis fire.
EXAMPLES: list[dict] = [
    {
        "id": "system-timestamp",
        "label": "시스템 프롬프트에 타임스탬프 주입",
        "description": "system 블록에 매 요청마다 바뀌는 값(타임스탬프)을 넣어 캐시가 깨지는 전형적 사례. 예상 진단: system_changed.",
        "model": "claude-opus-4-8",
        "maxTokens": 256,
        "expectType": "system_changed",
        "base": {
            "system": (
                "You are a documentation assistant. Answer concisely.\n\n"
                "<reference>\n"
                + ("The Claude API exposes a Messages endpoint for chat completions. " * 60)
                + "\n</reference>"
            ),
            "tools": [],
            "messages": [{"role": "user", "content": "Summarize the reference in one line."}],
        },
        "modified": {
            "system": (
                "You are a documentation assistant. Answer concisely. "
                "[request_time=2026-06-01T09:00:00Z]\n\n"
                "<reference>\n"
                + ("The Claude API exposes a Messages endpoint for chat completions. " * 60)
                + "\n</reference>"
            ),
            "tools": [],
            "messages": [{"role": "user", "content": "Summarize the reference in one line."}],
        },
    },
    {
        "id": "tools-reorder",
        "label": "도구 정의 순서 변경",
        "description": "tools 배열의 순서가 바뀌면 prefix 가 깨진다. 예상 진단: tools_changed.",
        "model": "claude-opus-4-8",
        "maxTokens": 256,
        "expectType": "tools_changed",
        "base": {
            "system": "You are a helpful assistant with tools.",
            "tools": [
                {"name": "get_weather", "description": "Get weather for a city.",
                 "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}},
                {"name": "get_time", "description": "Get current time for a timezone.",
                 "input_schema": {"type": "object", "properties": {"tz": {"type": "string"}}, "required": ["tz"]}},
            ],
            "messages": [{"role": "user", "content": "What's the weather in Seoul?"}],
        },
        "modified": {
            "system": "You are a helpful assistant with tools.",
            "tools": [
                {"name": "get_time", "description": "Get current time for a timezone.",
                 "input_schema": {"type": "object", "properties": {"tz": {"type": "string"}}, "required": ["tz"]}},
                {"name": "get_weather", "description": "Get weather for a city.",
                 "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}},
            ],
            "messages": [{"role": "user", "content": "What's the weather in Seoul?"}],
        },
    },
    {
        "id": "history-edited",
        "label": "대화 이력 수정 (append-only 위반)",
        "description": "이전 메시지를 덧붙이지 않고 수정하면 캐시가 깨진다. 예상 진단: messages_changed.",
        "model": "claude-opus-4-8",
        "maxTokens": 256,
        "expectType": "messages_changed",
        "base": {
            "system": "You are a concise assistant.",
            "tools": [],
            "messages": [
                {"role": "user", "content": "Remember the number 42."},
                {"role": "assistant", "content": "Got it, 42."},
                {"role": "user", "content": "What number did I give you?"},
            ],
        },
        "modified": {
            "system": "You are a concise assistant.",
            "tools": [],
            "messages": [
                {"role": "user", "content": "Remember the number 99."},
                {"role": "assistant", "content": "Got it, 99."},
                {"role": "user", "content": "What number did I give you?"},
            ],
        },
    },
]


# ───────── History ─────────

def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(_safe_read(HISTORY_PATH))
        if isinstance(data, list):
            return data[:_MAX_HISTORY]
    except Exception as e:
        log.warning("cache_diag history load failed: %s", e)
    return []


def _save_history(entry: dict) -> None:
    items = _load_history()
    items.insert(0, entry)
    items = items[:_MAX_HISTORY]
    try:
        _safe_write(HISTORY_PATH, json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        log.warning("cache_diag history save failed: %s", e)


# ───────── API key ─────────

def _anthropic_key() -> str:
    keys = load_api_keys()
    val = keys.get("anthropic-api")
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("apiKey") or ""
    return ""


# ───────── Messages API call (with cache-diagnosis beta header) ─────────

def _call_messages_api(api_key: str, body_obj: dict, timeout: int = 60) -> tuple[int, dict]:
    """POST /v1/messages with the cache-diagnosis beta header.

    Returns (status_code, json_body). status_code 0 means a transport error
    (no HTTP response); the error message is under json_body["error"]["message"].
    """
    import urllib.request
    import urllib.error

    body = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(
        _MESSAGES_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": BETA_HEADER,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
        except Exception:
            err = {"error": {"message": f"HTTP {e.code}"}}
        return e.code, err
    except Exception as e:
        return 0, {"error": {"message": str(e)}}


# ───────── Request builder ─────────

def _normalize_request(part: Any) -> dict:
    """Coerce a user-supplied {system, tools, messages} chunk into a clean dict.

    `system` may be a plain string or a list of content blocks (both valid for
    the Messages API). `tools` / `messages` must be lists. Missing -> empty.
    """
    if not isinstance(part, dict):
        part = {}
    system = part.get("system")
    tools = part.get("tools")
    messages = part.get("messages")
    out: dict[str, Any] = {}
    # system: keep as-is if str or list; drop if empty/None
    if isinstance(system, str):
        if system.strip():
            out["system"] = system
    elif isinstance(system, list) and system:
        out["system"] = system
    if isinstance(tools, list) and tools:
        out["tools"] = tools
    out["messages"] = messages if isinstance(messages, list) else []
    return out


def _build_body(model: str, max_tokens: int, part: dict, previous_message_id: str | None) -> dict:
    """Assemble a Messages API body for one turn, with the diagnostics opt-in."""
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": part.get("messages") or [],
        # Verified opt-in shape. Turn 1 passes null; turn 2 passes the prior id.
        "diagnostics": {"previous_message_id": previous_message_id},
    }
    if "system" in part:
        body["system"] = part["system"]
    if "tools" in part:
        body["tools"] = part["tools"]
    return body


# ───────── Diagnostics parsing (verified 4-state union) ─────────

def _parse_diagnostics(message: dict) -> dict:
    """Interpret the `diagnostics` field on a response Message.

    Returns a normalized dict:
      {
        "state": "absent" | "no_divergence" | "pending" | "reason",
        "type": <miss-reason type str | "">,    # only when state == "reason"
        "cacheMissedInputTokens": <int | None>,  # only for *_changed types
        "what": <str>, "fix": <str>, "section": <str>,
        "summary": <one-line human summary>,
      }
    """
    if "diagnostics" not in message:
        return {
            "state": "absent",
            "type": "",
            "cacheMissedInputTokens": None,
            "what": "", "fix": "", "section": "",
            "summary": "diagnostics field absent — beta header or diagnostics opt-in missing.",
        }
    diag = message.get("diagnostics")
    if diag is None:
        return {
            "state": "no_divergence",
            "type": "",
            "cacheMissedInputTokens": None,
            "what": "", "fix": "", "section": "",
            "summary": "No divergence detected — the prompt prefix is byte-stable (or this was the first turn).",
        }
    if not isinstance(diag, dict):
        # Defensive: unexpected shape.
        return {
            "state": "absent",
            "type": "",
            "cacheMissedInputTokens": None,
            "what": "", "fix": "", "section": "",
            "summary": f"Unexpected diagnostics shape: {type(diag).__name__}.",
        }
    reason = diag.get("cache_miss_reason")
    if reason is None:
        return {
            "state": "pending",
            "type": "",
            "cacheMissedInputTokens": None,
            "what": "", "fix": "", "section": "",
            "summary": "Comparison still running (inconclusive) — check the next turn.",
        }
    rtype = ""
    missed = None
    if isinstance(reason, dict):
        rtype = str(reason.get("type") or "")
        mv = reason.get("cache_missed_input_tokens")
        if isinstance(mv, (int, float)):
            missed = int(mv)
    info = _REASON_INFO.get(rtype, {})
    summary = _summarize_reason(rtype, missed)
    return {
        "state": "reason",
        "type": rtype,
        "cacheMissedInputTokens": missed,
        "what": info.get("what", ""),
        "fix": info.get("fix", ""),
        "section": info.get("section", ""),
        "summary": summary,
    }


def _summarize_reason(rtype: str, missed: int | None) -> str:
    """One-line 'cache broke at block N because ...' style summary."""
    info = _REASON_INFO.get(rtype)
    if rtype in _CHANGED_TYPES:
        section = info.get("section", rtype.replace("_changed", "")) if info else rtype
        tail = f" (~{missed:,} cacheable tokens lost after the divergence)" if missed else ""
        return f"Cache broke in the {section} block — {rtype}{tail}."
    if rtype == "previous_message_not_found":
        return "No comparison: no stored fingerprint for previous_message_id (not evidence your request changed)."
    if rtype == "unavailable":
        return "No comparison: diagnostics unavailable (a non-comparable param changed or divergence is beyond the horizon)."
    if rtype and rtype not in KNOWN_MISS_TYPES:
        # Unknown future type — surface it honestly rather than guessing.
        return f"Cache miss reason '{rtype}' (unrecognized type — beta field names may have changed)."
    return "Cache miss reason reported."


def _usage_summary(usage: dict | None) -> dict:
    u = usage or {}
    return {
        "inputTokens": int(u.get("input_tokens") or 0),
        "outputTokens": int(u.get("output_tokens") or 0),
        "cacheCreationInputTokens": int(u.get("cache_creation_input_tokens") or 0),
        "cacheReadInputTokens": int(u.get("cache_read_input_tokens") or 0),
    }


def _usage_deltas(base_usage: dict, mod_usage: dict) -> dict:
    """cache_read vs cache_creation deltas between turn 1 (base) and turn 2 (modified).

    A healthy cache HIT on turn 2 shows cacheReadInputTokens jumping up and
    cacheCreationInputTokens ~0. A BROKEN cache shows cacheRead near 0 and
    cacheCreation re-paying the write.
    """
    b = _usage_summary(base_usage)
    m = _usage_summary(mod_usage)
    return {
        "base": b,
        "modified": m,
        "deltaCacheRead": m["cacheReadInputTokens"] - b["cacheReadInputTokens"],
        "deltaCacheCreation": m["cacheCreationInputTokens"] - b["cacheCreationInputTokens"],
        # On a working cache, turn 2 reads what turn 1 wrote.
        "cacheHitOnModified": m["cacheReadInputTokens"] > 0,
    }


# ───────── Offline structural diff (best-effort fallback) ─────────
#
# Mirrors the API's comparison ORDER (model -> system -> tools -> messages)
# so it agrees with `cache_miss_reason` whenever the API also fired. Used to
# explain the break when ANTHROPIC_API_KEY is unset, or when the API returns
# `unavailable` / a still-pending comparison. NOT authoritative.

def _canon(obj: Any) -> str:
    """Deterministic JSON serialization (sorted keys) for byte comparison."""
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False)
    except Exception:
        return repr(obj)


def _local_diff(model: str, base: dict, modified: dict) -> dict:
    """Compare two requests byte-for-byte in cache-prefix order.

    Returns {"diverged": bool, "section": "", "index": int|None,
             "type": <*_changed|"">, "summary": str, "authoritative": False}.
    The first section that differs is reported (the API reports the earliest
    divergence too).
    """
    # 1. model
    if (base.get("_model") or model) != (modified.get("_model") or model):
        return {
            "diverged": True, "section": "model", "index": None,
            "type": "model_changed", "authoritative": False,
            "summary": "Local diff: model differs between the two requests.",
        }
    # 2. system
    if _canon(base.get("system")) != _canon(modified.get("system")):
        return {
            "diverged": True, "section": "system", "index": None,
            "type": "system_changed", "authoritative": False,
            "summary": "Local diff: system prompt changed (first divergence).",
        }
    # 3. tools (order-sensitive — reorder breaks the cache)
    bt = base.get("tools") or []
    mt = modified.get("tools") or []
    if _canon(bt) != _canon(mt):
        idx = _first_list_divergence(bt, mt)
        return {
            "diverged": True, "section": "tools", "index": idx,
            "type": "tools_changed", "authoritative": False,
            "summary": f"Local diff: tools array changed at index {idx if idx is not None else '?'}.",
        }
    # 4. messages — find first non-appended divergence (prefix mismatch)
    bm = base.get("messages") or []
    mm = modified.get("messages") or []
    idx = _first_list_divergence(bm, mm)
    if idx is not None and idx < min(len(bm), len(mm)):
        # An EARLIER message differs (not a pure append) -> cache-breaking.
        return {
            "diverged": True, "section": "messages", "index": idx,
            "type": "messages_changed", "authoritative": False,
            "summary": f"Local diff: messages[{idx}] was altered (not append-only).",
        }
    if idx is not None:
        # Difference is only at/after the shared prefix end -> pure append.
        return {
            "diverged": False, "section": "messages", "index": idx,
            "type": "", "authoritative": False,
            "summary": "Local diff: messages differ only by appended turns (append-only — cache prefix preserved).",
        }
    return {
        "diverged": False, "section": "", "index": None,
        "type": "", "authoritative": False,
        "summary": "Local diff: the two requests are byte-identical in model/system/tools/messages.",
    }


def _first_list_divergence(a: list, b: list) -> int | None:
    """Index of the first element that differs (or where one runs out)."""
    n = min(len(a), len(b))
    for i in range(n):
        if _canon(a[i]) != _canon(b[i]):
            return i
    if len(a) != len(b):
        return n
    return None


# ───────── API endpoints ─────────

def api_cache_diag_examples(_query: dict | None = None) -> dict:
    return {"examples": EXAMPLES, "betaHeader": BETA_HEADER}


def api_cache_diag_history(_query: dict | None = None) -> dict:
    return {"items": _load_history()}


def api_cache_diag_run(body: dict) -> dict:
    """Run two consecutive Messages API calls and diagnose the cache break.

    Call 1 (base) opts in with previous_message_id=null.
    Call 2 (modified) references call 1's id, so the API compares prefixes and
    returns `diagnostics.cache_miss_reason` identifying the first divergence.

    Always returns the offline structural diff (`localDiff`) so the UI can
    explain the break even without an API key / when the API is inconclusive.
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}

    model = (body.get("model") or "claude-opus-4-8").strip()
    try:
        max_tokens = int(body.get("maxTokens") or 256)
    except (TypeError, ValueError):
        max_tokens = 256
    max_tokens = max(1, min(max_tokens, 4096))

    base = _normalize_request(body.get("base"))
    modified = _normalize_request(body.get("modified"))

    if not base.get("messages"):
        return {"ok": False, "error": "base.messages required (non-empty list)"}
    if not modified.get("messages"):
        return {"ok": False, "error": "modified.messages required (non-empty list)"}

    # Offline structural diff — always available, never authoritative.
    local = _local_diff(model, base, modified)

    api_key = _anthropic_key()
    if not api_key:
        # Honest degraded state: no live call possible. Surface the local diff
        # as the explanation and tell the user how to enable the real beta.
        entry = {
            "id": f"cd-{uuid.uuid4().hex[:10]}",
            "ts": int(time.time()),
            "model": model,
            "status": "offline",
            "localDiff": local,
            "betaHeader": BETA_HEADER,
        }
        _save_history(entry)
        return {
            "ok": True,
            "mode": "offline",
            "needKey": True,
            "model": model,
            "betaHeader": BETA_HEADER,
            "localDiff": local,
            "diagnostics": None,
            "usageDeltas": None,
            "summary": (
                "Offline (no ANTHROPIC_API_KEY): showing a local byte-level "
                "structural diff. Set ANTHROPIC_API_KEY in the aiProviders tab "
                "to run the live cache-diagnosis beta for the authoritative reason."
            ),
            "note": (
                "Cache diagnostics is a Claude-API-only beta (not Bedrock/Vertex). "
                f"Live mode sends 'anthropic-beta: {BETA_HEADER}'."
            ),
            "entry": entry,
        }

    # ── Turn 1: base, opt in with previous_message_id=null ──
    body1 = _build_body(model, max_tokens, base, previous_message_id=None)
    t0 = int(time.time() * 1000)
    status1, data1 = _call_messages_api(api_key, body1)
    dur1 = int(time.time() * 1000) - t0

    if status1 != 200:
        err = (data1.get("error") or {}).get("message") or f"HTTP {status1}"
        entry = {
            "id": f"cd-{uuid.uuid4().hex[:10]}",
            "ts": int(time.time()),
            "model": model,
            "status": "err",
            "error": f"turn1: {err}",
            "localDiff": local,
        }
        _save_history(entry)
        return {
            "ok": False,
            "error": f"turn1 failed: {err}",
            "status": status1,
            "localDiff": local,
            "entry": entry,
        }

    msg_id = data1.get("id") or None
    usage1 = data1.get("usage") or {}

    # ── Turn 2: modified, reference turn 1's id ──
    body2 = _build_body(model, max_tokens, modified, previous_message_id=msg_id)
    t1 = int(time.time() * 1000)
    status2, data2 = _call_messages_api(api_key, body2)
    dur2 = int(time.time() * 1000) - t1

    if status2 != 200:
        err = (data2.get("error") or {}).get("message") or f"HTTP {status2}"
        entry = {
            "id": f"cd-{uuid.uuid4().hex[:10]}",
            "ts": int(time.time()),
            "model": model,
            "status": "err",
            "error": f"turn2: {err}",
            "previousMessageId": msg_id,
            "localDiff": local,
            "usageDeltas": _usage_deltas(usage1, {}),
        }
        _save_history(entry)
        return {
            "ok": False,
            "error": f"turn2 failed: {err}",
            "status": status2,
            "localDiff": local,
            "entry": entry,
        }

    usage2 = data2.get("usage") or {}
    diagnostics = _parse_diagnostics(data2)
    usage_deltas = _usage_deltas(usage1, usage2)

    # Compose the headline summary, preferring the authoritative API reason.
    if diagnostics["state"] == "reason" and diagnostics["type"] in _CHANGED_TYPES:
        headline = diagnostics["summary"]
        authoritative = True
    elif diagnostics["state"] == "no_divergence":
        headline = "No divergence — cache prefix preserved. " + (
            "Cache HIT confirmed on the modified request." if usage_deltas["cacheHitOnModified"]
            else "But the cache did not read (entry may have expired — see usage)."
        )
        authoritative = True
    elif diagnostics["state"] in ("pending", "absent") or diagnostics["type"] in _NO_COMPARISON_TYPES:
        # API could not pinpoint — fall back to the local diff explanation.
        headline = diagnostics["summary"] + " | Local diff fallback: " + local["summary"]
        authoritative = False
    else:
        headline = diagnostics["summary"]
        authoritative = diagnostics["state"] == "reason"

    entry = {
        "id": f"cd-{uuid.uuid4().hex[:10]}",
        "ts": int(time.time()),
        "model": model,
        "status": "ok",
        "previousMessageId": msg_id,
        "durationMs": dur1 + dur2,
        "diagnostics": diagnostics,
        "usageDeltas": usage_deltas,
        "localDiff": local,
        "summary": headline,
    }
    _save_history(entry)

    return {
        "ok": True,
        "mode": "live",
        "model": model,
        "betaHeader": BETA_HEADER,
        "previousMessageId": msg_id,
        "durationMs": {"turn1": dur1, "turn2": dur2, "total": dur1 + dur2},
        "diagnostics": diagnostics,
        "usageDeltas": usage_deltas,
        "localDiff": local,
        "authoritative": authoritative,
        "summary": headline,
        "note": (
            "Cache diagnostics is a Claude-API-only beta (not Bedrock/Vertex) and "
            "is best-effort: it never blocks your request. 'cache_missed_input_tokens' "
            "is a magnitude estimate from byte lengths, not a billing number."
        ),
        "entry": entry,
    }
