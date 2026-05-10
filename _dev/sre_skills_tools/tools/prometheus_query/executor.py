"""
Executor for prometheus_query tool.

Provides Prometheus/Mimir HTTP API integration for instant queries, range queries,
series discovery, label exploration, and metadata retrieval with multi-tenant support.
"""

import os
import json
import logging
import urllib.parse
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Auto-step selection based on time range duration
STEP_SELECTION = [
    (3600, "15s"),       # <1h -> 15s step
    (21600, "1m"),       # <6h -> 1m step
    (86400, "5m"),       # <24h -> 5m step
    (float("inf"), "1h") # >24h -> 1h step
]

# Maximum data points threshold before requiring human confirmation
MAX_AUTO_DATA_POINTS = 1_000_000
MAX_HARD_DATA_POINTS = 10_000_000


def _select_step(start_epoch: float, end_epoch: float) -> str:
    """Auto-select query step based on time range duration."""
    duration = end_epoch - start_epoch
    for threshold, step in STEP_SELECTION:
        if duration < threshold:
            return step
    return "1h"


def _parse_duration_seconds(duration_str: str) -> float:
    """Parse a Prometheus duration string (e.g., '15s', '1m', '5m', '1h') to seconds."""
    unit_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if not duration_str:
        return 60.0
    unit = duration_str[-1]
    if unit in unit_map:
        return float(duration_str[:-1]) * unit_map[unit]
    return float(duration_str)


def _parse_timestamp(ts_str: str) -> float:
    """Parse RFC3339 or Unix timestamp string to epoch float."""
    if not ts_str:
        import time
        return time.time()
    try:
        return float(ts_str)
    except ValueError:
        from datetime import datetime, timezone
        # Handle RFC3339 format
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        return dt.replace(tzinfo=timezone.utc if dt.tzinfo is None else dt.tzinfo).timestamp()


def _build_headers(tenant_id: str | None = None) -> dict[str, str]:
    """Build HTTP headers including auth and tenant ID."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # Auth token from environment
    auth_token = os.environ.get("PROMETHEUS_AUTH_TOKEN") or os.environ.get("MIMIR_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # ASAP/SLAuth token fallback
    asap_token = os.environ.get("ASAP_TOKEN")
    if asap_token and "Authorization" not in headers:
        headers["Authorization"] = asap_token

    # Multi-tenant header for Mimir
    if tenant_id:
        headers["X-Scope-OrgID"] = tenant_id

    return headers


async def _make_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make HTTP request to Prometheus/Mimir API and parse response envelope."""
    try:
        async with session.request(method, url, headers=headers, params=params, data=data) as resp:
            if resp.content_type == "application/json":
                body = await resp.json()
            else:
                text = await resp.text()
                return {
                    "status": "error",
                    "errorType": "non_json_response",
                    "error": f"HTTP {resp.status}: {text[:500]}",
                }

            # Surface warnings/infos from the Prometheus envelope
            result = {"status": body.get("status", "error")}
            if "data" in body:
                result["data"] = body["data"]
            if "error" in body:
                result["error"] = body["error"]
            if "errorType" in body:
                result["errorType"] = body["errorType"]
            if "warnings" in body:
                result["warnings"] = body["warnings"]
            if "infos" in body:
                result["infos"] = body["infos"]

            return result
    except aiohttp.ClientError as e:
        return {"status": "error", "errorType": "connection_error", "error": str(e)}


async def execute(arguments: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Main executor entry point for prometheus_query tool."""
    action = arguments.get("action")
    endpoint = arguments.get("endpoint") or os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
    tenant_id = arguments.get("tenant_id")
    headers = _build_headers(tenant_id)

    # Validate cross-tenant queries require confirmation
    if tenant_id and "|" in tenant_id:
        tenant_count = len(tenant_id.split("|"))
        if tenant_count > 2:
            return {
                "status": "confirmation_required",
                "message": f"Cross-tenant query across {tenant_count} tenants may have performance implications. Confirm to proceed.",
                "tenant_ids": tenant_id.split("|"),
            }

    base_url = endpoint.rstrip("/")

    async with aiohttp.ClientSession() as session:

        # --- Instant Query ---
        if action == "instant_query":
            query = arguments.get("query")
            if not query:
                return {"status": "error", "errorType": "missing_parameter", "error": "Parameter 'query' is required for instant_query."}

            params = {"query": query}
            if arguments.get("time"):
                params["time"] = arguments["time"]
            if arguments.get("timeout"):
                params["timeout"] = arguments["timeout"]
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])
            if arguments.get("stats"):
                params["stats"] = "all"

            url = f"{base_url}/api/v1/query"
            # Use POST for long queries to avoid URL length limits
            if len(query) > 500:
                return await _make_request(session, "POST", url, headers, data=params)
            return await _make_request(session, "GET", url, headers, params=params)

        # --- Range Query ---
        elif action == "range_query":
            query = arguments.get("query")
            start = arguments.get("start")
            end = arguments.get("end")
            if not query:
                return {"status": "error", "errorType": "missing_parameter", "error": "Parameter 'query' is required for range_query."}
            if not start or not end:
                return {"status": "error", "errorType": "missing_parameter", "error": "Parameters 'start' and 'end' are required for range_query."}

            start_epoch = _parse_timestamp(start)
            end_epoch = _parse_timestamp(end)

            # Auto-select step if not provided
            step = arguments.get("step") or _select_step(start_epoch, end_epoch)

            # Safety guardrail: estimate data points
            step_seconds = _parse_duration_seconds(step)
            if step_seconds > 0:
                estimated_points = (end_epoch - start_epoch) / step_seconds
                if estimated_points > MAX_HARD_DATA_POINTS:
                    return {
                        "status": "error",
                        "errorType": "safety_limit",
                        "error": f"Estimated {estimated_points:.0f} data points per series exceeds safety limit of {MAX_HARD_DATA_POINTS}. Use a larger step size or narrower time range.",
                    }
                if estimated_points > MAX_AUTO_DATA_POINTS:
                    return {
                        "status": "confirmation_required",
                        "message": f"Range query may return ~{estimated_points:.0f} data points per series. Confirm to proceed or use a larger step.",
                        "suggested_step": _select_step(start_epoch, end_epoch),
                    }

            params = {"query": query, "start": start, "end": end, "step": step}
            if arguments.get("timeout"):
                params["timeout"] = arguments["timeout"]
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])
            if arguments.get("stats"):
                params["stats"] = "all"

            url = f"{base_url}/api/v1/query_range"
            if len(query) > 500:
                return await _make_request(session, "POST", url, headers, data=params)
            return await _make_request(session, "GET", url, headers, params=params)

        # --- Series Discovery ---
        elif action == "list_series":
            match_selector = arguments.get("match")
            if not match_selector:
                return {"status": "error", "errorType": "missing_parameter", "error": "Parameter 'match' is required for list_series."}

            params = {"match[]": match_selector}
            if arguments.get("start"):
                params["start"] = arguments["start"]
            if arguments.get("end"):
                params["end"] = arguments["end"]
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])

            url = f"{base_url}/api/v1/series"
            return await _make_request(session, "GET", url, headers, params=params)

        # --- Label Names ---
        elif action == "label_names":
            params = {}
            if arguments.get("match"):
                params["match[]"] = arguments["match"]
            if arguments.get("start"):
                params["start"] = arguments["start"]
            if arguments.get("end"):
                params["end"] = arguments["end"]
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])

            url = f"{base_url}/api/v1/labels"
            return await _make_request(session, "GET", url, headers, params=params)

        # --- Label Values ---
        elif action == "label_values":
            label_name = arguments.get("label_name")
            if not label_name:
                return {"status": "error", "errorType": "missing_parameter", "error": "Parameter 'label_name' is required for label_values."}

            label_encoded = urllib.parse.quote(label_name, safe="")
            params = {}
            if arguments.get("match"):
                params["match[]"] = arguments["match"]
            if arguments.get("start"):
                params["start"] = arguments["start"]
            if arguments.get("end"):
                params["end"] = arguments["end"]
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])

            url = f"{base_url}/api/v1/label/{label_encoded}/values"
            return await _make_request(session, "GET", url, headers, params=params)

        # --- Metadata ---
        elif action == "metadata":
            params = {}
            if arguments.get("metric_name"):
                params["metric"] = arguments["metric_name"]
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])

            url = f"{base_url}/api/v1/metadata"
            return await _make_request(session, "GET", url, headers, params=params)

        # --- Targets ---
        elif action == "targets":
            url = f"{base_url}/api/v1/targets"
            return await _make_request(session, "GET", url, headers)

        # --- Rules ---
        elif action == "rules":
            url = f"{base_url}/api/v1/rules"
            return await _make_request(session, "GET", url, headers)

        # --- Alerts ---
        elif action == "alerts":
            url = f"{base_url}/api/v1/alerts"
            return await _make_request(session, "GET", url, headers)

        else:
            return {
                "status": "error",
                "errorType": "invalid_action",
                "error": f"Unknown action: {action}. Valid actions: instant_query, range_query, list_series, label_names, label_values, metadata, targets, rules, alerts",
            }
