"""Real-tmux integration tests for the Auto-Resume in-pane relaunch primitives.

The rest of the suite drives `_resume_in_tmux_pane` with every tmux/macOS
side-effect mocked. These tests exercise the ACTUAL tmux primitives the
unattended worker depends on — `tmux_send_line`, `tmux_capture`,
`tmux_pane_command`, and `_tmux_target` pane discovery — against a real,
throwaway tmux server. Skipped when tmux is not installed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time

import pytest

import server.auto_resume_inject as ari

pytestmark = pytest.mark.skipif(
    shutil.which("tmux") is None, reason="tmux not installed"
)


@pytest.fixture()
def tmux_pane():
    """A detached single-pane tmux server on a throwaway socket placed in the
    standard per-uid dir so `_tmux_sockets()` can discover it. Torn down after."""
    sock_dir = f"/tmp/tmux-{os.getuid()}"
    os.makedirs(sock_dir, exist_ok=True)
    sock = f"{sock_dir}/lc-test-{os.getpid()}"
    subprocess.run(
        ["tmux", "-S", sock, "new-session", "-d", "-s", "lctest", "-x", "120", "-y", "40"],
        check=True, timeout=10,
    )
    try:
        out = subprocess.check_output(
            ["tmux", "-S", sock, "list-panes", "-F", "#{pane_id} #{pane_pid}"],
            text=True, timeout=10,
        ).strip().split("\n")[0]
        pane_id, pane_pid = out.split()[0], int(out.split()[1])
        yield {"sock": sock, "pane": pane_id, "pane_pid": pane_pid}
    finally:
        subprocess.run(["tmux", "-S", sock, "kill-server"], timeout=10, check=False)
        try:
            os.remove(sock)
        except OSError:
            pass


def _wait_for(fn, pred, timeout=6.0):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = fn()
        if pred(last):
            return last
        time.sleep(0.2)
    return last


class TestTmuxLive:
    def test_send_line_lands_in_pane(self, tmux_pane):
        """tmux_send_line types a real command + Enter; capture-pane sees its
        output. This is the exact mechanism _resume_in_tmux_pane uses to relaunch
        `claude --resume` in the live pane."""
        ok, msg = ari.tmux_send_line(tmux_pane["sock"], tmux_pane["pane"], "echo LCMARKER_7788")
        assert ok, f"send_line failed: {msg}"
        cap = _wait_for(
            lambda: ari.tmux_capture(tmux_pane["sock"], tmux_pane["pane"]),
            lambda c: "LCMARKER_7788" in c,
        )
        assert "LCMARKER_7788" in cap

    def test_pane_current_command_reports_shell(self, tmux_pane):
        """tmux_pane_command drives the 'wait until claude exited and pane fell
        back to a shell' loop in _resume_in_tmux_pane."""
        cmd = ari.tmux_pane_command(tmux_pane["sock"], tmux_pane["pane"])
        assert cmd, "expected a non-empty foreground command"
        assert "claude" not in cmd.lower()  # a bare shell, not claude

    def test_tmux_target_discovers_real_pane(self, tmux_pane):
        """_tmux_target(pid) is how the worker decides to relaunch in-pane vs
        headless. Given the pane's own pid it must locate (socket, pane_id)."""
        target = ari._tmux_target(tmux_pane["pane_pid"])
        assert target is not None, "expected _tmux_target to find the live pane"
        _sock, pane = target
        assert pane == tmux_pane["pane"]

    def test_capture_empty_for_bogus_pane(self, tmux_pane):
        """A non-existent pane id degrades to '' (no crash) — the readiness
        polls must not throw on a vanished pane."""
        assert ari.tmux_capture(tmux_pane["sock"], "%99999") == ""
        assert ari.tmux_pane_command(tmux_pane["sock"], "%99999") is None
