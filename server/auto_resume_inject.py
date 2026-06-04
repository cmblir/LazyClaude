"""Live TTY injection for Auto-Resume (macOS).

The default Auto-Resume mechanism (auto_resume.py) spawns
`claude --resume <id> -p <prompt>` as a separate subprocess. That
subprocess writes new turns to the SAME session JSONL — the data
gets injected at the file level — but the user's *live* terminal
window keeps showing whatever it was showing (e.g. a frozen
"1) Continue 2) Quit" rate-limit selection prompt).

This module fills that gap on macOS:

  Strategy A — TTY-targeted AppleScript (iTerm2, Terminal.app):
    1. Find the PID for the live Claude session
    2. Read the TTY that PID is bound to (`ps -o tty=`)
    3. Walk iTerm2 / Terminal.app windows via AppleScript to
       find the matching session
    4. `write text "..." newline 1` per keystroke

  Strategy B — System Events keystroke (Warp, kitty, alacritty,
  wezterm, anything-else):
    1. Walk the process tree from PID upward to find the bundle
       identifier of the macOS app hosting this terminal.
    2. `tell application "<X>" to activate` to bring it forward.
    3. For ASCII keystrokes (e.g. "1"): `keystroke "1"` via
       System Events, then key code 36 (Return).
    4. For the user prompt (may be Korean / Unicode): set the
       clipboard, paste with Cmd+V, then Return — this handles
       arbitrary Unicode reliably without depending on the
       active keyboard layout.
    5. Restore the original clipboard at the end.

  Strategy A is preferred when available — it's TTY-targeted
  (no race with another window) and doesn't disturb the active
  app focus. Strategy B is the fallback for terminals that don't
  publish a tty-aware AppleScript dictionary.

Why keystrokes instead of writing to /dev/ttysNNN directly:
    Writing to the slave end of a pty from a non-controlling
    process gets the bytes echoed back as input only on Linux with
    TIOCSTI ioctl, which Apple removed in macOS 10.13 for security.
    AppleScript's `write text` and System Events `keystroke` APIs
    are the supported equivalents.

Permissions:
    Strategy B requires Accessibility permission for whichever
    process invokes osascript (the dashboard's Python in our
    case). The first call surfaces a system permission prompt;
    once granted, it sticks. We surface the underlying error
    verbatim so the user can grant it manually if needed.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from typing import Optional

from .logger import log


# Known macOS terminal apps. The keys are the substrings we look for
# in the process command (case-insensitive); the values are the
# canonical app names AppleScript expects for `tell application`.
_TERMINAL_APPS_BY_CMD: list[tuple[str, str]] = [
    ("warp.app/contents/macos/stable", "Warp"),
    ("warp.app/", "Warp"),
    ("iterm.app/", "iTerm2"),
    ("iterm2.app/", "iTerm2"),
    ("terminal.app/", "Terminal"),
    ("kitty.app/", "kitty"),
    ("wezterm/", "WezTerm"),
    ("alacritty.app/", "Alacritty"),
    ("ghostty.app/", "Ghostty"),
    ("hyper.app/", "Hyper"),
    ("tabby.app/", "Tabby"),
    # VS Code's integrated terminal — System Events keystrokes still
    # work because it routes them to the focused panel.
    ("visual studio code", "Code"),
    ("vscode", "Code"),
    ("cursor.app/", "Cursor"),
]


# ───────── PID → TTY ─────────

def _tty_for_pid(pid: int) -> Optional[str]:
    """Return the TTY device the process is bound to, e.g. 'ttys001'.
    None if the process is gone OR has no controlling terminal.
    """
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "tty="],
            text=True, timeout=5,
        )
        tty = out.strip()
        # ps may return '?' or empty for daemonised / no-tty processes.
        if not tty or tty == "?" or tty == "??":
            return None
        return tty
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _full_tty_path(short: str) -> str:
    """Normalize 'ttys001' → '/dev/ttys001'."""
    if short.startswith("/dev/"):
        return short
    return f"/dev/{short}"


# ───────── PID → terminal app ─────────

def _ppid_of(pid: int) -> Optional[int]:
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "ppid="],
            text=True, timeout=5,
        )
        s = out.strip()
        if not s:
            return None
        return int(s)
    except Exception:
        return None


def _command_of(pid: int) -> str:
    try:
        return subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "command="],
            text=True, timeout=5,
        ).strip()
    except Exception:
        return ""


def _pid_ancestry(pid: int, max_depth: int = 30) -> set[int]:
    """Return {pid, parent, grandparent, ...} up to the root."""
    out: set[int] = set()
    cur: Optional[int] = pid
    for _ in range(max_depth):
        if cur is None or cur <= 1 or cur in out:
            break
        out.add(cur)
        cur = _ppid_of(cur)
    return out


def _tmux_sockets() -> list[Optional[str]]:
    """All candidate tmux socket paths for this user, plus the default."""
    socks: list[Optional[str]] = []
    try:
        socks.extend(sorted(glob.glob(f"/tmp/tmux-{os.getuid()}/*")))
    except Exception:
        pass
    socks.append(None)  # default socket (tmux figures it out)
    # de-dup while preserving order
    seen: set = set()
    uniq: list[Optional[str]] = []
    for s in socks:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def _tmux_target(pid: int) -> Optional[tuple[str, str]]:
    """If ``pid`` (or an ancestor) runs inside a tmux pane, return
    (socket, pane_id), else None.

    ``tmux -S <socket> send-keys -t <pane_id>`` then delivers keystrokes to
    that EXACT pane — focus-independent and terminal-agnostic (the gold-
    standard way to drive a live TUI, and it works inside Warp).

    We ask tmux itself rather than reading the pid's environment: macOS does
    not reliably expose another process's env via ``ps eww``. ``#{pane_pid}``
    is the pane's root (login shell); the claude process is a descendant, so
    we match any pane_pid that appears in the pid's ancestry.
    """
    if shutil.which("tmux") is None:
        return None
    ancestry = _pid_ancestry(pid)
    if not ancestry:
        return None
    for sock in _tmux_sockets():
        base = ["tmux", "-S", sock] if sock else ["tmux"]
        try:
            out = subprocess.check_output(
                base + ["list-panes", "-a", "-F", "#{pane_pid} #{pane_id}"],
                text=True, errors="replace", timeout=5, stderr=subprocess.DEVNULL,
            )
        except Exception:
            continue
        for line in out.splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            try:
                pane_pid = int(parts[0])
            except ValueError:
                continue
            if pane_pid in ancestry:
                return (sock or "", parts[1])
    return None


def _tmux_base(socket: str) -> list[str]:
    tmux = shutil.which("tmux") or "tmux"
    return [tmux, "-S", socket] if socket else [tmux]


def tmux_pane_command(socket: str, pane: str) -> Optional[str]:
    """Current foreground command of a tmux pane (e.g. 'claude', 'zsh')."""
    try:
        out = subprocess.check_output(
            _tmux_base(socket) + ["display-message", "-p", "-t", pane, "#{pane_current_command}"],
            text=True, errors="replace", timeout=5, stderr=subprocess.DEVNULL,
        )
        return out.strip() or None
    except Exception:
        return None


def tmux_capture(socket: str, pane: str) -> str:
    """Visible text of a tmux pane (for readiness / prompt detection)."""
    try:
        return subprocess.check_output(
            _tmux_base(socket) + ["capture-pane", "-p", "-t", pane],
            text=True, errors="replace", timeout=5, stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ""


def tmux_send_line(socket: str, pane: str, line: str) -> tuple[bool, str]:
    """Send one literal line followed by Enter into a tmux pane."""
    return _tmux_inject(socket, pane, [line])


def _tmux_inject(socket: str, pane: str, keystrokes: list[str]) -> tuple[bool, str]:
    """Send each keystroke into a tmux pane: literal text, then Enter."""
    tmux = shutil.which("tmux")
    if tmux is None:
        return False, "tmux not on PATH"
    base = [tmux, "-S", socket] if socket else [tmux]
    for k in keystrokes:
        try:
            r1 = subprocess.run(
                base + ["send-keys", "-t", pane, "-l", "--", k],
                capture_output=True, text=True, timeout=5,
            )
            if r1.returncode != 0:
                return False, (r1.stderr or r1.stdout or "send-keys -l failed").strip()
            r2 = subprocess.run(
                base + ["send-keys", "-t", pane, "Enter"],
                capture_output=True, text=True, timeout=5,
            )
            if r2.returncode != 0:
                return False, (r2.stderr or r2.stdout or "send-keys Enter failed").strip()
        except subprocess.SubprocessError as e:
            return False, f"tmux send-keys failed: {e}"
    return True, f"tmux:{pane}"


def _warp_session_uuid(pid: int, max_depth: int = 20) -> Optional[str]:
    """Return the Warp session UUID that owns ``pid``, or None.

    Warp exports ``WARP_TERMINAL_SESSION_UUID`` / ``WARP_FOCUS_URL`` into every
    pane's shell environment. ``open warp://session/<uuid>`` then focuses that
    EXACT pane — the missing piece that lets us keystroke into the right tab
    instead of whatever Warp tab happens to be focused. We read the env of the
    pid (or a parent shell) via ``ps eww`` (same-user only on macOS).
    """
    cur: Optional[int] = pid
    seen: set[int] = set()
    for _ in range(max_depth):
        if cur is None or cur <= 1 or cur in seen:
            break
        seen.add(cur)
        try:
            env = subprocess.check_output(
                ["ps", "eww", "-p", str(cur)], text=True, errors="replace", timeout=5
            )
        except Exception:
            env = ""
        m = re.search(r"WARP_TERMINAL_SESSION_UUID=([0-9a-fA-F-]+)", env)
        if m:
            return m.group(1)
        m = re.search(r"WARP_FOCUS_URL=warp://session/([0-9a-fA-F-]+)", env)
        if m:
            return m.group(1)
        cur = _ppid_of(cur)
    return None


def _warp_focus_session(uuid: str) -> tuple[bool, str]:
    """Focus a specific Warp pane via its session URL. Brings Warp forward and
    selects the matching tab/pane so a subsequent keystroke lands there."""
    try:
        p = subprocess.run(
            ["open", f"warp://session/{uuid}"],
            capture_output=True, text=True, timeout=5,
        )
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "open failed").strip()
        return True, "warp-focused"
    except Exception as e:
        return False, f"open warp:// failed: {e}"


def _detect_terminal_app(pid: int, max_depth: int = 20) -> Optional[str]:
    """Walk up the process tree from `pid` and return the first
    macOS terminal app name we recognize, or None.

    Stops at depth `max_depth`, root (pid 1), or when the parent
    chain breaks. Matches by substring against `ps -o command=` —
    case-insensitive.
    """
    cur: Optional[int] = pid
    seen: set[int] = set()
    for _ in range(max_depth):
        if cur is None or cur <= 1 or cur in seen:
            return None
        seen.add(cur)
        cmd_lower = _command_of(cur).lower()
        for needle, app_name in _TERMINAL_APPS_BY_CMD:
            if needle in cmd_lower:
                return app_name
        cur = _ppid_of(cur)
    return None


# ───────── AppleScript runners ─────────

def _run_osascript(script: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Execute an AppleScript snippet via osascript.
    Returns (ok, stdout_or_error). osascript is part of macOS — if
    it's missing, we're not on macOS at all.
    """
    if shutil.which("osascript") is None:
        return False, "osascript not on PATH (not macOS?)"
    try:
        p = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "osascript failed").strip()
        return True, (p.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return False, f"osascript timed out after {timeout}s"
    except Exception as e:
        return False, f"osascript crashed: {e}"


def _escape_applescript_string(s: str) -> str:
    """Escape a string for embedding in an AppleScript double-quoted literal.
    AppleScript escapes are: \\ → \\\\, " → \\\".
    Newlines are preserved as literal — `write text` consumes them as the
    user typing newline (which we want for the trailing Return).
    """
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# ───────── iTerm2 ─────────

def _iterm2_inject(target_tty: str, keystrokes: list[str]) -> tuple[bool, str]:
    """Find the iTerm session whose `tty` matches `target_tty` and
    send each item in `keystrokes` as a separate `write text` line.

    Each keystroke is sent with `newline 1` so the receiving program
    sees the line as committed (Return pressed).

    The macOS app is registered as "iTerm" in its scripting
    dictionary (despite being marketed as iTerm2). The class is
    "iTerm2" but `tell application` uses "iTerm".
    """
    target_full = _full_tty_path(target_tty)
    parts = []
    for k in keystrokes:
        esc = _escape_applescript_string(k)
        parts.append(f'write text "{esc}" newline 1')
        parts.append("delay 0.15")
    body = "\n".join(parts)
    script = f'''
on injectIntoMatchingSession(targetTTY)
    tell application "iTerm"
        repeat with w in windows
            repeat with t in tabs of w
                repeat with s in sessions of t
                    if (tty of s) is targetTTY then
                        tell s
                            {body}
                        end tell
                        return "iterm:matched"
                    end if
                end repeat
            end repeat
        end repeat
    end tell
    return "iterm:no-match"
end injectIntoMatchingSession

return injectIntoMatchingSession("{target_full}")
'''
    ok, out = _run_osascript(script, timeout=8.0)
    if not ok:
        return False, f"iterm osascript failed: {out}"
    if "no-match" in out:
        return False, f"iterm: no session with tty {target_full}"
    return True, "iterm"


# ───────── Terminal.app ─────────

def _terminal_app_inject(target_tty: str, keystrokes: list[str]) -> tuple[bool, str]:
    """Same idea for Apple's bundled Terminal.app. Terminal exposes
    `tty` on tabs (not sessions). `do script "..." in <tab>` runs the
    string AS IF the user typed it, including the newline at the end.
    """
    target_full = _full_tty_path(target_tty)
    # do script appends an implicit Return when the string has no
    # trailing newline. To send Return between two strings we just
    # include the newline ourselves; AppleScript's \\n inside a
    # double-quoted string becomes a real LF when osascript runs.
    parts = []
    for k in keystrokes:
        esc = _escape_applescript_string(k)
        parts.append(f'do script "{esc}" in matchedTab')
        parts.append("delay 0.15")
    body = "\n".join(parts)
    script = f'''
on injectIntoMatchingTab(targetTTY)
    tell application "Terminal"
        repeat with w in windows
            try
                repeat with tabRef in tabs of w
                    try
                        if (tty of tabRef) is targetTTY then
                            set matchedTab to tabRef
                            {body}
                            return "terminal-app:matched"
                        end if
                    on error
                        -- ignore tab walk errors
                    end try
                end repeat
            on error
                -- ignore window walk errors
            end try
        end repeat
    end tell
    return "terminal-app:no-match"
end injectIntoMatchingTab

return injectIntoMatchingTab("{target_full}")
'''
    ok, out = _run_osascript(script, timeout=10.0)
    if not ok:
        return False, f"terminal.app osascript failed: {out}"
    if "no-match" in out:
        return False, f"terminal.app: no tab with tty {target_full}"
    return True, "terminal-app"


# ───────── System Events keystroke fallback ─────────

def _system_events_inject(app_name: str, keystrokes: list[str]) -> tuple[bool, str]:
    """Strategy B — activate the target app and send keystrokes via
    System Events. Used for terminals that don't expose a tty-aware
    AppleScript dictionary (Warp, kitty, alacritty, wezterm, IDE
    integrated terminals).

    Sequence per keystroke:
      1. `keystroke "<text>"` — System Events types the string directly.
      2. Press Return (key code 36).
      3. Wait 150ms before the next keystroke.

    Direct `keystroke` (NOT clipboard + Cmd+V): a programmatic Cmd+V
    is silently swallowed by Warp's terminal input — the paste never
    lands and osascript still returns success, so the dashboard
    reported "injected" while nothing reached the prompt. `keystroke`
    posts the characters straight to the focused field and works in
    Warp. System Events `keystroke` also handles Unicode strings, so
    we no longer need the clipboard layer (which had the side effect
    of clobbering the user's clipboard).
    """
    if not keystrokes:
        return False, "no keystrokes to send"
    # Build the `keystroke "<text>" / key code 36` blocks. Delay 0.25s
    # before the FIRST keystroke so the activated app takes focus, and
    # 0.15s between subsequent ones so claude-cli can react.
    blocks = []
    for i, k in enumerate(keystrokes):
        esc = _escape_applescript_string(k)
        prefix_delay = "0.25" if i == 0 else "0.15"
        blocks.append(f'''
        delay {prefix_delay}
        keystroke "{esc}"
        delay 0.10
        key code 36
        ''')
    body = "\n".join(blocks)
    app_esc = _escape_applescript_string(app_name)
    script = f'''
on injectKeystrokesViaSE(appName)
    try
        tell application appName to activate
        delay 0.30
        tell application "System Events"
            {body}
        end tell
        return "system-events:ok"
    on error errMsg number errNum
        return "system-events:error " & errNum & " " & errMsg
    end try
end injectKeystrokesViaSE

return injectKeystrokesViaSE("{app_esc}")
'''
    # Tighter timeout — System Events keystroke fires fast when
    # Accessibility permission is granted; the only thing that
    # makes it slow is a permission prompt blocking on the user.
    # If we hang past 6s+overhead, surface the well-known cause
    # rather than waiting forever.
    ok, out = _run_osascript(script, timeout=6.0 + 0.4 * len(keystrokes))
    perm_hint = (
        "Open System Settings → Privacy & Security → Accessibility and "
        "enable the entry for python3 / Python.app (or whatever process "
        "is running the dashboard). On the first call you may also see a "
        "system dialog — if you missed it, the toggle in Settings is the "
        "permanent fix."
    )
    if not ok:
        if "timed out" in out.lower():
            return False, (
                f"system-events osascript timed out — most likely the dashboard's "
                f"Python is missing Accessibility permission. {perm_hint} "
                f"Original: {out}"
            )
        return False, f"system-events osascript failed: {out}"
    if out.startswith("system-events:error"):
        # Common error codes:
        #   -1719 / 1002: not allowed to send keystrokes (Accessibility denied)
        #   -1728:        target app not found / not running
        #   -1712:        AppleEvent timeout (target app slow)
        if "1002" in out or "-1719" in out:
            return False, (
                f"{out} — Accessibility permission denied. {perm_hint}"
            )
        return False, out
    return True, f"system-events:{app_name}"


# ───────── Warp (focus exact pane, then keystroke) ─────────

def _warp_inject(uuid: str, keystrokes: list[str]) -> tuple[bool, str]:
    """Warp injection: focus the pane via warp://session/<uuid>, then keystroke.

    NOTE: this is best-effort only. In practice the focus-then-keystroke
    sequence has proved UNRELIABLE (keystrokes can fail to land), so it is
    gated behind ``allow_system_events`` — i.e. only the manual endpoint, where
    the user is watching, tries it. The unattended worker uses the precise
    strategies (tmux send-keys, iTerm2/Terminal.app tty-targeting) only.
    """
    ok, msg = _warp_focus_session(uuid)
    if not ok:
        return False, f"warp focus failed: {msg}"
    ok2, msg2 = _system_events_inject("Warp", keystrokes)
    if not ok2:
        return False, f"warp pane focused but keystroke failed: {msg2}"
    return True, "warp-session"


# ───────── Main entrypoint ─────────

def inject_live(
    pid: int,
    prompt: str,
    *,
    press_choice: Optional[str] = "1",
    allow_system_events: bool = True,
) -> dict:
    """Best-effort live keystroke injection into the terminal that
    hosts the given PID.

    Args:
        pid: PID of the running `claude` process.
        prompt: User-supplied text to inject. Gets a trailing
                Return (so claude's input-line submits).
        press_choice: If set (default '1'), this character is
                injected FIRST as its own line — used to dismiss
                rate-limit / login selection prompts before the
                real prompt arrives. Pass None to skip.
        allow_system_events: Gates the IMPRECISE strategies — Warp
                focus-by-session-URL (A2, flaky) and the BLIND
                System Events keystroke fallback (B, types into
                whatever pane is focused, can hit the WRONG one).
                Unattended callers MUST pass False so only the
                precise strategies run (tmux send-keys; iTerm2/
                Terminal.app tty-targeting). Defaults to True for
                the manual endpoint, where the user is watching.

    Returns:
        {
          "ok": bool,
          "mechanism": str|None,   # "iterm" / "terminal-app" /
                                   # "system-events:<App>" / None
          "tty": str|None,
          "terminalApp": str|None, # App detected via process tree
          "tried": [<labels>],
          "error": str|None,
        }
    """
    if shutil.which("osascript") is None:
        return {
            "ok": False, "mechanism": None, "tty": None, "terminalApp": None,
            "tried": [],
            "error": "osascript not on PATH (live injection requires macOS)",
        }
    tty_short = _tty_for_pid(pid)
    if not tty_short:
        return {
            "ok": False, "mechanism": None, "tty": None, "terminalApp": None,
            "tried": [],
            "error": f"could not resolve TTY for pid {pid} (process gone or no controlling terminal)",
        }
    # Build the keystroke list: optional choice + the prompt itself.
    keys: list[str] = []
    if press_choice:
        keys.append(str(press_choice))
    keys.append(prompt)
    tty_full = _full_tty_path(tty_short)
    tried: list[str] = []
    last_err = ""

    # Strategy 0 (highest priority): tmux send-keys. Pane-precise, focus-
    # independent, works in ANY host terminal (including Warp) — the most
    # reliable mechanism by far. If the session runs inside tmux, use it.
    tmux_t = _tmux_target(pid)
    if tmux_t:
        socket, pane = tmux_t
        tried.append(f"tmux:{pane}")
        try:
            ok, msg = _tmux_inject(socket, pane, keys)
        except Exception as e:
            ok, msg = False, f"tmux crashed: {e}"
        if ok:
            log.info("auto_resume.inject_live: success via %s (tty %s)", msg, tty_full)
            return {
                "ok": True, "mechanism": msg, "tty": tty_full,
                "terminalApp": "tmux", "tried": tried, "error": None,
            }
        last_err = msg
        log.info("auto_resume.inject_live: tmux send-keys failed (%s)", msg)

    # Detect the hosting terminal app upfront — used both to decide
    # whether to bother with Strategy A (skip if we already know the
    # terminal isn't iTerm/Terminal.app) and as the target for
    # Strategy B.
    detected_app = _detect_terminal_app(pid)

    # Strategy A: TTY-targeted AppleScript. Doesn't disturb focus,
    # exact match against `tty of <session>`. Skip the per-app
    # probe when the detected terminal already shows it's not
    # one of these — saves a multi-second AppleScript walk that
    # would only fail.
    apple_script_strategies: list[tuple] = []
    if detected_app in (None, "iTerm2", "iTerm"):
        apple_script_strategies.append((_iterm2_inject, "iterm"))
    if detected_app in (None, "Terminal"):
        apple_script_strategies.append((_terminal_app_inject, "terminal-app"))
    for fn, label in apple_script_strategies:
        tried.append(label)
        try:
            ok, msg = fn(tty_short, keys)
        except Exception as e:
            ok, msg = False, f"{label} crashed: {e}"
        if ok:
            log.info("auto_resume.inject_live: success via %s into %s", msg, tty_full)
            return {
                "ok": True, "mechanism": msg, "tty": tty_full,
                "terminalApp": msg.split(":", 1)[0],
                "tried": tried, "error": None,
            }
        last_err = msg
        log.info("auto_resume.inject_live: %s did not match (%s)", label, msg)

    # Strategy A2: Warp — focus the pane via warp://session/<uuid>, then
    # keystroke. Best-effort only (has proved flaky), so it's gated behind
    # allow_system_events alongside the blind fallback — the unattended worker
    # (allow_system_events=False) skips it and relies on tmux/TTY instead.
    if allow_system_events and detected_app in (None, "Warp"):
        warp_uuid = _warp_session_uuid(pid)
        if warp_uuid:
            tried.append("warp-session")
            try:
                ok, msg = _warp_inject(warp_uuid, keys)
            except Exception as e:
                ok, msg = False, f"warp-session crashed: {e}"
            if ok:
                log.info(
                    "auto_resume.inject_live: success via warp-session %s into %s",
                    warp_uuid, tty_full,
                )
                return {
                    "ok": True, "mechanism": "warp-session", "tty": tty_full,
                    "terminalApp": "Warp", "tried": tried, "error": None,
                }
            last_err = msg
            log.info("auto_resume.inject_live: warp-session failed (%s)", msg)

    # Strategy B: BLIND System Events fallback — types into the FOCUSED pane,
    # which may be the wrong one. Off for unattended callers.
    if not allow_system_events:
        return {
            "ok": False, "mechanism": None, "tty": tty_full,
            "terminalApp": detected_app, "tried": tried,
            "error": (f"no pane-precise injection available for {tty_full} "
                      f"(terminal: {detected_app}); blind System Events fallback "
                      f"disabled (allow_system_events=False). last: {last_err}"),
        }
    if not detected_app:
        return {
            "ok": False, "mechanism": None, "tty": tty_full,
            "terminalApp": None, "tried": tried,
            "error": (f"no AppleScript-tty match for {tty_full} and could not detect "
                      f"a terminal app in the process ancestry"),
        }
    tried.append(f"system-events:{detected_app}")
    try:
        ok, msg = _system_events_inject(detected_app, keys)
    except Exception as e:
        ok, msg = False, f"system-events crashed: {e}"
    if ok:
        log.info("auto_resume.inject_live: success via %s into %s", msg, tty_full)
        return {
            "ok": True, "mechanism": msg, "tty": tty_full,
            "terminalApp": detected_app, "tried": tried, "error": None,
        }
    last_err = msg
    return {
        "ok": False, "mechanism": None, "tty": tty_full,
        "terminalApp": detected_app, "tried": tried,
        "error": (f"all strategies failed for {tty_full} (terminal: {detected_app}); "
                  f"last attempt: {last_err}"),
    }
