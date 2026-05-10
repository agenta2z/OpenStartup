"""log_query tool executor — vendor-neutral log backend dispatcher.

Implements the Atlassian sre-tool executor protocol. Returns dict directly
(no ToolExecutionResult wrapping — uniform with prometheus_query, grafana_manage,
alertmanager_query, opsgenie_manage).

Currently supported providers:
  - loki        (Grafana Loki / LogQL) — full
  - splunk      (Splunk SPL)           — stub (raises ProviderNotImplemented)
  - elasticsearch                       — stub (raises ProviderNotImplemented)
  - cloudwatch_logs                     — stub (raises ProviderNotImplemented)

Environment:
    LOG_QUERY_URL or LOKI_URL: Backend base URL.
    LOG_BACKEND:               Override provider auto-detection (loki/splunk/...).
    LOG_QUERY_USER / _PASSWORD or LOG_QUERY_BEARER_TOKEN: Auth.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=60, connect=10)
_DEFAULT_LIMIT = 100
_LOKI_HARD_LIMIT = 5000


# ---------------------------------------------------------------------------
# Generic helpers (provider-independent)
# ---------------------------------------------------------------------------


class ProviderNotImplemented(Exception):
    """Raised when an action targets a provider whose adapter is not yet shipped."""


def _ok(data: Any, metadata: dict | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "metadata": metadata or {}, "warnings": warnings or []}


def _err(message: str, *, provider: str | None = None, action: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": message, "data": None, "metadata": {}, "warnings": []}
    if provider:
        out["metadata"]["provider"] = provider
    if action:
        out["metadata"]["action"] = action
    return out


def _resolve_provider(arguments: dict[str, Any], endpoint: str) -> str:
    """Pick provider in priority order: explicit --provider > LOG_BACKEND env > endpoint URL hint > 'loki'."""
    if (p := arguments.get("provider")):
        return str(p).lower()
    if (p := os.environ.get("LOG_BACKEND")):
        return p.lower()
    # URL-based heuristic
    e = endpoint.lower()
    if "splunk" in e:
        return "splunk"
    if "elastic" in e or ":9200" in e:
        return "elasticsearch"
    if "logs.amazonaws" in e or "logs." in e and "amazonaws" in e:
        return "cloudwatch_logs"
    # Default
    return "loki"


def _resolve_endpoint(arguments: dict[str, Any]) -> str:
    return (
        arguments.get("endpoint")
        or os.environ.get("LOG_QUERY_URL")
        or os.environ.get("LOKI_URL")
        or ""
    )


def _parse_duration_seconds(s: str) -> float:
    """Parse '5m', '1h30m', '7d' → seconds. Raises ValueError for unknown format."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([smhdw])", s.strip().lower()):
        total += float(num) * units[unit]
    if total == 0:
        raise ValueError(f"Cannot parse duration: {s!r}")
    return total


def _parse_timestamp(ts: str | float | int | None) -> float:
    """Parse RFC3339 string or unix epoch (sec/ms/us/ns) to float seconds."""
    if ts is None:
        return time.time()
    if isinstance(ts, (int, float)):
        # Auto-detect ns/us/ms/s
        f = float(ts)
        if f > 1e15:  # ns
            return f / 1e9
        if f > 1e12:  # ms
            return f / 1e3
        return f
    s = str(ts).strip()
    # Plain numeric
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return _parse_timestamp(float(s))
    # RFC3339 / ISO 8601
    from datetime import datetime, timezone
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(timezone.utc).timestamp()


def _resolve_time_range(arguments: dict[str, Any]) -> tuple[float, float]:
    """Returns (start_epoch_sec, end_epoch_sec)."""
    end = _parse_timestamp(arguments.get("end")) if arguments.get("end") else time.time()
    if arguments.get("start"):
        start = _parse_timestamp(arguments.get("start"))
    elif arguments.get("since"):
        start = end - _parse_duration_seconds(arguments["since"])
    else:
        start = end - 3600  # default last 1h
    if start >= end:
        raise ValueError(f"start ({start}) must be < end ({end})")
    return start, end


def _select_step_seconds(start: float, end: float) -> int:
    """Auto-pick a reasonable step for query_range volume buckets."""
    span = end - start
    if span < 3600:
        return 15
    if span < 21600:
        return 60
    if span < 86400:
        return 300
    return 3600


def _get_auth_kwargs() -> dict:
    if (u := os.environ.get("LOG_QUERY_USER")) and (p := os.environ.get("LOG_QUERY_PASSWORD")):
        return {"auth": aiohttp.BasicAuth(u, p)}
    return {}


def _get_headers(arguments: dict[str, Any]) -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    if (t := arguments.get("tenant_id")):
        h["X-Scope-OrgID"] = t
    if (b := os.environ.get("LOG_QUERY_BEARER_TOKEN")):
        h["Authorization"] = f"Bearer {b}"
    return h


# ---------------------------------------------------------------------------
# LokiProvider — full implementation
# ---------------------------------------------------------------------------


class LokiProvider:
    """Adapter for Grafana Loki HTTP API v1.

    Reference: https://grafana.com/docs/loki/latest/reference/api/
    """

    def __init__(self, endpoint: str, headers: dict[str, str], session_kwargs: dict):
        self.endpoint = endpoint.rstrip("/")
        self.headers = headers
        self.session_kwargs = session_kwargs

    async def _request(self, session: aiohttp.ClientSession, path: str, params: dict | None = None) -> dict:
        url = f"{self.endpoint}{path}"
        try:
            async with session.get(url, params=params, headers=self.headers) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    return _err(
                        f"Loki HTTP {resp.status}: {text[:500]}",
                        provider="loki",
                    )
                try:
                    return {"_loki_raw": json.loads(text)}
                except json.JSONDecodeError:
                    return _err(f"Loki returned non-JSON: {text[:200]}", provider="loki")
        except aiohttp.ClientError as exc:
            return _err(f"Loki transport error: {exc}", provider="loki")

    @staticmethod
    def _normalize_streams(loki_data: dict) -> dict:
        """Normalize Loki's matrix/streams shape to vendor-neutral {streams: [...]}."""
        result_type = loki_data.get("resultType", "streams")
        result = loki_data.get("result", [])
        if result_type == "streams":
            streams = [
                {
                    "stream": s.get("stream", {}),
                    "values": [
                        [_to_iso(v[0]), v[1]]
                        for v in s.get("values", [])
                    ],
                }
                for s in result
            ]
            return {"streams": streams, "stats": loki_data.get("stats", {})}
        # matrix (metric query) — preserve as-is under "matrix"
        return {"matrix": result, "stats": loki_data.get("stats", {})}

    async def query(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        q = arguments.get("query")
        if not q:
            return _err("--query is required for query action", provider="loki", action="query")
        params: dict[str, Any] = {
            "query": q,
            "limit": str(min(int(arguments.get("limit") or _DEFAULT_LIMIT), _LOKI_HARD_LIMIT)),
            "direction": arguments.get("direction") or "backward",
        }
        if arguments.get("end") or arguments.get("start"):
            try:
                start, end = _resolve_time_range(arguments)
                params["start"] = str(int(start * 1e9))
                params["end"] = str(int(end * 1e9))
            except ValueError as e:
                return _err(str(e), provider="loki", action="query")
        raw = await self._request(session, "/loki/api/v1/query", params)
        if not raw.get("ok", True) and "_loki_raw" not in raw:
            return raw
        normalized = self._normalize_streams(raw["_loki_raw"].get("data", {}))
        return _ok(
            normalized,
            metadata={"provider": "loki", "action": "query", "endpoint": self.endpoint, "query": q},
        )

    async def query_range(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        q = arguments.get("query")
        if not q:
            return _err("--query is required for query_range", provider="loki", action="query_range")
        try:
            start, end = _resolve_time_range(arguments)
        except ValueError as e:
            return _err(str(e), provider="loki", action="query_range")
        params: dict[str, Any] = {
            "query": q,
            "start": str(int(start * 1e9)),
            "end": str(int(end * 1e9)),
            "limit": str(min(int(arguments.get("limit") or _DEFAULT_LIMIT), _LOKI_HARD_LIMIT)),
            "direction": arguments.get("direction") or "backward",
        }
        if arguments.get("step"):
            params["step"] = arguments["step"]
        raw = await self._request(session, "/loki/api/v1/query_range", params)
        if not raw.get("ok", True) and "_loki_raw" not in raw:
            return raw
        normalized = self._normalize_streams(raw["_loki_raw"].get("data", {}))
        warnings: list[str] = []
        # Truncation hint
        for stream in normalized.get("streams", []):
            if len(stream.get("values", [])) >= int(params["limit"]):
                warnings.append(f"Result truncated at limit={params['limit']}; consider narrower query or increase --limit")
                break
        return _ok(
            normalized,
            metadata={
                "provider": "loki",
                "action": "query_range",
                "endpoint": self.endpoint,
                "query": q,
                "time_range": {"start": start, "end": end, "duration_sec": end - start},
            },
            warnings=warnings,
        )

    async def labels(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        params: dict[str, Any] = {}
        if arguments.get("start") or arguments.get("since"):
            try:
                start, end = _resolve_time_range(arguments)
                params["start"] = str(int(start * 1e9))
                params["end"] = str(int(end * 1e9))
            except ValueError as e:
                return _err(str(e), provider="loki", action="labels")
        raw = await self._request(session, "/loki/api/v1/labels", params)
        if not raw.get("ok", True) and "_loki_raw" not in raw:
            return raw
        return _ok(
            {"labels": raw["_loki_raw"].get("data", [])},
            metadata={"provider": "loki", "action": "labels", "endpoint": self.endpoint},
        )

    async def label_values(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        label = arguments.get("label")
        if not label:
            return _err("--label is required for label_values", provider="loki", action="label_values")
        params: dict[str, Any] = {}
        if arguments.get("match"):
            params["query"] = arguments["match"]
        raw = await self._request(session, f"/loki/api/v1/label/{label}/values", params)
        if not raw.get("ok", True) and "_loki_raw" not in raw:
            return raw
        return _ok(
            {"values": raw["_loki_raw"].get("data", [])},
            metadata={"provider": "loki", "action": "label_values", "endpoint": self.endpoint, "label": label},
        )

    async def volume(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        q = arguments.get("query")
        if not q:
            return _err("--query is required for volume", provider="loki", action="volume")
        try:
            start, end = _resolve_time_range(arguments)
        except ValueError as e:
            return _err(str(e), provider="loki", action="volume")
        params: dict[str, Any] = {
            "query": q,
            "start": str(int(start * 1e9)),
            "end": str(int(end * 1e9)),
            "step": arguments.get("step") or f"{_select_step_seconds(start, end)}s",
        }
        raw = await self._request(session, "/loki/api/v1/index/volume_range", params)
        if not raw.get("ok", True) and "_loki_raw" not in raw:
            return raw
        return _ok(
            raw["_loki_raw"].get("data", {}),
            metadata={
                "provider": "loki",
                "action": "volume",
                "endpoint": self.endpoint,
                "query": q,
                "time_range": {"start": start, "end": end},
            },
        )

    async def tail(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        # Loki's tail endpoint is a websocket — not implemented in this MVP.
        return _err(
            "tail action is not yet implemented for the Loki provider. "
            "Use query_range with --since 1m instead, or run `logcli tail` from the CLI.",
            provider="loki",
            action="tail",
        )


def _to_iso(loki_ns: str | int) -> str:
    """Convert Loki's nanosecond timestamp string to RFC3339."""
    from datetime import datetime, timezone
    sec = int(str(loki_ns)) / 1e9
    return datetime.fromtimestamp(sec, tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Provider stubs (raise ProviderNotImplemented)
# ---------------------------------------------------------------------------


class _StubProvider:
    name = "stub"

    def __init__(self, endpoint: str, *_, **__):
        self.endpoint = endpoint

    async def _unsupported(self, *_, **__) -> dict:
        return _err(
            f"Provider '{self.name}' is declared but not yet implemented in this version of log_query. "
            f"Pull request welcome — see ARCHITECTURE.md.",
            provider=self.name,
        )

    query = query_range = labels = label_values = volume = tail = _unsupported


class SplunkProvider(_StubProvider):
    name = "splunk"


class ElasticsearchProvider(_StubProvider):
    name = "elasticsearch"


class CloudWatchLogsProvider(_StubProvider):
    name = "cloudwatch_logs"


# ---------------------------------------------------------------------------
# Provider registry + dispatch
# ---------------------------------------------------------------------------


_PROVIDERS = {
    "loki": LokiProvider,
    "splunk": SplunkProvider,
    "elasticsearch": ElasticsearchProvider,
    "cloudwatch_logs": CloudWatchLogsProvider,
}

_VALID_ACTIONS = {"query", "query_range", "tail", "labels", "label_values", "volume"}


async def execute(
    arguments: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Entry point for the log_query tool executor."""
    action = arguments.get("action")
    if not action:
        return _err("action parameter is required")
    if action not in _VALID_ACTIONS:
        return _err(f"Unknown action: {action!r}. Valid: {sorted(_VALID_ACTIONS)}")

    endpoint = _resolve_endpoint(arguments)
    if not endpoint:
        return _err(
            "Log backend endpoint not set. Pass --endpoint or set LOG_QUERY_URL / LOKI_URL.",
            action=action,
        )

    provider_name = _resolve_provider(arguments, endpoint)
    provider_cls = _PROVIDERS.get(provider_name)
    if not provider_cls:
        return _err(
            f"Unknown provider: {provider_name!r}. Valid: {sorted(_PROVIDERS)}",
            action=action,
        )

    headers = _get_headers(arguments)
    session_kwargs = {"timeout": _REQUEST_TIMEOUT, **_get_auth_kwargs()}

    # Dry-run
    if arguments.get("dry_run"):
        return _ok(
            {
                "action": action,
                "provider": provider_name,
                "endpoint": endpoint,
                "headers": {k: v for k, v in headers.items() if k.lower() != "authorization"},
                "arguments": {
                    k: v for k, v in arguments.items()
                    if k not in ("action", "dry_run", "endpoint")
                },
            },
            metadata={"action": action, "provider": provider_name, "dry_run": True},
        )

    provider = provider_cls(endpoint, headers, session_kwargs)
    handler = getattr(provider, action, None)
    if handler is None:
        return _err(f"Action {action!r} not implemented on {provider_name!r}", action=action)

    async with aiohttp.ClientSession(**session_kwargs) as session:
        try:
            return await handler(session, arguments)
        except Exception as exc:
            logger.exception("log_query.execute crashed in %s.%s", provider_name, action)
            return _err(f"Unexpected error: {exc!r}", provider=provider_name, action=action)
