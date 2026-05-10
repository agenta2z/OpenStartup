"""Tests for runbook_search executor — fully mocked."""

from __future__ import annotations

import asyncio
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import executor  # type: ignore  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


class TestResolveProvider:
    def test_explicit_wins(self):
        assert executor._resolve_provider({"provider": "notion"}, "https://x.atlassian.net/wiki") == "notion"

    def test_env_overrides_url(self, monkeypatch):
        monkeypatch.setenv("DOCS_BACKEND", "mkdocs")
        assert executor._resolve_provider({}, "https://x.atlassian.net/wiki") == "mkdocs"

    def test_url_heuristic_confluence(self):
        assert executor._resolve_provider({}, "https://x.atlassian.net/wiki") == "confluence"

    def test_url_heuristic_notion(self):
        assert executor._resolve_provider({}, "https://api.notion.com/v1") == "notion"

    def test_default_atlassian_docs(self):
        assert executor._resolve_provider({}, "") == "atlassian_docs"


class TestResolveEndpoint:
    def test_explicit_arg(self, monkeypatch):
        monkeypatch.setenv("CONFLUENCE_URL", "http://env.url")
        assert executor._resolve_endpoint({"endpoint": "http://arg.url"}) == "http://arg.url"

    def test_confluence_url(self, monkeypatch):
        monkeypatch.delenv("DOCS_URL", raising=False)
        monkeypatch.setenv("CONFLUENCE_URL", "http://conf.url")
        assert executor._resolve_endpoint({}) == "http://conf.url"

    def test_empty(self, monkeypatch):
        monkeypatch.delenv("CONFLUENCE_URL", raising=False)
        monkeypatch.delenv("DOCS_URL", raising=False)
        assert executor._resolve_endpoint({}) == ""


class TestStripHtml:
    def test_basic_tags(self):
        assert "Hello world" in executor._strip_html("<p>Hello <b>world</b></p>")

    def test_empty(self):
        assert executor._strip_html("") == ""

    def test_truncation(self):
        long_text = "a" * 500
        result = executor._strip_html(f"<p>{long_text}</p>", max_len=100)
        assert len(result) <= 101  # 100 chars + ellipsis
        assert result.endswith("…")


# ---------------------------------------------------------------------------
# Top-level execute() validation
# ---------------------------------------------------------------------------


class TestExecuteValidation:
    def test_no_action(self):
        result = _run(executor.execute({}))
        assert not result["ok"]
        assert "action parameter is required" in result["error"]

    def test_unknown_action(self):
        result = _run(executor.execute({"action": "frobnicate"}))
        assert not result["ok"]
        assert "Unknown action" in result["error"]

    def test_no_endpoint_for_confluence(self, monkeypatch):
        monkeypatch.delenv("CONFLUENCE_URL", raising=False)
        monkeypatch.delenv("DOCS_URL", raising=False)
        result = _run(executor.execute({"action": "search", "query": "x", "provider": "confluence"}))
        assert not result["ok"]
        assert "requires --endpoint" in result["error"]

    def test_atlassian_docs_no_endpoint_ok(self):
        # atlassian_docs default doesn't need endpoint, but stub will reject the action
        result = _run(executor.execute({"action": "search", "query": "x"}))
        assert not result["ok"]
        assert "atlassian_docs" in result["error"].lower()

    def test_dry_run(self):
        result = _run(executor.execute({
            "action": "search",
            "query": "incident response",
            "endpoint": "https://x.atlassian.net/wiki",
            "dry_run": True,
        }))
        assert result["ok"]
        assert result["data"]["action"] == "search"
        assert result["data"]["provider"] == "confluence"

    def test_dry_run_explicit_provider(self):
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "endpoint": "http://x",
            "provider": "notion",
            "dry_run": True,
        }))
        assert result["ok"]
        assert result["data"]["provider"] == "notion"


# ---------------------------------------------------------------------------
# ConfluenceProvider — mocked
# ---------------------------------------------------------------------------


class TestConfluenceProvider:
    def test_search_requires_query_or_label(self):
        result = _run(executor.execute({
            "action": "search",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert not result["ok"]
        assert "Either --query or --label" in result["error"]

    def test_search_builds_cql(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(path=path, params=params)
            return {"_raw": {"results": [], "totalSize": 0}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "search",
            "query": "incident response",
            "space": "ENG",
            "label": "runbook",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert result["ok"]
        assert captured["path"] == "/rest/api/content/search"
        cql = captured["params"]["cql"]
        # Order-agnostic
        assert 'text ~ "incident response"' in cql
        assert 'space = "ENG"' in cql
        assert 'label = "runbook"' in cql
        assert "type in (page, blogpost)" in cql

    def test_search_escapes_quotes_in_query(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(path=path, params=params)
            return {"_raw": {"results": [], "totalSize": 0}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        _run(executor.execute({
            "action": "search",
            "query": 'foo "bar" baz',
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        # Quote in query should be backslash-escaped in the CQL
        assert r'\"bar\"' in captured["params"]["cql"]

    def test_search_normalizes_results(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return {"_raw": {
                "results": [{
                    "content": {
                        "id": "1234",
                        "title": "On-call Runbook for API",
                        "space": {"key": "ENG"},
                        "metadata": {"labels": {"results": [{"name": "runbook"}, {"name": "oncall"}]}},
                        "version": {"when": "2026-04-01T10:00:00Z"},
                        "_links": {"webui": "/spaces/ENG/pages/1234/On-call+Runbook"},
                    },
                    "excerpt": "<p>How to respond to <b>incidents</b></p>",
                }],
                "totalSize": 1,
            }}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "search",
            "query": "runbook",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert result["ok"]
        rows = result["data"]["results"]
        assert len(rows) == 1
        r = rows[0]
        assert r["id"] == "1234"
        assert r["title"] == "On-call Runbook for API"
        assert r["space"] == "ENG"
        assert r["labels"] == ["runbook", "oncall"]
        assert "1234" in r["url"]
        assert "<b>" not in r["snippet"]  # html stripped
        assert r["last_updated"] == "2026-04-01T10:00:00Z"

    def test_search_emits_truncation_warning(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return {"_raw": {"results": [{"content": {"id": str(i), "title": f"p{i}"}} for i in range(5)], "totalSize": 100}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "limit": 5,
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert result["ok"]
        assert any("truncated" in w.lower() for w in result["warnings"])
        assert result["metadata"]["total_count"] == 100

    def test_search_include_body(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(params=params)
            return {"_raw": {"results": [{
                "content": {
                    "id": "1",
                    "title": "T",
                    "body": {"storage": {"value": "<p>full body content</p>"}},
                },
                "excerpt": "snip",
            }], "totalSize": 1}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "include_body": True,
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert result["ok"]
        assert "body.storage" in captured["params"]["expand"]
        assert "full body content" in result["data"]["results"][0]["body"]

    def test_get_requires_id(self):
        result = _run(executor.execute({
            "action": "get",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert not result["ok"]
        assert "--id is required" in result["error"]

    def test_get_extracts_id_from_url(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(path=path)
            return {"_raw": {"id": "9999", "title": "T", "space": {"key": "ENG"}, "version": {"when": "now"}}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "get",
            "id": "https://x.atlassian.net/wiki/spaces/ENG/pages/9999/Title",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert result["ok"]
        assert "/9999" in captured["path"]

    def test_get_invalid_url(self, monkeypatch):
        result = _run(executor.execute({
            "action": "get",
            "id": "https://example.com/no/page/id/here",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert not result["ok"]
        assert "Cannot extract page ID" in result["error"]

    def test_list_by_label_requires_label(self):
        result = _run(executor.execute({
            "action": "list_by_label",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert not result["ok"]
        assert "--label is required" in result["error"]

    def test_recent_orders_by_lastmodified(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(params=params)
            return {"_raw": {"results": [], "totalSize": 0}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "recent",
            "space": "ENG",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert result["ok"]
        assert "ORDER BY lastmodified DESC" in captured["params"]["cql"]
        assert 'space = "ENG"' in captured["params"]["cql"]

    def test_http_error_returned_cleanly(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return executor._err("Confluence HTTP 401: unauthorized", provider="confluence")

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert not result["ok"]
        assert "401" in result["error"]


class TestStubProviders:
    def test_atlassian_docs_stub(self):
        result = _run(executor.execute({"action": "search", "query": "x", "provider": "atlassian_docs"}))
        assert not result["ok"]
        assert "atlassian_docs" in result["error"].lower()

    def test_notion_stub(self):
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "provider": "notion",
            "endpoint": "https://api.notion.com",
        }))
        assert not result["ok"]
        assert "notion" in result["error"].lower()

    def test_mkdocs_stub(self):
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "provider": "mkdocs",
            "endpoint": "http://docs.local",
        }))
        assert not result["ok"]
        assert "mkdocs" in result["error"].lower()


class TestResultShape:
    def test_success_shape(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return {"_raw": {"results": [], "totalSize": 0}}

        monkeypatch.setattr(executor.ConfluenceProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "search",
            "query": "x",
            "endpoint": "https://x.atlassian.net/wiki",
        }))
        assert set(result.keys()) >= {"ok", "data", "metadata", "warnings"}

    def test_failure_shape(self):
        result = _run(executor.execute({"action": "search"}))  # no endpoint, default atlassian_docs stub
        assert set(result.keys()) >= {"ok", "data", "metadata", "warnings", "error"}
