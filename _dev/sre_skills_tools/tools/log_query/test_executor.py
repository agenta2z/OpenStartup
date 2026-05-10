"""Tests for log_query executor — fully mocked, no live backends needed.

Run: pytest tools/log_query/test_executor.py -v
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

# Ensure the tool dir is importable as a flat module
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import executor  # type: ignore  # noqa: E402


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


def _mock_loki_streams_response(payload: dict) -> dict:
    """Wrap a payload as if it came from Loki's /query or /query_range."""
    return {"_loki_raw": {"status": "success", "data": payload}}


# ---------------------------------------------------------------------------
# Tests for resolution helpers (provider/endpoint/time)
# ---------------------------------------------------------------------------


class TestResolveProvider:
    def test_explicit_provider_wins(self):
        assert executor._resolve_provider({"provider": "splunk"}, "http://loki:3100") == "splunk"

    def test_env_var_overrides_url_heuristic(self, monkeypatch):
        monkeypatch.setenv("LOG_BACKEND", "elasticsearch")
        assert executor._resolve_provider({}, "http://loki:3100") == "elasticsearch"

    def test_url_heuristic_splunk(self):
        assert executor._resolve_provider({}, "https://splunk.corp:8089") == "splunk"

    def test_url_heuristic_elasticsearch_by_port(self):
        assert executor._resolve_provider({}, "http://es-host:9200") == "elasticsearch"

    def test_default_loki(self):
        assert executor._resolve_provider({}, "http://loghost:3100") == "loki"


class TestResolveEndpoint:
    def test_explicit_wins(self, monkeypatch):
        monkeypatch.setenv("LOG_QUERY_URL", "http://env.url")
        assert executor._resolve_endpoint({"endpoint": "http://arg.url"}) == "http://arg.url"

    def test_log_query_url_takes_precedence_over_loki_url(self, monkeypatch):
        monkeypatch.setenv("LOG_QUERY_URL", "http://primary")
        monkeypatch.setenv("LOKI_URL", "http://fallback")
        assert executor._resolve_endpoint({}) == "http://primary"

    def test_loki_url_fallback(self, monkeypatch):
        monkeypatch.delenv("LOG_QUERY_URL", raising=False)
        monkeypatch.setenv("LOKI_URL", "http://fallback")
        assert executor._resolve_endpoint({}) == "http://fallback"

    def test_empty(self, monkeypatch):
        monkeypatch.delenv("LOG_QUERY_URL", raising=False)
        monkeypatch.delenv("LOKI_URL", raising=False)
        assert executor._resolve_endpoint({}) == ""


class TestParseDuration:
    def test_minutes(self):
        assert executor._parse_duration_seconds("5m") == 300

    def test_hours(self):
        assert executor._parse_duration_seconds("2h") == 7200

    def test_days(self):
        assert executor._parse_duration_seconds("1d") == 86400

    def test_compound(self):
        assert executor._parse_duration_seconds("1h30m") == 5400

    def test_invalid(self):
        with pytest.raises(ValueError):
            executor._parse_duration_seconds("not a duration")


class TestParseTimestamp:
    def test_unix_seconds(self):
        assert executor._parse_timestamp("1700000000") == 1700000000.0

    def test_unix_ms_auto(self):
        assert executor._parse_timestamp(1700000000000) == 1700000000.0

    def test_unix_ns_auto(self):
        assert executor._parse_timestamp(1700000000000000000) == 1700000000.0

    def test_rfc3339_z(self):
        # 2023-11-14T22:13:20Z → 1700000000
        assert executor._parse_timestamp("2023-11-14T22:13:20Z") == 1700000000.0


class TestResolveTimeRange:
    def test_explicit_start_end(self):
        s, e = executor._resolve_time_range({"start": "1700000000", "end": "1700003600"})
        assert s == 1700000000 and e == 1700003600

    def test_since_only(self):
        s, e = executor._resolve_time_range({"since": "1h"})
        assert (e - s) == 3600

    def test_default_last_hour(self):
        import time
        s, e = executor._resolve_time_range({})
        assert 3590 < (e - s) < 3610

    def test_inverted_raises(self):
        with pytest.raises(ValueError):
            executor._resolve_time_range({"start": "100", "end": "50"})


# ---------------------------------------------------------------------------
# Tests for execute() — top-level dispatch
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

    def test_no_endpoint(self, monkeypatch):
        monkeypatch.delenv("LOG_QUERY_URL", raising=False)
        monkeypatch.delenv("LOKI_URL", raising=False)
        result = _run(executor.execute({"action": "labels"}))
        assert not result["ok"]
        assert "endpoint not set" in result["error"]

    def test_unknown_provider(self):
        result = _run(executor.execute({
            "action": "labels",
            "endpoint": "http://x:3100",
            "provider": "made_up_provider",
        }))
        assert not result["ok"]
        assert "Unknown provider" in result["error"]

    def test_dry_run(self):
        result = _run(executor.execute({
            "action": "query",
            "query": '{job="x"}',
            "endpoint": "http://x:3100",
            "dry_run": True,
        }))
        assert result["ok"]
        assert result["data"]["action"] == "query"
        assert result["data"]["provider"] == "loki"
        assert result["data"]["arguments"]["query"] == '{job="x"}'
        # Authorization MUST NOT leak
        assert "authorization" not in {k.lower() for k in result["data"]["headers"]}


class TestExecuteStubProviders:
    """Splunk / ES / CWL providers should return _err with provider name."""

    def test_splunk_stub(self):
        result = _run(executor.execute({
            "action": "query",
            "query": "search foo",
            "provider": "splunk",
            "endpoint": "https://splunk:8089",
        }))
        assert not result["ok"]
        assert "splunk" in result["error"].lower()
        assert result["metadata"]["provider"] == "splunk"

    def test_elasticsearch_stub(self):
        result = _run(executor.execute({
            "action": "query",
            "query": "level:error",
            "provider": "elasticsearch",
            "endpoint": "http://es:9200",
        }))
        assert not result["ok"]
        assert "elasticsearch" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests for LokiProvider — mocked HTTP
# ---------------------------------------------------------------------------


class TestLokiProvider:
    """All Loki HTTP calls are intercepted via patch on _request."""

    def test_query_requires_query_param(self):
        result = _run(executor.execute({
            "action": "query",
            "endpoint": "http://loki:3100",
        }))
        assert not result["ok"]
        assert "--query is required" in result["error"]

    def test_query_range_requires_query_and_resolves_time(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(path=path, params=params)
            return {"_loki_raw": {"data": {"resultType": "streams", "result": []}}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "query_range",
            "query": '{job="api"} |= "error"',
            "since": "30m",
            "endpoint": "http://loki:3100",
        }))
        assert result["ok"]
        assert captured["path"] == "/loki/api/v1/query_range"
        assert captured["params"]["query"] == '{job="api"} |= "error"'
        assert captured["params"]["direction"] == "backward"
        # start/end converted to ns
        start_ns = int(captured["params"]["start"])
        end_ns = int(captured["params"]["end"])
        assert (end_ns - start_ns) // int(1e9) == 1800

    def test_query_range_normalizes_streams(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return {"_loki_raw": {"data": {
                "resultType": "streams",
                "result": [
                    {"stream": {"app": "x"}, "values": [["1700000000000000000", "log line A"]]}
                ],
            }}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "query_range",
            "query": '{app="x"}',
            "since": "5m",
            "endpoint": "http://loki:3100",
        }))
        assert result["ok"]
        streams = result["data"]["streams"]
        assert len(streams) == 1
        assert streams[0]["stream"] == {"app": "x"}
        assert streams[0]["values"][0][1] == "log line A"
        assert streams[0]["values"][0][0].startswith("2023-11-14T")

    def test_query_range_emits_truncation_warning_at_limit(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            limit = int(params["limit"])
            return {"_loki_raw": {"data": {
                "resultType": "streams",
                "result": [{
                    "stream": {"app": "y"},
                    "values": [[f"{1700000000 + i:d}000000000", f"line {i}"] for i in range(limit)],
                }],
            }}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "query_range",
            "query": "{app=\"y\"}",
            "since": "5m",
            "limit": 5,
            "endpoint": "http://loki:3100",
        }))
        assert result["ok"]
        assert any("truncated" in w.lower() for w in result["warnings"])

    def test_labels(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            assert path == "/loki/api/v1/labels"
            return {"_loki_raw": {"data": ["app", "env", "level"]}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "labels",
            "endpoint": "http://loki:3100",
        }))
        assert result["ok"]
        assert result["data"]["labels"] == ["app", "env", "level"]

    def test_label_values_requires_label(self):
        result = _run(executor.execute({
            "action": "label_values",
            "endpoint": "http://loki:3100",
        }))
        assert not result["ok"]
        assert "--label is required" in result["error"]

    def test_label_values_with_match(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(path=path, params=params)
            return {"_loki_raw": {"data": ["api-1", "api-2"]}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "label_values",
            "label": "instance",
            "match": '{job="api"}',
            "endpoint": "http://loki:3100",
        }))
        assert result["ok"]
        assert captured["path"] == "/loki/api/v1/label/instance/values"
        assert captured["params"]["query"] == '{job="api"}'
        assert result["data"]["values"] == ["api-1", "api-2"]

    def test_volume(self, monkeypatch):
        captured: dict = {}

        async def fake_request(self, session, path, params=None):
            captured.update(path=path, params=params)
            return {"_loki_raw": {"data": {"resultType": "matrix", "result": []}}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "volume",
            "query": '{app="x"}',
            "since": "1h",
            "endpoint": "http://loki:3100",
        }))
        assert result["ok"]
        assert captured["path"] == "/loki/api/v1/index/volume_range"
        assert "step" in captured["params"]

    def test_tail_returns_unsupported(self):
        # Loki tail is websocket; our MVP returns explicit error
        result = _run(executor.execute({
            "action": "tail",
            "query": '{app="x"}',
            "endpoint": "http://loki:3100",
        }))
        assert not result["ok"]
        assert "tail action is not yet implemented" in result["error"]

    def test_http_error_propagates_as_err(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return executor._err("Loki HTTP 503: backend overloaded", provider="loki")

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({
            "action": "labels",
            "endpoint": "http://loki:3100",
        }))
        assert not result["ok"]
        assert "503" in result["error"]


class TestExecuteHeaderHandling:
    def test_tenant_id_becomes_x_scope_orgid(self, monkeypatch):
        captured_headers: dict = {}

        # Record headers via initialiser interception
        orig_init = executor.LokiProvider.__init__

        def spy_init(self, endpoint, headers, session_kwargs):
            captured_headers.update(headers)
            orig_init(self, endpoint, headers, session_kwargs)

        async def fake_request(self, session, path, params=None):
            return {"_loki_raw": {"data": []}}

        monkeypatch.setattr(executor.LokiProvider, "__init__", spy_init)
        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        _run(executor.execute({
            "action": "labels",
            "endpoint": "http://loki:3100",
            "tenant_id": "team-a",
        }))
        assert captured_headers.get("X-Scope-OrgID") == "team-a"

    def test_bearer_token_added_from_env(self, monkeypatch):
        monkeypatch.setenv("LOG_QUERY_BEARER_TOKEN", "tok-123")
        captured: dict = {}

        orig_init = executor.LokiProvider.__init__

        def spy_init(self, endpoint, headers, session_kwargs):
            captured.update(headers)
            orig_init(self, endpoint, headers, session_kwargs)

        async def fake_request(self, session, path, params=None):
            return {"_loki_raw": {"data": []}}

        monkeypatch.setattr(executor.LokiProvider, "__init__", spy_init)
        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        _run(executor.execute({"action": "labels", "endpoint": "http://loki:3100"}))
        assert captured["Authorization"] == "Bearer tok-123"


class TestExecuteResultShape:
    """Top-level dict shape MUST be {ok, data, metadata, warnings, [error]} for every code path."""

    def test_success_shape(self, monkeypatch):
        async def fake_request(self, session, path, params=None):
            return {"_loki_raw": {"data": ["a"]}}

        monkeypatch.setattr(executor.LokiProvider, "_request", fake_request)
        result = _run(executor.execute({"action": "labels", "endpoint": "http://loki:3100"}))
        assert set(result.keys()) >= {"ok", "data", "metadata", "warnings"}

    def test_failure_shape(self):
        result = _run(executor.execute({"action": "query"}))  # no endpoint
        assert set(result.keys()) >= {"ok", "data", "metadata", "warnings", "error"}
