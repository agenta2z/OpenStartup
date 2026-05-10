"""
Executor for grafana_manage tool.

Provides Grafana HTTP API integration for dashboard CRUD, annotation management,
alert rule provisioning, folder organization, and data source operations.
"""

import os
import json
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Operations that require human confirmation before execution
WRITE_OPERATIONS = {
    "dashboard_create", "dashboard_update", "dashboard_delete",
    "alert_rules_create", "alert_rules_update", "alert_rules_delete",
    "folder_create", "folder_update", "folder_delete",
}

# Operations that are read-only and can execute autonomously
READ_OPERATIONS = {
    "dashboard_get", "dashboard_search", "dashboard_versions", "dashboard_tags",
    "annotation_list", "alert_rules_list", "alert_rules_get", "alert_rules_export",
    "alertmanager_alerts", "alertmanager_groups", "alertmanager_silences",
    "folder_list", "folder_get", "datasource_list", "datasource_get",
    "datasource_proxy_query",
}

# Annotation writes are lower risk — autonomous with audit logging
ANNOTATION_WRITES = {"annotation_create", "annotation_update", "annotation_delete"}


def _build_headers(org_id: int | None = None) -> dict[str, str]:
    """Build HTTP headers including auth token and org scope."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    api_token = os.environ.get("GRAFANA_API_TOKEN")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    if org_id:
        headers["X-Grafana-Org-Id"] = str(org_id)

    return headers


async def _request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict[str, str],
    json_data: Any = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Make HTTP request to Grafana API."""
    try:
        kwargs: dict[str, Any] = {"headers": headers}
        if json_data is not None:
            kwargs["json"] = json_data
        if params:
            kwargs["params"] = params

        async with session.request(method, url, **kwargs) as resp:
            if resp.status == 204:
                return {"status": "success", "message": "Resource deleted successfully."}
            if resp.content_type == "application/json":
                body = await resp.json()
                if resp.status >= 400:
                    return {
                        "status": "error",
                        "http_status": resp.status,
                        "message": body.get("message", str(body)),
                    }
                return body if isinstance(body, dict) else {"status": "success", "data": body}
            else:
                text = await resp.text()
                if resp.status >= 400:
                    return {"status": "error", "http_status": resp.status, "message": text[:500]}
                return {"status": "success", "data": text}
    except aiohttp.ClientError as e:
        return {"status": "error", "errorType": "connection_error", "message": str(e)}


async def execute(arguments: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Main executor entry point for grafana_manage tool."""
    action = arguments.get("action")
    endpoint = arguments.get("endpoint") or os.environ.get("GRAFANA_URL", "http://localhost:3000")
    org_id = arguments.get("org_id")
    headers = _build_headers(org_id)
    base_url = endpoint.rstrip("/")

    async with aiohttp.ClientSession() as session:

        # ==================== DASHBOARD OPERATIONS ====================

        if action == "dashboard_get":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required for dashboard_get."}
            return await _request(session, "GET", f"{base_url}/api/dashboards/uid/{uid}", headers)

        elif action == "dashboard_search":
            params = {}
            if arguments.get("query"):
                params["query"] = arguments["query"]
            if arguments.get("tags"):
                for tag in arguments["tags"].split(","):
                    params.setdefault("tag", [])
                    if isinstance(params["tag"], list):
                        params["tag"].append(tag.strip())
                    else:
                        params["tag"] = tag.strip()
            params["type"] = "dash-db"
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])
            return await _request(session, "GET", f"{base_url}/api/search", headers, params=params)

        elif action == "dashboard_create":
            dashboard_json = arguments.get("dashboard_json")
            if not dashboard_json:
                return {"status": "error", "message": "Parameter 'dashboard_json' is required."}
            body = json.loads(dashboard_json) if isinstance(dashboard_json, str) else dashboard_json
            if arguments.get("folder_uid"):
                body["folderUid"] = arguments["folder_uid"]
            if arguments.get("message"):
                body["message"] = arguments["message"]
            if arguments.get("overwrite"):
                body["overwrite"] = True
            return await _request(session, "POST", f"{base_url}/api/dashboards/db", headers, json_data=body)

        elif action == "dashboard_update":
            dashboard_json = arguments.get("dashboard_json")
            if not dashboard_json:
                return {"status": "error", "message": "Parameter 'dashboard_json' is required."}
            body = json.loads(dashboard_json) if isinstance(dashboard_json, str) else dashboard_json
            if arguments.get("folder_uid"):
                body["folderUid"] = arguments["folder_uid"]
            if arguments.get("message"):
                body["message"] = arguments["message"]
            if arguments.get("overwrite"):
                body["overwrite"] = True
            return await _request(session, "POST", f"{base_url}/api/dashboards/db", headers, json_data=body)

        elif action == "dashboard_delete":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            return await _request(session, "DELETE", f"{base_url}/api/dashboards/uid/{uid}", headers)

        elif action == "dashboard_versions":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            return await _request(session, "GET", f"{base_url}/api/dashboards/uid/{uid}/versions", headers)

        elif action == "dashboard_tags":
            return await _request(session, "GET", f"{base_url}/api/dashboards/tags", headers)

        # ==================== ANNOTATION OPERATIONS ====================

        elif action == "annotation_list":
            params = {}
            if arguments.get("from"):
                params["from"] = arguments["from"]
            if arguments.get("to"):
                params["to"] = arguments["to"]
            if arguments.get("tags"):
                for tag in arguments["tags"].split(","):
                    params.setdefault("tags", [])
                    if isinstance(params["tags"], list):
                        params["tags"].append(tag.strip())
            if arguments.get("dashboard_id"):
                params["dashboardId"] = str(arguments["dashboard_id"])
            if arguments.get("panel_id"):
                params["panelId"] = str(arguments["panel_id"])
            if arguments.get("limit"):
                params["limit"] = str(arguments["limit"])
            return await _request(session, "GET", f"{base_url}/api/annotations", headers, params=params)

        elif action == "annotation_create":
            body = {}
            if arguments.get("dashboard_id"):
                body["dashboardId"] = arguments["dashboard_id"]
            if arguments.get("panel_id"):
                body["panelId"] = arguments["panel_id"]
            if arguments.get("text"):
                body["text"] = arguments["text"]
            if arguments.get("tags"):
                body["tags"] = [t.strip() for t in arguments["tags"].split(",")]
            if arguments.get("from"):
                body["time"] = int(arguments["from"])
            if arguments.get("to"):
                body["timeEnd"] = int(arguments["to"])
            return await _request(session, "POST", f"{base_url}/api/annotations", headers, json_data=body)

        elif action == "annotation_update":
            ann_id = arguments.get("annotation_id")
            if not ann_id:
                return {"status": "error", "message": "Parameter 'annotation_id' is required."}
            body = {}
            if arguments.get("text"):
                body["text"] = arguments["text"]
            if arguments.get("tags"):
                body["tags"] = [t.strip() for t in arguments["tags"].split(",")]
            return await _request(session, "PATCH", f"{base_url}/api/annotations/{ann_id}", headers, json_data=body)

        elif action == "annotation_delete":
            ann_id = arguments.get("annotation_id")
            if not ann_id:
                return {"status": "error", "message": "Parameter 'annotation_id' is required."}
            return await _request(session, "DELETE", f"{base_url}/api/annotations/{ann_id}", headers)

        # ==================== ALERT RULE OPERATIONS ====================

        elif action == "alert_rules_list":
            return await _request(session, "GET", f"{base_url}/api/v1/provisioning/alert-rules", headers)

        elif action == "alert_rules_get":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            return await _request(session, "GET", f"{base_url}/api/v1/provisioning/alert-rules/{uid}", headers)

        elif action == "alert_rules_create":
            rule_json = arguments.get("alert_rule_json")
            if not rule_json:
                return {"status": "error", "message": "Parameter 'alert_rule_json' is required."}
            body = json.loads(rule_json) if isinstance(rule_json, str) else rule_json
            create_headers = {**headers, "X-Disable-Provenance": "true"}
            return await _request(session, "POST", f"{base_url}/api/v1/provisioning/alert-rules", create_headers, json_data=body)

        elif action == "alert_rules_update":
            uid = arguments.get("uid")
            rule_json = arguments.get("alert_rule_json")
            if not uid or not rule_json:
                return {"status": "error", "message": "Parameters 'uid' and 'alert_rule_json' are required."}
            body = json.loads(rule_json) if isinstance(rule_json, str) else rule_json
            update_headers = {**headers, "X-Disable-Provenance": "true"}
            return await _request(session, "PUT", f"{base_url}/api/v1/provisioning/alert-rules/{uid}", update_headers, json_data=body)

        elif action == "alert_rules_delete":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            return await _request(session, "DELETE", f"{base_url}/api/v1/provisioning/alert-rules/{uid}", headers)

        elif action == "alert_rules_export":
            fmt = arguments.get("export_format", "json")
            params = {"format": fmt}
            if arguments.get("uid"):
                url = f"{base_url}/api/v1/provisioning/alert-rules/{arguments['uid']}/export"
            elif arguments.get("folder_uid") and arguments.get("rule_group"):
                url = f"{base_url}/api/v1/provisioning/folder/{arguments['folder_uid']}/rule-groups/{arguments['rule_group']}/export"
            else:
                url = f"{base_url}/api/v1/provisioning/alert-rules/export"
            return await _request(session, "GET", url, headers, params=params)

        # ==================== ALERTMANAGER OPERATIONS ====================

        elif action == "alertmanager_alerts":
            return await _request(session, "GET", f"{base_url}/api/alertmanager/grafana/api/v2/alerts", headers)

        elif action == "alertmanager_groups":
            return await _request(session, "GET", f"{base_url}/api/alertmanager/grafana/api/v2/alerts/groups", headers)

        elif action == "alertmanager_silences":
            return await _request(session, "GET", f"{base_url}/api/alertmanager/grafana/api/v2/silences", headers)

        # ==================== FOLDER OPERATIONS ====================

        elif action == "folder_list":
            return await _request(session, "GET", f"{base_url}/api/folders", headers)

        elif action == "folder_get":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            return await _request(session, "GET", f"{base_url}/api/folders/{uid}", headers)

        elif action == "folder_create":
            body = {}
            if arguments.get("uid"):
                body["uid"] = arguments["uid"]
            if arguments.get("query"):
                body["title"] = arguments["query"]
            if arguments.get("folder_uid"):
                body["parentUid"] = arguments["folder_uid"]
            return await _request(session, "POST", f"{base_url}/api/folders", headers, json_data=body)

        elif action == "folder_update":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            body = {}
            if arguments.get("query"):
                body["title"] = arguments["query"]
            if arguments.get("overwrite"):
                body["overwrite"] = True
            return await _request(session, "PUT", f"{base_url}/api/folders/{uid}", headers, json_data=body)

        elif action == "folder_delete":
            uid = arguments.get("uid")
            if not uid:
                return {"status": "error", "message": "Parameter 'uid' is required."}
            return await _request(session, "DELETE", f"{base_url}/api/folders/{uid}", headers)

        # ==================== DATA SOURCE OPERATIONS ====================

        elif action == "datasource_list":
            return await _request(session, "GET", f"{base_url}/api/datasources", headers)

        elif action == "datasource_get":
            ds_uid = arguments.get("datasource_uid") or arguments.get("uid")
            if not ds_uid:
                return {"status": "error", "message": "Parameter 'datasource_uid' or 'uid' is required."}
            return await _request(session, "GET", f"{base_url}/api/datasources/uid/{ds_uid}", headers)

        elif action == "datasource_proxy_query":
            ds_uid = arguments.get("datasource_uid")
            query = arguments.get("query")
            if not ds_uid or not query:
                return {"status": "error", "message": "Parameters 'datasource_uid' and 'query' are required."}
            params = {"query": query}
            if arguments.get("from"):
                params["start"] = arguments["from"]
            if arguments.get("to"):
                params["end"] = arguments["to"]
            return await _request(
                session, "GET",
                f"{base_url}/api/datasources/proxy/uid/{ds_uid}/api/v1/query",
                headers, params=params,
            )

        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}. See tool definition for valid actions.",
            }
