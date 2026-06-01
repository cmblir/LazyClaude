"""Prompt Caching 플레이그라운드 — Anthropic Messages API cache_control 실험.

사용자가 system / tools / messages 의 각 블록에 `cache_control: ephemeral` 을
지정 → Messages API 호출 → `cache_creation_input_tokens`,
`cache_read_input_tokens` 를 UI 에 돌려준다.

히스토리: `~/.claude-dashboard-prompt-cache.json` (최근 20건)
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

HISTORY_PATH = _env_path(
    "CLAUDE_DASHBOARD_PROMPT_CACHE",
    Path.home() / ".claude-dashboard-prompt-cache.json",
)
_MAX_HISTORY = 20

# 기본 예시 3종 — UI 첫 진입 시 보여줄 템플릿
EXAMPLES: list[dict] = [
    {
        "id": "system-prompt",
        "label": "시스템 프롬프트 캐시",
        "description": "대형 시스템 프롬프트를 캐시해 동일 대화 반복 시 비용 절감.",
        "model": "claude-sonnet-4-6",
        "maxTokens": 1024,
        "system": [
            {
                "type": "text",
                "text": (
                    "당신은 Claude 대시보드의 도우미입니다. "
                    "응답은 항상 한국어로 합니다. "
                    "코드는 ```로 감싸고 설명은 3줄 이내로 요약합니다. "
                    "이 시스템 프롬프트는 테스트용 고정 블록입니다. " * 40
                ),
                "cache_control": {"type": "ephemeral"},
            },
        ],
        "tools": [],
        "messages": [
            {"role": "user", "content": "오늘의 핵심 개념을 한 줄로 요약해줘."},
        ],
    },
    {
        "id": "document-cache",
        "label": "대용량 문서 캐시",
        "description": "긴 문서를 user 메시지로 첨부하고 캐시 → 추가 질문 시 재사용.",
        "model": "claude-sonnet-4-6",
        "maxTokens": 1024,
        "system": [],
        "tools": [],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "다음 문서를 기반으로 답해주세요.\n\n"
                            "<document>\n"
                            + ("Claude API 는 Anthropic 의 고성능 LLM 접근 인터페이스입니다. " * 80)
                            + "\n</document>"
                        ),
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": "문서의 핵심 주장을 2문장으로 요약해주세요."},
                ],
            },
        ],
    },
    {
        "id": "tools-cache",
        "label": "도구 정의 캐시",
        "description": "tool 정의를 캐시하면 같은 tools 세트를 반복 호출할 때 재활용.",
        "model": "claude-sonnet-4-6",
        "maxTokens": 1024,
        "system": [
            {"type": "text", "text": "당신은 여러 도구를 잘 쓰는 비서입니다."}
        ],
        "tools": [
            {
                "name": "get_weather",
                "description": "특정 도시의 날씨를 조회한다.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "도시 이름"},
                    },
                    "required": ["city"],
                },
                "cache_control": {"type": "ephemeral"},
            },
        ],
        "messages": [
            {"role": "user", "content": "서울 날씨 어때?"},
        ],
    },
]


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(_safe_read(HISTORY_PATH))
        if isinstance(data, list):
            return data[:_MAX_HISTORY]
    except Exception as e:
        log.warning("prompt_cache history load failed: %s", e)
    return []


def _save_history(entry: dict) -> None:
    items = _load_history()
    items.insert(0, entry)
    items = items[:_MAX_HISTORY]
    try:
        _safe_write(HISTORY_PATH, json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        log.warning("prompt_cache history save failed: %s", e)


def _anthropic_key() -> str:
    keys = load_api_keys()
    val = keys.get("anthropic-api")
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("apiKey") or ""
    return ""


def _call_messages_api(
    api_key: str,
    body_obj: dict,
    timeout: int = 60,
) -> tuple[int, dict]:
    """Messages API 호출. (status_code, json_body) 반환."""
    import urllib.request
    import urllib.error

    body = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
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


# ───────── 비용 추정 ─────────
#
# Anthropic 공식 가격 (per 1M tokens, USD, 2026-04 기준):
#   opus-4-7   : input $15  / cache_write $18.75 / cache_read $1.5  / output $75
#   sonnet-4-6 : input $3   / cache_write $3.75  / cache_read $0.3  / output $15
#   haiku-4-5  : input $0.8 / cache_write $1.0   / cache_read $0.08 / output $4
_PRICING = {
    "claude-opus-4-7":    {"in": 15.0, "cw": 18.75, "cr": 1.50,  "out": 75.0},
    "claude-sonnet-4-6":  {"in": 3.0,  "cw": 3.75,  "cr": 0.30,  "out": 15.0},
    "claude-haiku-4-5":   {"in": 0.8,  "cw": 1.0,   "cr": 0.08,  "out": 4.0},
}


def _estimate_cost(model: str, usage: dict) -> dict:
    """usage dict → 비용 상세 (캐시 절감 계산 포함)."""
    price = None
    for mid, p in _PRICING.items():
        if mid in (model or ""):
            price = p
            break
    if not price:
        return {"usdTotal": 0.0, "usdSaved": 0.0, "note": "unknown-model"}

    ti = usage.get("input_tokens", 0) or 0
    to_ = usage.get("output_tokens", 0) or 0
    cw = usage.get("cache_creation_input_tokens", 0) or 0
    cr = usage.get("cache_read_input_tokens", 0) or 0

    cost_in = (ti / 1_000_000) * price["in"]
    cost_cw = (cw / 1_000_000) * price["cw"]
    cost_cr = (cr / 1_000_000) * price["cr"]
    cost_out = (to_ / 1_000_000) * price["out"]
    usd_total = cost_in + cost_cw + cost_cr + cost_out

    # 캐시 미사용 가정 비용: (ti + cw + cr) 전부를 input 단가로
    hypothetical = ((ti + cw + cr) / 1_000_000) * price["in"] + cost_out
    saved = max(0.0, hypothetical - usd_total)

    return {
        "usdInput": round(cost_in, 6),
        "usdCacheWrite": round(cost_cw, 6),
        "usdCacheRead": round(cost_cr, 6),
        "usdOutput": round(cost_out, 6),
        "usdTotal": round(usd_total, 6),
        "usdSaved": round(saved, 6),
    }


# ───────── API 엔드포인트 ─────────

def api_prompt_cache_examples(_query: dict | None = None) -> dict:
    return {"examples": EXAMPLES}


def api_prompt_cache_history(_query: dict | None = None) -> dict:
    return {"items": _load_history()}


# ───────── 분석 (Analytics) ─────────
#
# 두 개의 소스를 합산한다:
#   1. 이 랩의 자체 히스토리 파일 (~/.claude-dashboard-prompt-cache.json) —
#      각 entry.usage 에 input_tokens / cache_read_input_tokens /
#      cache_creation_input_tokens 가 들어 있고, 1시간 캐시 사용 시
#      entry.usage.cache_creation.{ephemeral_5m_input_tokens,
#      ephemeral_1h_input_tokens} 로 TTL 분할이 노출된다 (Anthropic 공식 docs
#      verified 2026-06: prompt-caching usage fields).
#   2. SQLite sessions 테이블 (Claude Code 세션 인덱스) — input_tokens /
#      output_tokens / cache_read_tokens / cache_creation_tokens 의 flat 컬럼.
#      이 소스는 TTL(5m vs 1h) 분할 정보를 보존하지 않으므로 hit-rate / 절감액
#      집계에만 쓰고, TTL split 은 랩 히스토리에서만 surface 한다.
#
# 캐시 절감액 추정: cache_read 토큰은 input 단가의 ~0.1x 로 청구되므로,
# "캐시 미사용 가정"(cache_read 를 1x input 단가로 청구) 대비 절감액은
#   saved = cache_read_tokens * (in_price - cr_price) / 1e6
# in_price/cr_price 는 모델별 _PRICING 에서 가져온다.

# Daily-trend / hit-rate 추정에 쓸 cache_read 단가가 _PRICING 에 없는 모델
# (sessions 테이블의 model 문자열 등)을 위한 fallback prefix 매칭표.
# cost_timeline 의 검증된 base 단가(2026-06)와 일관되게 cache_read=0.1x,
# cache_write=1.25x 를 적용한다.
_PRICING_PREFIX = {
    "claude-opus":   {"in": 5.0, "cw": 6.25, "cr": 0.50, "out": 25.0},
    "claude-sonnet": {"in": 3.0, "cw": 3.75, "cr": 0.30, "out": 15.0},
    "claude-haiku":  {"in": 1.0, "cw": 1.25, "cr": 0.10, "out": 5.0},
}


def _price_for(model: str) -> dict:
    """모델 문자열 → 단가 dict (cost_timeline 검증 단가 우선).

    분석용 절감액 계산은 cost_timeline 의 검증된 base 단가(2026-06:
    Opus $5/$25, Sonnet $3/$15, Haiku $1/$5, cache_read=0.1x)를 따른다.
    prefix(_PRICING_PREFIX) → 정확 일치(_PRICING legacy) → Sonnet fallback 순.
    legacy _PRICING 은 구버전 base 단가를 일부 포함하므로 prefix 를 우선한다."""
    m = (model or "").lower()
    for prefix, p in _PRICING_PREFIX.items():
        if prefix in m:
            return p
    for mid, p in _PRICING.items():
        if mid in m:
            return p
    return _PRICING_PREFIX["claude-sonnet"]


def _saved_usd(model: str, cache_read: int) -> float:
    """cache_read 토큰을 1x input 단가로 청구했을 때 대비 절감액(USD)."""
    p = _price_for(model)
    cr_price = p.get("cr")
    if cr_price is None:
        cr_price = p["in"] * 0.1
    delta = max(0.0, p["in"] - cr_price)
    return (cache_read / 1_000_000) * delta


def _coerce_usage(usage: dict) -> dict:
    """랩 히스토리 / API usage 객체 → 표준화된 토큰 dict + TTL split."""
    ti = int(usage.get("input_tokens") or 0)
    to_ = int(usage.get("output_tokens") or 0)
    cw = int(usage.get("cache_creation_input_tokens") or 0)
    cr = int(usage.get("cache_read_input_tokens") or 0)
    cc = usage.get("cache_creation")
    ttl5m = 0
    ttl1h = 0
    if isinstance(cc, dict):
        ttl5m = int(cc.get("ephemeral_5m_input_tokens") or 0)
        ttl1h = int(cc.get("ephemeral_1h_input_tokens") or 0)
    return {
        "input": ti, "output": to_,
        "cacheWrite": cw, "cacheRead": cr,
        "ttl5m": ttl5m, "ttl1h": ttl1h,
    }


def _analytics() -> dict:
    """랩 히스토리 + SQLite sessions 를 합산한 prompt-cache 분석.

    반환:
      hitRate          : cache_read / (cache_read + input)  (전체 + 소스별)
      usdSaved         : 캐시로 절감한 추정 비용 (모델별 단가 적용)
      daily            : [{day, cacheRead, input, cacheWrite, hitRate, usdSaved}]
      bySource         : lab / sessions 별 요약
      ttlSplit         : {available, ephemeral5m, ephemeral1h, note}
    """
    import datetime as dt

    # 누적 합산기
    total = {"input": 0, "output": 0, "cacheWrite": 0, "cacheRead": 0, "usdSaved": 0.0}
    by_source: dict[str, dict] = {}
    daily: dict[str, dict] = {}
    ttl5m_total = 0
    ttl1h_total = 0
    ttl_available = False

    def _add_source(name: str) -> dict:
        return by_source.setdefault(name, {
            "source": name, "input": 0, "output": 0,
            "cacheWrite": 0, "cacheRead": 0, "usdSaved": 0.0, "count": 0,
        })

    def _add_day(day: str) -> dict:
        return daily.setdefault(day, {
            "day": day, "input": 0, "output": 0,
            "cacheWrite": 0, "cacheRead": 0, "usdSaved": 0.0, "count": 0,
        })

    def _accumulate(src: str, ts_sec: int, model: str, u: dict) -> None:
        nonlocal ttl5m_total, ttl1h_total, ttl_available
        saved = _saved_usd(model, u["cacheRead"])
        total["input"] += u["input"]
        total["output"] += u["output"]
        total["cacheWrite"] += u["cacheWrite"]
        total["cacheRead"] += u["cacheRead"]
        total["usdSaved"] += saved
        bs = _add_source(src)
        bs["input"] += u["input"]
        bs["output"] += u["output"]
        bs["cacheWrite"] += u["cacheWrite"]
        bs["cacheRead"] += u["cacheRead"]
        bs["usdSaved"] = round(bs["usdSaved"] + saved, 6)
        bs["count"] += 1
        if ts_sec:
            day = dt.date.fromtimestamp(ts_sec).isoformat()
            bd = _add_day(day)
            bd["input"] += u["input"]
            bd["output"] += u["output"]
            bd["cacheWrite"] += u["cacheWrite"]
            bd["cacheRead"] += u["cacheRead"]
            bd["usdSaved"] = round(bd["usdSaved"] + saved, 6)
            bd["count"] += 1
        if u["ttl5m"] or u["ttl1h"]:
            ttl_available = True
            ttl5m_total += u["ttl5m"]
            ttl1h_total += u["ttl1h"]

    # ── 소스 1: 랩 자체 히스토리 ──
    for entry in _load_history():
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "ok":
            continue
        usage = entry.get("usage") or {}
        if not isinstance(usage, dict):
            continue
        u = _coerce_usage(usage)
        # 캐시 활동이 전혀 없으면 건너뛴다 (hit-rate 분모 오염 방지는 아래 분모로 처리)
        ts = int(entry.get("ts") or 0)
        _accumulate("lab", ts, entry.get("model") or "", u)

    # ── 소스 2: SQLite sessions ──
    try:
        from .db import _db, _db_init
        _db_init()
        with _db() as c:
            rows = c.execute(
                "SELECT started_at, input_tokens, output_tokens, "
                "       cache_read_tokens, cache_creation_tokens, model "
                "FROM sessions "
                "WHERE COALESCE(cache_read_tokens,0) > 0 "
                "   OR COALESCE(cache_creation_tokens,0) > 0"
            ).fetchall()
        for r in rows:
            # sessions.started_at 은 밀리초 (system.py 참조: ts/1000).
            ts_ms = r["started_at"] or 0
            ts_sec = int(ts_ms / 1000) if ts_ms else 0
            u = {
                "input": int(r["input_tokens"] or 0),
                "output": int(r["output_tokens"] or 0),
                "cacheWrite": int(r["cache_creation_tokens"] or 0),
                "cacheRead": int(r["cache_read_tokens"] or 0),
                "ttl5m": 0, "ttl1h": 0,  # sessions 는 TTL 분할 미보존
            }
            _accumulate("sessions", ts_sec, r["model"] or "", u)
    except Exception as e:
        log.warning("prompt_cache analytics: sessions read failed: %s", e)

    # ── 파생값 계산 ──
    def _hit_rate(cache_read: int, inp: int) -> float:
        denom = cache_read + inp
        return round(cache_read / denom, 4) if denom > 0 else 0.0

    overall_hit = _hit_rate(total["cacheRead"], total["input"])

    daily_list = []
    for day in sorted(daily.keys()):
        d = daily[day]
        d["hitRate"] = _hit_rate(d["cacheRead"], d["input"])
        d["usdSaved"] = round(d["usdSaved"], 6)
        daily_list.append(d)

    by_source_list = []
    for src in sorted(by_source.keys()):
        b = by_source[src]
        b["hitRate"] = _hit_rate(b["cacheRead"], b["input"])
        b["usdSaved"] = round(b["usdSaved"], 6)
        by_source_list.append(b)

    if ttl_available:
        ttl_note = (
            "TTL 분할은 1시간 캐시를 사용한 랩 호출의 usage.cache_creation "
            "객체에서만 제공됩니다 (Anthropic 공식). SQLite 세션 인덱스는 "
            "flat cache_creation_tokens 만 보존하므로 여기엔 포함되지 않습니다."
        )
    else:
        ttl_note = (
            "5분 vs 1시간 TTL 분할 데이터가 없습니다. Anthropic usage 객체는 "
            "1시간 캐시(cache_control ttl='1h') 사용 시에만 cache_creation."
            "{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens} 를 반환합니다. "
            "SQLite 세션 인덱스의 flat cache_creation_tokens 로는 분리 불가합니다."
        )

    return {
        "ok": True,
        "totals": {
            "input": total["input"],
            "output": total["output"],
            "cacheWrite": total["cacheWrite"],
            "cacheRead": total["cacheRead"],
            "hitRate": overall_hit,
            "usdSaved": round(total["usdSaved"], 6),
        },
        "daily": daily_list,
        "bySource": by_source_list,
        "ttlSplit": {
            "available": ttl_available,
            "ephemeral5m": ttl5m_total,
            "ephemeral1h": ttl1h_total,
            "note": ttl_note,
        },
    }


def api_prompt_cache_analytics(_query: dict | None = None) -> dict:
    """Prompt-cache 분석 엔드포인트.

    랩 자체 히스토리 + SQLite 세션 토큰 컬럼을 합산해
    cache hit-rate / 추정 절감액 / 일별 추이 / TTL split 을 반환한다.
    """
    try:
        return _analytics()
    except Exception as e:
        log.warning("prompt_cache analytics failed: %s", e)
        return {"ok": False, "error": str(e)}


def api_prompt_cache_test(body: dict) -> dict:
    """프롬프트 + cache_control 로 Messages API 호출 → usage 반환."""
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}

    model = (body.get("model") or "claude-sonnet-4-6").strip()
    max_tokens = int(body.get("maxTokens") or 1024)
    system = body.get("system") or []
    tools = body.get("tools") or []
    messages = body.get("messages") or []

    if not isinstance(messages, list) or not messages:
        return {"ok": False, "error": "messages required (list)"}

    api_key = _anthropic_key()
    if not api_key:
        return {
            "ok": False,
            "needKey": True,
            "error": "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장하거나 환경변수 설정",
        }

    body_obj: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        body_obj["system"] = system
    if tools:
        body_obj["tools"] = tools

    t0 = int(time.time() * 1000)
    status, data = _call_messages_api(api_key, body_obj)
    duration = int(time.time() * 1000) - t0

    if status != 200:
        err = (data.get("error") or {}).get("message") or f"HTTP {status}"
        entry = {
            "id": f"pc-{uuid.uuid4().hex[:10]}",
            "ts": int(time.time()),
            "model": model,
            "status": "err",
            "error": err,
            "durationMs": duration,
            "request": body_obj,
        }
        _save_history(entry)
        return {"ok": False, "error": err, "status": status, "entry": entry}

    usage = data.get("usage") or {}
    text_blocks = [
        b.get("text", "")
        for b in (data.get("content") or [])
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    cost = _estimate_cost(model, usage)

    entry = {
        "id": f"pc-{uuid.uuid4().hex[:10]}",
        "ts": int(time.time()),
        "model": model,
        "status": "ok",
        "durationMs": duration,
        "usage": usage,
        "cost": cost,
        "output": "".join(text_blocks),
        "request": body_obj,
        "raw": data,
    }
    _save_history(entry)

    return {
        "ok": True,
        "model": model,
        "durationMs": duration,
        "usage": usage,
        "cost": cost,
        "output": entry["output"],
        "entry": entry,
    }
