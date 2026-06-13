"""SSRF guard (H2/H3) — the workflow HTTP node must block internal targets,
including the encoded-IP / CGNAT forms the old string-prefix check missed.

These are offline: literal IPs resolve numerically (no DNS), and encoded forms
either resolve to loopback or fail to resolve — both yield "blocked" because
`_http_is_internal` is fail-closed on resolution errors.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def wf(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_DASHBOARD_DB", str(tmp_path / "wf.db"))
    monkeypatch.setenv("CLAUDE_DASHBOARD_WORKFLOWS", str(tmp_path / "workflows.json"))
    from server import config as _c; importlib.reload(_c)
    from server import db as _db; importlib.reload(_db)
    from server import workflows; importlib.reload(workflows)
    return workflows


@pytest.mark.parametrize("host", [
    "127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.1", "172.31.255.255",
    "169.254.169.254", "2130706433", "0x7f000001", "100.64.1.2", "::1",
    "localhost", "foo.localhost",
])
def test_blocks_internal(wf, host):
    assert wf._http_is_internal(host) is True


@pytest.mark.parametrize("host", ["8.8.8.8", "1.1.1.1"])
def test_allows_public_ip(wf, host):
    assert wf._http_is_internal(host) is False


def test_ip_is_blocked_helper(wf):
    assert wf._ip_is_blocked("2130706433") is False     # not a valid IP string
    assert wf._ip_is_blocked("127.0.0.1") is True        # resolved loopback
    assert wf._ip_is_blocked("100.64.0.0") is True       # CGNAT lower bound
    assert wf._ip_is_blocked("100.127.255.255") is True  # CGNAT upper bound
    assert wf._ip_is_blocked("100.128.0.0") is False     # just outside CGNAT
    assert wf._ip_is_blocked("9.9.9.9") is False
    assert wf._ip_is_blocked("not-an-ip") is False
