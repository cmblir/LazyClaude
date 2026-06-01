"""Unit tests for deterministic logic in server.auto_resume.

Covers: _classify_exit, _parse_reset_time, _exponential_backoff,
        _push_hash_and_check_stall, _jsonl_idle_seconds, _looks_rate_limited.

Run via `make test` or `pytest tests/ -v` from repo root.
"""
from __future__ import annotations

import pytest

from server.auto_resume import (
    EXIT_REASONS,
    SNAPSHOT_STALL_LIMIT,
    _classify_exit,
    _exponential_backoff,
    _jsonl_idle_seconds,
    _looks_rate_limited,
    _parse_reset_time,
    _push_hash_and_check_stall,
)


# ───────── _classify_exit ─────────

class TestClassifyExit:
    def test_exit_zero_is_clean(self):
        assert _classify_exit(0, "", "", "") == "clean"

    def test_auth_expired_takes_precedence(self):
        # Should win even if rate-limit hint is also present
        assert _classify_exit(1, "Unauthorized: please run /login", "rate limit", "") == "auth_expired"

    def test_context_full_classified(self):
        assert _classify_exit(1, "context window exceeded", "", "") == "context_full"
        assert _classify_exit(1, "prompt is too long for the model", "", "") == "context_full"

    def test_rate_limit_classified(self):
        assert _classify_exit(1, "5-hour limit reached", "", "") == "rate_limit"
        assert _classify_exit(1, "", "", "you have exceeded the usage limit") == "rate_limit"
        assert _classify_exit(1, "HTTP 429 Too Many Requests", "", "") == "rate_limit"

    def test_unknown_fallback(self):
        assert _classify_exit(139, "SIGSEGV", "", "") == "unknown"
        assert _classify_exit(2, "random error", "", "") == "unknown"

    def test_returns_only_valid_reason(self):
        for code in [0, 1, 2, 137, 139]:
            reason = _classify_exit(code, "noise", "noise", "noise")
            assert reason in EXIT_REASONS


# ───────── _parse_reset_time ─────────

class TestParseResetTime:
    def test_empty_returns_none(self, fixed_now):
        assert _parse_reset_time("", now_ts=fixed_now) is None
        assert _parse_reset_time("   ", now_ts=fixed_now) is None

    def test_relative_minutes(self, fixed_now):
        # "in 5 minutes" -> ~300s in future (returns epoch_ms)
        result = _parse_reset_time("try again in 5 minutes", now_ts=fixed_now)
        assert result is not None
        delta_sec = (result / 1000.0) - fixed_now
        assert 295 < delta_sec < 320  # 5min + safety margin

    def test_relative_seconds(self, fixed_now):
        result = _parse_reset_time("wait 30 seconds", now_ts=fixed_now)
        assert result is not None
        delta_sec = (result / 1000.0) - fixed_now
        assert 25 < delta_sec < 50

    def test_relative_hours(self, fixed_now):
        result = _parse_reset_time("try again in 2 hours", now_ts=fixed_now)
        assert result is not None
        delta_sec = (result / 1000.0) - fixed_now
        assert 7000 < delta_sec < 7300  # 2h ± margin

    def test_no_match_returns_none(self, fixed_now):
        assert _parse_reset_time("something completely unrelated", now_ts=fixed_now) is None

    def test_session_limit_absolute_pm(self, fixed_now):
        # The exact wording the user reported: "you've hit your session limit
        # - resets 5:50pm" must parse to 17:50 (today or tomorrow if past).
        result = _parse_reset_time(
            "you've hit your session limit - resets 5:50pm", now_ts=fixed_now
        )
        assert result is not None
        from datetime import datetime
        dt = datetime.fromtimestamp(result / 1000.0)
        assert (dt.hour, dt.minute) == (17, 50)

    def test_absolute_hour_only_with_meridiem(self, fixed_now):
        # Newer CLI wording drops the minutes: "resets 3am".
        result = _parse_reset_time("5-hour limit reached . resets 3am", now_ts=fixed_now)
        assert result is not None
        from datetime import datetime
        dt = datetime.fromtimestamp(result / 1000.0)
        assert (dt.hour, dt.minute) == (3, 0)

    def test_bare_number_without_meridiem_is_ambiguous(self, fixed_now):
        # A lone number with neither minutes nor am/pm must NOT be read as a
        # time (e.g. "resets 3 attempts later").
        assert _parse_reset_time("resets 3 attempts later", now_ts=fixed_now) is None

    def test_24h_clock_still_parses(self, fixed_now):
        # 24-hour "resets at 14:30" (no meridiem, has minutes) still works.
        result = _parse_reset_time("resets at 14:30", now_ts=fixed_now)
        assert result is not None
        from datetime import datetime
        dt = datetime.fromtimestamp(result / 1000.0)
        assert (dt.hour, dt.minute) == (14, 30)

    def test_rollover_anchored_to_message_time_not_now(self, fixed_now):
        # A reset whose clock time already passed relative to NOW but is still
        # AFTER the message-emission anchor must resolve to the past (reset
        # already happened), NOT roll forward 24h. This is the tpl_talk case:
        # "resets 5:50pm" written at 5:15pm, read at 6:12pm.
        from datetime import datetime, timedelta
        anchor = fixed_now - 3600                       # message 1h ago
        reset_dt = datetime.fromtimestamp(anchor) + timedelta(minutes=50)
        clock = reset_dt.strftime("%I:%M%p").lstrip("0").lower()
        result = _parse_reset_time(
            "you've hit your session limit . resets %s" % clock,
            now_ts=fixed_now, anchor_ts=anchor,
        )
        assert result is not None
        assert result / 1000.0 < fixed_now, "reset already passed -> must be in the past"
        assert (fixed_now - result / 1000.0) < 3600, "must not roll a full day forward"

    def test_machine_epoch_reset_parsed(self, fixed_now):
        # Claude Code's machine string: "...usage limit reached|<unix_epoch>".
        epoch = 1780390200
        result = _parse_reset_time(
            "Claude AI usage limit reached|%d" % epoch, now_ts=fixed_now
        )
        assert result is not None
        assert abs(result - epoch * 1000) < 10_000  # epoch ms + small margin

    def test_after_midnight_reset_still_rolls_forward(self, fixed_now):
        # Inverse guard: an 11pm message with "resets 3am" must roll to the
        # next day relative to the anchor (genuine after-midnight reset).
        from datetime import datetime
        # Anchor at 23:00 local on fixed_now's date.
        base = datetime.fromtimestamp(fixed_now).replace(hour=23, minute=0, second=0, microsecond=0)
        anchor = base.timestamp()
        result = _parse_reset_time("resets 3am", now_ts=anchor, anchor_ts=anchor)
        assert result is not None
        dt = datetime.fromtimestamp(result / 1000.0)
        assert (dt.hour, dt.minute) == (3, 0)
        assert result / 1000.0 > anchor, "3am after an 11pm anchor is tomorrow"


# ───────── _exponential_backoff ─────────

class TestExponentialBackoff:
    def test_first_attempt_is_base(self):
        # base = 60 (1m). attempt=1 -> 60*2^0 = 60
        assert _exponential_backoff(1) == 60

    def test_doubles_each_attempt(self):
        v1 = _exponential_backoff(1)
        v2 = _exponential_backoff(2)
        v3 = _exponential_backoff(3)
        assert v1 < v2 < v3
        assert v2 == v1 * 2
        assert v3 == v2 * 2

    def test_capped_at_30_min(self):
        # cap = 1800 (30m). attempt=10 capped, not 60*2^9=30720
        assert _exponential_backoff(10) == 1800
        assert _exponential_backoff(100) == 1800

    def test_attempt_lower_bound_clamped(self):
        # attempt < 1 normalized to 1
        assert _exponential_backoff(0) == 60
        assert _exponential_backoff(-5) == 60

    def test_monotone_until_cap(self):
        prev = 0
        for a in range(1, 20):
            v = _exponential_backoff(a)
            assert v >= prev
            prev = v


# ───────── _push_hash_and_check_stall ─────────

class TestPushHashStall:
    def test_first_call_records_no_stall(self):
        entry: dict = {}
        assert _push_hash_and_check_stall(entry, "h1") is False
        assert entry.get("snapshotHashes") == ["h1"]

    def test_repeated_same_hash_triggers_stall(self):
        entry: dict = {}
        # Up to SNAPSHOT_STALL_LIMIT identical hashes; the limit-th call signals stall
        results = []
        for _ in range(SNAPSHOT_STALL_LIMIT):
            results.append(_push_hash_and_check_stall(entry, "h1"))
        # The last one should be True (stall reached)
        assert results[-1] is True

    def test_different_hash_breaks_streak(self):
        entry: dict = {}
        _push_hash_and_check_stall(entry, "h1")
        _push_hash_and_check_stall(entry, "h1")
        # Different hash should NOT trigger stall
        assert _push_hash_and_check_stall(entry, "h2") is False

    def test_empty_hash_short_circuits(self):
        entry: dict = {"snapshotHashes": ["h1", "h1", "h1"]}
        # Empty fresh hash bails without stall signal
        assert _push_hash_and_check_stall(entry, "") is False

    def test_stall_limit_constant_present(self):
        # Sanity: constant is in a sensible range
        assert 2 <= SNAPSHOT_STALL_LIMIT <= 10


# ───────── _jsonl_idle_seconds & _looks_rate_limited ─────────

class TestJsonlHelpers:
    def test_idle_seconds_missing_file(self, tmp_path):
        missing = tmp_path / "does-not-exist.jsonl"
        assert _jsonl_idle_seconds(missing) == 0.0

    def test_idle_seconds_fresh_file(self, tmp_path):
        f = tmp_path / "fresh.jsonl"
        f.write_text("hello\n")
        idle = _jsonl_idle_seconds(f)
        assert 0.0 <= idle < 5.0

    def test_looks_rate_limited_true(self, tmp_path):
        f = tmp_path / "rl.jsonl"
        f.write_text(
            '{"role":"assistant","content":"You have hit the 5-hour limit."}\n'
        )
        assert _looks_rate_limited(f) is True

    def test_looks_rate_limited_false_on_normal(self, tmp_path):
        f = tmp_path / "ok.jsonl"
        f.write_text('{"role":"assistant","content":"Hello world."}\n')
        assert _looks_rate_limited(f) is False

    def test_looks_rate_limited_missing_file(self, tmp_path):
        f = tmp_path / "missing.jsonl"
        assert _looks_rate_limited(f) is False


# ───────── _process_one full lifecycle (integration) ─────────

class TestProcessOneLifecycle:
    """End-to-end: idle+rate-limited jsonl -> spawn fake claude -> STATE_DONE -> auto-disable."""

    def _setup(self, tmp_path, monkeypatch, claude_exit: int, claude_stderr: str = ""):
        import os
        import server.auto_resume as ar

        # Redirect on-disk state to tmp
        state_path = tmp_path / "auto-resume.json"
        monkeypatch.setattr(ar, "AUTO_RESUME_PATH", state_path)

        # Build a fake jsonl with rate-limit signature, mtime old enough
        # to trip idleSeconds gate
        cwd = tmp_path / "session-cwd"
        cwd.mkdir()
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(
            '{"role":"assistant","content":"5-hour limit reached, try again later"}\n'
        )
        old_mtime = time.time() - 600  # 10 min ago
        os.utime(jsonl, (old_mtime, old_mtime))

        # Stub out terminal liveness check (otherwise dead-tick logic kicks in)
        monkeypatch.setattr(ar, "_live_cli_sessions", lambda: {"sess-int-1": {}})

        # Fake `claude` binary as a shell script
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_claude = fake_bin / "claude"
        if claude_exit == 0:
            fake_claude.write_text("#!/bin/sh\necho resumed-ok\nexit 0\n")
        else:
            fake_claude.write_text(
                f"#!/bin/sh\nprintf '%s' {claude_stderr!r} 1>&2\nexit {claude_exit}\n"
            )
        fake_claude.chmod(0o755)
        monkeypatch.setattr(ar, "_claude_bin", lambda: str(fake_claude))

        # Seed an enabled binding
        sid = "sess-int-1"
        store = {
            sid: {
                "sessionId": sid,
                "enabled": True,
                "cwd": str(cwd),
                "jsonlPath": str(jsonl),
                "prompt": "continue",
                "pollInterval": 60,
                "idleSeconds": 30,
                "maxAttempts": 5,
                "useContinue": False,
                "extraArgs": [],
                "installHooks": False,
                "createdAt": int(time.time() * 1000),
                "attempts": 0,
                "lastAttemptAt": 0,
                "nextAttemptAt": 0,
                "state": "watching",
                "snapshotHashes": [],
            }
        }
        ar._dump_all(store)
        return ar, sid

    def test_clean_exit_marks_done_and_disables(self, tmp_path, monkeypatch):
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        ar._process_one(sid)
        store = ar._load_all()
        e = store[sid]
        assert e["state"] == "done", f"expected STATE_DONE, got {e['state']} err={e.get('lastError')}"
        assert e["lastExitCode"] == 0
        assert e["lastExitReason"] == "clean"
        assert e["attempts"] == 1
        assert e["nextAttemptAt"] == 0

    def test_rate_limit_exit_schedules_retry_keeps_enabled(self, tmp_path, monkeypatch):
        ar, sid = self._setup(
            tmp_path, monkeypatch, claude_exit=1,
            claude_stderr="HTTP 429 Too Many Requests",
        )
        ar._process_one(sid)
        store = ar._load_all()
        e = store[sid]
        assert e["lastExitReason"] == "rate_limit"
        assert e["enabled"] is True
        assert e["nextAttemptAt"] > 0
        assert e["attempts"] == 1

    def test_max_attempts_exhausts(self, tmp_path, monkeypatch):
        ar, sid = self._setup(
            tmp_path, monkeypatch, claude_exit=1,
            claude_stderr="HTTP 429 Too Many Requests",
        )
        # Pre-bump attempts to one below cap; one more pass should exhaust.
        store = ar._load_all()
        store[sid]["attempts"] = store[sid]["maxAttempts"]
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert e["state"] == "exhausted"
        assert e["enabled"] is False
        assert "max attempts" in (e.get("stopReason") or "").lower()

    def _stub_bind_path(self, ar, sid, monkeypatch):
        """Stub out the filesystem probes api_auto_resume_set does so the
        bind body reaches the deadline-resolution code without needing
        a real ~/.claude/projects/<id>/<sid>.jsonl."""
        from pathlib import Path as _P
        e = ar._load_all()[sid]
        jsonl_path = _P(e["jsonlPath"])
        monkeypatch.setattr(ar, "_resolve_jsonl", lambda *a, **kw: jsonl_path)
        monkeypatch.setattr(ar, "_resolve_cwd_from_jsonl", lambda p: e["cwd"])
        monkeypatch.setattr(ar, "_live_cli_sessions", lambda: {sid: {"pid": 1}})
        # _claude_bin already stubbed in _setup; don't override.

    def test_api_set_accepts_durationSec_and_computes_deadline(self, tmp_path, monkeypatch):
        # The user asked: "let me pick how long, not how many tries."
        # Verify api_auto_resume_set accepts durationSec and stores the
        # resulting deadlineMs so future _process_one ticks see it.
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        self._stub_bind_path(ar, sid, monkeypatch)

        before = int(time.time() * 1000)
        result = ar.api_auto_resume_set({
            "sessionId":     sid,
            "cwd":           ar._load_all()[sid]["cwd"],
            "durationSec":   3600,        # 1 hour
            "useContinue":   False,
            "extraArgs":     [],
            "installHooks":  False,
        })
        after = int(time.time() * 1000)
        assert result.get("ok") is True, result
        e = ar._load_all()[sid]
        # deadlineMs should land within (before+3600s, after+3600s).
        assert before + 3600 * 1000 <= e["deadlineMs"] <= after + 3600 * 1000
        # _public_state should expose it.
        ps = result["entry"]
        assert ps["deadlineMs"] == e["deadlineMs"]

    def test_api_set_accepts_explicit_deadlineMs(self, tmp_path, monkeypatch):
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        self._stub_bind_path(ar, sid, monkeypatch)
        target = int(time.time() * 1000) + 7200 * 1000   # 2 hours from now
        result = ar.api_auto_resume_set({
            "sessionId":     sid,
            "cwd":           ar._load_all()[sid]["cwd"],
            "deadlineMs":    target,
            "useContinue":   False,
            "extraArgs":     [],
            "installHooks":  False,
        })
        assert result.get("ok") is True, result
        assert ar._load_all()[sid]["deadlineMs"] == target

    def test_deadline_in_past_exhausts_immediately(self, tmp_path, monkeypatch):
        # User asked: stop at a specific time, not after N attempts.
        # When deadlineMs has already passed, the next _process_one
        # tick must flip state to exhausted without spawning claude.
        ar, sid = self._setup(
            tmp_path, monkeypatch, claude_exit=1,
            claude_stderr="HTTP 429 Too Many Requests",
        )
        store = ar._load_all()
        # Set deadline 60 seconds in the past.
        store[sid]["deadlineMs"] = int(time.time() * 1000) - 60_000
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert e["state"] == "exhausted"
        assert e["enabled"] is False
        assert "deadline reached" in (e.get("stopReason") or "").lower()

    def test_deadline_in_future_does_not_exhaust(self, tmp_path, monkeypatch):
        # Inverse: a future deadline should not trip the exhaustion check.
        # The session should proceed normally (in this case schedule a retry
        # because we set up a rate-limit exit).
        ar, sid = self._setup(
            tmp_path, monkeypatch, claude_exit=1,
            claude_stderr="HTTP 429 Too Many Requests",
        )
        store = ar._load_all()
        store[sid]["deadlineMs"] = int(time.time() * 1000) + 24 * 3600 * 1000
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        # State should be the rate-limit retry path, not exhausted.
        assert e["state"] != "exhausted"
        assert e["enabled"] is True

    def test_auth_expired_disables_permanently(self, tmp_path, monkeypatch):
        ar, sid = self._setup(
            tmp_path, monkeypatch, claude_exit=1,
            claude_stderr="Unauthorized: please run /login",
        )
        ar._process_one(sid)
        store = ar._load_all()
        e = store[sid]
        assert e["state"] == "failed"
        assert e["lastExitReason"] == "auth_expired"
        assert e["enabled"] is False

    # ── maxAttempts above the old 60 clamp ──

    def test_api_set_respects_maxAttempts_above_60(self, tmp_path, monkeypatch):
        # Regression: the old `min(60, raw_max)` silently truncated any value
        # the user raised past 60. Now it must be stored verbatim.
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        self._stub_bind_path(ar, sid, monkeypatch)
        result = ar.api_auto_resume_set({
            "sessionId":    sid,
            "cwd":          ar._load_all()[sid]["cwd"],
            "maxAttempts":  200,
            "useContinue":  False,
            "extraArgs":    [],
            "installHooks": False,
        })
        assert result.get("ok") is True, result
        assert ar._load_all()[sid]["maxAttempts"] == 200
        assert result["entry"]["maxAttempts"] == 200

    def test_rebind_resets_attempts_to_zero(self, tmp_path, monkeypatch):
        # Re-arming a session that previously exhausted must give a fresh
        # budget, not carry the old attempts forward (the second half of the
        # "stuck at 60" bug).
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        self._stub_bind_path(ar, sid, monkeypatch)
        store = ar._load_all()
        store[sid]["attempts"] = 60
        store[sid]["state"] = "exhausted"
        store[sid]["snapshotHashes"] = ["h", "h", "h"]
        store[sid]["_resetParked"] = True
        ar._dump_all(store)

        result = ar.api_auto_resume_set({
            "sessionId":    sid,
            "cwd":          ar._load_all()[sid]["cwd"],
            "maxAttempts":  100,
            "useContinue":  False,
            "extraArgs":    [],
            "installHooks": False,
        })
        assert result.get("ok") is True, result
        e = ar._load_all()[sid]
        assert e["attempts"] == 0, "re-bind must reset attempts"
        assert e["maxAttempts"] == 100
        assert e["state"] == "watching"
        assert e["snapshotHashes"] == []
        assert e["_resetParked"] is False

    def test_api_set_maxAttempts_zero_is_unlimited(self, tmp_path, monkeypatch):
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        self._stub_bind_path(ar, sid, monkeypatch)
        result = ar.api_auto_resume_set({
            "sessionId":    sid,
            "cwd":          ar._load_all()[sid]["cwd"],
            "maxAttempts":  0,
            "useContinue":  False,
            "extraArgs":    [],
            "installHooks": False,
        })
        assert result.get("ok") is True, result
        assert ar._load_all()[sid]["maxAttempts"] == 0

    def test_api_set_maxAttempts_clamped_at_ceiling(self, tmp_path, monkeypatch):
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        self._stub_bind_path(ar, sid, monkeypatch)
        result = ar.api_auto_resume_set({
            "sessionId":    sid,
            "cwd":          ar._load_all()[sid]["cwd"],
            "maxAttempts":  10 ** 9,   # absurd typo
            "useContinue":  False,
            "extraArgs":    [],
            "installHooks": False,
        })
        assert result.get("ok") is True, result
        assert ar._load_all()[sid]["maxAttempts"] == ar.MAX_ATTEMPTS_CEILING

    # ── "session limit -> resume at reset time" (park then inject) ──

    def _write_cap_jsonl(self, ar, sid, content):
        import json
        import os
        from pathlib import Path
        jsonl = Path(ar._load_all()[sid]["jsonlPath"])
        jsonl.write_text(
            json.dumps({"role": "assistant", "content": content}) + "\n"
        )
        old = time.time() - 600   # 10 min ago -> trips idleSeconds gate
        os.utime(jsonl, (old, old))

    def test_future_reset_parks_without_burning_attempt(self, tmp_path, monkeypatch):
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        from datetime import datetime, timedelta
        target = datetime.now() + timedelta(hours=2)
        clock = target.strftime("%I:%M%p").lstrip("0").lower()   # e.g. "5:50pm"
        self._write_cap_jsonl(
            ar, sid, "you've hit your session limit - resets %s" % clock
        )

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert e["state"] == "waiting", e
        assert e["_resetParked"] is True
        assert e["attempts"] == 0, "parking must NOT consume an attempt"
        target_ms = int(target.timestamp() * 1000)
        assert abs(e["nextAttemptAt"] - target_ms) < 5 * 60 * 1000, (
            e["nextAttemptAt"], target_ms,
        )
        assert e["lastResetAt"] == e["nextAttemptAt"]

    def test_parked_reset_elapsed_resumes_via_spawn(self, tmp_path, monkeypatch):
        # Once parked (_resetParked=True) and the reset has elapsed, the next
        # tick must RESUME — i.e. fall through to the truncate+`claude --resume`
        # path — not re-park to tomorrow. (Live injection is no longer used: a
        # usage-limited session is unrecoverable in place, Claude Code #58427.)
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        spawned = {"n": 0}
        monkeypatch.setattr(
            ar, "_spawn_resume",
            lambda e: (spawned.__setitem__("n", spawned["n"] + 1) or (0, "", "")),
        )
        self._write_cap_jsonl(ar, sid, "you've hit your session limit - resets 5:50pm")
        store = ar._load_all()
        store[sid]["_resetParked"] = True
        store[sid]["nextAttemptAt"] = int(time.time() * 1000) - 1000
        store[sid]["spawnFallback"] = True
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert spawned["n"] == 1, "parked + elapsed must resume (spawn), not re-park"
        assert e["_resetParked"] is False, "flag must clear after resuming"
        assert e["attempts"] == 1

    def test_stale_reset_already_passed_resumes_now(self, tmp_path, monkeypatch):
        # tpl_talk scenario: cap message written ~1h ago with a reset time that
        # has already elapsed relative to now. Must resume immediately, NOT park
        # ~24h via a tomorrow-rollover (anchored to the message time).
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        spawned = {"n": 0}
        monkeypatch.setattr(
            ar, "_spawn_resume",
            lambda e: (spawned.__setitem__("n", spawned["n"] + 1) or (0, "", "")),
        )
        import json as _json
        import os
        from datetime import datetime, timedelta
        from pathlib import Path
        now = time.time()
        msg_ts = now - 3600                              # message 1h ago
        reset_dt = datetime.fromtimestamp(msg_ts) + timedelta(minutes=35)  # ~25m ago
        clock = reset_dt.strftime("%I:%M%p").lstrip("0").lower()
        j = Path(ar._load_all()[sid]["jsonlPath"])
        j.write_text(_json.dumps({
            "role": "assistant",
            "content": "you've hit your session limit . resets %s (Asia/Seoul)" % clock,
        }) + "\n")
        os.utime(j, (msg_ts, msg_ts))                    # mtime = message time
        store = ar._load_all()
        store[sid]["spawnFallback"] = True
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert spawned["n"] == 1, "reset already passed -> resume now (spawn), not park"
        assert e.get("_resetParked") in (False, None), "must not park"
        assert e["attempts"] == 1

    def test_spawn_fallback_false_pauses(self, tmp_path, monkeypatch):
        # spawnFallback=False: in-place resume is impossible (Claude Code
        # #58427/#59520), so with the detached `claude --resume` opted out the
        # worker must PAUSE rather than spawn.
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        monkeypatch.setattr(ar, "_live_cli_sessions", lambda: {sid: {"pid": 4242}})
        spawned = {"n": 0}
        monkeypatch.setattr(
            ar, "_spawn_resume",
            lambda e: (spawned.__setitem__("n", spawned["n"] + 1) or (0, "", "")),
        )
        self._write_cap_jsonl(ar, sid, "you've hit your session limit, try again later")
        store = ar._load_all()
        store[sid]["spawnFallback"] = False
        store[sid]["pid"] = 4242
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert spawned["n"] == 0, "spawnFallback=false must not spawn"
        assert e["state"] == "failed"
        assert e["enabled"] is False

    def test_spawn_fallback_true_resumes_via_spawn(self, tmp_path, monkeypatch):
        # spawnFallback=True (default): truncate synthetic tail + `claude
        # --resume`. Here the fake claude exits 0 -> DONE.
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        monkeypatch.setattr(ar, "_live_cli_sessions", lambda: {sid: {"pid": 4242}})
        self._write_cap_jsonl(ar, sid, "you've hit your session limit, try again later")
        store = ar._load_all()
        store[sid]["spawnFallback"] = True
        store[sid]["pid"] = 4242
        ar._dump_all(store)

        ar._process_one(sid)
        e = ar._load_all()[sid]
        assert e["state"] == "done", e
        assert e["lastExitReason"] == "clean"
        assert e["attempts"] == 1

    def test_park_does_not_spawn_claude(self, tmp_path, monkeypatch):
        # While parked we must NOT spawn `claude --resume`; assert the spawn
        # path is never reached for a future-reset cap.
        ar, sid = self._setup(tmp_path, monkeypatch, claude_exit=0)
        spawned = {"n": 0}
        monkeypatch.setattr(
            ar, "_spawn_resume",
            lambda entry: (spawned.__setitem__("n", spawned["n"] + 1) or (0, "", "")),
        )
        from datetime import datetime, timedelta
        target = datetime.now() + timedelta(hours=3)
        clock = target.strftime("%I:%M%p").lstrip("0").lower()
        self._write_cap_jsonl(
            ar, sid, "you've hit your session limit - resets %s" % clock
        )
        ar._process_one(sid)
        assert spawned["n"] == 0, "must not spawn while parked for a future reset"
        assert ar._load_all()[sid]["state"] == "waiting"


class TestTruncateSyntheticTail:
    """Claude Code #58427/#59520 workaround — revert jsonl to last real msg_."""

    def _line(self, **kw):
        import json
        return json.dumps(kw)

    def test_truncates_synthetic_tail_to_last_real_msg(self, tmp_path, monkeypatch):
        import server.auto_resume as ar
        j = tmp_path / "s.jsonl"
        j.write_text("\n".join([
            self._line(type="assistant", message={"id": "msg_01REAL", "model": "claude-opus-4-8"}),
            self._line(type="user", message={"role": "user", "content": "do it"}),
            self._line(type="assistant", message={"id": "22ab97a8-uuid", "model": "<synthetic>"}, isApiErrorMessage=True),
            self._line(type="assistant", message={"id": "e6f-uuid", "model": "<synthetic>"}, isApiErrorMessage=True),
        ]) + "\n")
        res = ar._truncate_synthetic_tail(str(j))
        assert res["ok"] is True
        assert res["removed"] == 3  # user + 2 synthetic after the last real msg_
        # last line is now the real msg_ assistant
        import json
        lines = [l for l in j.read_text().splitlines() if l.strip()]
        last = json.loads(lines[-1])
        assert last["message"]["id"] == "msg_01REAL"
        # backup exists
        import os
        assert os.path.exists(res["backup"])

    def test_noop_when_tail_already_clean(self, tmp_path):
        import server.auto_resume as ar
        j = tmp_path / "s.jsonl"
        j.write_text("\n".join([
            self._line(type="assistant", message={"id": "msg_01A", "model": "claude-opus-4-8"}),
            self._line(type="assistant", message={"id": "msg_01B", "model": "claude-opus-4-8"}),
        ]) + "\n")
        res = ar._truncate_synthetic_tail(str(j))
        assert res["ok"] is True
        assert res["removed"] == 0

    def test_no_real_msg_returns_not_ok(self, tmp_path):
        import server.auto_resume as ar
        j = tmp_path / "s.jsonl"
        j.write_text(self._line(type="assistant", message={"id": "uuid-only", "model": "<synthetic>"}) + "\n")
        res = ar._truncate_synthetic_tail(str(j))
        assert res["ok"] is False
        assert "no real msg_" in res["reason"]

    def test_missing_file(self, tmp_path):
        import server.auto_resume as ar
        res = ar._truncate_synthetic_tail(str(tmp_path / "nope.jsonl"))
        assert res["ok"] is False


# Needed for the integration tests above
import time  # noqa: E402
