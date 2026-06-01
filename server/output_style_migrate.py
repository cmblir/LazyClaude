"""Output-style deprecation migrator / advisor — READ-ONLY audit.

Feature #21. Verified facts (official docs, https://code.claude.com/docs/en/output-styles
fetched 2026-06-01):

  - The output-styles FEATURE is NOT deprecated. Custom output style
    Markdown files at ``~/.claude/output-styles/*.md`` are still fully
    supported and applied via the system prompt.
  - Only the standalone ``/output-style`` SLASH COMMAND was deprecated in
    v2.1.73 and REMOVED in v2.1.91. Verbatim from the docs:
      "The standalone /output-style command was deprecated in v2.1.73 and
       removed in v2.1.91. Use /config or edit the outputStyle setting
       directly."
  - Switch styles via ``/config`` → Output style, or by editing the
    ``outputStyle`` field in a settings file. Output style is part of the
    system prompt (read once at session start; takes effect after /clear
    or a new session).
  - Storage levels: user ``~/.claude/output-styles``, project
    ``.claude/output-styles``, managed-policy ``.claude/output-styles``.
    The file name is the style name unless ``name`` frontmatter is set.
  - Frontmatter fields: name, description, keep-coding-instructions,
    force-for-plugin.
  - Built-in styles: Default, Proactive, Explanatory, Learning.
  - For project conventions/codebase, the docs recommend CLAUDE.md
    instead; Skills for reusable workflows; Agents for scoped helpers.

So this module is an ADVISORY/HEALTH audit, not a "your styles are dead"
migrator. It surfaces:
  - styles that are fine (ok),
  - the removed ``/output-style`` command path (advisory: switch method),
  - orphaned ``outputStyle`` settings that point at a style with no
    matching file and no built-in name (orphaned),
and for each emits a suggested CLAUDE.md / skill migration snippet that
captures the style's INTENT, for users who want to move tone/role
guidance into more durable mechanisms.

This module is strictly read-only — it never writes. Memory CRUD and the
existing output-style editor live elsewhere; this only reads.
"""
from __future__ import annotations

import re

from .claude_md import get_settings
from .config import CLAUDE_HOME
from .utils import _parse_frontmatter, _safe_read, _strip_frontmatter

# ───────── constants ─────────

OUTPUT_STYLES_DIR = CLAUDE_HOME / "output-styles"
SETTINGS_PATH = CLAUDE_HOME / "settings.json"

# Built-in output styles shipped by Claude Code (docs, verified 2026-06-01).
# Keyed lowercase for case-insensitive matching against the settings value.
_BUILTIN_STYLES: dict[str, str] = {
    "default": "Built-in software-engineering system prompt.",
    "proactive": "Built-in: executes immediately, prefers action over planning.",
    "explanatory": "Built-in: adds educational 'Insights' while coding.",
    "learning": "Built-in: learn-by-doing, inserts TODO(human) markers.",
}

# Recognised frontmatter keys (docs, verified 2026-06-01). Anything else is
# flagged as an unknown key in the advisory so users can clean it up.
_KNOWN_FRONTMATTER = {"name", "description", "keep-coding-instructions", "force-for-plugin"}

# The one genuine deprecation in this feature area.
_COMMAND_DEPRECATION = {
    "command": "/output-style",
    "deprecatedIn": "v2.1.73",
    "removedIn": "v2.1.91",
    "quote": (
        "The standalone /output-style command was deprecated in v2.1.73 and "
        "removed in v2.1.91. Use /config or edit the outputStyle setting directly."
    ),
    "replacement": (
        "Run /config → Output style, or set the 'outputStyle' field in a "
        "settings file. Output style is read once at session start, so a "
        "change takes effect after /clear or in a new session."
    ),
    "docUrl": "https://code.claude.com/docs/en/output-styles",
}

_DOC_URL = "https://code.claude.com/docs/en/output-styles"


def _normalize_style_key(value: str) -> str:
    """Match a settings/outputStyle value against built-in / file ids loosely.

    Built-ins are referred to by capitalised name ("Explanatory"); custom
    styles by file stem or frontmatter ``name``. We lowercase + collapse
    separators so "Diagrams first", "diagrams-first", "diagrams_first" all
    compare equal.
    """
    return re.sub(r"[\s_-]+", "-", (value or "").strip().lower())


def _suggest_claude_md_snippet(name: str, intent: str) -> str:
    """A CLAUDE.md block that captures the style's tone/role intent.

    CLAUDE.md adds a user message after the system prompt, so it always
    applies and is the docs-recommended home for durable project/communication
    conventions (vs. output styles which replace the system prompt).
    """
    intent_line = intent.strip() or "Describe the tone, role and output format here."
    # Keep snippet's body as the user's own intent text; only the scaffold is English.
    return (
        "## Response style (migrated from output style "
        f"'{name}')\n\n"
        f"{intent_line}\n\n"
        "<!-- Source: ~/.claude/output-styles/"
        f"{name}.md. CLAUDE.md applies on every turn and survives /clear, "
        "unlike a switchable output style. Trim to the tone/role guidance "
        "only; keep codebase facts in their own sections. -->\n"
    )


def _suggest_skill_snippet(name: str, intent: str) -> str:
    """A SKILL.md scaffold for intent that is task-scoped rather than global.

    Skills load task-specific instructions only when relevant, so they suit a
    style whose guidance only matters for a specific workflow (e.g. "always
    answer with a diagram when explaining architecture").
    """
    desc = (intent.strip().splitlines() or ["Reusable response-style workflow."])[0][:120]
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {desc}\n"
        "---\n\n"
        f"# {name}\n\n"
        f"{intent.strip() or 'Describe when to apply this style and what it should produce.'}\n\n"
        "<!-- Place at ~/.claude/skills/<name>/SKILL.md. A skill loads only "
        "when invoked/relevant, unlike an output style that applies every "
        "turn. Use this when the tone/format only matters for a specific "
        "task. -->\n"
    )


def _intent_from_style(meta: dict, body: str) -> str:
    """Best-effort 'what is this style trying to do' text for migration snippets."""
    desc = (meta.get("description") or "").strip()
    body_excerpt = (body or "").strip()
    if desc and body_excerpt:
        return f"{desc}\n\n{body_excerpt}"
    return desc or body_excerpt


def _audit_one_style(path, meta: dict, raw: str, referenced_key: str) -> dict:
    """Build an advisory for a single output-style file. status: ok|orphaned.

    A file-backed style is never 'deprecated' (the feature isn't); it's 'ok'.
    'orphaned' is reserved for the settings pointer, handled separately.
    """
    name = meta.get("name") or path.stem
    body = _strip_frontmatter(raw)[:4000]
    intent = _intent_from_style(meta, body)
    style_key = _normalize_style_key(meta.get("name") or path.stem)

    unknown_keys = sorted(k for k in meta.keys() if k not in _KNOWN_FRONTMATTER)
    warnings: list[str] = []
    if unknown_keys:
        warnings.append(
            "Unrecognised frontmatter keys: " + ", ".join(unknown_keys)
            + ". Known keys: name, description, keep-coding-instructions, force-for-plugin."
        )
    if not meta.get("description"):
        warnings.append("No 'description' — it won't show a hint in the /config picker.")
    keep_coding = str(meta.get("keep-coding-instructions", "")).strip().lower() in ("true", "yes", "1")

    is_active = bool(referenced_key) and referenced_key == style_key

    return {
        "id": path.stem,
        "name": name,
        "file": path.name,
        "path": str(path),
        "status": "ok",
        "active": is_active,
        "keepCodingInstructions": keep_coding,
        "description": meta.get("description", ""),
        "frontmatter": {k: meta.get(k) for k in sorted(meta.keys())},
        "unknownFrontmatterKeys": unknown_keys,
        "warnings": warnings,
        "advisory": (
            "The output-styles feature is current — this style is healthy. "
            + ("It is the active outputStyle in settings.json. " if is_active else "")
            + "The only removed piece is the /output-style command (use /config "
            "or the outputStyle setting). If this is communication/role guidance "
            "you want applied on every turn, consider mirroring it into CLAUDE.md; "
            "if it only matters for one workflow, a skill fits better."
        ),
        "recommendedReplacement": (
            "Keep as an output style and switch via /config or the outputStyle "
            "setting. Optionally mirror the intent into CLAUDE.md (always-on) or "
            "a skill (task-scoped)."
        ),
        "migration": {
            "claudeMd": _suggest_claude_md_snippet(path.stem, intent),
            "skill": _suggest_skill_snippet(path.stem, intent),
        },
        "intentExcerpt": (intent[:400] + ("…" if len(intent) > 400 else "")),
        "raw": raw[:8000],
    }


def api_output_style_audit(query: dict) -> dict:
    """GET /api/output-style/audit — READ-ONLY output-style health + migration advisory.

    Returns a per-style advisory plus a settings-pointer advisory and the
    verified deprecation note for the removed ``/output-style`` command.

    Shape::

        {
          "ok": True,
          "featureDeprecated": False,
          "commandDeprecation": { command, deprecatedIn, removedIn, quote, ... },
          "dirExists": bool, "dir": "...",
          "settings": { "outputStyle": <value or None>, "path": "...", "exists": bool },
          "settingPointer": { status: ok|deprecated|orphaned, ... },
          "styles": [ <advisory>, ... ],
          "summary": { total, active, orphanedSetting, withWarnings },
          "docUrl": "...",
          "note": "..."
        }

    ``query`` is accepted for the standard GET handler signature but unused —
    this endpoint takes no parameters.
    """
    _ = query  # endpoint takes no params; kept for handler signature compat.

    # ── settings.json outputStyle pointer (read-only) ──
    settings = get_settings()
    raw_setting = settings.get("outputStyle") if isinstance(settings, dict) else None
    setting_value = raw_setting if isinstance(raw_setting, str) else ""
    referenced_key = _normalize_style_key(setting_value)

    # ── enumerate user-level output-style files ──
    styles: list[dict] = []
    dir_exists = OUTPUT_STYLES_DIR.exists()
    file_keys: set[str] = set()
    if dir_exists:
        for p in sorted(OUTPUT_STYLES_DIR.glob("*.md")):
            raw = _safe_read(p)
            meta = _parse_frontmatter(raw)
            advisory = _audit_one_style(p, meta, raw, referenced_key)
            styles.append(advisory)
            file_keys.add(_normalize_style_key(meta.get("name") or p.stem))
            file_keys.add(_normalize_style_key(p.stem))

    # ── classify the settings pointer ──
    setting_pointer: dict
    if not setting_value:
        setting_pointer = {
            "status": "ok",
            "value": None,
            "advisory": (
                "No 'outputStyle' set in settings.json — Claude Code uses the "
                "built-in Default style. Nothing to migrate."
            ),
            "recommendedReplacement": "",
        }
    elif referenced_key in _BUILTIN_STYLES:
        setting_pointer = {
            "status": "ok",
            "value": setting_value,
            "advisory": (
                f"outputStyle '{setting_value}' is a built-in style "
                f"({_BUILTIN_STYLES[referenced_key]}). Still supported; switch via "
                "/config rather than the removed /output-style command."
            ),
            "recommendedReplacement": (
                "No action needed. To change it, use /config → Output style or edit "
                "the outputStyle field directly."
            ),
        }
    elif referenced_key in file_keys:
        setting_pointer = {
            "status": "ok",
            "value": setting_value,
            "advisory": (
                f"outputStyle '{setting_value}' resolves to a custom style file "
                "under ~/.claude/output-styles. Healthy."
            ),
            "recommendedReplacement": (
                "No action needed. Change it via /config or the outputStyle setting; "
                "the /output-style command is gone (removed in v2.1.91)."
            ),
        }
    else:
        setting_pointer = {
            "status": "orphaned",
            "value": setting_value,
            "advisory": (
                f"outputStyle '{setting_value}' points to a style that is neither a "
                "built-in (Default/Proactive/Explanatory/Learning) nor a file under "
                "~/.claude/output-styles. Claude Code will fall back to Default. It may "
                "be a project-level or plugin-provided style, or a stale/typo'd value."
            ),
            "recommendedReplacement": (
                "Verify the name (check .claude/output-styles in your project and any "
                "plugin output-styles), fix the typo, or remove the outputStyle field "
                "to use Default."
            ),
        }

    summary = {
        "total": len(styles),
        "active": sum(1 for s in styles if s.get("active")),
        "withWarnings": sum(1 for s in styles if s.get("warnings")),
        "orphanedSetting": 1 if setting_pointer["status"] == "orphaned" else 0,
    }

    return {
        "ok": True,
        # The feature is NOT deprecated — only the slash command was removed.
        "featureDeprecated": False,
        "commandDeprecation": dict(_COMMAND_DEPRECATION),
        "dirExists": dir_exists,
        "dir": str(OUTPUT_STYLES_DIR),
        "settings": {
            "outputStyle": setting_value or None,
            "path": str(SETTINGS_PATH),
            "exists": SETTINGS_PATH.exists(),
        },
        "settingPointer": setting_pointer,
        "builtins": [{"name": k.capitalize(), "description": v} for k, v in _BUILTIN_STYLES.items()],
        "styles": styles,
        "summary": summary,
        "docUrl": _DOC_URL,
        "note": (
            "READ-ONLY audit. The output-styles feature is current; only the "
            "standalone /output-style command was deprecated (v2.1.73) and removed "
            "(v2.1.91). Suggested CLAUDE.md/skill snippets are optional migrations "
            "of a style's intent into always-on or task-scoped mechanisms."
        ),
    }
