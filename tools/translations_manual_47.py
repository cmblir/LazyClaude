"""Auto-Resume binding form: resume-delay selector (resumeDelaySec).

The Auto-Resume binding form gained a "재개 지연" selector — auto (parse the
reset moment from the cap message) vs. a manual delay (2h / 3h / custom hours
after the limit hit). Lives in dist/app.js, which the index.html-only
extractor does not scan, so the translations are registered here by hand.

Loaded by ``tools/translations_manual.py``.
"""
from __future__ import annotations

NEW_EN: dict[str, str] = {
    "재개 지연": "Resume delay",
    "자동 — 한도 리셋 시각에 재개": "Auto — resume at the limit reset time",
    "2시간 뒤": "After 2 hours",
    "3시간 뒤": "After 3 hours",
    "시간 후 재개": "hours, then resume",
    "한도 적중 후 언제 재개할지 — 자동은 한도 메시지의 리셋 시각을 파싱해 그 시점에 재개":
        "When to resume after hitting the limit — Auto parses the reset time "
        "from the cap message and resumes exactly then",
}

NEW_ZH: dict[str, str] = {
    "재개 지연": "恢复延迟",
    "자동 — 한도 리셋 시각에 재개": "自动 — 在限额重置时间恢复",
    "2시간 뒤": "2小时后",
    "3시간 뒤": "3小时后",
    "시간 후 재개": "小时后恢复",
    "한도 적중 후 언제 재개할지 — 자동은 한도 메시지의 리셋 시각을 파싱해 그 시점에 재개":
        "限额触发后何时恢复 — 自动模式解析限额消息中的重置时间并在该时刻恢复",
}
