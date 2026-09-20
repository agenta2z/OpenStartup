# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""Shared ``HubController`` construction for OpenTeam (in-turn AND out-of-turn).

The ``ToolDispatcher`` builds a :class:`HubController` per agentic turn wired to
an interactive ``stream_sink`` (see ``tool_dispatcher._build_hub_controller``).
REST-triggered hub actions fire OUTSIDE a turn, so they have no per-turn
``WebSocketInteractive`` — they push live updates through
``ConnectionRegistry.emit`` instead (``app.state.connection_registry``) and have
no interactive sink.

To avoid duplicating the (non-trivial) dependency wiring in two places, both
paths funnel through :func:`build_hub_controller` here. It mirrors the
dispatcher's wiring exactly — ``WorkflowContext.from_dict`` from the session,
``persist`` → ``update_workflow_context``, ``add_task_ref`` /
``update_task_ref_status`` → ``session_store`` message rows, ``session_dir`` /
``session_tasks_dir`` from the store — but takes its collaborators as explicit
arguments instead of reading them off a ``ToolDispatcher`` instance.

This module imports NO ``fastapi``: the routers do request-parse + DI, then call
this. The ML logic lives in ``agent_foundation.experiment_hub`` (plan #13).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

logger: logging.Logger = logging.getLogger(__name__)

# Async event emitter the HubController is injected with:
#   ``async def emit_event(session_id: str, payload: dict) -> Any``.
# Out-of-turn this is ``ConnectionRegistry.emit``; in-turn it is the
# dispatcher's interactive adapter.
EmitEvent = Callable[[str, dict[str, Any]], Awaitable[Any]]


def _iso_now() -> str:
    """ISO 8601 UTC timestamp (matches SessionStore message timestamps)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_session_callbacks(
    session_store: Any, session_id: str, wc: Any
) -> tuple[
    Callable[[], Awaitable[None]],
    Callable[..., Awaitable[None]],
    Callable[[str, str], Awaitable[bool]],
]:
    """Build the ``(persist, add_task_ref, update_task_ref_status)`` callables the
    ``HubController`` is injected with, bound to one session + its live ``wc``.

    Factored out of :func:`build_hub_controller` so that function stays a flat
    wire-up. All three are best-effort: a persistence / message-write failure
    must never break a hub run (on-disk state is the source of truth on
    reconnect, and the chip markers are advisory)."""

    async def _persist() -> None:
        # The controller mutates active_multi_task_id + phase_outputs + the task
        # queue; flush the live wc back to disk so a restart resumes correctly.
        try:
            session_store.update_workflow_context(session_id, wc.to_dict())
        except Exception as exc:  # noqa: BLE001 — persist failure must not break the run
            logger.warning("[hub_factory] workflow_context persist failed: %s", exc)

    async def _add_task_ref(**kwargs: Any) -> None:
        # Subtask chips only; the hub-level subtab IS the dashboard_ref (created
        # by the dispatcher's dashboard_open).
        task_id = kwargs.get("task_id")
        if not task_id:
            return
        try:
            session_store.append_message(
                session_id,
                {
                    "id": f"task-ref-{task_id}",
                    "role": "task_ref",
                    "taskId": task_id,
                    "timestamp": _iso_now(),
                    **kwargs,
                },
            )
        except Exception as exc:  # noqa: BLE001 — chip marker is best-effort
            logger.warning("[hub_factory] add_task_ref failed: %s", exc)

    async def _update_task_ref_status(task_id: str, status: str) -> bool:
        try:
            return (
                session_store.update_message(
                    session_id, f"task-ref-{task_id}", {"status": status}
                )
                is not None
            )
        except Exception:  # noqa: BLE001 — best-effort
            return False

    return _persist, _add_task_ref, _update_task_ref_status


def build_hub_controller(
    *,
    session_store: Any,
    session_id: str,
    session_context: dict[str, Any],
    emit_event: EmitEvent,
    stream_sink: Any = None,
    exec_task: Any = None,
) -> tuple[Any, Any] | None:
    """Construct a ``HubController`` wired to OpenTeam's session machinery.

    Returns ``(controller, workflow_context)``, or ``None`` when the
    ``experiment_hub`` backend is unimportable or the session is unavailable
    (the caller treats ``None`` as a 503 / graceful no-op). The returned
    ``workflow_context`` is the live instance the controller mutates; callers
    MUST persist it (``session_store.update_workflow_context(session_id,
    wc.to_dict())``) after the controller call mutates it.

    Mirrors ``tool_dispatcher._build_hub_controller``'s dependency wiring; the
    only differences for the out-of-turn REST path are supplied by the caller:
    ``emit_event=request.app.state.connection_registry.emit`` and
    ``stream_sink=None`` (no per-turn interactive exists outside a turn).
    """
    if not session_id or session_store is None:
        return None

    # Lazy import — keeps this module importable (and the server bootable) even
    # when the experiment_hub backend isn't on the path yet. Matches the
    # dispatcher's defensive import.
    try:
        from agent_foundation.experiment_hub.hub_controller import HubController
        from agent_foundation.server.workflow_context import WorkflowContext
    except Exception as exc:  # noqa: BLE001 — backend optional
        logger.warning("[hub_factory] experiment_hub backend unavailable: %s", exc)
        return None

    session = session_store.get_session(session_id) or {}
    try:
        wc = WorkflowContext.from_dict(session.get("workflow_context") or {})
    except Exception:  # noqa: BLE001 — corrupt persisted state → start fresh
        wc = WorkflowContext()

    persist_cb, add_task_ref, update_task_ref_status = _make_session_callbacks(
        session_store, session_id, wc
    )

    try:
        controller = HubController(
            session_id=session_id,
            session_dir=session_store.get_session_dir(session_id),
            session_tasks_dir=session_store.get_session_tasks_dir(session_id),
            workflow_context=wc,
            emit_event=emit_event,
            persist=persist_cb,
            stream_sink=stream_sink,
            # TODO(port): wire exec_task to the host task executor so in-hub
            # implementation runs (auto_implement / the WS implement-hypothesis
            # path) execute their /task branch. The auto_implement=False handoff
            # path + submission_run (executed by the hub itself) do not need it,
            # so REST run/cancel of a submission works with exec_task=None.
            exec_task=exec_task,
            workflow_target_path=str(session_context.get("working_dir", "") or ""),
            session_context=session_context,
            add_task_ref=add_task_ref,
            update_task_ref_status=update_task_ref_status,
        )
    except Exception as exc:  # noqa: BLE001 — surface as None → 503 at the route
        logger.warning("[hub_factory] HubController construction failed: %s", exc)
        return None
    return controller, wc


def make_hub_event_emitter(
    connection_registry: Any, hub_id_holder: dict[str, str]
) -> EmitEvent:
    """Adapt RankEvolve-shaped ``HubController`` payloads → the generic
    ``dashboard_*`` WS protocol, broadcasting via ``ConnectionRegistry.emit``.

    This is the OUT-OF-TURN equivalent of the dispatcher's in-turn
    ``_make_hub_emit``. Pass it as ``emit_event`` to :func:`build_hub_controller`
    for REST / WS-``hub_command`` paths (NOT ``connection_registry.emit`` raw —
    the controller emits ``task_status`` / ``submission_state`` / ``token`` /
    ``setup_*`` payloads that the FE only routes to the hub bus when wrapped in a
    ``dashboard_event``). A hub-level ``task_status{task_type:"multi"}`` becomes a
    ``dashboard_status``; every other event is forwarded RAW inside a
    ``dashboard_event`` (the FE reducer switches on ``payload.type``). Routes by
    ``hub_id`` — seed ``hub_id_holder={"hub_id": <known multi_task_id>}`` (the
    REST/WS caller knows it) and it is refreshed from any multi lifecycle event.
    """

    async def _emit(session_id: str, payload: dict[str, Any]) -> Any:
        from agent_foundation.server.dashboard.dashboard_protocol import (
            build_dashboard_event,
            build_dashboard_status,
        )

        if payload.get("task_type") == "multi" and payload.get("task_id"):
            hub_id_holder["hub_id"] = str(payload["task_id"])
        hub_id = (
            hub_id_holder.get("hub_id")
            or str(payload.get("multi_task_id") or "")
            or str(payload.get("task_id") or "")
        )
        ptype = payload.get("type")
        if ptype == "task_status" and payload.get("task_type") == "multi":
            msg = build_dashboard_status(
                hub_id=hub_id, status=str(payload.get("status") or "open")
            )
        else:
            msg = build_dashboard_event(
                hub_id=hub_id,
                event_type=str(ptype or payload.get("status") or "update"),
                payload=payload,
            )
        try:
            return await connection_registry.emit(session_id, msg)
        except Exception as exc:  # noqa: BLE001 — emit is best-effort
            logger.warning("[hub_factory] dashboard emit failed: %s", exc)
            return 0

    return _emit
