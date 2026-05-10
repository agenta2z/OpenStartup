"""Alertmanager tool executor — dispatches alertmanager_query actions to Prometheus Alertmanager HTTP API v2.

Implements the ToolExecutorCallable protocol for alert listing, alert group queries,
silence management, and status checks.

Environment:
    ALERTMANAGER_URL: Required. Alertmanager base URL (e.g. http://alertmanager:9093).
    ALERTMANAGER_USER: Optional. Basic auth username.
    ALERTMANAGER_PASSWORD: Optional. Basic auth password.
    ALERTMANAGER_BEARER_TOKEN: Optional. Bearer token for auth.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_API_BASE = "/api/v2"
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)

# Actions that require human confirmation
_CONFIRMATION_REQUIRED = {"create_silence"}

# Read-only actions (always autonomous)
_READ_ACTIONS = {"list_alerts", "list_alert_groups", "list_silences", "get_silence",
                 "get_status", "list_receivers"}


def _get_auth(session_kwargs: dict) -> None:
    """Configure authentication on session kwargs."""
    user = os.environ.get("ALERTMANAGER_USER", "")
    password = os.environ.get("ALERTMANAGER_PASSWORD", "")
    token = os.environ.get("ALERTMANAGER_BEARER_TOKEN", "")
    if user and password:
        session_kwargs["auth"] = aiohttp.BasicAuth(user, password)
    elif token:
        session_kwargs.setdefault("headers", {})["Authorization"] = f"Bearer {token}"


def _ok(data: Any, message: str = "Success", count: int | None = None) -> dict:
    result: dict[str, Any] = {"ok": True, "data": data, "message": message}
    if count is not None:
        result["count"] = count
    return result


def _err(message: str, data: Any = None) -> dict:
    return {"ok": False, "data": data, "message": message}


def _parse_filter(filter_str: str) -> list[str]:
    """Parse comma-separated matchers, preserving matcher syntax."""
    if not filter_str:
        return []
    # Split on comma but not within quotes
    matchers = []
    current = ""
    in_quotes = False
    for char in filter_str:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            if current.strip():
                matchers.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        matchers.append(current.strip())
    return matchers


# --- API Operation Functions ---

async def _list_alerts(session: aiohttp.ClientSession, base_url: str,
                       args: dict) -> dict:
    params: list[tuple[str, str]] = []

    # Boolean filters — Alertmanager defaults all to true
    for flag in ("active", "silenced", "inhibited", "unprocessed"):
        if args.get(flag) is not None:
            params.append((flag, str(args[flag]).lower()))
        no_flag = f"no_{flag}"
        if args.get(no_flag) or args.get(f"no-{flag}"):
            params.append((flag, "false"))

    # Label matchers
    if args.get("filter"):
        for matcher in _parse_filter(args["filter"]):
            params.append(("filter", matcher))

    # Receiver filter
    if args.get("receiver"):
        params.append(("receiver", args["receiver"]))

    async with session.get(f"{base_url}{_API_BASE}/alerts",
                           params=params) as resp:
        if resp.status == 200:
            alerts = await resp.json()
            limit = int(args.get("limit", 100))
            # Client-side limiting (Alertmanager has no server-side pagination)
            truncated = alerts[:limit]
            return _ok(truncated, f"Retrieved {len(truncated)} alerts (total: {len(alerts)})",
                       count=len(alerts))
        text = await resp.text()
        return _err(f"List alerts failed: {resp.status} — {text}")


async def _list_alert_groups(session: aiohttp.ClientSession, base_url: str,
                             args: dict) -> dict:
    params: list[tuple[str, str]] = []
    for flag in ("active", "silenced", "inhibited"):
        if args.get(flag) is not None:
            params.append((flag, str(args[flag]).lower()))
        no_flag = f"no_{flag}"
        if args.get(no_flag) or args.get(f"no-{flag}"):
            params.append((flag, "false"))

    if args.get("filter"):
        for matcher in _parse_filter(args["filter"]):
            params.append(("filter", matcher))

    if args.get("receiver"):
        params.append(("receiver", args["receiver"]))

    async with session.get(f"{base_url}{_API_BASE}/alerts/groups",
                           params=params) as resp:
        if resp.status == 200:
            groups = await resp.json()
            return _ok(groups, f"Retrieved {len(groups)} alert groups",
                       count=len(groups))
        text = await resp.text()
        return _err(f"List alert groups failed: {resp.status} — {text}")


async def _list_silences(session: aiohttp.ClientSession, base_url: str,
                         args: dict) -> dict:
    params: list[tuple[str, str]] = []
    if args.get("filter"):
        for matcher in _parse_filter(args["filter"]):
            params.append(("filter", matcher))

    async with session.get(f"{base_url}{_API_BASE}/silences",
                           params=params) as resp:
        if resp.status == 200:
            silences = await resp.json()
            # Filter to active silences by default
            limit = int(args.get("limit", 100))
            truncated = silences[:limit]
            return _ok(truncated, f"Retrieved {len(truncated)} silences (total: {len(silences)})",
                       count=len(silences))
        text = await resp.text()
        return _err(f"List silences failed: {resp.status} — {text}")


async def _get_silence(session: aiohttp.ClientSession, base_url: str,
                       args: dict) -> dict:
    silence_id = args.get("silence_id")
    if not silence_id:
        return _err("--silence_id is required for get_silence")

    async with session.get(f"{base_url}{_API_BASE}/silence/{silence_id}") as resp:
        if resp.status == 200:
            silence = await resp.json()
            return _ok(silence, "Silence retrieved")
        text = await resp.text()
        return _err(f"Get silence failed: {resp.status} — {text}")


async def _create_silence(session: aiohttp.ClientSession, base_url: str,
                          args: dict) -> dict:
    if not args.get("matchers"):
        return _err("--matchers is required for create_silence (JSON array of matcher objects)")
    if not args.get("ends_at"):
        return _err("--ends_at is required for create_silence (ISO 8601 datetime)")
    if not args.get("comment"):
        return _err("--comment is required for create_silence")

    try:
        matchers = json.loads(args["matchers"])
        if not isinstance(matchers, list):
            return _err("--matchers must be a JSON array")
    except json.JSONDecodeError as exc:
        return _err(f"--matchers is not valid JSON: {exc}")

    # Validate matcher structure
    for i, m in enumerate(matchers):
        if not isinstance(m, dict) or "name" not in m or "value" not in m:
            return _err(f"Matcher {i} must have 'name' and 'value' fields")
        m.setdefault("isRegex", False)
        m.setdefault("isEqual", True)

    body = {
        "matchers": matchers,
        "startsAt": args.get("starts_at", ""),  # Empty = server uses now
        "endsAt": args["ends_at"],
        "createdBy": args.get("created_by", "ai-sre"),
        "comment": args["comment"],
    }
    # Remove empty startsAt so server defaults to now
    if not body["startsAt"]:
        import datetime
        body["startsAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    async with session.post(f"{base_url}{_API_BASE}/silences",
                            json=body,
                            headers={"Content-Type": "application/json"}) as resp:
        if resp.status == 200:
            data = await resp.json()
            return _ok(data, f"Silence created: {data.get('silenceID', 'unknown')}")
        text = await resp.text()
        return _err(f"Create silence failed: {resp.status} — {text}")


async def _expire_silence(session: aiohttp.ClientSession, base_url: str,
                          args: dict) -> dict:
    silence_id = args.get("silence_id")
    if not silence_id:
        return _err("--silence_id is required for expire_silence")

    async with session.delete(f"{base_url}{_API_BASE}/silence/{silence_id}") as resp:
        if resp.status == 200:
            return _ok({"silence_id": silence_id}, "Silence expired")
        text = await resp.text()
        return _err(f"Expire silence failed: {resp.status} — {text}")


async def _get_status(session: aiohttp.ClientSession, base_url: str,
                      args: dict) -> dict:
    async with session.get(f"{base_url}{_API_BASE}/status") as resp:
        if resp.status == 200:
            status = await resp.json()
            return _ok(status, "Alertmanager status retrieved")
        text = await resp.text()
        return _err(f"Get status failed: {resp.status} — {text}")


async def _list_receivers(session: aiohttp.ClientSession, base_url: str,
                          args: dict) -> dict:
    async with session.get(f"{base_url}{_API_BASE}/receivers") as resp:
        if resp.status == 200:
            receivers = await resp.json()
            return _ok(receivers, f"Retrieved {len(receivers)} receivers",
                       count=len(receivers))
        text = await resp.text()
        return _err(f"List receivers failed: {resp.status} — {text}")


# --- Dispatch ---

_ACTION_DISPATCH = {
    "list_alerts": _list_alerts,
    "list_alert_groups": _list_alert_groups,
    "list_silences": _list_silences,
    "get_silence": _get_silence,
    "create_silence": _create_silence,
    "expire_silence": _expire_silence,
    "get_status": _get_status,
    "list_receivers": _list_receivers,
}


async def execute(
    arguments: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Entry point for the alertmanager_query tool executor."""
    action = arguments.get("action")
    if not action:
        return _err("action parameter is required")

    if action not in _ACTION_DISPATCH:
        return _err(
                f"Unknown action: {action}. Valid: {sorted(_ACTION_DISPATCH.keys())}"
            )

    # Resolve base URL
    am_url = arguments.get("alertmanager_url") or os.environ.get("ALERTMANAGER_URL", "")
    if not am_url:
        return _err(
                "ALERTMANAGER_URL environment variable is not set and --alertmanager_url not provided"
            )
    # Strip trailing slash
    am_url = am_url.rstrip("/")

    # Dry-run mode
    if arguments.get("dry_run"):
        return _ok(
            {"action": action, "base_url": am_url, "arguments": {
                k: v for k, v in arguments.items()
                if k not in ("action", "dry_run", "alertmanager_url")
            }},
            f"Dry run: would execute {action}",
        )

    # Configure session
    session_kwargs: dict[str, Any] = {"timeout": _REQUEST_TIMEOUT}
    _get_auth(session_kwargs)

    handler = _ACTION_DISPATCH[action]
    try:
        async with aiohttp.ClientSession(**session_kwargs) as session:
            result = await handler(session, am_url, arguments)
    except aiohttp.ClientError as exc:
        result = _err(f"HTTP error: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error in alertmanager_query")
        result = _err(f"Unexpected error: {exc}")

    return result
