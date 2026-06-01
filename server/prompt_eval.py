"""Prompt eval / regression suite — assertion-based test sets over model calls.

Goes beyond model_bench.py (which only measures latency/cost): each *test set*
holds a list of *cases*, every case carries a prompt + a list of *assertions*.
Running a set crosses every case with every selected `assignee`
("provider:model"), calls `execute_with_assignee`, evaluates the assertions
against the model output (and its latency/tokens), records pass/fail, then
diffs the result against a stored *baseline* per (set, assignee) so a
regression (a case that previously passed and now fails) is surfaced
explicitly.

Storage: ``~/.claude-dashboard-evals.json`` (override env
``CLAUDE_DASHBOARD_EVALS``). Shape::

    {
      "sets": [
        {"id": "...", "name": "...",
         "cases": [
           {"prompt": "...", "assertions": [
              {"type": "contains", "value": "..."},
              {"type": "json_path_equals", "path": "data.id", "value": 1},
              ...
           ]}
         ]}
      ],
      "baselines": {
        "<setId>::<assignee>": {
          "ts": 1700000000,
          "cases": [{"passed": true, "tokens": 10, "latencyMs": 800,
                     "assertions": [bool, ...]}]
        }
      }
    }

Assertion types: contains, not_contains, regex, equals, json_valid,
json_path_equals, max_tokens, max_latency_ms.

LIVE runs need an Anthropic key (ANTHROPIC_API_KEY env or the anthropic-api
key in the dashboard config) — the unified ``execute_with_assignee`` either
shells out to the `claude` CLI (which carries its own auth) or hits the API.
When neither a CLI nor a key is available the run still returns a structured
result with every cell flagged ``ok:false`` + a clear ``error`` message, so
the matrix degrades honestly rather than fabricating passes.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from .config import _env_path
from .logger import log
from .utils import _safe_read, _safe_write

# ───────── storage path ─────────
EVALS_PATH: Path = _env_path(
    "CLAUDE_DASHBOARD_EVALS", Path.home() / ".claude-dashboard-evals.json"
)

# Assertion types we understand. `path` is only meaningful for
# json_path_equals; the rest ignore it.
ASSERTION_TYPES: tuple[str, ...] = (
    "contains",
    "not_contains",
    "regex",
    "equals",
    "json_valid",
    "json_path_equals",
    "max_tokens",
    "max_latency_ms",
)

# Guard rails so a single run can't fan out into thousands of model calls.
_MAX_CASES = 50
_MAX_ASSERTIONS = 30
_MAX_ASSIGNEES = 8
_MAX_CELLS = 200  # cases * assignees


# ═══════════════════════════════════════════
#  Store load / save
# ═══════════════════════════════════════════

def _load_store() -> dict:
    """Read the evals JSON, tolerating absent/corrupt files (honest empty)."""
    raw = _safe_read(EVALS_PATH)
    if not raw.strip():
        return {"sets": [], "baselines": {}}
    try:
        data = json.loads(raw)
    except Exception as e:
        log.warning("evals store parse failed (%s) — starting empty", e)
        return {"sets": [], "baselines": {}}
    if not isinstance(data, dict):
        return {"sets": [], "baselines": {}}
    data.setdefault("sets", [])
    data.setdefault("baselines", {})
    if not isinstance(data["sets"], list):
        data["sets"] = []
    if not isinstance(data["baselines"], dict):
        data["baselines"] = {}
    return data


def _save_store(store: dict) -> bool:
    return _safe_write(EVALS_PATH, json.dumps(store, ensure_ascii=False, indent=2))


# ═══════════════════════════════════════════
#  Sanitization
# ═══════════════════════════════════════════

def _sanitize_assertion(raw: Any) -> dict | None:
    """Validate one assertion dict. Returns the normalized dict or None
    if the type is unknown (caller drops it)."""
    if not isinstance(raw, dict):
        return None
    a_type = str(raw.get("type") or "").strip()
    if a_type not in ASSERTION_TYPES:
        return None
    out: dict[str, Any] = {"type": a_type}
    # value: keep as-is for equals/json_path_equals (could be str/num/bool/null);
    # coerce to str for text matchers; coerce to int for numeric thresholds.
    if a_type in ("contains", "not_contains", "regex"):
        out["value"] = str(raw.get("value") or "")
    elif a_type in ("max_tokens", "max_latency_ms"):
        try:
            out["value"] = int(raw.get("value") or 0)
        except (TypeError, ValueError):
            out["value"] = 0
    elif a_type == "equals":
        out["value"] = raw.get("value", "")
    elif a_type == "json_path_equals":
        out["value"] = raw.get("value", "")
        out["path"] = str(raw.get("path") or "").strip()
    # json_valid takes no value/path.
    return out


def _sanitize_case(raw: Any) -> dict:
    prompt = ""
    assertions: list[dict] = []
    if isinstance(raw, dict):
        prompt = str(raw.get("prompt") or "")
        for a in (raw.get("assertions") or [])[:_MAX_ASSERTIONS]:
            clean = _sanitize_assertion(a)
            if clean is not None:
                assertions.append(clean)
    return {"prompt": prompt, "assertions": assertions}


def _sanitize_set(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    set_id = str(raw.get("id") or "").strip()
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", set_id):
        set_id = "set-" + uuid.uuid4().hex[:10]
    name = str(raw.get("name") or "").strip() or set_id
    cases_raw = raw.get("cases") or []
    cases = [_sanitize_case(c) for c in cases_raw[:_MAX_CASES]] if isinstance(cases_raw, list) else []
    return {"id": set_id, "name": name, "cases": cases}


# ═══════════════════════════════════════════
#  Assertion evaluator (pure, no I/O — unit-testable offline)
# ═══════════════════════════════════════════

_PATH_SEG_RE = re.compile(r"[^.\[\]]+|\[\d+\]")


def _resolve_json_path(obj: Any, path: str) -> tuple[bool, Any]:
    """Minimal dotted/bracket path resolver (stdlib only — no jsonpath dep).

    Supports ``a.b.c``, ``a.0.b`` (numeric segment indexes a list) and
    ``a[0].b`` bracket syntax. A leading ``$`` or ``$.`` is tolerated.
    Returns ``(found, value)``; ``found`` is False if any segment misses.
    """
    if path.startswith("$"):
        path = path[1:]
        if path.startswith("."):
            path = path[1:]
    if path == "":
        return True, obj
    cur = obj
    for seg in _PATH_SEG_RE.findall(path):
        if seg.startswith("[") and seg.endswith("]"):
            idx_str = seg[1:-1]
        else:
            idx_str = seg
        if isinstance(cur, dict):
            if idx_str not in cur:
                return False, None
            cur = cur[idx_str]
        elif isinstance(cur, list):
            if not idx_str.lstrip("-").isdigit():
                return False, None
            i = int(idx_str)
            if i < -len(cur) or i >= len(cur):
                return False, None
            cur = cur[i]
        else:
            return False, None
    return True, cur


def _values_equal(a: Any, b: Any) -> bool:
    """Equality that treats a stringified number like the number, so a
    JSON value ``1`` matches a user-typed expected ``"1"``."""
    if a == b:
        return True
    # Cross-type numeric/string leniency.
    try:
        if isinstance(a, bool) or isinstance(b, bool):
            return False  # don't let True == 1 surprise users
        return float(str(a)) == float(str(b))
    except (TypeError, ValueError):
        return str(a) == str(b)


def evaluate_assertion(assertion: dict, response: dict) -> dict:
    """Evaluate a single assertion against a model response.

    *response* is a normalized dict: ``{output, tokensTotal, latencyMs}``.
    Returns ``{type, passed, detail}``. Never raises — a bad assertion
    (e.g. invalid regex) fails closed with an explanatory detail.
    """
    a_type = assertion.get("type")
    output = response.get("output") or ""
    tokens = int(response.get("tokensTotal") or 0)
    latency = int(response.get("latencyMs") or 0)
    value = assertion.get("value")

    try:
        if a_type == "contains":
            passed = str(value) in output
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else f"output does not contain {value!r}"}

        if a_type == "not_contains":
            passed = str(value) not in output
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else f"output unexpectedly contains {value!r}"}

        if a_type == "regex":
            try:
                pat = re.compile(str(value))
            except re.error as e:
                return {"type": a_type, "passed": False, "detail": f"invalid regex: {e}"}
            passed = bool(pat.search(output))
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else f"regex {value!r} did not match"}

        if a_type == "equals":
            passed = output.strip() == str(value).strip()
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else "output != expected (after strip)"}

        if a_type == "json_valid":
            try:
                json.loads(output)
                return {"type": a_type, "passed": True, "detail": ""}
            except Exception as e:
                return {"type": a_type, "passed": False, "detail": f"not valid JSON: {e}"}

        if a_type == "json_path_equals":
            path = assertion.get("path") or ""
            try:
                parsed = json.loads(output)
            except Exception as e:
                return {"type": a_type, "passed": False, "detail": f"output not JSON: {e}"}
            found, actual = _resolve_json_path(parsed, path)
            if not found:
                return {"type": a_type, "passed": False, "detail": f"path {path!r} not found"}
            passed = _values_equal(actual, value)
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else f"path {path!r} = {actual!r}, expected {value!r}"}

        if a_type == "max_tokens":
            limit = int(value or 0)
            passed = tokens <= limit
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else f"tokens {tokens} > {limit}"}

        if a_type == "max_latency_ms":
            limit = int(value or 0)
            passed = latency <= limit
            return {"type": a_type, "passed": passed,
                    "detail": "" if passed else f"latency {latency}ms > {limit}ms"}

    except Exception as e:  # never let one assertion crash a run
        return {"type": a_type, "passed": False, "detail": f"evaluator error: {e}"}

    return {"type": a_type, "passed": False, "detail": f"unknown assertion type: {a_type}"}


def evaluate_case(assertions: list[dict], response: dict) -> dict:
    """Evaluate every assertion of a case. A case with zero assertions but a
    successful model call counts as passed (smoke check); a failed model
    call (``response['ok'] is False``) always fails."""
    results = [evaluate_assertion(a, response) for a in (assertions or [])]
    call_ok = bool(response.get("ok", True))
    passed = call_ok and all(r["passed"] for r in results)
    return {
        "ok": call_ok,
        "passed": passed,
        "assertions": results,
        "passedBools": [r["passed"] for r in results],
    }


# ═══════════════════════════════════════════
#  HTTP handlers
# ═══════════════════════════════════════════

def api_eval_sets(_query: dict | None = None) -> dict:
    """List all test sets + their baseline summaries + the assertion-type
    catalogue (so the UI can render the type picker)."""
    store = _load_store()
    baselines = store.get("baselines") or {}
    base_summary: dict[str, dict] = {}
    for key, b in baselines.items():
        if not isinstance(b, dict):
            continue
        cases = b.get("cases") or []
        base_summary[key] = {
            "ts": b.get("ts", 0),
            "caseCount": len(cases),
            "passCount": sum(1 for c in cases if isinstance(c, dict) and c.get("passed")),
        }
    return {
        "ok": True,
        "sets": store.get("sets") or [],
        "baselines": base_summary,
        "assertionTypes": list(ASSERTION_TYPES),
    }


def api_eval_set_save(body: dict) -> dict:
    """Create or update a test set (upsert by id)."""
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    clean = _sanitize_set(body)
    store = _load_store()
    sets = store["sets"]
    for i, s in enumerate(sets):
        if isinstance(s, dict) and s.get("id") == clean["id"]:
            sets[i] = clean
            break
    else:
        sets.append(clean)
    if not _save_store(store):
        return {"ok": False, "error": "failed to write evals store"}
    return {"ok": True, "set": clean}


def api_eval_set_delete(body: dict) -> dict:
    """Delete a test set + any baselines keyed to it."""
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    set_id = str(body.get("id") or body.get("setId") or "").strip()
    if not set_id:
        return {"ok": False, "error": "id required"}
    store = _load_store()
    before = len(store["sets"])
    store["sets"] = [s for s in store["sets"] if not (isinstance(s, dict) and s.get("id") == set_id)]
    # Drop baselines for this set (key prefix "<setId>::").
    store["baselines"] = {
        k: v for k, v in (store.get("baselines") or {}).items()
        if not (isinstance(k, str) and k.startswith(set_id + "::"))
    }
    if not _save_store(store):
        return {"ok": False, "error": "failed to write evals store"}
    return {"ok": True, "deleted": before - len(store["sets"]), "id": set_id}


def _baseline_key(set_id: str, assignee: str) -> str:
    return f"{set_id}::{assignee}"


def _run_one(assignee: str, prompt: str, timeout: int) -> dict:
    """Call the model once via the unified entry, normalize to a response
    dict. Honest failure on missing key/CLI — never fabricates output."""
    t0 = time.time()
    try:
        from .ai_providers import execute_with_assignee
    except Exception as e:  # import-time failure should not crash the run
        return {"ok": False, "output": "", "error": f"providers unavailable: {e}",
                "tokensIn": 0, "tokensOut": 0, "tokensTotal": 0,
                "latencyMs": int((time.time() - t0) * 1000), "provider": "", "model": ""}
    try:
        resp = execute_with_assignee(assignee, prompt, timeout=timeout, fallback=False)
    except Exception as e:
        return {"ok": False, "output": "", "error": str(e),
                "tokensIn": 0, "tokensOut": 0, "tokensTotal": 0,
                "latencyMs": int((time.time() - t0) * 1000), "provider": "", "model": ""}
    latency = int((time.time() - t0) * 1000)
    ok = getattr(resp, "status", "err") == "ok"
    return {
        "ok": ok,
        "output": getattr(resp, "output", "") or "",
        "error": "" if ok else (getattr(resp, "error", "") or "model call failed"),
        "tokensIn": getattr(resp, "tokens_in", 0) or 0,
        "tokensOut": getattr(resp, "tokens_out", 0) or 0,
        "tokensTotal": (getattr(resp, "tokens_total", 0)
                        or ((getattr(resp, "tokens_in", 0) or 0) + (getattr(resp, "tokens_out", 0) or 0))),
        # Provider duration if it reports one, else our wall-clock.
        "latencyMs": getattr(resp, "duration_ms", 0) or latency,
        "provider": getattr(resp, "provider", "") or "",
        "model": getattr(resp, "model", "") or "",
        "costUsd": getattr(resp, "cost_usd", 0.0) or 0.0,
    }


def api_eval_run(body: dict) -> dict:
    """Run a test set across one or more assignees.

    body: {setId, assignees:[...], timeout?, saveBaseline?}

    For each (case × assignee): call the model, evaluate assertions, record
    pass/fail + tokens + latency. Compare each cell to the stored baseline
    for (set, assignee) and flag regressions (was-pass → now-fail). If
    `saveBaseline` is truthy, persist this run's per-case pass state as the
    new baseline for each assignee.
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    set_id = str(body.get("setId") or "").strip()
    assignees_raw = body.get("assignees") or []
    if not isinstance(assignees_raw, list) or not assignees_raw:
        return {"ok": False, "error": "assignees required"}
    assignees = [str(a).strip() for a in assignees_raw if str(a).strip()][:_MAX_ASSIGNEES]
    if not assignees:
        return {"ok": False, "error": "no valid assignees"}
    timeout = int(body.get("timeout") or 180)
    save_baseline = bool(body.get("saveBaseline"))

    store = _load_store()
    target = next((s for s in store["sets"] if isinstance(s, dict) and s.get("id") == set_id), None)
    if not target:
        return {"ok": False, "error": f"set not found: {set_id}"}
    cases = target.get("cases") or []
    if not cases:
        return {"ok": False, "error": "set has no cases"}
    if len(cases) * len(assignees) > _MAX_CELLS:
        return {"ok": False,
                "error": f"too many cells ({len(cases)}×{len(assignees)} > {_MAX_CELLS})"}

    baselines = store.get("baselines") or {}

    # matrix[assignee] = list of per-case cells (same order as cases)
    matrix: dict[str, list[dict]] = {}
    regressions: list[dict] = []
    new_baselines: dict[str, dict] = {}

    for assignee in assignees:
        cells: list[dict] = []
        base = baselines.get(_baseline_key(set_id, assignee)) or {}
        base_cases = base.get("cases") or []
        for idx, case in enumerate(cases):
            prompt = case.get("prompt") or ""
            assertions = case.get("assertions") or []
            resp = _run_one(assignee, prompt, timeout)
            verdict = evaluate_case(assertions, resp)
            cell = {
                "caseIndex": idx,
                "prompt": prompt,
                "ok": resp["ok"],
                "passed": verdict["passed"],
                "error": resp.get("error") or "",
                "output": (resp.get("output") or "")[:2000],
                "tokensIn": resp.get("tokensIn", 0),
                "tokensOut": resp.get("tokensOut", 0),
                "tokensTotal": resp.get("tokensTotal", 0),
                "latencyMs": resp.get("latencyMs", 0),
                "provider": resp.get("provider", ""),
                "model": resp.get("model", ""),
                "assertions": verdict["assertions"],
            }
            # Regression: this case passed in baseline but fails now.
            base_passed = None
            if idx < len(base_cases) and isinstance(base_cases[idx], dict):
                base_passed = base_cases[idx].get("passed")
            cell["baselinePassed"] = base_passed
            cell["regressed"] = bool(base_passed) and not verdict["passed"]
            if cell["regressed"]:
                regressions.append({
                    "assignee": assignee,
                    "caseIndex": idx,
                    "prompt": prompt[:120],
                    "error": cell["error"],
                })
            cells.append(cell)
        matrix[assignee] = cells
        new_baselines[_baseline_key(set_id, assignee)] = {
            "ts": int(time.time()),
            "cases": [
                {"passed": c["passed"], "tokens": c["tokensTotal"], "latencyMs": c["latencyMs"]}
                for c in cells
            ],
        }

    # Aggregate per assignee.
    summary: dict[str, dict] = {}
    for assignee, cells in matrix.items():
        passed = sum(1 for c in cells if c["passed"])
        ok_cells = [c for c in cells if c["ok"]]
        summary[assignee] = {
            "total": len(cells),
            "passed": passed,
            "failed": len(cells) - passed,
            "passRate": round(passed / len(cells), 3) if cells else 0.0,
            "avgLatencyMs": round(sum(c["latencyMs"] for c in ok_cells) / len(ok_cells)) if ok_cells else 0,
            "totalTokens": sum(c["tokensTotal"] for c in cells),
        }

    if save_baseline:
        baselines.update(new_baselines)
        store["baselines"] = baselines
        _save_store(store)

    return {
        "ok": True,
        "setId": set_id,
        "setName": target.get("name") or set_id,
        "assignees": assignees,
        "matrix": matrix,
        "summary": summary,
        "regressions": regressions,
        "regressionCount": len(regressions),
        "baselineSaved": save_baseline,
        "ts": int(time.time()),
    }
