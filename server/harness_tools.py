"""Claude 하네스 도구 카탈로그 — 인기 토큰 절감/관측/라우팅 도구를 한곳에서
보고 바로 설치·실행한다.

설계는 rtk_lab / ccr_setup 과 동일: 설치/실행 명령은 **카탈로그에 하드코딩된
것만** 실행하며(사용자 입력이 명령에 들어가지 않음), macOS 에서는 Terminal.app
창에서 대화형으로 돌려 사용자가 진행 상황을 직접 본다. 모든 저장소·명령은
공식 소스(2026-06)로 검증한 값이다.

RTK 와 claude-code-router(ccr) 는 이미 전용 탭이 있으므로 여기서는 카탈로그에
교차 링크만 둔다(openTab).
"""
from __future__ import annotations

from pathlib import Path

from .cli_tools import _which, _run_in_terminal
from .config import CLAUDE_HOME


# (id, name, category, desc, repo, lang, license, install|run|openTab, use, check)
# category: token(토큰 절감) · analytics(사용량 관측) · routing(모델 라우팅) · list(큐레이션)
HARNESS_TOOLS: list[dict] = [
    {
        "id": "caveman", "name": "Caveman", "category": "token",
        "desc": "출력 토큰 ~65% 절감 — 에이전트가 '원시인 말투'(군더더기 제거, 기술 내용·코드·에러는 보존)로 답하도록 강제하는 Claude Code 스킬.",
        "repo": "https://github.com/JuliusBrussee/caveman",
        "lang": "JS/Python", "license": "MIT",
        "install": "curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh | bash",
        "use": "에이전트에서 /caveman (lite·full·ultra·wenyan), Node ≥18 필요",
        "check": {"type": "path", "value": str(CLAUDE_HOME / "skills" / "caveman")},
        "openTab": "caveman",
    },
    {
        "id": "ccusage", "name": "ccusage", "category": "analytics",
        "desc": "로컬 JSONL 에서 Claude Code(및 Codex/Gemini 등) 토큰·비용을 일/주/월/세션별로 분석하는 CLI. 설치 없이 즉시 실행.",
        "repo": "https://github.com/ryoppippi/ccusage",
        "lang": "Rust/TS", "license": "MIT",
        "run": "npx -y ccusage@latest",
        "use": "npx ccusage / bunx ccusage — 기본은 일자별 리포트",
        "check": None,
    },
    {
        "id": "rtk", "name": "RTK (Rust Token Killer)", "category": "token",
        "desc": "Rust 프록시로 dev 명령(git/ls 등) 토큰 60-90% 절감. 대시보드에 전용 탭이 있어요.",
        "repo": "https://github.com/rtk-ai/rtk",
        "lang": "Rust", "license": "MIT",
        "openTab": "rtk",
        "check": {"type": "cmd", "value": "rtk"},
    },
    {
        "id": "ccr", "name": "claude-code-router", "category": "routing",
        "desc": "요청을 작업 유형별로 더 저렴한 모델/프로바이더(Haiku·DeepSeek·Ollama 등)로 라우팅. 대시보드에 전용 탭이 있어요.",
        "repo": "https://github.com/musistudio/claude-code-router",
        "lang": "TypeScript", "license": "MIT",
        "openTab": "ccr",
        "check": {"type": "cmd", "value": "ccr"},
    },
    {
        "id": "awesome-claude-code", "name": "awesome-claude-code", "category": "list",
        "desc": "Claude Code 도구·IDE 통합·프레임워크·리소스 큐레이션 목록.",
        "repo": "https://github.com/jqueryscript/awesome-claude-code",
        "lang": "", "license": "",
    },
    {
        "id": "awesome-claude-code-toolkit", "name": "awesome-claude-code-toolkit", "category": "list",
        "desc": "에이전트·스킬·명령·플러그인·훅·MCP 설정을 망라한 대형 Claude Code 툴킷 모음.",
        "repo": "https://github.com/rohitg00/awesome-claude-code-toolkit",
        "lang": "", "license": "",
    },
    {
        "id": "awesome-claude-skills", "name": "awesome-claude-skills", "category": "list",
        "desc": "Claude 워크플로우 커스터마이즈용 스킬·리소스 큐레이션 목록.",
        "repo": "https://github.com/ComposioHQ/awesome-claude-skills",
        "lang": "", "license": "",
    },
]

CATEGORY_LABELS = {
    "token": "토큰 절감",
    "analytics": "사용량 관측",
    "routing": "모델 라우팅",
    "list": "큐레이션 목록",
}

_BY_ID = {t["id"]: t for t in HARNESS_TOOLS}


def _installed(tool: dict) -> bool | None:
    """Best-effort 설치 감지. None = 감지 불가(설치 불필요/즉시 실행형)."""
    check = tool.get("check")
    if not check:
        return None
    if check["type"] == "cmd":
        return bool(_which(check["value"]))
    if check["type"] == "path":
        try:
            return Path(check["value"]).expanduser().exists()
        except Exception:
            return False
    return None


def api_harness_tools_list(_q: dict | None = None) -> dict:
    """카탈로그 + 도구별 설치 상태 + 카테고리 라벨 반환."""
    tools = []
    for t in HARNESS_TOOLS:
        entry = {k: t.get(k) for k in
                 ("id", "name", "category", "desc", "repo", "lang", "license",
                  "install", "run", "use", "openTab")}
        entry["categoryLabel"] = CATEGORY_LABELS.get(t["category"], t["category"])
        entry["installed"] = _installed(t)
        tools.append(entry)
    return {
        "ok": True,
        "tools": tools,
        "categories": [{"id": k, "label": v} for k, v in CATEGORY_LABELS.items()],
        "npxAvailable": bool(_which("npx") or _which("bunx")),
    }


# ── Caveman dedicated tab ───────────────────────────────────────────────────
# caveman installs as a *suite* of Claude Code skills (symlinked into
# ~/.claude/skills/ → ~/.agents/skills/) plus a plugin marketplace entry.
CAVEMAN_REPO = "https://github.com/JuliusBrussee/caveman"
CAVEMAN_INSTALL = ("curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/"
                   "caveman/main/install.sh | bash")
CAVEMAN_LEVELS = ["lite", "full", "ultra", "wenyan-lite", "wenyan-full", "wenyan-ultra"]
CAVEMAN_COMPONENTS = {
    "caveman": "압축 모드 — 출력 토큰 ~75% 절감 (군더더기 제거, 코드·에러·기술내용 보존). /caveman [레벨]",
    "cavecrew": "caveman 스타일 서브에이전트 위임 가이드 (investigator·builder·reviewer) — 결과를 압축해 메인 컨텍스트 절약",
    "caveman-commit": "압축 커밋 메시지 생성 (Conventional Commits). /caveman-commit",
    "caveman-compress": "CLAUDE.md·메모리 파일을 caveman 포맷으로 압축해 입력 토큰 절감. /caveman-compress <파일>",
    "caveman-help": "caveman 모드·스킬·명령 레퍼런스 카드. /caveman-help",
    "caveman-review": "압축 코드리뷰 코멘트 (위치·문제·수정 한 줄). /caveman-review",
    "caveman-stats": "이번 세션 실제 토큰 사용·절감 통계 (세션 로그 기반). /caveman-stats",
}


def api_caveman_status(_q: dict | None = None) -> dict:
    """caveman 스위트 설치 상태 + 컴포넌트별 감지 + 사용 가이드."""
    skills = CLAUDE_HOME / "skills"
    comps = []
    for name, desc in CAVEMAN_COMPONENTS.items():
        comps.append({"name": name, "command": "/" + name, "desc": desc,
                      "installed": (skills / name).exists()})
    installed_count = sum(1 for c in comps if c["installed"])
    return {
        "ok": True,
        "installed": (skills / "caveman").exists(),
        "installedCount": installed_count,
        "totalComponents": len(comps),
        "components": comps,
        "skillsDir": str(skills),
        "repo": CAVEMAN_REPO,
        "installCmd": CAVEMAN_INSTALL,
        "levels": CAVEMAN_LEVELS,
        "nodeAvailable": bool(_which("node")),
    }


def api_caveman_action(body: dict | None = None) -> dict:
    """install / reinstall the caveman suite in Terminal (curated command only)."""
    action = ((body or {}).get("action") or "install").lower()
    if action not in ("install", "reinstall"):
        return {"ok": False, "error": "unsupported action", "error_key": "err_unsupported"}
    result = _run_in_terminal(CAVEMAN_INSTALL)
    return {**result, "action": action, "command": CAVEMAN_INSTALL}


def api_harness_tool_run(body: dict | None = None) -> dict:
    """카탈로그에 등록된 도구의 install/run 명령을 Terminal 에서 실행.

    body: {id}. 보안상 **카탈로그(HARNESS_TOOLS)에 하드코딩된 명령만** 실행하며,
    사용자 입력은 명령에 섞이지 않는다(id 검증 후 고정 문자열 사용).
    """
    tid = (body or {}).get("id")
    tool = _BY_ID.get(tid) if isinstance(tid, str) else None
    if not tool:
        return {"ok": False, "error": "unknown tool", "error_key": "err_unknown_tool"}
    cmd = tool.get("install") or tool.get("run")
    if not cmd:
        return {"ok": False, "error": "this tool has no runnable command (link-only)",
                "error_key": "err_no_command"}
    result = _run_in_terminal(cmd)
    kind = "install" if tool.get("install") else "run"
    return {**result, "id": tid, "kind": kind, "command": cmd}
