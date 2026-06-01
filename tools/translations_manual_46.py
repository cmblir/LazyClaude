"""Auto-Resume add-binding dialog: spawnFallback toggle (in-pane resume work).

The Auto-Resume manager's "new binding" dialog gained a spawnFallback checkbox.
Lives in dist/app.js, which the index.html-only extractor does not scan, so its
translation is registered here by hand.

Loaded by ``tools/translations_manual.py``.
"""
from __future__ import annotations

NEW_EN: dict[str, str] = {
    "정밀 재개 불가 시 백그라운드 claude --resume 허용 (해제 시 일시정지)":
        "Allow background `claude --resume` when precise resume isn't possible (pause if unchecked)",
}

NEW_ZH: dict[str, str] = {
    "정밀 재개 불가 시 백그라운드 claude --resume 허용 (해제 시 일시정지)":
        "无法精确恢复时允许后台 claude --resume（取消勾选则暂停）",
}
