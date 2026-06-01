"""Bash Sandbox Manager — read/edit the sandboxed Bash tool config in settings.json.

Claude Code's sandboxed Bash tool runs shell commands under OS-level filesystem
and network isolation (macOS Seatbelt, Linux/WSL2 bubblewrap). It is configured
through the top-level `sandbox` object in `~/.claude/settings.json`.

This module surfaces the current `sandbox` block, explains each key, and writes
back ONLY verified sandbox keys via an atomic read-merge-write that:
  - refuses to run if settings.json is malformed (so we never clobber it),
  - takes a timestamped `settings.json.bak.<ts>` backup before writing,
  - validates every supplied value against the documented type / allowed set,
  - leaves every unrelated top-level key untouched.

Verified against the official docs (fetched 2026-06):
  https://code.claude.com/docs/en/sandboxing
  https://code.claude.com/docs/en/settings  (#sandbox-settings)

Documented `sandbox` schema:
  sandbox.enabled                         bool   default false
  sandbox.failIfUnavailable               bool   default false
  sandbox.autoAllowBashIfSandboxed        bool   default true
  sandbox.allowUnsandboxedCommands        bool   default true
  sandbox.excludedCommands                str[]
  sandbox.filesystem.allowWrite           str[]
  sandbox.filesystem.denyWrite            str[]
  sandbox.filesystem.denyRead             str[]
  sandbox.filesystem.allowRead            str[]
  sandbox.filesystem.allowManagedReadPathsOnly  bool  (managed-only)
  sandbox.network.allowedDomains          str[]
  sandbox.network.allowUnixSockets        str[]  (macOS)
  sandbox.network.allowAllUnixSockets     bool
  sandbox.network.allowLocalBinding       bool   (macOS)
  sandbox.network.allowMachLookup         str[]  (macOS)
  sandbox.network.httpProxyPort           int    (custom proxy)
  sandbox.network.socksProxyPort          int    (custom proxy)

NOTE: keys whose exact spelling the settings reference truncated (deniedDomains,
allowManagedDomainsOnly, enableWeakerNetworkIsolation, enableWeakerNestedSandbox)
are referenced in prose in the sandboxing guide but were NOT confirmed in the
machine-readable settings table during verification, so they are intentionally
excluded from the writable allowlist below to avoid writing an unverified key.
They are mentioned read-only in the explainer text. See `integrationNotes`.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .config import SETTINGS_JSON
from .logger import log
from .utils import _safe_read, _safe_write


# ───────── verified schema ─────────
# Per-key metadata drives both validation and the UI explainer. `path` is the
# nested location under the top-level `sandbox` object.

_BOOL_KEYS: dict[str, dict[str, Any]] = {
    "enabled": {
        "path": ["enabled"],
        "default": False,
        "label": "샌드박스 활성화",
        "desc": "Bash 명령을 OS 수준 격리(macOS Seatbelt / Linux·WSL2 bubblewrap) 안에서 실행. user settings에 true면 모든 프로젝트에 적용.",
    },
    "autoAllowBashIfSandboxed": {
        "path": ["autoAllowBashIfSandboxed"],
        "default": True,
        "label": "샌드박스 내 Bash 자동 허용",
        "desc": "샌드박스로 실행 가능한 Bash 명령을 매번 묻지 않고 자동 승인. deny 규칙과 위험 경로 삭제는 여전히 프롬프트됨.",
    },
    "failIfUnavailable": {
        "path": ["failIfUnavailable"],
        "default": False,
        "label": "샌드박스 불가 시 시작 실패",
        "desc": "의존성 누락 등으로 샌드박스를 시작할 수 없으면 경고 후 비격리 실행하는 대신 Claude Code 시작 자체를 막음. 관리형 배포의 보안 게이트용.",
    },
    "allowUnsandboxedCommands": {
        "path": ["allowUnsandboxedCommands"],
        "default": True,
        "label": "비샌드박스 재시도 허용 (escape hatch)",
        "desc": "샌드박스 제약으로 실패한 명령을 dangerouslyDisableSandbox로 격리 밖에서 재시도(권한 프롬프트 경유). false면 Strict 모드 — 반드시 격리 또는 excludedCommands 안에서만 실행.",
    },
}

# filesystem.* booleans (managed-only key surfaced for completeness)
_FS_BOOL_KEYS: dict[str, dict[str, Any]] = {
    "allowManagedReadPathsOnly": {
        "path": ["filesystem", "allowManagedReadPathsOnly"],
        "default": False,
        "label": "관리형 allowRead만 허용 (managed)",
        "desc": "관리형 설정에서만 의미. true면 managed settings의 filesystem.allowRead만 적용되고 user/project/local의 allowRead는 무시됨.",
        "managed_only": True,
    },
}

# network.* booleans
_NET_BOOL_KEYS: dict[str, dict[str, Any]] = {
    "allowAllUnixSockets": {
        "path": ["network", "allowAllUnixSockets"],
        "default": False,
        "label": "모든 Unix 소켓 허용",
        "desc": "샌드박스 안에서 모든 Unix 도메인 소켓 연결 허용. /var/run/docker.sock 등 강력한 서비스 노출 위험 — 신중히.",
    },
    "allowLocalBinding": {
        "path": ["network", "allowLocalBinding"],
        "default": False,
        "label": "localhost 바인딩 허용 (macOS)",
        "desc": "macOS 전용. 샌드박스 명령이 localhost 포트에 바인딩하도록 허용.",
    },
}

# string-array keys
_ARRAY_KEYS: dict[str, dict[str, Any]] = {
    "excludedCommands": {
        "path": ["excludedCommands"],
        "label": "격리 제외 명령 (excludedCommands)",
        "desc": "이 명령들은 샌드박스 밖에서 실행. docker, gh, gcloud, terraform 등 호환되지 않는 도구용. 예: \"docker *\". 목록은 좁게 유지.",
    },
    "fs_allowWrite": {
        "path": ["filesystem", "allowWrite"],
        "label": "추가 쓰기 허용 경로 (filesystem.allowWrite)",
        "desc": "기본은 작업 디렉토리만 쓰기 가능. 여기 추가하면 그 경로도 쓰기 허용(하위 프로세스 포함). 예: ~/.kube, /tmp/build. 스코프 간 병합됨.",
    },
    "fs_denyWrite": {
        "path": ["filesystem", "denyWrite"],
        "label": "쓰기 금지 경로 (filesystem.denyWrite)",
        "desc": "지정 경로 쓰기 차단.",
    },
    "fs_denyRead": {
        "path": ["filesystem", "denyRead"],
        "label": "읽기 금지 경로 (filesystem.denyRead)",
        "desc": "기본 읽기 정책은 ~/.aws/credentials, ~/.ssh 까지 읽을 수 있음 — 자격증명 디렉토리를 여기 추가해 차단 권장. 예: ~/.aws, ~/.ssh.",
    },
    "fs_allowRead": {
        "path": ["filesystem", "allowRead"],
        "label": "읽기 재허용 경로 (filesystem.allowRead)",
        "desc": "denyRead 영역 안에서 특정 경로만 다시 읽기 허용. 예: denyRead [~/] + allowRead [.] (project settings에서 . 은 프로젝트 루트).",
    },
    "net_allowedDomains": {
        "path": ["network", "allowedDomains"],
        "label": "허용 도메인 (network.allowedDomains)",
        "desc": "기본은 사전 허용 도메인 없음 — 새 도메인 첫 접근 시 프롬프트. 여기 미리 넣으면 프롬프트 생략. 와일드카드 서브도메인(*.npmjs.org) 지원. github.com 같은 넓은 허용은 데이터 유출 경로가 될 수 있음.",
    },
    "net_allowUnixSockets": {
        "path": ["network", "allowUnixSockets"],
        "label": "허용 Unix 소켓 (macOS)",
        "desc": "macOS 전용. 샌드박스가 접근 가능한 Unix 소켓 경로 목록.",
    },
    "net_allowMachLookup": {
        "path": ["network", "allowMachLookup"],
        "label": "허용 Mach 서비스 (macOS)",
        "desc": "macOS 전용. 샌드박스가 조회 가능한 XPC/Mach 서비스 이름. * 접미사 지원.",
    },
}

# integer keys (custom proxy ports)
_INT_KEYS: dict[str, dict[str, Any]] = {
    "net_httpProxyPort": {
        "path": ["network", "httpProxyPort"],
        "label": "HTTP 프록시 포트 (network.httpProxyPort)",
        "desc": "고급: 사용자 정의 프록시로 아웃바운드 트래픽 라우팅(TLS 검사/필터링/로깅). 미설정이면 내장 프록시 사용.",
        "min": 1,
        "max": 65535,
    },
    "net_socksProxyPort": {
        "path": ["network", "socksProxyPort"],
        "label": "SOCKS 프록시 포트 (network.socksProxyPort)",
        "desc": "고급: 사용자 정의 SOCKS 프록시 포트.",
        "min": 1,
        "max": 65535,
    },
}


def _explanations() -> list[dict[str, Any]]:
    """Flat, ordered explainer list for the UI: every documented writable key."""
    out: list[dict[str, Any]] = []
    for key, m in {**_BOOL_KEYS, **_FS_BOOL_KEYS, **_NET_BOOL_KEYS}.items():
        out.append({
            "key": key,
            "kind": "bool",
            "path": "sandbox." + ".".join(m["path"]),
            "label": m["label"],
            "desc": m["desc"],
            "default": m.get("default", False),
            "managed_only": bool(m.get("managed_only")),
        })
    for key, m in _ARRAY_KEYS.items():
        out.append({
            "key": key,
            "kind": "array",
            "path": "sandbox." + ".".join(m["path"]),
            "label": m["label"],
            "desc": m["desc"],
        })
    for key, m in _INT_KEYS.items():
        out.append({
            "key": key,
            "kind": "int",
            "path": "sandbox." + ".".join(m["path"]),
            "label": m["label"],
            "desc": m["desc"],
        })
    return out


def _read_settings() -> tuple[dict | None, str | None]:
    """Return (parsed_dict, None) or (None, error_key) if missing/malformed.

    A non-existent file is treated as an empty settings object (valid — we can
    create the sandbox block). A file that exists but does not parse as a JSON
    object is a hard error: we never overwrite a file we can't safely merge.
    """
    raw = _safe_read(SETTINGS_JSON)
    if not raw.strip():
        if SETTINGS_JSON.exists():
            # exists but empty/whitespace — treat as empty object
            return {}, None
        return {}, None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None, "err_settings_malformed"
    if not isinstance(parsed, dict):
        return None, "err_settings_malformed"
    return parsed, None


def _current_sandbox(settings: dict) -> dict:
    sb = settings.get("sandbox")
    return sb if isinstance(sb, dict) else {}


def api_bash_sandbox_get(query: dict | None = None) -> dict:
    """Read settings.json and surface the current sandbox config + explanations.

    GET handler. `query` is unused. Returns the raw `sandbox` block (or {}),
    a per-key explanation list, whether sandboxing is enabled, the settings
    file path, and whether the file is currently parseable.
    """
    settings, err = _read_settings()
    if err:
        return {
            "ok": True,
            "available": True,
            "malformed": True,
            "error_key": err,
            "error": "settings.json이 올바른 JSON이 아닙니다. 저장이 비활성화됩니다.",
            "settings_path": str(SETTINGS_JSON),
            "sandbox": {},
            "enabled": False,
            "explanations": _explanations(),
            "docs_url": "https://code.claude.com/docs/en/sandboxing",
        }
    sb = _current_sandbox(settings)
    return {
        "ok": True,
        "available": True,
        "malformed": False,
        "settings_path": str(SETTINGS_JSON),
        "settings_exists": SETTINGS_JSON.exists(),
        "sandbox": sb,
        "enabled": bool(sb.get("enabled", False)),
        "explanations": _explanations(),
        "docs_url": "https://code.claude.com/docs/en/sandboxing",
    }


# ───────── validation ─────────

def _validate_str_array(val: Any) -> list[str] | None:
    """Coerce a JSON value into a clean list[str], or None if invalid."""
    if not isinstance(val, list):
        return None
    out: list[str] = []
    for item in val:
        if not isinstance(item, str):
            return None
        s = item.strip()
        if s:
            out.append(s)
    return out


def _set_nested(root: dict, path: list[str], value: Any) -> None:
    cur = root
    for seg in path[:-1]:
        nxt = cur.get(seg)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[seg] = nxt
        cur = nxt
    cur[path[-1]] = value


def _del_nested(root: dict, path: list[str]) -> None:
    cur = root
    for seg in path[:-1]:
        nxt = cur.get(seg)
        if not isinstance(nxt, dict):
            return
        cur = nxt
    cur.pop(path[-1], None)


def _prune_empty(d: dict, keys: list[str]) -> None:
    """Drop sub-objects (filesystem/network) and sandbox itself if left empty."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, dict) and not v:
            d.pop(k, None)


def api_bash_sandbox_set(body: dict | None) -> dict:
    """Write ONLY verified sandbox keys into settings.json (atomic, backed up).

    POST handler. `body` may contain any subset of the documented keys (using
    the flat names from `_explanations`, e.g. "enabled", "fs_allowWrite",
    "net_allowedDomains", "net_httpProxyPort"). Values are validated against the
    documented type / range. Unknown keys are rejected. Unrelated top-level
    settings are never touched. A null/None value for a key removes it.
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body", "error_key": "err_bad_body"}

    settings, err = _read_settings()
    if err:
        return {
            "ok": False,
            "error": "settings.json이 올바른 JSON이 아닙니다. 손상 방지를 위해 저장을 거부합니다.",
            "error_key": err,
        }

    # Build the validated patch BEFORE mutating anything.
    bool_meta = {**_BOOL_KEYS, **_FS_BOOL_KEYS, **_NET_BOOL_KEYS}
    sets: list[tuple[list[str], Any]] = []
    dels: list[list[str]] = []

    for key, raw in body.items():
        if key in bool_meta:
            path = bool_meta[key]["path"]
            if raw is None:
                dels.append(path)
                continue
            if not isinstance(raw, bool):
                return {"ok": False, "error": f"{key}는 true/false여야 합니다",
                        "error_key": "err_value_invalid", "field": key}
            sets.append((path, raw))
        elif key in _ARRAY_KEYS:
            path = _ARRAY_KEYS[key]["path"]
            if raw is None:
                dels.append(path)
                continue
            arr = _validate_str_array(raw)
            if arr is None:
                return {"ok": False, "error": f"{key}는 문자열 배열이어야 합니다",
                        "error_key": "err_value_invalid", "field": key}
            if arr:
                sets.append((path, arr))
            else:
                dels.append(path)
        elif key in _INT_KEYS:
            meta = _INT_KEYS[key]
            path = meta["path"]
            if raw is None or raw == "":
                dels.append(path)
                continue
            if isinstance(raw, bool) or not isinstance(raw, int):
                return {"ok": False, "error": f"{key}는 정수여야 합니다",
                        "error_key": "err_value_invalid", "field": key}
            if not (meta["min"] <= raw <= meta["max"]):
                return {"ok": False,
                        "error": f"{key}는 {meta['min']}~{meta['max']} 범위여야 합니다",
                        "error_key": "err_value_range", "field": key}
            sets.append((path, raw))
        else:
            return {"ok": False, "error": f"알 수 없는 키: {key}",
                    "error_key": "err_unknown_key", "field": key}

    if not sets and not dels:
        return {"ok": False, "error": "변경할 항목이 없습니다", "error_key": "err_no_changes"}

    # ── timestamped backup BEFORE writing (only if a real file exists) ──
    backup_path = None
    if SETTINGS_JSON.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_path = SETTINGS_JSON.with_name(f"{SETTINGS_JSON.name}.bak.{ts}")
        current_raw = _safe_read(SETTINGS_JSON)
        if not _safe_write(backup_path, current_raw):
            return {"ok": False, "error": "백업 생성 실패 — 저장을 중단합니다",
                    "error_key": "err_backup_failed"}

    # ── read-merge: mutate only the sandbox subtree of the parsed dict ──
    sb = settings.get("sandbox")
    if not isinstance(sb, dict):
        sb = {}
    settings["sandbox"] = sb

    for path, value in sets:
        _set_nested(sb, path, value)
    for path in dels:
        _del_nested(sb, path)

    # tidy: remove now-empty nested objects, then sandbox if fully empty
    _prune_empty(sb, ["filesystem", "network"])
    if not sb:
        settings.pop("sandbox", None)

    out = json.dumps(settings, ensure_ascii=False, indent=2) + "\n"
    if not _safe_write(SETTINGS_JSON, out):
        return {"ok": False, "error": "settings.json 쓰기 실패",
                "error_key": "err_write_failed", "backup": str(backup_path) if backup_path else None}

    log.info("bash_sandbox: updated %d key(s), removed %d, backup=%s",
             len(sets), len(dels), backup_path)
    return {
        "ok": True,
        "sandbox": settings.get("sandbox", {}),
        "enabled": bool(settings.get("sandbox", {}).get("enabled", False)),
        "backup": str(backup_path) if backup_path else None,
        "settings_path": str(SETTINGS_JSON),
    }
