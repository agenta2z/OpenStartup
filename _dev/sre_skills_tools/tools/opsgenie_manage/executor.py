"""Opsgenie tool executor — dispatches opsgenie_manage actions to Opsgenie REST API v2.

Implements the ToolExecutorCallable protocol for all Opsgenie alert, incident,
schedule, and escalation operations. Uses GenieKey authentication.

Environment:
    OPSGENIE_API_KEY: Required. Opsgenie API key (GenieKey).
    OPSGENIE_REGION: Optional. 'us' (default) or 'eu'.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

# --- Configuration ---

_BASE_URLS = {
    "us": "https://api.opsgenie.com",
    "eu": "https://api.eu.opsgenie.com",
}

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)

# Actions that require human confirmation (write operations with significant impact)
_CONFIRMATION_REQUIRED_ACTIONS = {
    "create_alert", "close_alert", "close_incident", "resolve_incident",
    "delete_alert", "update_priority", "snooze_alert",
}

# Read-only actions (always autonomous)
_READ_ACTIONS = {
    "get_alert", "list_alerts", "count_alerts", "get_incident", "list_incidents",
    "get_on_call", "list_schedules", "get_escalation_policy", "list_escalation_policies",
}

# Metadata-only write actions (autonomous at L3)
_METADATA_ACTIONS = {
    "acknowledge_alert", "unacknowledge_alert", "add_note", "add_tags",
    "escalate_alert", "assign_alert", "add_responder", "add_timeline_entry",
    "create_incident",
}


def _get_base_url(region: str = "us") -> str:
    return _BASE_URLS.get(region, _BASE_URLS["us"])


def _get_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"GenieKey {api_key}",
        "Content-Type": "application/json",
    }


def _parse_responders(responders_str: str) -> list[dict[str, str]]:
    """Parse comma-separated responder strings like 'team:SRE,user:jdoe'."""
    result = []
    if not responders_str:
        return result
    for item in responders_str.split(","):
        item = item.strip()
        if ":" not in item:
            continue
        resp_type, resp_id = item.split(":", 1)
        resp_type = resp_type.strip().lower()
        resp_id = resp_id.strip()
        if resp_type in ("team", "user", "escalation", "schedule"):
            # Use 'name' for string identifiers, 'id' for UUID-like values
            id_field = "id" if len(resp_id) > 20 and "-" in resp_id else "name"
            if resp_type == "user":
                id_field = "username" if "@" in resp_id else "id"
            result.append({"type": resp_type, id_field: resp_id})
    return result


def _parse_tags(tags_str: str) -> list[str]:
    """Parse comma-separated tags."""
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()][:20]


def _ok(data: Any, message: str = "Success", request_id: str = "") -> dict:
    return {"ok": True, "request_id": request_id, "data": data, "message": message}


def _err(message: str, data: Any = None) -> dict:
    return {"ok": False, "request_id": "", "data": data, "message": message}


# --- API Operation Functions ---

async def _create_alert(session: aiohttp.ClientSession, base_url: str,
                        headers: dict, args: dict) -> dict:
    message = args.get("message")
    if not message:
        return _err("--message is required for create_alert")

    body: dict[str, Any] = {"message": message[:130]}
    if args.get("alias"):
        body["alias"] = args["alias"][:512]
    if args.get("description"):
        body["description"] = args["description"][:15000]
    if args.get("priority"):
        body["priority"] = args["priority"]
    if args.get("responders"):
        body["responders"] = _parse_responders(args["responders"])
    if args.get("tags"):
        body["tags"] = _parse_tags(args["tags"])
    if args.get("entity"):
        body["entity"] = args["entity"][:512]
    if args.get("source"):
        body["source"] = args["source"][:100]
    else:
        body["source"] = "ai-sre"
    if args.get("note"):
        body["note"] = args["note"][:25000]
    if args.get("user"):
        body["user"] = args["user"][:100]
    if args.get("details"):
        try:
            body["details"] = json.loads(args["details"])
        except json.JSONDecodeError:
            return _err("--details must be a valid JSON string")

    async with session.post(f"{base_url}/v2/alerts", headers=headers,
                            json=body) as resp:
        data = await resp.json()
        if resp.status in (200, 201, 202):
            return _ok(data, "Alert creation request accepted",
                       data.get("requestId", ""))
        return _err(f"Create alert failed: {resp.status}", data)


async def _get_alert(session: aiohttp.ClientSession, base_url: str,
                     headers: dict, args: dict) -> dict:
    alert_id = args.get("alert_id")
    if not alert_id:
        return _err("--alert_id is required for get_alert")

    id_type = args.get("identifier_type", "id")
    params = {"identifierType": id_type}
    async with session.get(f"{base_url}/v2/alerts/{alert_id}",
                           headers=headers, params=params) as resp:
        data = await resp.json()
        if resp.status == 200:
            return _ok(data.get("data", data), "Alert retrieved")
        return _err(f"Get alert failed: {resp.status}", data)


async def _list_alerts(session: aiohttp.ClientSession, base_url: str,
                       headers: dict, args: dict) -> dict:
    params: dict[str, Any] = {
        "limit": min(int(args.get("limit", 20)), 100),
        "offset": int(args.get("offset", 0)),
        "sort": args.get("sort", "createdAt"),
        "order": args.get("order", "desc"),
    }
    if args.get("query"):
        params["query"] = args["query"]

    async with session.get(f"{base_url}/v2/alerts", headers=headers,
                           params=params) as resp:
        data = await resp.json()
        if resp.status == 200:
            alerts = data.get("data", [])
            return _ok(alerts, f"Retrieved {len(alerts)} alerts")
        return _err(f"List alerts failed: {resp.status}", data)


async def _count_alerts(session: aiohttp.ClientSession, base_url: str,
                        headers: dict, args: dict) -> dict:
    params: dict[str, Any] = {}
    if args.get("query"):
        params["query"] = args["query"]

    async with session.get(f"{base_url}/v2/alerts/count", headers=headers,
                           params=params) as resp:
        data = await resp.json()
        if resp.status == 200:
            return _ok(data.get("data", data), "Alert count retrieved")
        return _err(f"Count alerts failed: {resp.status}", data)


async def _alert_action(session: aiohttp.ClientSession, base_url: str,
                        headers: dict, args: dict, action: str) -> dict:
    """Generic alert action (acknowledge, close, snooze, unacknowledge, escalate, assign)."""
    alert_id = args.get("alert_id")
    if not alert_id:
        return _err(f"--alert_id is required for {action}")

    id_type = args.get("identifier_type", "id")
    params = {"identifierType": id_type}

    body: dict[str, Any] = {}
    if args.get("note"):
        body["note"] = args["note"][:25000]
    if args.get("user"):
        body["user"] = args["user"][:100]
    if args.get("source"):
        body["source"] = args["source"][:100]
    else:
        body["source"] = "ai-sre"

    # Action-specific fields
    if action == "snooze":
        if not args.get("snooze_until"):
            return _err("--snooze_until is required for snooze_alert")
        body["endTime"] = args["snooze_until"]
    elif action == "assign":
        if not args.get("assignee"):
            return _err("--assignee is required for assign_alert")
        body["owner"] = {"username": args["assignee"]}
    elif action == "escalate":
        if not args.get("escalation_id"):
            return _err("--escalation_id is required for escalate_alert")
        body["escalation"] = {"id": args["escalation_id"]}
    elif action == "update_priority":
        if not args.get("priority"):
            return _err("--priority is required for update_priority")
        # Priority update uses a custom action endpoint
        pass

    # Map action names to API paths
    action_path_map = {
        "acknowledge": "acknowledge",
        "close": "close",
        "snooze": "snooze",
        "unacknowledge": "unacknowledge",
        "escalate": "escalate",
        "assign": "assign",
    }
    api_action = action_path_map.get(action, action)

    async with session.post(
        f"{base_url}/v2/alerts/{alert_id}/{api_action}",
        headers=headers, params=params, json=body
    ) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, f"Alert {action} request accepted",
                       data.get("requestId", ""))
        return _err(f"Alert {action} failed: {resp.status}", data)


async def _add_note(session: aiohttp.ClientSession, base_url: str,
                    headers: dict, args: dict) -> dict:
    alert_id = args.get("alert_id")
    if not alert_id:
        return _err("--alert_id is required for add_note")
    if not args.get("note"):
        return _err("--note is required for add_note")

    id_type = args.get("identifier_type", "id")
    params = {"identifierType": id_type}
    body = {
        "note": args["note"][:25000],
        "user": args.get("user", "ai-sre"),
        "source": args.get("source", "ai-sre"),
    }

    async with session.post(f"{base_url}/v2/alerts/{alert_id}/notes",
                            headers=headers, params=params, json=body) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, "Note added", data.get("requestId", ""))
        return _err(f"Add note failed: {resp.status}", data)


async def _add_tags(session: aiohttp.ClientSession, base_url: str,
                    headers: dict, args: dict) -> dict:
    alert_id = args.get("alert_id")
    if not alert_id:
        return _err("--alert_id is required for add_tags")
    if not args.get("tags"):
        return _err("--tags is required for add_tags")

    id_type = args.get("identifier_type", "id")
    params = {"identifierType": id_type}
    body = {
        "tags": _parse_tags(args["tags"]),
        "user": args.get("user", "ai-sre"),
        "source": args.get("source", "ai-sre"),
    }

    async with session.post(f"{base_url}/v2/alerts/{alert_id}/tags",
                            headers=headers, params=params, json=body) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, "Tags added", data.get("requestId", ""))
        return _err(f"Add tags failed: {resp.status}", data)


async def _update_priority(session: aiohttp.ClientSession, base_url: str,
                           headers: dict, args: dict) -> dict:
    alert_id = args.get("alert_id")
    if not alert_id:
        return _err("--alert_id is required for update_priority")
    if not args.get("priority"):
        return _err("--priority is required for update_priority")

    id_type = args.get("identifier_type", "id")
    params = {"identifierType": id_type}

    # Opsgenie uses a custom action for priority updates
    body = {"priority": args["priority"]}

    async with session.put(f"{base_url}/v2/alerts/{alert_id}/priority",
                           headers=headers, params=params, json=body) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, f"Priority updated to {args['priority']}",
                       data.get("requestId", ""))
        return _err(f"Update priority failed: {resp.status}", data)


# --- Incident Operations ---

async def _create_incident(session: aiohttp.ClientSession, base_url: str,
                           headers: dict, args: dict) -> dict:
    message = args.get("message")
    if not message:
        return _err("--message is required for create_incident")

    body: dict[str, Any] = {
        "message": message[:500],
        "priority": args.get("priority", "P3"),
    }
    if args.get("description"):
        body["description"] = args["description"][:15000]
    if args.get("service_name"):
        body["impactedServices"] = [args["service_name"]]
    if args.get("tags"):
        body["tags"] = _parse_tags(args["tags"])
    if args.get("details"):
        try:
            body["details"] = json.loads(args["details"])
        except json.JSONDecodeError:
            return _err("--details must be a valid JSON string")
    if args.get("note"):
        body["note"] = args["note"][:25000]
    if args.get("responders"):
        body["responders"] = _parse_responders(args["responders"])

    async with session.post(f"{base_url}/v1/incidents/create",
                            headers=headers, json=body) as resp:
        data = await resp.json()
        if resp.status in (200, 201, 202):
            return _ok(data, "Incident creation request accepted",
                       data.get("requestId", ""))
        return _err(f"Create incident failed: {resp.status}", data)


async def _get_incident(session: aiohttp.ClientSession, base_url: str,
                        headers: dict, args: dict) -> dict:
    incident_id = args.get("incident_id")
    if not incident_id:
        return _err("--incident_id is required for get_incident")

    async with session.get(f"{base_url}/v1/incidents/{incident_id}",
                           headers=headers) as resp:
        data = await resp.json()
        if resp.status == 200:
            return _ok(data.get("data", data), "Incident retrieved")
        return _err(f"Get incident failed: {resp.status}", data)


async def _list_incidents(session: aiohttp.ClientSession, base_url: str,
                          headers: dict, args: dict) -> dict:
    params: dict[str, Any] = {
        "limit": min(int(args.get("limit", 20)), 100),
        "offset": int(args.get("offset", 0)),
        "sort": args.get("sort", "createdAt"),
        "order": args.get("order", "desc"),
    }
    if args.get("query"):
        params["query"] = args["query"]

    async with session.get(f"{base_url}/v1/incidents",
                           headers=headers, params=params) as resp:
        data = await resp.json()
        if resp.status == 200:
            incidents = data.get("data", [])
            return _ok(incidents, f"Retrieved {len(incidents)} incidents")
        return _err(f"List incidents failed: {resp.status}", data)


async def _close_incident(session: aiohttp.ClientSession, base_url: str,
                          headers: dict, args: dict) -> dict:
    incident_id = args.get("incident_id")
    if not incident_id:
        return _err("--incident_id is required for close_incident/resolve_incident")

    body: dict[str, Any] = {}
    if args.get("note"):
        body["note"] = args["note"][:25000]

    async with session.post(f"{base_url}/v1/incidents/{incident_id}/close",
                            headers=headers, json=body) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, "Incident close request accepted",
                       data.get("requestId", ""))
        return _err(f"Close incident failed: {resp.status}", data)


async def _add_responder(session: aiohttp.ClientSession, base_url: str,
                         headers: dict, args: dict) -> dict:
    incident_id = args.get("incident_id")
    if not incident_id:
        return _err("--incident_id is required for add_responder")
    if not args.get("responders"):
        return _err("--responders is required for add_responder")

    body = {
        "responders": _parse_responders(args["responders"]),
        "message": args.get("note", "Responder added by AI SRE"),
    }

    async with session.post(
        f"{base_url}/v1/incidents/{incident_id}/responders",
        headers=headers, json=body
    ) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, "Responder added", data.get("requestId", ""))
        return _err(f"Add responder failed: {resp.status}", data)


async def _add_timeline_entry(session: aiohttp.ClientSession, base_url: str,
                              headers: dict, args: dict) -> dict:
    incident_id = args.get("incident_id")
    if not incident_id:
        return _err("--incident_id is required for add_timeline_entry")
    if not args.get("timeline_entry"):
        return _err("--timeline_entry is required for add_timeline_entry")

    body = {"note": args["timeline_entry"]}

    async with session.post(
        f"{base_url}/v1/incidents/{incident_id}/timeline",
        headers=headers, json=body
    ) as resp:
        data = await resp.json()
        if resp.status in (200, 202):
            return _ok(data, "Timeline entry added")
        return _err(f"Add timeline entry failed: {resp.status}", data)


# --- Schedule & Escalation Operations ---

async def _get_on_call(session: aiohttp.ClientSession, base_url: str,
                       headers: dict, args: dict) -> dict:
    schedule_id = args.get("schedule_id")
    if not schedule_id:
        return _err("--schedule_id is required for get_on_call")

    async with session.get(
        f"{base_url}/v2/schedules/{schedule_id}/on-calls",
        headers=headers
    ) as resp:
        data = await resp.json()
        if resp.status == 200:
            return _ok(data.get("data", data), "On-call data retrieved")
        return _err(f"Get on-call failed: {resp.status}", data)


async def _list_schedules(session: aiohttp.ClientSession, base_url: str,
                          headers: dict, args: dict) -> dict:
    async with session.get(f"{base_url}/v2/schedules", headers=headers) as resp:
        data = await resp.json()
        if resp.status == 200:
            schedules = data.get("data", [])
            return _ok(schedules, f"Retrieved {len(schedules)} schedules")
        return _err(f"List schedules failed: {resp.status}", data)


async def _get_escalation_policy(session: aiohttp.ClientSession, base_url: str,
                                 headers: dict, args: dict) -> dict:
    esc_id = args.get("escalation_id")
    if not esc_id:
        return _err("--escalation_id is required for get_escalation_policy")

    async with session.get(f"{base_url}/v2/escalations/{esc_id}",
                           headers=headers) as resp:
        data = await resp.json()
        if resp.status == 200:
            return _ok(data.get("data", data), "Escalation policy retrieved")
        return _err(f"Get escalation policy failed: {resp.status}", data)


async def _list_escalation_policies(session: aiohttp.ClientSession, base_url: str,
                                    headers: dict, args: dict) -> dict:
    async with session.get(f"{base_url}/v2/escalations", headers=headers) as resp:
        data = await resp.json()
        if resp.status == 200:
            policies = data.get("data", [])
            return _ok(policies, f"Retrieved {len(policies)} escalation policies")
        return _err(f"List escalation policies failed: {resp.status}", data)


# --- Dispatch ---

_ACTION_DISPATCH = {
    "create_alert": _create_alert,
    "get_alert": _get_alert,
    "list_alerts": _list_alerts,
    "count_alerts": _count_alerts,
    "acknowledge_alert": lambda s, b, h, a: _alert_action(s, b, h, a, "acknowledge"),
    "close_alert": lambda s, b, h, a: _alert_action(s, b, h, a, "close"),
    "snooze_alert": lambda s, b, h, a: _alert_action(s, b, h, a, "snooze"),
    "unacknowledge_alert": lambda s, b, h, a: _alert_action(s, b, h, a, "unacknowledge"),
    "escalate_alert": lambda s, b, h, a: _alert_action(s, b, h, a, "escalate"),
    "assign_alert": lambda s, b, h, a: _alert_action(s, b, h, a, "assign"),
    "update_priority": _update_priority,
    "add_note": _add_note,
    "add_tags": _add_tags,
    "create_incident": _create_incident,
    "get_incident": _get_incident,
    "list_incidents": _list_incidents,
    "close_incident": _close_incident,
    "resolve_incident": _close_incident,  # Same API endpoint
    "add_responder": _add_responder,
    "add_timeline_entry": _add_timeline_entry,
    "get_on_call": _get_on_call,
    "list_schedules": _list_schedules,
    "get_escalation_policy": _get_escalation_policy,
    "list_escalation_policies": _list_escalation_policies,
}


async def execute(
    arguments: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Entry point for the opsgenie_manage tool executor."""
    action = arguments.get("action")
    if not action:
        return _err("action parameter is required")

    if action not in _ACTION_DISPATCH:
        return _err(f"Unknown action: {action}. Valid actions: {sorted(_ACTION_DISPATCH.keys())}")

    # Resolve API key
    api_key = os.environ.get("OPSGENIE_API_KEY", "")
    if not api_key:
        return _err("OPSGENIE_API_KEY environment variable is not set")

    region = arguments.get("region", os.environ.get("OPSGENIE_REGION", "us"))
    base_url = _get_base_url(region)
    headers = _get_headers(api_key)

    # Dry-run mode
    if arguments.get("dry_run"):
        return _ok(
            {"action": action, "base_url": base_url, "arguments": {
                k: v for k, v in arguments.items()
                if k not in ("action", "dry_run", "region")
            }},
            f"Dry run: would execute {action}",
        )

    # Execute the action
    handler = _ACTION_DISPATCH[action]
    try:
        async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
            result = await handler(session, base_url, headers, arguments)
    except aiohttp.ClientError as exc:
        result = _err(f"HTTP error: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error in opsgenie_manage")
        result = _err(f"Unexpected error: {exc}")

    return result
