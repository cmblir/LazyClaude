"""Unit tests for server.plugin_hub — Claude Code plugin discovery/install.

Network (GitHub REST + raw CDN) and the `claude` CLI are mocked so the suite is
deterministic and offline. Run via `pytest tests/test_plugin_hub.py`.
"""
from __future__ import annotations

import server.plugin_hub as ph


def _clear_cache():
    with ph._CACHE_LOCK:
        ph._SEARCH_CACHE.clear()


# ───────── identifier validation ─────────


class TestValidation:
    def test_repo_regex_accepts_owner_repo(self):
        assert ph._RE_REPO.match("anthropics/claude-code")
        assert ph._RE_REPO.match("JuliusBrussee/caveman")

    def test_repo_regex_rejects_injection(self):
        for bad in ["a/b; rm -rf /", "a/b && x", "../etc", "no-slash", "a/b/c", "a /b"]:
            assert not ph._RE_REPO.match(bad), bad

    def test_name_regex(self):
        assert ph._RE_NAME.match("caveman")
        assert not ph._RE_NAME.match("a b")
        assert not ph._RE_NAME.match("a;b")


# ───────── search ─────────


class TestSearch:
    def _fake_items(self):
        return {
            "total_count": 2,
            "items": [
                {
                    "full_name": "owner/good",
                    "name": "good",
                    "owner": {"login": "owner"},
                    "stargazers_count": 500,
                    "description": "a plugin",
                    "html_url": "https://github.com/owner/good",
                    "default_branch": "main",
                    "license": {"spdx_id": "MIT"},
                    "topics": ["claude-code-plugin"],
                    "archived": False,
                },
                {
                    "full_name": "anthropics/official",
                    "name": "official",
                    "owner": {"login": "anthropics"},
                    "stargazers_count": 9000,
                    "archived": True,  # should be filtered out
                },
            ],
        }

    def test_search_returns_cards_and_filters_archived(self, monkeypatch):
        _clear_cache()
        monkeypatch.setattr(ph, "_http_get", lambda url, **k: (200, self._fake_items(), {}))
        r = ph.api_plugin_hub_search({"q": [""], "limit": ["30"]})
        assert r["ok"] is True
        assert r["total"] == 2
        names = [c["fullName"] for c in r["repos"]]
        assert "owner/good" in names
        assert "anthropics/official" not in names  # archived dropped
        assert r["repos"][0]["license"] == "MIT"

    def test_search_marks_official_owner(self, monkeypatch):
        _clear_cache()
        payload = {
            "total_count": 1,
            "items": [
                {
                    "full_name": "anthropics/skills",
                    "name": "skills",
                    "owner": {"login": "anthropics"},
                    "stargazers_count": 1,
                    "archived": False,
                }
            ],
        }
        monkeypatch.setattr(ph, "_http_get", lambda url, **k: (200, payload, {}))
        r = ph.api_plugin_hub_search({"q": [""]})
        assert r["repos"][0]["official"] is True

    def test_search_rate_limit_surfaces_clean_error(self, monkeypatch):
        _clear_cache()
        monkeypatch.setattr(ph, "_http_get", lambda url, **k: (403, None, {"x-ratelimit-remaining": "0"}))
        r = ph.api_plugin_hub_search({"q": ["x"]})
        assert r["ok"] is False
        assert "rate limit" in r["error"].lower()

    def test_search_caches(self, monkeypatch):
        _clear_cache()
        calls = {"n": 0}

        def fake(url, **k):
            calls["n"] += 1
            return 200, {"total_count": 0, "items": []}, {}

        monkeypatch.setattr(ph, "_http_get", fake)
        ph.api_plugin_hub_search({"q": ["dup"]})
        ph.api_plugin_hub_search({"q": ["dup"]})
        assert calls["n"] == 1  # second served from cache

    def test_search_text_query_builds_scoped_expression(self, monkeypatch):
        _clear_cache()
        seen = {}
        monkeypatch.setattr(ph, "_http_get", lambda url, **k: (seen.update({"url": url}), (200, {"total_count": 0, "items": []}, {}))[1])
        ph.api_plugin_hub_search({"q": ["memory"]})
        assert "claude" in seen["url"] and "code" in seen["url"]


# ───────── inspect ─────────


class TestInspect:
    def test_inspect_rejects_bad_repo(self):
        r = ph.api_plugin_hub_inspect({"repo": ["not-a-repo"]})
        assert r["ok"] is False

    def test_inspect_parses_marketplace(self, monkeypatch):
        mkt = {
            "name": "caveman",
            "description": "caveman marketplace",
            "plugins": [
                {"name": "caveman", "description": "talk like caveman", "source": "./", "category": "productivity"}
            ],
        }

        def fake(url, **k):
            if url.endswith("/repos/JuliusBrussee/caveman"):
                return 200, {"full_name": "JuliusBrussee/caveman", "default_branch": "main",
                             "owner": {"login": "JuliusBrussee"}, "stargazers_count": 100}, {}
            if "marketplace.json" in url:
                return 200, mkt, {}
            if "plugin.json" in url:
                return 200, {"name": "caveman", "skills": ["x"]}, {}
            return 404, None, {}

        monkeypatch.setattr(ph, "_http_get", fake)
        r = ph.api_plugin_hub_inspect({"repo": ["JuliusBrussee/caveman"]})
        assert r["ok"] is True
        assert r["marketplaceName"] == "caveman"
        assert len(r["plugins"]) == 1
        p = r["plugins"][0]
        assert p["name"] == "caveman"
        assert p["installCmd"] == "claude plugin install caveman@caveman"
        assert p["risk"]["components"] == ["skills"]
        assert p["risk"]["runsCode"] is False

    def test_inspect_flags_runs_code_for_hooks(self, monkeypatch):
        mkt = {"name": "m", "plugins": [{"name": "p", "source": "./p"}]}

        def fake(url, **k):
            if url.endswith("/repos/o/r"):
                return 200, {"default_branch": "main", "owner": {"login": "o"}}, {}
            if "marketplace.json" in url:
                return 200, mkt, {}
            if "plugin.json" in url:
                return 200, {"name": "p", "hooks": "hooks/hooks.json"}, {}
            return 404, None, {}

        monkeypatch.setattr(ph, "_http_get", fake)
        r = ph.api_plugin_hub_inspect({"repo": ["o/r"]})
        assert r["plugins"][0]["risk"]["runsCode"] is True
        assert "hooks" in r["plugins"][0]["risk"]["components"]

    def test_inspect_non_marketplace_graceful(self, monkeypatch):
        def fake(url, **k):
            if "/repos/" in url:
                return 200, {"default_branch": "main", "owner": {"login": "o"}}, {}
            return 404, None, {}  # no marketplace.json on any branch

        monkeypatch.setattr(ph, "_http_get", fake)
        r = ph.api_plugin_hub_inspect({"repo": ["o/plain-skills"]})
        assert r["ok"] is False
        assert "marketplace.json" in r["error"]


# ───────── install (gated) ─────────


class TestInstall:
    def test_install_requires_confirm(self):
        r = ph.api_plugin_hub_install({"repo": "o/r", "plugin": "p", "marketplace": "m"})
        assert r["ok"] is False
        assert r.get("needsConfirm") is True

    def test_install_validates_identifiers(self, monkeypatch):
        monkeypatch.setattr(ph, "_claude_bin", lambda: "/usr/bin/claude")
        r = ph.api_plugin_hub_install({"confirm": True, "repo": "o/r; rm", "plugin": "p", "marketplace": "m"})
        assert r["ok"] is False and "repo" in r["error"]
        r = ph.api_plugin_hub_install({"confirm": True, "repo": "o/r", "plugin": "p p", "marketplace": "m"})
        assert r["ok"] is False

    def test_install_runs_add_then_install(self, monkeypatch):
        monkeypatch.setattr(ph, "_claude_bin", lambda: "/usr/bin/claude")
        cmds = []

        def fake_run(args, timeout=120):
            cmds.append(args)
            return 0, "ok", ""

        monkeypatch.setattr(ph, "_run_claude", fake_run)
        r = ph.api_plugin_hub_install(
            {"confirm": True, "repo": "JuliusBrussee/caveman", "plugin": "caveman", "marketplace": "caveman"}
        )
        assert r["ok"] is True
        assert cmds[0] == ["plugin", "marketplace", "add", "JuliusBrussee/caveman"]
        assert cmds[1] == ["plugin", "install", "caveman@caveman", "--scope", "user"]

    def test_install_marketplace_already_exists_is_nonfatal(self, monkeypatch):
        monkeypatch.setattr(ph, "_claude_bin", lambda: "/usr/bin/claude")
        seq = iter([(1, "", "marketplace already added"), (0, "installed", "")])
        monkeypatch.setattr(ph, "_run_claude", lambda args, timeout=120: next(seq))
        r = ph.api_plugin_hub_install(
            {"confirm": True, "repo": "o/r", "plugin": "p", "marketplace": "m"}
        )
        assert r["ok"] is True

    def test_install_no_claude_bin(self, monkeypatch):
        monkeypatch.setattr(ph, "_claude_bin", lambda: None)
        r = ph.api_plugin_hub_install({"confirm": True, "repo": "o/r", "plugin": "p", "marketplace": "m"})
        assert r["ok"] is False and "PATH" in r["error"]


class TestInstalled:
    def test_no_claude_returns_empty(self, monkeypatch):
        monkeypatch.setattr(ph, "_claude_bin", lambda: None)
        r = ph.api_plugin_hub_installed({})
        assert r["ok"] is True and r["plugins"] == []

    def test_parses_json_list(self, monkeypatch):
        monkeypatch.setattr(ph, "_claude_bin", lambda: "/usr/bin/claude")
        monkeypatch.setattr(ph, "_run_claude", lambda args, timeout=30: (0, '[{"name":"caveman"}]', ""))
        r = ph.api_plugin_hub_installed({})
        assert r["ok"] is True
        assert r["plugins"] == [{"name": "caveman"}]
