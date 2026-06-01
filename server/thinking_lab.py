"""Extended Thinking 플레이그라운드 — Claude 의 reasoning block 을 분리 시각화.

Anthropic Messages API 의 thinking 모드를 활성화 → 응답 `content` 에서
`type:"thinking"` 블록과 `type:"text"` 블록을 분리해서 돌려준다. Haiku 는 비지원 경고.

Two thinking dialects (verified against the official adaptive-thinking docs,
fetched 2026-06-01):

- Adaptive (`thinking: {type: "adaptive"}`, NO budget_tokens): the recommended
  control on the newest models, with thinking depth driven by the top-level
  `output_config.effort` parameter. On Opus 4.8 / Opus 4.7 this is the *only*
  supported mode — manual `type:"enabled"` is rejected with HTTP 400. Their
  `thinking.display` default is `"omitted"` (blank thinking text), so we set
  `display:"summarized"` explicitly to receive summaries.
- Manual (`thinking: {type: "enabled", budget_tokens: N}`): still required by
  older models (Sonnet 4.5, Opus 4.5, Opus 4.1, …); deprecated-but-functional
  on Opus 4.6 / Sonnet 4.6.

Billed reasoning tokens are reported at
`usage.output_tokens_details.thinking_tokens`.

히스토리: `~/.claude-dashboard-thinking-lab.json` (최근 20건)
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
    "CLAUDE_DASHBOARD_THINKING_LAB",
    Path.home() / ".claude-dashboard-thinking-lab.json",
)
_MAX_HISTORY = 20

# ───────── Thinking-mode model awareness ─────────
# Verified against https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking
# (fetched 2026-06-01).
#
# ADAPTIVE_ONLY  — adaptive is the only mode; manual type:"enabled" → HTTP 400.
# ADAPTIVE_OK    — adaptive supported (manual deprecated-but-functional here).
# DISPLAY_OMITTED — thinking.display defaults to "omitted"; must opt into
#                   "summarized" explicitly to receive visible thinking text.
#
# Anything not listed below is treated as a legacy model that REQUIRES manual
# thinking: {type: "enabled", budget_tokens: N}.
ADAPTIVE_ONLY_MODELS = {"claude-opus-4-8", "claude-opus-4-7"}
ADAPTIVE_OK_MODELS = ADAPTIVE_ONLY_MODELS | {"claude-opus-4-6", "claude-sonnet-4-6"}
DISPLAY_OMITTED_MODELS = {"claude-opus-4-8", "claude-opus-4-7"}

# Complete effort enum — exactly five values per the official effort docs:
# "The values documented on this page are the complete set the API accepts."
# `high` is the default and equals omitting the parameter.
EFFORT_LEVELS = ["low", "medium", "high", "xhigh", "max"]


def _supports_adaptive(model: str) -> bool:
    return (model or "").lower() in ADAPTIVE_OK_MODELS


def _adaptive_only(model: str) -> bool:
    return (model or "").lower() in ADAPTIVE_ONLY_MODELS


def _display_defaults_omitted(model: str) -> bool:
    return (model or "").lower() in DISPLAY_OMITTED_MODELS


def _build_thinking_request(
    model: str,
    *,
    budget: int,
    effort: str | None = None,
) -> tuple[dict, dict | None]:
    """Return ``(thinking_block, output_config_or_None)`` for ``model``.

    - Adaptive-capable models → ``thinking: {type: "adaptive"}`` (no
      budget_tokens). For models whose ``display`` defaults to ``"omitted"``
      (Opus 4.8 / 4.7) we set ``display: "summarized"`` so the thinking text is
      not blank. The ``effort`` parameter (if supplied) rides on the top-level
      ``output_config`` field — NOT under ``thinking``.
    - Legacy models → ``thinking: {type: "enabled", budget_tokens: N}``.
    """
    if _supports_adaptive(model):
        thinking: dict = {"type": "adaptive"}
        if _display_defaults_omitted(model):
            thinking["display"] = "summarized"
        output_config: dict | None = None
        if effort and effort in EFFORT_LEVELS:
            output_config = {"effort": effort}
        return thinking, output_config
    # Legacy: manual extended thinking is required.
    return {"type": "enabled", "budget_tokens": budget}, None


THINKING_MODELS = [
    {"id": "claude-opus-4-8", "label": "Opus 4.8", "supported": True, "mode": "adaptive"},
    {"id": "claude-opus-4-7", "label": "Opus 4.7", "supported": True, "mode": "adaptive"},
    {"id": "claude-opus-4-6", "label": "Opus 4.6", "supported": True, "mode": "adaptive"},
    {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "supported": True, "mode": "adaptive"},
    {"id": "claude-haiku-4-5", "label": "Haiku 4.5", "supported": False, "mode": None},
]

# Default example targets Opus 4.8 (adaptive-only) — the previous default
# (claude-sonnet-4-6 with manual budget_tokens) still works on Sonnet 4.6 but
# would 400 on Opus 4.8 / 4.7. The `effort` field drives adaptive depth on the
# adaptive-capable models; `budgetTokens` is only used as a fallback for legacy
# models that still require manual extended thinking.
EXAMPLES: list[dict] = [
    {
        "id": "math-reasoning",
        "label": "수학 추론",
        "description": "복잡한 수식 단계를 thinking block 으로 확인.",
        "model": "claude-opus-4-8",
        "effort": "medium",
        "budgetTokens": 4096,
        "maxTokens": 4096,
        "prompt": "자동차가 시속 72km 로 출발해 30분마다 속도를 10% 씩 높이면 2시간 후 누적 주행거리는 몇 km 인가?",
    },
    {
        "id": "code-debug",
        "label": "코드 디버깅",
        "description": "버그 분석 과정 · 가설 검증 과정을 시각화.",
        "model": "claude-sonnet-4-6",
        "effort": "medium",
        "budgetTokens": 6000,
        "maxTokens": 4096,
        "prompt": "파이썬 dict 의 키 순서 보존은 어느 버전부터 공식 보증되는지, 그리고 왜 이전에는 안 됐는지 설명해줘.",
    },
    {
        "id": "plan-design",
        "label": "설계 플래닝",
        "description": "아키텍처 결정 과정을 thinking 에 노출.",
        "model": "claude-opus-4-8",
        "effort": "high",
        "budgetTokens": 10000,
        "maxTokens": 4096,
        "prompt": "소규모 팀(5명)이 매일 10만 이벤트를 처리하는 실시간 알림 시스템을 만들려고 한다. SQS vs Kafka vs Redis Streams 중 어떤 선택이 적합한지 트레이드오프를 설계해서 답해줘.",
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
        log.warning("thinking_lab history load failed: %s", e)
    return []


def _save_history(entry: dict) -> None:
    items = _load_history()
    items.insert(0, entry)
    items = items[:_MAX_HISTORY]
    try:
        _safe_write(HISTORY_PATH, json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        log.warning("thinking_lab history save failed: %s", e)


def _anthropic_key() -> str:
    keys = load_api_keys()
    val = keys.get("anthropic-api")
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("apiKey") or ""
    return ""


def api_thinking_lab_models(_query: dict | None = None) -> dict:
    return {"models": THINKING_MODELS}


def api_thinking_lab_examples(_query: dict | None = None) -> dict:
    return {"examples": EXAMPLES}


def api_thinking_lab_history(_query: dict | None = None) -> dict:
    return {"items": _load_history()}


def api_thinking_lab_test(body: dict) -> dict:
    import urllib.request
    import urllib.error

    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}

    model = (body.get("model") or "claude-opus-4-8").strip()
    budget = int(body.get("budgetTokens") or 4096)
    max_tokens = int(body.get("maxTokens") or 2048)
    prompt = (body.get("prompt") or "").strip()
    # effort drives adaptive thinking depth (output_config.effort). Default
    # unset → omit the field entirely so the API applies the model default
    # (`high` on Opus 4.8). Unknown values are dropped.
    effort_raw = (body.get("effort") or "").strip().lower()
    effort = effort_raw if effort_raw in EFFORT_LEVELS else None
    if not prompt:
        return {"ok": False, "error": "prompt required"}

    # budget 범위 안전화 (legacy 모델의 manual extended thinking 에만 사용)
    budget = max(1024, min(32000, budget))
    # max_tokens 는 budget + 일부 여유
    if max_tokens <= budget:
        max_tokens = budget + 1024

    if "haiku" in model:
        return {
            "ok": False,
            "unsupported": True,
            "error": "Extended Thinking 은 Haiku 에서 지원되지 않습니다. Opus 또는 Sonnet 사용.",
        }

    api_key = _anthropic_key()
    if not api_key:
        return {
            "ok": False,
            "needKey": True,
            "error": "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장하거나 환경변수 설정",
        }

    # Model-aware thinking block: adaptive (no budget_tokens) for newer models,
    # legacy enabled+budget_tokens only where still required. See
    # _build_thinking_request docstring for the verified rules.
    thinking_block, output_config = _build_thinking_request(
        model, budget=budget, effort=effort
    )
    body_obj: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "thinking": thinking_block,
        "messages": [{"role": "user", "content": prompt}],
    }
    if output_config is not None:
        body_obj["output_config"] = output_config

    t0 = int(time.time() * 1000)
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body_obj).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            err = (err_body.get("error") or {}).get("message") or f"HTTP {e.code}"
        except Exception:
            err = f"HTTP {e.code}"
        duration = int(time.time() * 1000) - t0
        entry = {
            "id": f"tl-{uuid.uuid4().hex[:10]}",
            "ts": int(time.time()),
            "model": model,
            "mode": thinking_block.get("type"),
            "effort": effort,
            "budgetTokens": budget,
            "status": "err",
            "error": err,
            "durationMs": duration,
            "prompt": prompt,
        }
        _save_history(entry)
        return {"ok": False, "error": err}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    duration = int(time.time() * 1000) - t0

    thinking_blocks: list[str] = []
    text_blocks: list[str] = []
    for block in (data.get("content") or []):
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "thinking":
            thinking_blocks.append(block.get("thinking") or "")
        elif btype == "text":
            text_blocks.append(block.get("text") or "")

    usage = data.get("usage") or {}
    # Billed reasoning tokens: usage.output_tokens_details.thinking_tokens
    # (verified). May be absent on older responses / non-thinking turns.
    details = usage.get("output_tokens_details") or {}
    thinking_tokens = details.get("thinking_tokens")
    entry = {
        "id": f"tl-{uuid.uuid4().hex[:10]}",
        "ts": int(time.time()),
        "model": model,
        "mode": thinking_block.get("type"),
        "effort": effort,
        "budgetTokens": budget,
        "status": "ok",
        "durationMs": duration,
        "usage": usage,
        "thinkingTokens": thinking_tokens,
        "thinking": "\n\n───\n\n".join(thinking_blocks),
        "output": "".join(text_blocks),
        "prompt": prompt,
        "stopReason": data.get("stop_reason"),
    }
    _save_history(entry)

    return {
        "ok": True,
        "model": model,
        "mode": thinking_block.get("type"),
        "effort": effort,
        "budgetTokens": budget,
        "durationMs": duration,
        "usage": usage,
        "thinkingTokens": thinking_tokens,
        "thinking": entry["thinking"],
        "output": entry["output"],
        "thinkingBlocks": len(thinking_blocks),
        "stopReason": entry["stopReason"],
    }
