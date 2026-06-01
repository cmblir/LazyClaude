"""Anthropic 공식 hosted tools 플레이그라운드 — web_search / code_execution / web_fetch.

기존 tool_use_lab 은 사용자가 tool schema 를 정의하고 tool_result 를
수동으로 공급하는 반면, 여기는 Anthropic 이 서버 측에서 **직접 실행**
하는 hosted tool 을 실습한다.

지원 도구 (verified 2026-06-01, platform.claude.com docs 기준):
- web_search (tool type: `web_search_20260209`) — 웹 검색 + citation. GA, beta header 불필요.
- code_execution (tool type: `code_execution_20250825`) — Bash + 파일 연산 sandbox.
  beta header `code-execution-2025-08-25` 필요.
- web_fetch (tool type: `web_fetch_20260209`) — URL 본문 fetch + citation. GA, beta header 불필요.
  보안상 **대화 컨텍스트에 이미 등장한 URL** 만 fetch 가능 (사용자 메시지 / 이전 검색·fetch 결과).
  Claude 가 임의 생성한 URL 이나 컨테이너 도구(Code Execution/Bash) 산출 URL 은 fetch 불가.

web_search / web_fetch 는 GA 로 `anthropic-beta` 헤더가 없다 (`beta` == "").
code_execution 만 beta header 를 사용한다. Anthropic 스펙 변경 시 `TOOL_CATALOG` 만 갱신.
실패하면 에러 메시지를 그대로 사용자에게 노출.

히스토리: `~/.claude-dashboard-server-tools.json` (최근 20건)
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
    "CLAUDE_DASHBOARD_SERVER_TOOLS",
    Path.home() / ".claude-dashboard-server-tools.json",
)
_MAX_HISTORY = 20

# Anthropic hosted tool 카탈로그 — verified 2026-06-01 (platform.claude.com docs).
# 실제 API 스펙이 바뀌면 이 맵만 갱신하면 된다.
# `beta` == "" 이면 GA 도구 (anthropic-beta 헤더 미부착).
TOOL_CATALOG: list[dict] = [
    {
        "id": "web_search",
        "label": "🌐 Web Search",
        "description": "Anthropic 서버 측 웹 검색 + citation. GA — beta header 불필요. "
                       "최신 `web_search_20260209` 은 dynamic filtering 지원 (code_execution 동시 활성화 필요). "
                       "검색당 $10/1,000 + 표준 토큰 비용.",
        "apiType": "web_search_20260209",
        "beta": "",
        "block": {"type": "web_search_20260209", "name": "web_search", "max_uses": 3},
        "supportedModels": [
            "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6",
        ],
    },
    {
        "id": "code_execution",
        "label": "🧪 Code Execution",
        "description": "Anthropic 호스팅 sandbox — Bash + 파일 연산 (stdout/stderr/return_code). "
                       "`code_execution_20250825` 는 모든 지원 모델에서 사용 가능. "
                       "web_search/web_fetch 와 함께 쓰면 무료, 아니면 월 1,550 시간 무료 후 컨테이너당 $0.05/시간.",
        "apiType": "code_execution_20250825",
        "beta": "code-execution-2025-08-25",
        "block": {"type": "code_execution_20250825", "name": "code_execution"},
        "supportedModels": [
            "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6",
        ],
    },
    {
        "id": "web_fetch",
        "label": "📄 Web Fetch",
        "description": "Anthropic 서버 측 URL 본문 fetch + citation. GA — beta header 불필요. "
                       "보안상 **대화 컨텍스트에 이미 등장한 URL** 만 fetch 가능 (Claude 가 임의 생성한 URL 불가). "
                       "JS 렌더링 사이트 미지원. 추가 비용 없음 (표준 토큰 비용만).",
        "apiType": "web_fetch_20260209",
        "beta": "",
        "block": {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3},
        "supportedModels": [
            "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6",
        ],
    },
]

EXAMPLES: list[dict] = [
    {
        "id": "search-latest",
        "label": "최신 뉴스 검색",
        "description": "웹 검색으로 최근 뉴스를 요약하고 출처 citation 포함.",
        "model": "claude-sonnet-4-6",
        "enabledTools": ["web_search"],
        "prompt": "오늘 AI 업계에서 주목할 만한 뉴스 3개를 요약해줘. 각 항목에 출처 링크 포함.",
    },
    {
        "id": "calc-python",
        "label": "Python 으로 계산",
        "description": "코드 실행으로 계산/분석 수행.",
        "model": "claude-sonnet-4-6",
        "enabledTools": ["code_execution"],
        "prompt": "1부터 100 까지 소수의 합을 계산해서 보여줘. Python 으로 직접 계산해.",
    },
    {
        "id": "search-then-analyze",
        "label": "검색 + 분석 결합",
        "description": "웹 검색 + 코드 실행을 함께 사용.",
        "model": "claude-opus-4-8",
        "enabledTools": ["web_search", "code_execution"],
        "prompt": "최근 3년간 Anthropic, OpenAI, Google DeepMind 의 논문 편수를 웹에서 찾아보고, 그 수치로 막대 그래프의 값 배열 [A, O, G] 을 출력해.",
    },
    {
        "id": "fetch-url",
        "label": "URL 본문 요약",
        "description": "web_fetch 로 URL 본문을 가져와 요약. "
                       "프롬프트에 URL 을 직접 포함해야 fetch 가능 (컨텍스트에 없는 URL 은 fetch 불가).",
        "model": "claude-opus-4-8",
        "enabledTools": ["web_fetch"],
        "prompt": "https://www.anthropic.com/news 의 내용을 가져와서 핵심 발표 3가지를 요약해줘. 출처 citation 포함.",
    },
]


def _anthropic_key() -> str:
    keys = load_api_keys()
    val = keys.get("anthropic-api")
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("apiKey") or ""
    return ""


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(_safe_read(HISTORY_PATH))
        if isinstance(data, list):
            return data[:_MAX_HISTORY]
    except Exception as e:
        log.warning("server_tools history load failed: %s", e)
    return []


def _save_history(entry: dict) -> None:
    items = _load_history()
    items.insert(0, entry)
    items = items[:_MAX_HISTORY]
    try:
        _safe_write(HISTORY_PATH, json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        log.warning("server_tools history save failed: %s", e)


def api_server_tools_catalog(_q: dict | None = None) -> dict:
    return {"tools": TOOL_CATALOG, "examples": EXAMPLES}


def api_server_tools_history(_q: dict | None = None) -> dict:
    return {"items": _load_history()}


def api_server_tools_run(body: dict) -> dict:
    """hosted tool 활성화 상태로 Messages API 호출."""
    import urllib.request
    import urllib.error

    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}

    model = (body.get("model") or "claude-sonnet-4-6").strip()
    max_tokens = int(body.get("maxTokens") or 2048)
    prompt = (body.get("prompt") or "").strip()
    system_prompt = (body.get("system") or "").strip()
    enabled = body.get("enabledTools") or []

    if not prompt:
        return {"ok": False, "error": "prompt required"}
    if not isinstance(enabled, list) or not enabled:
        return {"ok": False, "error": "enabledTools required (non-empty list)"}

    selected = [t for t in TOOL_CATALOG if t["id"] in enabled]
    if not selected:
        return {"ok": False, "error": "no valid tools selected"}

    # 모델 지원 가드
    unsupported = [t["label"] for t in selected if model not in t["supportedModels"]]
    if unsupported:
        return {
            "ok": False,
            "unsupported": True,
            "error": f"{', '.join(unsupported)} 는 {model} 에서 지원되지 않습니다.",
        }

    api_key = _anthropic_key()
    if not api_key:
        return {
            "ok": False, "needKey": True,
            "error": "ANTHROPIC_API_KEY 미설정 — aiProviders 탭에서 저장",
        }

    tools = [t["block"] for t in selected]
    # GA 도구는 beta == "" 이므로 빈 값은 제외. 비어 있으면 anthropic-beta 헤더 자체를 보내지 않는다.
    betas = ",".join(dict.fromkeys(t["beta"] for t in selected if t["beta"]))

    body_obj: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "tools": tools,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        body_obj["system"] = system_prompt

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    if betas:
        headers["anthropic-beta"] = betas

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body_obj).encode("utf-8"),
        headers=headers,
    )

    t0 = int(time.time() * 1000)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            ej = json.loads(e.read().decode("utf-8"))
            msg = (ej.get("error") or {}).get("message") or f"HTTP {e.code}"
        except Exception:
            msg = f"HTTP {e.code}"
        duration = int(time.time() * 1000) - t0
        entry = {
            "id": f"stl-{uuid.uuid4().hex[:10]}",
            "ts": int(time.time()),
            "model": model, "enabledTools": enabled,
            "status": "err", "error": msg, "durationMs": duration,
            "prompt": prompt,
        }
        _save_history(entry)
        return {"ok": False, "error": msg, "durationMs": duration}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    duration = int(time.time() * 1000) - t0
    blocks = data.get("content") or []

    # content 블록 분류
    text_parts: list[str] = []
    server_tool_uses: list[dict] = []
    tool_results: list[dict] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        bt = b.get("type", "")
        if bt == "text":
            text_parts.append(b.get("text") or "")
        elif bt == "server_tool_use":
            server_tool_uses.append({
                "id": b.get("id"),
                "name": b.get("name"),
                "input": b.get("input") or {},
            })
        elif bt.endswith("_tool_result"):
            tool_results.append({
                "kind": bt,
                "toolUseId": b.get("tool_use_id"),
                "content": b.get("content"),
            })

    usage = data.get("usage") or {}
    entry = {
        "id": f"stl-{uuid.uuid4().hex[:10]}",
        "ts": int(time.time()),
        "model": model, "enabledTools": enabled,
        "status": "ok",
        "durationMs": duration,
        "usage": usage,
        "stopReason": data.get("stop_reason"),
        "output": "".join(text_parts),
        "serverToolUses": server_tool_uses,
        "toolResults": tool_results,
        "prompt": prompt,
    }
    _save_history(entry)

    return {
        "ok": True,
        "model": model,
        "durationMs": duration,
        "usage": usage,
        "output": entry["output"],
        "serverToolUses": server_tool_uses,
        "toolResults": tool_results,
        "stopReason": data.get("stop_reason"),
    }
