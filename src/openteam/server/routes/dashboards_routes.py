# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""Session-scoped Dashboard (hub) subtab lifecycle REST routes.

Mounted at ``/api/sessions/{session_id}``. Two endpoints:

  * ``GET  /api/sessions/{sid}/dashboards`` — list the session's OPEN dashboard
    subtabs (the Experiment Hub tabs the user can switch to), reconstructed from
    the persisted ``dashboard_ref`` history rows + the active-pointer in
    ``dashboard_state``.
  * ``POST /api/sessions/{sid}/dashboards/{hub_id}/close`` — close one subtab:
    mark its ``dashboard_ref`` row ``closed``, clear it from the active pointer,
    and cancel any out-of-turn runs the hub still has on the run supervisor.

This is NOT the legacy mock ``dashboard_routes.py`` (a single ``/summary``
fixture endpoint) — this router operates on real persisted session state and the
out-of-turn ``HubRunSupervisor``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


def _session_store(request: Request) -> Any:
    """Resolve the SessionStore off ``app.state.data_service`` or 503."""
    svc = getattr(request.app.state, "data_service", None)
    store = getattr(svc, "session_store", None)
    if store is None:
        raise HTTPException(503, "Session store not available (mock mode?)")
    return store


@router.get("/{session_id}/dashboards")
async def list_dashboards(request: Request, session_id: str) -> dict[str, Any]:
    """List the session's open dashboard subtabs (newest first).

    A subtab is materialized as a ``dashboard_ref`` message (persisted by the
    dispatcher's ``dashboard_open``); ``status != "closed"`` means it is live.
    Each row carries ``hubId`` / ``dashboardId`` / ``label`` / ``icon`` — exactly
    what the FE tab bar needs to re-offer the tab on reload. The session's
    ``dashboard_state.active_hub_id`` flags which one is focused.
    """
    store = _session_store(request)
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(404, f"Session {session_id} not found")

    active_hub_id = ""
    try:
        active_hub_id = str(
            store.load_dashboard_state(session_id).get("active_hub_id") or ""
        )
    except Exception as exc:  # noqa: BLE001 — pointer is advisory
        logger.warning("[dashboards] load_dashboard_state failed: %s", exc)

    dashboards: list[dict[str, Any]] = []
    for m in session.get("messages", []):
        if m.get("role") != "dashboard_ref" or m.get("status") == "closed":
            continue
        hub_id = m.get("hubId")
        if not hub_id:
            continue
        dashboards.append(
            {
                "hub_id": hub_id,
                "dashboard_id": m.get("dashboardId"),
                "label": m.get("label") or m.get("dashboardId") or hub_id,
                "icon": m.get("icon") or "",
                "status": m.get("status") or "open",
                "active": hub_id == active_hub_id,
                "opened_at": m.get("timestamp"),
            }
        )
    # Newest first so the FE renders the most recently opened tab leftmost if it
    # wants; opened_at is ISO 8601 so a lexical reverse sort is chronological.
    dashboards.sort(key=lambda d: d.get("opened_at") or "", reverse=True)
    return {"data": dashboards}


@router.post("/{session_id}/dashboards/{hub_id}/close")
async def close_dashboard(
    request: Request, session_id: str, hub_id: str
) -> dict[str, Any]:
    """Close a dashboard subtab + cancel any of its out-of-turn runs.

    Steps:
      1. Mark the matching ``dashboard_ref`` row ``closed`` (so a reload / the
         ``GET .../dashboards`` list no longer offers a dead subtab).
      2. Clear it from the persisted ``dashboard_state`` active pointer (and from
         the live ``WorkflowContext`` via ``close_multi_task``) so the session
         doesn't auto-refocus a closed hub.
      3. Cancel every run this session has in flight on the ``HubRunSupervisor``.
         Runs aren't tagged by hub_id, so we cancel the whole session's runs —
         conservative + safe (a closed hub should not keep a subprocess alive,
         and submission runs are the only out-of-turn runs today).
    """
    store = _session_store(request)
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(404, f"Session {session_id} not found")

    # 1. Mark the dashboard_ref closed.
    updated = store.update_message(
        session_id, f"dashboard-ref-{hub_id}", {"status": "closed"}
    )
    if updated is None:
        # No such open subtab — surface 404 so the FE can drop its stale tab.
        raise HTTPException(
            404, f"Dashboard {hub_id} not found in session {session_id}"
        )

    # 2. Clear the active pointer if it pointed at this hub, and close it on the
    # live WorkflowContext (best-effort; the dashboard_ref is the source of truth
    # for the subtab marker).
    try:
        state = store.load_dashboard_state(session_id)
        if str(state.get("active_hub_id") or "") == hub_id:
            store.save_dashboard_state(
                session_id,
                {"active_hub_id": "", "dashboard_id": state.get("dashboard_id")},
            )
    except Exception as exc:  # noqa: BLE001 — pointer cleanup is best-effort
        logger.warning("[dashboards] active-pointer clear failed: %s", exc)
    _close_in_workflow_context(store, session_id, hub_id)

    # 3. Cancel the session's out-of-turn runs.
    cancelled = 0
    supervisor = getattr(request.app.state, "hub_run_supervisor", None)
    if supervisor is not None:
        try:
            cancelled = await supervisor.cancel_session(session_id)
        except Exception as exc:  # noqa: BLE001 — cancel best-effort; subtab is already closed
            logger.warning("[dashboards] cancel_session failed: %s", exc)

    logger.info(
        "[dashboards] closed %s for session %s (cancelled %d run(s))",
        hub_id,
        session_id,
        cancelled,
    )
    return {"data": {"hub_id": hub_id, "closed": True, "cancelled_runs": cancelled}}


def _close_in_workflow_context(store: Any, session_id: str, hub_id: str) -> None:
    """Best-effort: clear ``active_multi_task_id`` / record the close on the
    session's persisted ``WorkflowContext`` so a resume doesn't refocus the hub.

    Uses the in-memory ``WorkflowContext`` round-trip (``from_dict`` →
    ``close_multi_task`` → ``to_dict``) so the persisted ``closed_multi_task_ids``
    set stays consistent with the dispatcher's own bookkeeping. Import is lazy so
    a missing backend never breaks the close.
    """
    try:
        from agent_foundation.server.workflow_context import WorkflowContext
    except Exception:  # noqa: BLE001 — backend optional
        return
    session = store.get_session(session_id) or {}
    try:
        wc = WorkflowContext.from_dict(session.get("workflow_context") or {})
        wc.close_multi_task(hub_id)
        store.update_workflow_context(session_id, wc.to_dict())
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("[dashboards] workflow_context close failed: %s", exc)
