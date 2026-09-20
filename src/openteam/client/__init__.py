"""Generic OpenTeam client: discover-or-launch a running server + attach sessions.

Frontend-agnostic. RovoDev TUI, future Slack bot, future IDE plugin, future
``openteam-sdk`` PyPI package all import from here — never from ``openteam.server``.

Invariant I14 (CI-enforced by ``test_no_server_imports.py``): no module under
``openteam.client`` may import ``openteam.server.*`` — even transitively. The
only allowed reverse direction is ``openteam.server._register`` importing
schema constants from ``openteam.client.discovery``.

Public API:
    DISCOVERY_DIR, SCHEMA_VERSION, SERVICE_NAME, ServerHandle,
    compute_server_id, discover_servers, find_server,
    pid_alive, health_check,
    ensure_server, auto_launch_server, NoServerAvailable,
    attach_session_via_http, AttachResult, AttachFailed
"""

from openteam.client.attach import attach_session_via_http, AttachFailed, AttachResult
from openteam.client.discovery import (
    compute_server_id,
    discover_servers,
    DISCOVERY_DIR,
    find_server,
    health_check,
    pid_alive,
    SCHEMA_VERSION,
    ServerHandle,
    SERVICE_NAME,
)
from openteam.client.supervisor import (
    auto_launch_server,
    ensure_server,
    NoServerAvailable,
)

__all__ = [
    "DISCOVERY_DIR",
    "SCHEMA_VERSION",
    "SERVICE_NAME",
    "ServerHandle",
    "compute_server_id",
    "discover_servers",
    "find_server",
    "pid_alive",
    "health_check",
    "ensure_server",
    "auto_launch_server",
    "NoServerAvailable",
    "attach_session_via_http",
    "AttachResult",
    "AttachFailed",
]
