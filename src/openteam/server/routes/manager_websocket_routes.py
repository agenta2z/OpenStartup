"""WebSocket endpoint for real-time Manager ↔ AI chat streaming.

Adapted from rankevolve's agent_websocket_routes.py.
Simplified: no AgentServiceBridge/file-queue — calls ConversationService directly.

Protocol (client → server):
    {"type": "init", "session_id": "..."}
    {"type": "message", "content": "user text"}
    {"type": "cancel"}
    {"type": "ping"}

Protocol (server → client):
    {"type": "session_init", "session_id": "...", "messages": [...]}
    {"type": "message_start"}
    {"type": "token", "content": "chunk", "metadata": {"agent_name": "Orchestrator"}}
    {"type": "message_end", "final_content": "...", "message_id": "..."}
    {"type": "status", "status": "complete"|"error", "detail": "..."}
    {"type": "error", "message": "..."}
    {"type": "heartbeat"}
    {"type": "pong"}
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)
router = APIRouter()


def _make_timestamp() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


import json as _json
import os as _os
import re as _re
from pathlib import Path as _Path

# Bug 1 fix: support hyphens in command names (normalized to underscores for tool lookup)
_SLASH_CMD_RE = _re.compile(r"^/([a-zA-Z][a-zA-Z0-9_-]*)\b(.*)", _re.DOTALL)


# Patch 3.2 — boolean-aware + shlex-quoted parser. Whitelist for /task's bool flags
# so /task --plan "request" parses as {plan: True, request: "request"} not {plan: "request"}.
# The parser itself now lives in services/cli_args (one source of truth, shared
# with the agent action path in ToolDispatcher); imported here as _parse_slash_args.
from openteam.server.services.cli_args import parse_cli_args as _parse_slash_args

_TASK_BOOL_FLAGS = {
    "plan",
    "execute",
    "full",
    "confirm",
    "no_dual",
    "analysis",
    "multi_iter",
    "in_place",
    "copy_workspace",
}
# CANONICAL CONVENTION (Option D, 2026-05-18): `arguments` dict keys are
# ALWAYS underscored. _parse_slash_args normalizes incoming `--foo-bar`
# tokens via `.replace("-","_")` so this set MUST use underscore form too.

# Patch 3.1 — task-* alias mapping (cmd_name is post-`replace("-", "_")` so keys use _).
_TASK_MODE_ALIASES = {
    "task_plan": "plan",
    "task_execute": "execute",
    "task_full": "full",
    "task_confirm": "confirm",
}


async def _try_dev_slash_command(
    text: str,
    sid: str,
    send_safe: Any,
    dev_tool_tasks: "dict[str, asyncio.Task[Any]]" = None,
    dev_tool_input_queues: "dict[str, asyncio.Queue[Any]]" = None,
    session_store=None,
    pending_input_cache: "dict[str, Any] | None" = None,
    snapshot_store: Any = None,
) -> bool:
    """Intercept ``/command-name --args`` slash commands.

    Returns True if the message was handled (caller should skip normal flow).

    Patch 3.1 — gating uses tool.json's ``slash_enabled`` (defaults to ``not agent_enabled``
    for backward compat with /mock_task) and ``dev_mode_only`` (defaults to True). /task
    declares both ``slash_enabled: true`` and ``dev_mode_only: false`` so it's available
    without OPENTEAM_DEV_MODE.

    Patch 3.4 — dev_tool_tasks + dev_tool_input_queues registries enable per-task
    cancellation and pending-input routing.
    """
    if dev_tool_tasks is None:
        dev_tool_tasks = {}
    if dev_tool_input_queues is None:
        dev_tool_input_queues = {}

    m = _SLASH_CMD_RE.match(text.strip())
    if not m:
        return False

    cmd_name = m.group(1).replace("-", "_")
    args_str = m.group(2).strip()

    # Patch 3.1 — task-* aliases map to the canonical "task" tool.
    injected_mode = _TASK_MODE_ALIASES.get(cmd_name)
    if injected_mode:
        cmd_name = "task"

    try:
        from agent_foundation.resources.tools.registry import load_all_tools

        tools_dir = _Path(__file__).resolve().parent.parent / "resources" / "tools"
        registry = load_all_tools(extra_dirs=[tools_dir])
        tool_def = registry.get(cmd_name)

        # Resolve aliases / preferred_prompt_alias to the canonical tool name
        # (e.g. /enter_sop → sop). Direct-name hits skip this.
        if not tool_def:
            for _name, _t in registry.items():
                if cmd_name in getattr(_t, "aliases", []) or cmd_name == getattr(
                    _t, "preferred_prompt_alias", ""
                ):
                    cmd_name = _name
                    tool_def = _t
                    break

        if not tool_def:
            available = [n for n, t in registry.items() if not t.agent_enabled]
            await send_safe(
                {
                    "type": "error",
                    "message": f"Unknown command `/{cmd_name}`. Available: {', '.join(f'/{n}' for n in available) or '(none)'}",
                }
            )
            return True

        # Patch 3.1 — gate via slash_enabled (corrected formula: inner default True
        # to match ToolDefinition.agent_enabled default).
        tool_json_path = _Path(tool_def.source_path)
        try:
            tool_data = _json.loads(tool_json_path.read_text(encoding="utf-8"))
        except OSError as exc:
            await send_safe(
                {
                    "type": "error",
                    "message": f"Could not load tool.json for /{cmd_name}: {exc}",
                }
            )
            return True

        slash_enabled = tool_data.get(
            "slash_enabled", not tool_data.get("agent_enabled", True)
        )
        if not slash_enabled:
            return False  # let the agent path (ToolDispatcher) handle it

        if tool_data.get("dev_mode_only", True) and not _os.environ.get(
            "OPENTEAM_DEV_MODE"
        ):
            await send_safe(
                {
                    "type": "error",
                    "message": f"`/{cmd_name}` requires OPENTEAM_DEV_MODE=1",
                }
            )
            return True

        # Patch 3.3 — pass /task's known bool flags so the parser handles --plan etc. correctly.
        bool_flags = _TASK_BOOL_FLAGS if cmd_name == "task" else frozenset()
        parsed_args = _parse_slash_args(args_str, bool_flags=bool_flags)
        if cmd_name == "task" and injected_mode and "mode" not in parsed_args:
            parsed_args["mode"] = injected_mode

        task_id = f"dev-{uuid.uuid4().hex[:8]}"

        await send_safe(
            {
                "type": "task_status",
                "task_id": task_id,
                "tool_name": cmd_name,
                "status": "starting",
                "request": f"/{cmd_name} {args_str}".strip(),
            }
        )

        from openteam.server.services.websocket_interactive import WebSocketInteractive

        # Patch 3.4 — register per-task input queue so pending_input_response can route to it.
        input_queue: "asyncio.Queue[Any]" = asyncio.Queue()
        interactive = WebSocketInteractive(
            send_safe,
            input_queue,
            task_input_queues=dev_tool_input_queues,
            pending_input_cache=pending_input_cache,
            snapshot_store=snapshot_store,
            session_id=sid,
        )
        dev_tool_input_queues[task_id] = input_queue

        async def _run_dev_tool() -> None:
            try:
                executor_ref = tool_data.get("executor")
                if not executor_ref:
                    await send_safe(
                        {
                            "type": "error",
                            "message": f"No executor defined for /{cmd_name}",
                        }
                    )
                    return

                module_path, func_name = executor_ref.rsplit(":", 1)
                import importlib

                mod = importlib.import_module(module_path)
                execute_fn = getattr(mod, func_name)

                _session_root = ""
                if session_store is not None and sid:
                    try:
                        _session_root = str(session_store.get_session_dir(sid))
                    except Exception:
                        import logging as _log

                        _log.getLogger(__name__).warning(
                            "slash-path: could not resolve session_root for sid=%s; "
                            "falling back to standalone workspace",
                            sid,
                        )
                session_context = {
                    "interactive": interactive,
                    "task_id": task_id,
                    "session_id": sid,
                    "session_root": _session_root,
                    # The dev-slash queue is registered above (line ~205), so the
                    # "registered receive queue" contract is fulfilled — the
                    # conversational router may safely use interactive here.
                    "router_interactive_safe": True,
                }
                result = await execute_fn(parsed_args, session_context)

                # Patch 3.5 — handle both ToolExecutionResult (canonical) and dict
                # (legacy /mock_task contract).
                if hasattr(result, "result"):
                    result_text = str(result.result)
                    context_updates = getattr(result, "context_updates", None) or {}
                elif isinstance(result, dict):
                    result_text = result.get("output", str(result))
                    context_updates = result.get("context_updates", {})
                else:
                    result_text = str(result)
                    context_updates = {}

                await send_safe(
                    {
                        "type": "task_completed",
                        "task_id": task_id,
                        "tool_name": cmd_name,
                        "result_summary": result_text[:500],
                        "context_updates": context_updates,
                        # Standalone dev-slash path — no active inferencer/SOP
                        # in scope. Emit None for schema consistency with the
                        # SOP-driven dispatcher emit; Fix 1's FE consumer
                        # treats absent/None field as "no hint" → generic
                        # `<SOPNextStepGuidance>` deference.
                        "next_step_tool": None,
                    }
                )
            except asyncio.CancelledError:
                # R7.4 — CancelledError is BaseException-derived; must be caught explicitly.
                try:
                    await send_safe(
                        {
                            "type": "task_status",
                            "task_id": task_id,
                            "tool_name": cmd_name,
                            "status": "cancelled",
                        }
                    )
                finally:
                    raise  # propagate so the asyncio task enters cancelled state
            except Exception as exc:
                logger.exception("[dev_slash] /%s failed", cmd_name)
                await send_safe(
                    {
                        "type": "task_status",
                        "task_id": task_id,
                        "tool_name": cmd_name,
                        "status": "error",
                        "error": str(exc)[:500],
                        "error_type": type(exc).__name__,
                    }
                )

        task_obj = asyncio.create_task(_run_dev_tool())
        dev_tool_tasks[task_id] = task_obj

        def _cleanup(_t: "asyncio.Task[Any]") -> None:
            dev_tool_tasks.pop(task_id, None)
            dev_tool_input_queues.pop(task_id, None)

        task_obj.add_done_callback(_cleanup)
        return True

    except Exception as exc:
        logger.exception("[dev_slash] Failed to dispatch /%s", cmd_name)
        await send_safe({"type": "error", "message": f"Dev command error: {exc}"})
        return True


async def _quiesce_session(active_task: Any, conv_svc: Any, session_id: str) -> None:
    """Cancel the active turn + cancel/await in-flight background tasks.

    Must run before any resume/restore disk mutation so the checkpoint copy /
    ``rmtree`` can't race a live writer. Module-level (not a loop-nested closure)
    so the loop variables are passed explicitly.
    """
    if active_task is not None and not active_task.done():
        active_task.cancel()
        # AWAIT the cancelled turn so its finally-block (run_state/store.json +
        # sop_state persistence) fully unwinds BEFORE any disk mutation below —
        # otherwise that trailing write could race or undo the truncate's
        # deletions. Standard cancel-and-wait idiom.
        try:
            await active_task
        except asyncio.CancelledError:
            pass  # expected — we just cancelled it
        except Exception as e:  # its unwind raised — log, don't block resume
            logger.debug("quiesce: active turn unwind raised: %s", e)
    if conv_svc is not None and hasattr(conv_svc, "drain_session_background_tasks"):
        await conv_svc.drain_session_background_tasks(session_id)


async def _replay_task_graph_snapshots(
    snapshot_store: Any, session_id: str, send_safe: Any
) -> None:
    """v4 Phase 4.1 — replay every per-task graph snapshot for ``session_id``.

    Called after each ``session_init`` send and on ``request_graph_replay`` so
    a freshly-connected client (browser refresh / WS reconnect / HMR /
    resume_from_turn) hydrates its ``useGraphState`` from the server's mirror
    instead of starting blank. The replay events are wire-compatible with the
    live event stream — the client's existing ``handleGraphTopology`` /
    ``handleNodeStream`` / ``handleGraphReconcile`` handlers process them
    without any new code path.

    Robustness contract: replay failures are logged + swallowed. A bad
    snapshot can't break the WS lifecycle; the worst case is a missing
    sub-graph until the user kicks something that re-emits.
    """
    if snapshot_store is None or not session_id:
        return
    try:
        snapshots = snapshot_store.get_session_snapshots(session_id)
    except Exception as exc:
        logger.warning("[replay] get_session_snapshots failed: %s", exc)
        return
    for snap in snapshots:
        try:
            events = snap.to_replay_events()
        except Exception as exc:
            logger.warning(
                "[replay] to_replay_events failed (task_id=%s): %s",
                getattr(snap, "task_id", "?"),
                exc,
            )
            continue
        for ev in events:
            try:
                await send_safe(ev)
            except Exception as exc:
                logger.warning(
                    "[replay] send_safe failed (task_id=%s, type=%s): %s",
                    snap.task_id,
                    ev.get("type"),
                    exc,
                )
                # Bail this snapshot but keep replaying the next one — one
                # bad event shouldn't suppress unrelated tasks' graphs.
                break


async def _evict_and_send_session_init(
    data_svc: Any,
    conv_svc: Any,
    session_id: str,
    send_safe: Any,
    snapshot_store: Any = None,
) -> None:
    """Evict the cached inferencer, reconcile chips, re-broadcast session_init.

    Eviction forces the next turn to rebuild the CI (which re-restores sop_state);
    reconcile repairs any stuck task_ref chips; the fresh session_init carries the
    truncated/restored messages (the UI auto-replays the human turn on resume).
    v4 Phase 4.1 — also replays per-task graph snapshots after session_init so
    UI sub-graphs survive the resume cycle.
    """
    # CRITICAL: capture the bg-task liveness snapshot BEFORE evict.
    # evict_session_inferencer pops _bg_tasks without cancelling the tasks
    # themselves (see ConversationService.evict_session_inferencer comment
    # "drained explicitly by resume/restore"). A post-evict fetch would
    # return an empty set, causing reconcile to false-positive any
    # orphaned-but-alive task_ref as "interrupted".
    _live_task_ids: set[str] | None = None
    if conv_svc is not None and hasattr(conv_svc, "get_live_task_ids"):
        try:
            _live_task_ids = conv_svc.get_live_task_ids(session_id)
        except Exception:
            _live_task_ids = None
    if conv_svc is not None and hasattr(conv_svc, "evict_session_inferencer"):
        conv_svc.evict_session_inferencer(session_id)
    ss = getattr(data_svc, "session_store", None)
    if ss is not None and hasattr(ss, "reconcile_task_ref_statuses"):
        try:
            ss.reconcile_task_ref_statuses(session_id, live_task_ids=_live_task_ids)
        except Exception:
            pass
    session = data_svc.get_session(session_id)
    await send_safe(
        {
            "type": "session_init",
            "session_id": session_id,
            "messages": (session or {}).get("messages", []),
        }
    )
    await _replay_task_graph_snapshots(snapshot_store, session_id, send_safe)


async def _dispatch_hub_command(
    websocket: WebSocket,
    session_id: str,
    send_safe: Any,
    data: dict[str, Any],
) -> None:
    """Handle a ``hub_command`` WS frame from the Experiment Hub frontend.

    The hub's three long-running actions — ``implement_hypothesis`` /
    ``resume_implement_task`` / ``run_experiment_combos`` — travel over the
    manager socket (not REST). Each builds a ``HubController`` OUT-OF-TURN (its
    RankEvolve-shaped events flow back to every open tab as the generic
    ``dashboard_*`` protocol via the ConnectionRegistry-backed adapter) and runs
    on the ``HubRunSupervisor`` so the socket loop is never blocked. Best-effort:
    a malformed/unsupported command reports an error frame, never raises.
    """
    command = str(data.get("command") or "")
    if not command:
        return
    hub_id = str(
        data.get("multi_task_id") or data.get("multiTaskId") or data.get("hub_id") or ""
    )
    app_state = websocket.app.state
    store = getattr(getattr(app_state, "data_service", None), "session_store", None)
    registry = getattr(app_state, "connection_registry", None)
    supervisor = getattr(app_state, "hub_run_supervisor", None)
    if store is None or registry is None or supervisor is None:
        await send_safe(
            {"type": "error", "message": "hub_command: hub runtime unavailable"}
        )
        return

    from openteam.server.services.hub_factory import (
        build_hub_controller,
        make_hub_event_emitter,
    )

    emit = make_hub_event_emitter(registry, {"hub_id": hub_id})
    built = build_hub_controller(
        session_store=store,
        session_id=session_id,
        session_context={"working_dir": str(data.get("workflowTargetPath") or "")},
        emit_event=emit,
        stream_sink=None,
    )
    if built is None:
        await send_safe(
            {
                "type": "error",
                "message": "hub_command: Experiment Hub backend unavailable",
            }
        )
        return
    controller, wc = built
    args = {k: v for k, v in data.items() if k not in ("type", "command")}
    if command in ("implement_hypothesis", "resume_implement_task"):
        coro = controller._exec_implement_hypothesis(args)
    elif command == "run_experiment_combos":
        coro = controller._exec_experiment_combos(args)
    else:
        await send_safe(
            {"type": "error", "message": f"hub_command: unknown command {command!r}"}
        )
        return

    async def _run_and_persist() -> None:
        try:
            await coro
        finally:
            try:
                store.update_workflow_context(session_id, wc.to_dict())
            except Exception:  # noqa: BLE001 — persist failure must not break the run
                pass

    disc = str(args.get("sub_task_id") or "")
    run_id = f"hubcmd-{command}-{hub_id}-{disc}".rstrip("-")
    await supervisor.spawn(session_id, run_id, _run_and_persist())


def _load_proposals_json(proposals_path: str) -> dict[str, Any]:
    """Load ``proposals.json`` from a research-propose outputs dir or file path.

    Mirrors ``tool_dispatcher._seed_from_dashboard_args`` (~:1326-1338): a dir is
    resolved to ``<dir>/proposals.json``; a bad/missing file yields ``{}`` so the
    hub opens (empty Selection tab) rather than raising.
    """
    if not proposals_path:
        return {}
    p = _Path(proposals_path)
    if p.is_dir():
        p = p / "proposals.json"
    if p.is_file():
        try:
            return _json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            logger.warning(
                "[open_dashboard] proposals load failed (%s): %s", proposals_path, exc
            )
    return {}


async def _dispatch_open_dashboard(
    websocket: WebSocket,
    session_id: str,
    send_safe: Any,
    data: dict[str, Any],
) -> None:
    """Handle an ``open_dashboard`` WS frame (R1 — chat "Go To Experiment Hub").

    NET-NEW inbound frame; a **sibling of ``hub_command``**. Opens + seeds the
    Experiment Hub subtab OUT-OF-TURN. Two hard constraints (verified in the
    plan): (i) it MUST leave any in-flight Phase-2b turn running — this handler is
    a sibling of ``hub_command`` and never touches ``active_task``; (ii) it MUST
    NOT put to ``active_input_queue`` (the pending input stays live so the SOP
    holds at Phase 2b; the in-hub confirm advances it via R2).

    Seeds proposals from the canonical
    ``phase_outputs["research_propose__proposals_path"]`` (the path the SOP passes
    as ``--proposals-path``), loads ``proposals.json``, canonicalizes to the hub
    dict, opens the hub with ``auto_implement=False``, and emits the one-shot
    ``dashboard_open`` frame the FE ``case 'dashboard_open'`` renders. Best-effort:
    a failure reports an ``error`` frame, never raises.
    """
    dashboard_id = str(data.get("dashboard_id") or "experiment_hub")
    raw_selected = data.get("selected_ids") or []
    if isinstance(raw_selected, str):
        selected_ids = [s.strip() for s in raw_selected.split(",") if s.strip()]
    elif isinstance(raw_selected, (list, tuple)):
        selected_ids = [str(x).strip() for x in raw_selected if str(x).strip()]
    else:
        selected_ids = []

    app_state = websocket.app.state
    store = getattr(getattr(app_state, "data_service", None), "session_store", None)
    registry = getattr(app_state, "connection_registry", None)
    if store is None or registry is None:
        await send_safe(
            {"type": "error", "message": "open_dashboard: hub runtime unavailable"}
        )
        return

    from openteam.server.services.hub_factory import (
        build_hub_controller,
        make_hub_event_emitter,
    )

    emit = make_hub_event_emitter(registry, {"hub_id": ""})
    built = build_hub_controller(
        session_store=store,
        session_id=session_id,
        session_context={},
        emit_event=emit,
        stream_sink=None,
    )
    if built is None:
        await send_safe(
            {
                "type": "error",
                "message": "open_dashboard: Experiment Hub backend unavailable",
            }
        )
        return
    controller, wc = built

    # Seed source: the canonical SOP-published proposals path. Do NOT read the
    # legacy `research_proposals_data` key (verified never written).
    proposals_path = str(
        (getattr(wc, "phase_outputs", None) or {}).get(
            "research_propose__proposals_path"
        )
        or ""
    )
    raw_proposals = _load_proposals_json(proposals_path)

    from agent_foundation.common.data_models.proposal.parser import (
        canonicalize_proposal_index_to_hub_dict,
    )

    hub_proposals = canonicalize_proposal_index_to_hub_dict(raw_proposals or {})

    # Build the dashboard_open seed the same way the in-turn opener does
    # (tool_dispatcher.create_experiment_hub:1049-1077 / open_experiment_hub) so
    # the Selection tab renders identically. Selection tab, empty runQueue
    # (auto_implement=False → Path B).
    seed: dict[str, Any] = {
        "selected_proposal_ids": selected_ids,
        "selected_details": [{"id": pid} for pid in selected_ids],
        "proposals_data": hub_proposals,
        "custom_queries": [],
        "group_by": "batch",
        "auto_implement": False,
        "initial_view": "selection",
        "runQueue": [],
        "activeView": 0,
        "unlockedViewIds": [0],
        "scenarioState": {
            "selectionSnapshot": {
                "proposals": hub_proposals,
                "selectedProposals": list(selected_ids),
                "customQueries": [],
            }
        },
    }

    # Open the hub out-of-turn (auto_implement=False). Returns the multi_task_id
    # (idempotent: focuses the existing hub if one is already open for the SOP).
    try:
        mid = await controller.open_experiment_hub(
            proposals_data=hub_proposals,
            pre_select_top_n=5,
            initial_view="selection",
        )
    except Exception as exc:  # noqa: BLE001 — surface as error, never raise
        logger.warning("[open_dashboard] open_experiment_hub failed: %s", exc)
        mid = None
    # Persist the mutated workflow_context (active_multi_task_id + phase_outputs).
    try:
        store.update_workflow_context(session_id, wc.to_dict())
    except Exception as exc:  # noqa: BLE001 — persist best-effort
        logger.warning("[open_dashboard] workflow_context persist failed: %s", exc)

    hub_id = str(mid or f"{dashboard_id}-{uuid.uuid4().hex[:8]}")

    # Resolve the dashboard manifest from the tool registry's dashboard_config
    # (mirrors tool_dispatcher._open_dashboard_impl:1190-1194) and persist a
    # dashboard_ref restore marker so a reconnect rebuilds the subtab.
    manifest_dict: dict[str, Any] = {"id": dashboard_id}
    try:
        from agent_foundation.resources.tools.registry import load_all_tools
        from agent_foundation.server.dashboard.dashboard_protocol import (
            DashboardManifest,
        )

        _tools_dir = _Path(__file__).resolve().parent.parent / "resources" / "tools"
        _registry = load_all_tools(extra_dirs=[_tools_dir])
        _tool_def = _registry.get(dashboard_id)
        _dashboard_config = getattr(_tool_def, "dashboard_config", None) or {}
        manifest = DashboardManifest.from_dashboard_config(
            dashboard_id, _dashboard_config
        )
        manifest_dict = manifest.to_dict()
        _label = _dashboard_config.get("label") or dashboard_id
        _icon = _dashboard_config.get("icon") or ""
        try:
            store.append_message(
                session_id,
                {
                    "id": f"dashboard-ref-{hub_id}",
                    "role": "dashboard_ref",
                    "hubId": hub_id,
                    "dashboardId": dashboard_id,
                    "label": _label,
                    "icon": _icon,
                    "status": "open",
                    "timestamp": _make_timestamp(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — restore marker best-effort
            logger.warning("[open_dashboard] dashboard_ref persist failed: %s", exc)
        if hasattr(store, "save_dashboard_state"):
            try:
                store.save_dashboard_state(
                    session_id,
                    {"active_hub_id": hub_id, "dashboard_id": dashboard_id},
                )
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning(
                    "[open_dashboard] dashboard_state persist failed: %s", exc
                )
    except Exception as exc:  # noqa: BLE001 — manifest resolve best-effort
        logger.warning("[open_dashboard] manifest resolve failed: %s", exc)

    # Emit the one-shot dashboard_open the FE consumes to create/focus the subtab.
    await send_safe(
        {
            "type": "dashboard_open",
            "hub_id": hub_id,
            "manifest": manifest_dict,
            "seed": seed,
        }
    )
    logger.info(
        "[open_dashboard] opened %s (hub_id=%s) for session %s (selected=%d)",
        dashboard_id,
        hub_id,
        session_id,
        len(selected_ids),
    )


async def _advance_phase3_to_3b(
    websocket: WebSocket,
    session_id: str,
    active_task: Any,
) -> bool:
    """R4 (N6 steps 1-4) — out-of-turn advance of the model_optimization SOP from
    Phase 3 → 3b in response to the hub's ``evolution_complete``.

    This is the codebase's FIRST out-of-turn ``sop_state`` write. A bare
    ``phase_outputs`` write + ``_check_phase_completion()`` is NOT enough — it
    mutates only in-memory state (lost on eviction/restart) and can be clobbered
    by a mid-flight turn's turn-exit persist. So, in order:

      1. Quiesce any in-flight turn (``_quiesce_session``) so its trailing persist
         can't overwrite us.
      2. Get the live cached CI (``None`` ⇒ mock ⇒ bail); write the declared
         Phase-3 output ``experiment_hub_evolution`` into ``sop_state.phase_outputs``
         (the dict Strategy 3 reads) and call ``_check_phase_completion()``.
      3. Persist ``sop_state`` exactly as the turn-exit writer does.
      4. Mirror ``workflow_context`` for the FE phase mirror.

    Returns ``True`` when the advance ran (caller then renders 3b via a normal
    turn), ``False`` on mock/no-CI (nothing to do).
    """
    app_state = websocket.app.state
    data_svc = getattr(app_state, "data_service", None)
    conv_svc = getattr(app_state, "conversation_service", None)
    store = getattr(data_svc, "session_store", None)
    if conv_svc is None or store is None:
        return False

    # 1. Quiesce any in-flight turn so its finally-block persist can't clobber us.
    if active_task is not None and not active_task.done():
        await _quiesce_session(active_task, conv_svc, session_id)

    # 2. Get the live CI + advance. None ⇒ mock ⇒ nothing to do.
    session = data_svc.get_session(session_id)
    if not hasattr(conv_svc, "_get_session_inferencer"):
        return False
    try:
        ci = conv_svc._get_session_inferencer(session_id, session=session)
    except Exception as exc:  # noqa: BLE001 — treat build failure as no-op
        logger.warning("[evolution_complete] inferencer build failed: %s", exc)
        return False
    if ci is None:
        logger.info("[evolution_complete] mock/no CI — skipping SOP advance")
        return False
    sop_state = getattr(ci, "sop_state", None)
    if sop_state is None or getattr(sop_state, "phase_outputs", None) is None:
        logger.info("[evolution_complete] no live sop_state — skipping SOP advance")
        return False
    # Write the DECLARED Phase-3 output into SOPState.phase_outputs (the dict
    # Strategy 3 reads — distinct from WorkflowContext.phase_outputs), then fire
    # _check_phase_completion → Strategy 3 advances 3→3b.
    sop_state.phase_outputs["experiment_hub_evolution"] = True
    try:
        ci._check_phase_completion()
    except Exception as exc:  # noqa: BLE001 — advance best-effort; still persist
        logger.warning("[evolution_complete] _check_phase_completion raised: %s", exc)

    # 3. Persist sop_state exactly as the turn-exit writer does (atomic).
    try:
        snap = conv_svc._sop_snapshot(ci)
        store.update_session(
            session_id,
            {
                "sop_state": snap["sop_state"],
                "suspended_sops": snap["suspended_sops"],
            },
        )
    except Exception as exc:  # noqa: BLE001 — persist best-effort
        logger.warning("[evolution_complete] sop_state persist failed: %s", exc)

    # 4. Mirror workflow_context for the FE phase pill. The advance mutated
    # sop_state.current_phase / .phase_outputs, but the FE pill reads
    # workflow_context (rebuilt from ci.prior_context). Sync prior_context FROM
    # sop_state (forward), then persist via the conversation service's own
    # canonical writer (rebuilds a WorkflowContext and calls
    # update_workflow_context — mirrors _dispatch_hub_command:511's intent).
    try:
        prior = getattr(ci, "prior_context", None)
        if isinstance(prior, dict):
            prior["current_phase"] = getattr(sop_state, "current_phase", None)
            _ps = getattr(sop_state, "phase_status", None)
            prior["phase_status"] = (
                getattr(_ps, "value", _ps)
                if _ps is not None
                else prior.get("phase_status")
            )
            _po = getattr(sop_state, "phase_outputs", None)
            if isinstance(_po, dict):
                prior.setdefault("phase_outputs", {})
                prior["phase_outputs"].update(_po)
        if session is not None and hasattr(conv_svc, "_persist_workflow_updates"):
            conv_svc._persist_workflow_updates(session, prior or {}, data_svc)
    except Exception as exc:  # noqa: BLE001 — mirror best-effort
        logger.warning("[evolution_complete] workflow_context mirror failed: %s", exc)

    logger.info(
        "[evolution_complete] advanced SOP for session %s; current_phase=%s",
        session_id,
        getattr(sop_state, "current_phase", "?"),
    )
    return True


@router.websocket("/manager")
async def manager_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id: str | None = None
    active_task: asyncio.Task[Any] | None = None
    # Shared queue for conversation tool input (confirmation, clarification).
    # Set by process_message() when a turn starts, read by the main loop
    # when pending_input_response messages arrive from the frontend.
    active_input_queue: asyncio.Queue[Any] | None = None
    # Patch 3.4 — per-task registries for dev slash commands (/task, /mock_task, ...).
    # Populated by _try_dev_slash_command; consumed by `cancel` and `pending_input_response`
    # handlers in the main loop to route by `task_id`.
    dev_tool_tasks: dict[str, asyncio.Task[Any]] = {}
    dev_tool_input_queues: dict[str, asyncio.Queue[Any]] = {}
    # Connection-scoped pending-input metadata cache (keyed by pending_input_id).
    # Written by WebSocketInteractive.asend_response (conversation path only),
    # read+popped by the pending_input_response handler to persist widget
    # submissions as widget_response history messages.
    pending_input_cache: dict[str, Any] = {}

    async def send_safe(msg: dict[str, Any]) -> None:
        """Send JSON to client. Logs errors but does not raise."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(msg)
        except Exception as e:
            logger.warning("send_safe failed (type=%s): %s", msg.get("type"), e)

    async def heartbeat_loop() -> None:
        """Send heartbeat every 30 seconds to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(30)
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({"type": "heartbeat"})
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def process_message(
        sid: str, text: str, *, message_id: str | None = None
    ) -> None:
        """Process a user message: persist, call LLM, stream tokens back.

        Uses run_conversation_turn() (workflow-controlled agentic loop) when
        available, falling back to astream_response() for mock backend.

        ``message_id`` (server-side resume re-injection): when given, it is the
        persisted id of the KEPT clicked turn. It wins over the WS frame's id so
        ``append_message``'s id-dedup matches the already-present turn and does
        NOT duplicate it — the re-run then proceeds exactly like a fresh turn.
        """
        nonlocal active_input_queue

        # Dev slash commands: intercept before conversation flow
        data_svc = websocket.app.state.data_service
        _ss = getattr(data_svc, "session_store", None)
        if await _try_dev_slash_command(
            text,
            sid,
            send_safe,
            dev_tool_tasks,
            dev_tool_input_queues,
            session_store=_ss,
            pending_input_cache=pending_input_cache,
            snapshot_store=getattr(
                websocket.app.state,
                "task_graph_snapshots",
                None,
            ),
        ):
            return
        conv_svc = getattr(websocket.app.state, "conversation_service", None)

        if not conv_svc or not hasattr(data_svc, "append_message"):
            await send_safe(
                {"type": "error", "message": "Conversation service not available"}
            )
            return

        # 1. Persist user message. Stamp the turn it triggers so resume +
        # drop-tasks can map a clicked human message → turn N unambiguously
        # (the message is appended before this turn's dir is created, so
        # next_turn_number returns the turn-to-be).
        # Use the client-supplied message_id when present so the optimistic UI
        # bubble and the persisted message share one id — this lets "resume from
        # this turn" target a turn sent in the CURRENT session (no reload needed),
        # not just turns rehydrated from a session_init.
        user_msg = {
            "id": message_id or data.get("message_id") or f"msg-{uuid.uuid4().hex[:8]}",
            "role": "manager",
            "content": text,
            "timestamp": _make_timestamp(),
        }
        _ss = getattr(data_svc, "session_store", None)
        if _ss is not None and hasattr(_ss, "next_turn_number"):
            try:
                user_msg["turn_number"] = _ss.next_turn_number(sid)
            except Exception as exc:
                logger.warning("next_turn_number failed for %s: %s", sid, exc)
        if data.get("is_auto_advance"):
            user_msg["metadata"] = {"is_auto_advance": True}
        session = data_svc.append_message(sid, user_msg)
        if session is None:
            await send_safe({"type": "error", "message": f"Session {sid} not found"})
            return

        # 2. Signal streaming start (= request_in_flight ON). Emitted only after
        # the pre-checks above (service-available, session-found) pass, so any
        # earlier return needs no terminal frame.
        await send_safe({"type": "message_start"})

        async def _emit_error_terminal(err_text: str) -> None:
            """Emit exactly ONE terminal message_end{error} + persist an error
            assistant message, then clear busy with status:error.

            message_id provenance: prefer the active round id from the
            conversation interactive; else mint a route id.
            """
            try:
                active_mid = getattr(interactive, "current_message_id", None)
            except (NameError, UnboundLocalError):
                active_mid = None
            message_id = active_mid or f"msg-{uuid.uuid4().hex[:8]}"
            await send_safe(
                {
                    "type": "message_end",
                    "error": True,
                    "message_id": message_id,
                    "final_content": err_text,
                }
            )
            try:
                data_svc.append_message(
                    sid,
                    {
                        "id": message_id,
                        "role": "assistant",
                        "agent_name": "Orchestrator",
                        "agent_id": "orchestrator",
                        "content": err_text,
                        "timestamp": _make_timestamp(),
                        "error": True,
                    },
                )
            except Exception as persist_exc:
                logger.warning("error-message persist failed: %s", persist_exc)
            # Clear-point (d): a turn error kills this turn's await — any widget
            # it emitted is stale, so drop the marker (single choke-point for all
            # process_message error exits). Idempotent; no-op if nothing pending.
            _estore = getattr(data_svc, "session_store", None)
            if _estore is not None and hasattr(_estore, "clear_pending_input"):
                try:
                    _estore.clear_pending_input(sid)
                except Exception as _eexc:
                    logger.warning("clear_pending_input (turn error) failed: %s", _eexc)
            await send_safe({"type": "status", "status": "error"})

        interactive = None  # bound below on the agentic path; referenced by
        # _emit_error_terminal for round-id provenance.

        try:
            # Use workflow-controlled agentic loop when a real inferencer
            # is available for this session. Mock falls through to
            # astream_response (canned-response branch). If the backend
            # build fails (e.g., claude_cli without claude on PATH), surface
            # a clear error to the client instead of crashing the route.
            existing_session = data_svc.get_session(sid)
            has_agentic_inferencer = False
            if hasattr(conv_svc, "run_conversation_turn") and hasattr(
                conv_svc, "_get_session_inferencer"
            ):
                try:
                    has_agentic_inferencer = (
                        conv_svc._get_session_inferencer(sid, session=existing_session)
                        is not None
                    )
                except Exception as build_exc:
                    logger.exception("Failed to build inferencer for session %s", sid)
                    # Busy is already ON (message_start emitted) — emit the
                    # balanced terminal message_end{error} + persist before
                    # returning so the UI clears request_in_flight.
                    await _emit_error_terminal(f"Backend unavailable: {build_exc}")
                    return
            if has_agentic_inferencer:
                from openteam.server.services.websocket_interactive import (
                    WebSocketInteractive,
                )

                active_input_queue = asyncio.Queue()
                # Pass the per-connection routing table so this interactive (the
                # one injected into the tool dispatcher) can mint registered
                # per-task child interactives via for_background_task().
                interactive = WebSocketInteractive(
                    send_safe,
                    active_input_queue,
                    task_input_queues=dev_tool_input_queues,
                    pending_input_cache=pending_input_cache,
                    snapshot_store=getattr(
                        websocket.app.state,
                        "task_graph_snapshots",
                        None,
                    ),
                    session_id=sid,
                    # Durable pending-widget persistence (Layer 2, Piece 1).
                    data_service=getattr(websocket.app.state, "data_service", None),
                )

                result = await conv_svc.run_conversation_turn(
                    session,
                    text,
                    interactive=interactive,
                    data_service=data_svc,
                )
                # Agentic path: per-round persistence + per-round message_end
                # bubbles are owned by ConversationService.on_round_complete.
                # The route only clears the turn-level busy with a terminal
                # status:complete (no post-loop assistant append / save_turn_data
                # / bubble-committing message_end here).
                await send_safe({"type": "status", "status": "complete"})
            else:
                # Fallback: mock backend via astream_response
                final_content = ""
                async for chunk in conv_svc.astream_response(session, text):
                    final_content += chunk
                    await send_safe(
                        {
                            "type": "token",
                            "content": chunk,
                            "metadata": {"agent_name": "Orchestrator"},
                        }
                    )

                # ── Mock path: route still owns persistence + bubble commit ──
                # 3. Compute turn number (1-based: count of existing assistant
                # messages before this one).
                existing_session = data_svc.get_session(sid)
                turn_number = (
                    sum(
                        1
                        for m in (existing_session or {}).get("messages", [])
                        if m.get("role") in ("assistant", "agent")
                    )
                    + 1
                )

                # 4. Persist assistant response (include turn_number for history lookup)
                msg_id = f"msg-{uuid.uuid4().hex[:8]}"
                assistant_msg = {
                    "id": msg_id,
                    "role": "assistant",
                    "agent_name": "Orchestrator",
                    "agent_id": "orchestrator",
                    "content": final_content,
                    "timestamp": _make_timestamp(),
                    "turn_number": turn_number,
                }
                data_svc.append_message(sid, assistant_msg)

                # 5. Capture prompt data and persist to disk (survives restarts)
                prompt_data = {}
                if hasattr(conv_svc, "get_last_prompt_data"):
                    try:
                        prompt_data = conv_svc.get_last_prompt_data(sid)
                    except Exception as e:
                        logger.warning("get_last_prompt_data failed: %s", e)
                        prompt_data = {}

                if hasattr(data_svc, "save_turn_data"):
                    try:
                        turn_data = dict(prompt_data) if prompt_data else {}
                        turn_data["inference_response"] = final_content
                        turn_data["user_input"] = text
                        turn_data["api_payload"] = {
                            "messages": (existing_session or {}).get("messages", []),
                        }
                        data_svc.save_turn_data(sid, turn_number, turn_data)
                    except Exception as e:
                        logger.warning("save_turn_data failed: %s", e)

                # 6. Signal streaming end — include prompt_data inline.
                import json as _json

                try:
                    _json.dumps(prompt_data)
                except (TypeError, ValueError) as e:
                    logger.warning(
                        "prompt_data is not JSON-serializable (%s) — sending without it",
                        e,
                    )
                    prompt_data = {}

                await send_safe(
                    {
                        "type": "message_end",
                        "final_content": final_content,
                        "message_id": msg_id,
                        "turn_number": turn_number,
                        "prompt_data": prompt_data,
                    }
                )

        except asyncio.CancelledError:
            logger.info("Message processing cancelled (session=%s)", sid)
            await send_safe(
                {"type": "status", "status": "complete", "detail": "Cancelled"}
            )
        except Exception as e:
            logger.error(
                "Error processing message (session=%s): %s", sid, e, exc_info=True
            )
            # Emit exactly ONE terminal message_end{error} + persist an error
            # assistant message, then status:error (busy off). message_id is the
            # active round id if a round is in flight, else a freshly minted id.
            await _emit_error_terminal(f"I encountered an error: {e!s}")
        finally:
            active_input_queue = None

    async def _run_resume_from_round(
        sid: str, target_turn: int, target_round: int, resume_blob: dict[str, Any]
    ) -> None:
        """Drive a round-resume auto-forward: build a fresh interactive and run
        ConversationService.resume_conversation_from_round with NO user-message
        append (the loop self-continues from round ``target_round``). Emits the
        turn-level busy envelope (message_start / terminal status). Per-round
        bubbles + message_end are owned by ConversationService._on_round_complete,
        so this does NOT emit bubble-committing frames itself. Mirrors the agentic
        branch of process_message; the error/cancel paths are replicated here.
        """
        nonlocal active_input_queue
        data_svc = websocket.app.state.data_service
        conv_svc = getattr(websocket.app.state, "conversation_service", None)
        session = data_svc.get_session(sid)
        if (
            conv_svc is None
            or session is None
            or not hasattr(conv_svc, "resume_conversation_from_round")
        ):
            await send_safe({"type": "error", "message": "Resume not available"})
            return

        # Busy ON (mirror process_message). Round bubbles stream as usual.
        await send_safe({"type": "message_start"})

        from openteam.server.services.websocket_interactive import WebSocketInteractive

        active_input_queue = asyncio.Queue()
        interactive = WebSocketInteractive(
            send_safe,
            active_input_queue,
            task_input_queues=dev_tool_input_queues,
            pending_input_cache=pending_input_cache,
            snapshot_store=getattr(
                websocket.app.state,
                "task_graph_snapshots",
                None,
            ),
            session_id=sid,
            data_service=data_svc,
        )
        try:
            await conv_svc.resume_conversation_from_round(
                session,
                target_turn=target_turn,
                target_round=target_round,
                resume_blob=resume_blob,
                interactive=interactive,
                data_service=data_svc,
            )
            await send_safe({"type": "status", "status": "complete"})
        except asyncio.CancelledError:
            logger.info("Resume-from-round cancelled (session=%s)", sid)
            await send_safe(
                {"type": "status", "status": "complete", "detail": "Cancelled"}
            )
        except Exception as e:
            logger.error(
                "Error resuming from round (session=%s): %s", sid, e, exc_info=True
            )
            _mid = (
                getattr(interactive, "current_message_id", None)
                or f"msg-{uuid.uuid4().hex[:8]}"
            )
            _err = f"I encountered an error resuming: {e!s}"
            await send_safe(
                {
                    "type": "message_end",
                    "error": True,
                    "message_id": _mid,
                    "final_content": _err,
                }
            )
            try:
                data_svc.append_message(
                    sid,
                    {
                        "id": _mid,
                        "role": "assistant",
                        "agent_name": "Orchestrator",
                        "agent_id": "orchestrator",
                        "content": _err,
                        "timestamp": _make_timestamp(),
                        "error": True,
                    },
                )
            except Exception as persist_exc:
                logger.warning("resume error-message persist failed: %s", persist_exc)
            await send_safe({"type": "status", "status": "error"})
        finally:
            active_input_queue = None

    async def _run_widget_recovery(sid, marker, blob, raw_value):
        """Drive deterministic pending-widget recovery: rebuild the interactive
        and run ConversationService.resume_conversation_from_widget, which injects
        the user's answer at the widget's iteration (NO LLM re-inference) and
        continues the SOP. Mirrors _run_resume_from_round's busy envelope."""
        nonlocal active_input_queue
        data_svc = websocket.app.state.data_service
        conv_svc = getattr(websocket.app.state, "conversation_service", None)
        session = data_svc.get_session(sid)
        if (
            conv_svc is None
            or session is None
            or not hasattr(conv_svc, "resume_conversation_from_widget")
        ):
            await send_safe(
                {"type": "error", "message": "Widget recovery not available"}
            )
            return
        from openteam.server.services.websocket_interactive import WebSocketInteractive

        await send_safe({"type": "message_start"})
        active_input_queue = asyncio.Queue()
        interactive = WebSocketInteractive(
            send_safe,
            active_input_queue,
            task_input_queues=dev_tool_input_queues,
            pending_input_cache=pending_input_cache,
            snapshot_store=getattr(websocket.app.state, "task_graph_snapshots", None),
            session_id=sid,
            data_service=data_svc,
        )
        try:
            await conv_svc.resume_conversation_from_widget(
                session,
                marker=marker,
                blob=blob,
                raw_value=raw_value,
                interactive=interactive,
                data_service=data_svc,
            )
            await send_safe({"type": "status", "status": "complete"})
        except asyncio.CancelledError:
            logger.info("Widget recovery cancelled (session=%s)", sid)
            await send_safe(
                {"type": "status", "status": "complete", "detail": "Cancelled"}
            )
        except Exception as e:
            logger.error(
                "Widget recovery failed (session=%s): %s", sid, e, exc_info=True
            )
            await send_safe(
                {"type": "error", "message": f"Widget recovery failed: {e!s}"}
            )
        finally:
            active_input_queue = None

    async def _maybe_recover_pending_widget(sid, data, parsed_content, active_task):
        """pending_input_response with NO live turn (reconnect/restart): validate
        against the durable marker + drive recovery. Returns the (possibly new)
        active_task."""
        _dsvc = websocket.app.state.data_service
        _store = getattr(_dsvc, "session_store", None)
        marker = _store.get_pending_input(sid) if _store is not None else None
        if not marker:
            await send_safe(
                {"type": "error", "message": "No pending widget to answer."}
            )
            return active_task
        # Reject a stale/duplicate answer for a superseded widget.
        _ans_id = data.get("pending_input_id")
        if (
            _ans_id
            and marker.get("pending_input_id")
            and _ans_id != marker.get("pending_input_id")
        ):
            logger.info("pending_input_response id mismatch (stale) — ignoring")
            return active_task
        blob = _store.read_pending_input_blob(sid)
        if blob is None:
            logger.warning("pending widget blob missing (session=%s) — clearing", sid)
            _store.clear_pending_input(sid)
            await send_safe(
                {"type": "error", "message": "Pending widget expired; please retry."}
            )
            return active_task
        # Persist the widget_response card from the marker (the connection cache
        # is empty after a reconnect). Dedup by id via append_message.
        try:
            _dsvc.append_message(
                sid,
                {
                    "id": marker.get("pending_input_id"),
                    "role": "widget_response",
                    "prompt": marker.get("prompt"),
                    "response": parsed_content,
                    "inputMode": marker.get("input_mode"),
                    "viewPath": marker.get("viewPath"),
                    "viewLabel": marker.get("viewLabel"),
                    "viewType": marker.get("viewType"),
                    "turn_number": marker.get("turn_number"),
                    "round_index": marker.get("round_index"),
                },
            )
        except Exception as e:
            logger.warning("widget_response (marker) persist failed: %s", e)
        if active_task and not active_task.done():
            active_task.cancel()
        return asyncio.create_task(
            _run_widget_recovery(sid, marker, blob, parsed_content)
        )

    heartbeat_task = asyncio.create_task(heartbeat_loop())

    try:
        # Wait for init message with session_id
        try:
            first_msg = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except asyncio.TimeoutError:
            await send_safe({"type": "error", "message": "No init message received"})
            return

        if first_msg.get("type") == "init" and first_msg.get("session_id"):
            session_id = first_msg["session_id"]
        else:
            await send_safe(
                {"type": "error", "message": "Expected init message with session_id"}
            )
            return

        # Load existing session and send to client
        data_svc = websocket.app.state.data_service
        # Repair any task_ref chips left stuck at starting/running by a prior
        # crash/restart so restored subtabs show their real (disk-derived) status.
        # Pass the bg-task liveness snapshot so a WS RECONNECT during a live task
        # doesn't false-positive its chip as "interrupted" — reconcile skips any
        # task whose task_id is still in ConversationService's registry.
        _init_ss = getattr(data_svc, "session_store", None)
        _init_conv_svc = getattr(websocket.app.state, "conversation_service", None)
        if _init_ss is not None and hasattr(_init_ss, "reconcile_task_ref_statuses"):
            _init_live: set[str] | None = None
            if _init_conv_svc is not None and hasattr(
                _init_conv_svc, "get_live_task_ids"
            ):
                try:
                    _init_live = _init_conv_svc.get_live_task_ids(session_id)
                except Exception:
                    _init_live = None
            try:
                _init_ss.reconcile_task_ref_statuses(
                    session_id, live_task_ids=_init_live
                )
            except Exception as exc:
                logger.warning("reconcile_task_ref_statuses failed: %s", exc)
        # Repair stale dashboard_ref subtab markers too (mirror of task_ref) so a
        # hub whose state sidecar vanished isn't offered as a dead subtab (#18).
        if _init_ss is not None and hasattr(
            _init_ss, "reconcile_dashboard_ref_statuses"
        ):
            try:
                _init_ss.reconcile_dashboard_ref_statuses(session_id)
            except Exception as exc:
                logger.warning("reconcile_dashboard_ref_statuses failed: %s", exc)
        # Heal a hub's task queue from disk (#18) so a server restart that
        # orphaned a local run doesn't leave the queue wedged on a phantom
        # `running` entry.
        if _init_ss is not None and hasattr(_init_ss, "reconcile_hub_queues"):
            try:
                _init_ss.reconcile_hub_queues(session_id)
            except Exception as exc:
                logger.warning("reconcile_hub_queues failed: %s", exc)
        # Register this connection so REST-triggered hub actions (which fire
        # outside an agentic turn) can push dashboard_event/dashboard_status to
        # every open tab (#12). Deregistered in the finally below.
        _conn_registry = getattr(websocket.app.state, "connection_registry", None)
        if _conn_registry is not None:
            try:
                await _conn_registry.register(session_id, send_safe)
            except Exception as exc:
                logger.warning("connection_registry.register failed: %s", exc)
        session = data_svc.get_session(session_id)
        if session:
            await send_safe(
                {
                    "type": "session_init",
                    "session_id": session_id,
                    "messages": session.get("messages", []),
                }
            )
        else:
            await send_safe(
                {
                    "type": "session_init",
                    "session_id": session_id,
                    "messages": [],
                }
            )

        # v4 Phase 4.1 — opportunistic prune + per-task graph replay. The
        # prune is cheap (O(active snapshots)) and bounded; doing it on each
        # connect keeps terminated snapshots from accumulating without a
        # background timer. Replay restores the UI's sub-graphs/streams that
        # were live before this connection started — the rebuild-from-task_ref
        # path in useManagerChat handles task chips, this handles the graph
        # state.
        _snap_store = getattr(websocket.app.state, "task_graph_snapshots", None)
        if _snap_store is not None:
            try:
                _snap_store.prune_expired()
            except Exception as exc:
                logger.warning("snapshot prune failed: %s", exc)
            await _replay_task_graph_snapshots(_snap_store, session_id, send_safe)

        # Layer 2, Piece 2 — re-display a persisted pending widget. A prior
        # connection may have emitted a conversation widget the user never
        # answered before the socket dropped (idle proxy close) or the server
        # restarted; session_init above nulled the FE's pendingInput. Re-emit the
        # widget from the durable marker so it reappears and stays answerable —
        # the answer routes through pending_input_response's no-live-turn branch,
        # which recovers the turn deterministically (Piece 3). Plain-init path
        # ONLY — NOT _evict_and_send_session_init, whose resume branches re-run
        # the turn and re-emit the widget themselves (a re-emit there double-fires).
        if _init_ss is not None and hasattr(_init_ss, "get_pending_input"):
            try:
                _pw_marker = _init_ss.get_pending_input(session_id)
            except Exception as exc:
                _pw_marker = None
                logger.warning("get_pending_input failed: %s", exc)
            if _pw_marker:
                _pw_frame: dict[str, Any] = {
                    "type": "pending_input",
                    "content": _pw_marker.get("prompt", ""),
                    "pending_input_id": _pw_marker.get("pending_input_id"),
                    "restored": True,
                }
                for _src, _dst in (
                    ("input_mode", "input_mode"),
                    ("prompt_data", "prompt_data"),
                    ("message_id", "message_id"),
                    ("round_index", "round_index"),
                    ("turn_number", "turn_number"),
                ):
                    _v = _pw_marker.get(_src)
                    if _v is not None:
                        _pw_frame[_dst] = _v
                await send_safe(_pw_frame)
                logger.info(
                    "re-displayed persisted pending widget (session=%s, id=%s)",
                    session_id,
                    _pw_marker.get("pending_input_id"),
                )

        logger.info("Manager WebSocket connected (session=%s)", session_id)

        # Main message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await send_safe({"type": "pong"})

            elif msg_type == "cancel":
                # R7.1 — cancel the dev-tool task identified by task_id (if provided)
                # in addition to the conversation task. UI's cancelRequest now sends
                # task_id from the active task_status context.
                cancelled_task_id = data.get("task_id")
                if cancelled_task_id and cancelled_task_id in dev_tool_tasks:
                    dt = dev_tool_tasks[cancelled_task_id]
                    if not dt.done():
                        dt.cancel()
                if active_task and not active_task.done():
                    active_task.cancel()
                # Clear-point (b): a cancel supersedes any pending widget — drop
                # the durable marker so it isn't re-displayed on the next connect.
                _csvc = websocket.app.state.data_service
                _cstore = getattr(_csvc, "session_store", None)
                if _cstore is not None and hasattr(_cstore, "clear_pending_input"):
                    try:
                        _cstore.clear_pending_input(session_id)
                    except Exception as _cexc:
                        logger.warning("clear_pending_input (cancel) failed: %s", _cexc)
                await send_safe(
                    {"type": "status", "status": "complete", "detail": "Cancelled"}
                )

            elif msg_type == "pending_input_response":
                # R9b — route by task_id when present (dev tool widget responses
                # like Approve/Reject from /task-confirm); fall back to the
                # conversation queue otherwise.
                import json as _json

                pi_task_id = data.get("task_id")
                raw_content = data.get("content", "")
                try:
                    parsed_content = _json.loads(raw_content)
                except (ValueError, TypeError):
                    parsed_content = raw_content
                target_q = dev_tool_input_queues.get(pi_task_id) if pi_task_id else None
                if target_q is None:
                    target_q = active_input_queue
                if target_q is not None:
                    await target_q.put(parsed_content)

                    # LIVE path: persist the widget_response card from the
                    # connection cache (dev-tool/task path has no entry → no-op),
                    # and clear the durable marker (the answer resolves it, so a
                    # later reconnect won't re-display a ghost).
                    pi_id = data.get("pending_input_id")
                    cache_entry = pending_input_cache.get(pi_id) if pi_id else None
                    if cache_entry and cache_entry.get("scope") == "conversation":
                        data_svc = websocket.app.state.data_service
                        widget_response = {
                            "id": pi_id,
                            "role": "widget_response",
                            "prompt": cache_entry.get("prompt"),
                            "response": parsed_content,
                            "inputMode": cache_entry.get("input_mode"),
                            "viewPath": cache_entry.get("viewPath"),
                            "viewLabel": cache_entry.get("viewLabel"),
                            "viewType": cache_entry.get("viewType"),
                            "turn_number": cache_entry.get("turn_number"),
                            "round_index": cache_entry.get("round_index"),
                        }
                        try:
                            data_svc.append_message(
                                cache_entry.get("session_id") or session_id,
                                widget_response,
                            )
                        except Exception as persist_exc:
                            logger.warning(
                                "widget_response persist failed: %s", persist_exc
                            )
                        pending_input_cache.pop(pi_id, None)
                        _wstore = getattr(data_svc, "session_store", None)
                        if _wstore is not None and hasattr(
                            _wstore, "clear_pending_input"
                        ):
                            try:
                                _wstore.clear_pending_input(
                                    cache_entry.get("session_id") or session_id
                                )
                            except Exception as _clr:
                                logger.warning("clear_pending_input failed: %s", _clr)
                else:
                    # RECOVERY path: no live turn (reconnect/restart) — the
                    # awaiting loop is gone. Recover deterministically from the
                    # durable marker (Layer 2, Piece 3).
                    active_task = await _maybe_recover_pending_widget(
                        session_id, data, parsed_content, active_task
                    )

            elif msg_type in ("resume_from_turn", "restore_checkpoint"):
                # Both mutate the session on disk, so the order is load-bearing:
                # FIRST quiesce in-flight work (cancel the active turn + cancel/await
                # agent-invoked background tasks) so the copy/rmtree can't race a
                # live writer; THEN mutate; THEN evict the cached inferencer (so the
                # next turn rebuilds and re-restores sop_state) and re-broadcast a
                # fresh session_init (the UI auto-replays the human turn on resume).
                data_svc = websocket.app.state.data_service
                _ss = getattr(data_svc, "session_store", None)
                conv_svc = getattr(websocket.app.state, "conversation_service", None)
                try:
                    resumed_content: str | None = None
                    resumed_message_id: str | None = None
                    if msg_type == "resume_from_turn":
                        message_id = data.get("message_id")
                        drop_tasks = bool(data.get("drop_tasks"))
                        if (
                            not message_id
                            or _ss is None
                            or not hasattr(_ss, "truncate_session_at_message")
                        ):
                            await send_safe(
                                {"type": "error", "message": "Resume not available"}
                            )
                            continue
                        await _quiesce_session(active_task, conv_svc, session_id)
                        # Off-load the blocking FS ops (checkpoint copytree +
                        # truncate rmtree) to a worker thread so they don't stall
                        # the event loop / starve the WS heartbeat (the reconnect
                        # that used to silently drop the client-side replay).
                        await asyncio.to_thread(_ss.checkpoint_session, session_id)
                        _trunc = await asyncio.to_thread(
                            _ss.truncate_session_at_message,
                            session_id,
                            message_id,
                            drop_tasks=drop_tasks,
                        )
                        # Capture the KEPT human turn for server-side re-injection.
                        _resumed = (_trunc or {}).get("resumed_message") or {}
                        if _resumed.get("role") in ("manager", "user"):
                            resumed_content = (_resumed.get("content") or "").strip()
                            resumed_message_id = _resumed.get("id")
                    else:  # restore_checkpoint
                        checkpoint = data.get("checkpoint")
                        if (
                            not checkpoint
                            or _ss is None
                            or not hasattr(_ss, "restore_checkpoint")
                        ):
                            await send_safe(
                                {"type": "error", "message": "Restore not available"}
                            )
                            continue
                        await _quiesce_session(active_task, conv_svc, session_id)
                        if _ss.restore_checkpoint(session_id, checkpoint) is None:
                            await send_safe(
                                {
                                    "type": "error",
                                    "message": f"Checkpoint {checkpoint} not found",
                                }
                            )
                            continue
                    await _evict_and_send_session_init(
                        data_svc,
                        conv_svc,
                        session_id,
                        send_safe,
                        snapshot_store=getattr(
                            websocket.app.state,
                            "task_graph_snapshots",
                            None,
                        ),
                    )
                    # ── R1: SERVER-SIDE re-injection ──────────────────────────
                    # The truncated session_init above cleared the UI to
                    # [welcome … kept turn] (no flash). Re-run that kept turn
                    # through the NORMAL pipeline — the backend OWNS re-injection,
                    # with no dependency on any client-side replay / sendMessage
                    # guard (the fragile path that silently dropped the turn on a
                    # WS reconnect). append_message's id-dedup (message_id) avoids
                    # a duplicate; run_conversation_turn re-enters the restored SOP.
                    if resumed_content:
                        if active_task and not active_task.done():
                            active_task.cancel()
                        active_task = asyncio.create_task(
                            process_message(
                                session_id,
                                resumed_content,
                                message_id=resumed_message_id,
                            )
                        )
                except Exception as exc:
                    logger.error(
                        "%s failed (session=%s): %s",
                        msg_type,
                        session_id,
                        exc,
                        exc_info=True,
                    )
                    await send_safe(
                        {"type": "error", "message": f"{msg_type} failed: {exc}"}
                    )

            elif msg_type == "resume_from_round":
                # Round-level resume: like resume_from_turn but rewinds to a
                # specific assistant ROUND and auto-forwards the loop (NO user
                # re-injection). The ordering is load-bearing (mirror
                # resume_from_turn): quiesce → checkpoint → READ the round-entry
                # blob (BEFORE truncate deletes round_Y/) → truncate → evict +
                # session_init → drive the resume as active_task.
                data_svc = websocket.app.state.data_service
                _ss = getattr(data_svc, "session_store", None)
                conv_svc = getattr(websocket.app.state, "conversation_service", None)
                try:
                    message_id = data.get("message_id")
                    drop_tasks = bool(data.get("drop_tasks"))
                    if (
                        not message_id
                        or _ss is None
                        or not hasattr(_ss, "read_round_resume_state")
                        or conv_svc is None
                    ):
                        await send_safe(
                            {"type": "error", "message": "Round resume not available"}
                        )
                        continue
                    # Read the round-entry snapshot FIRST. None → mock/legacy/empty
                    # round with no snapshot → reject gracefully (turn-resume still
                    # works). This also guards the truncate/evict below from running
                    # when there's nothing to resume.
                    _info = _ss.read_round_resume_state(session_id, message_id)
                    if not _info:
                        await send_safe(
                            {
                                "type": "error",
                                "message": "Round resume unavailable for this round",
                            }
                        )
                        continue
                    await _quiesce_session(active_task, conv_svc, session_id)
                    # Off-load blocking FS ops to a worker thread (as resume_from_turn
                    # does) with lightweight progress frames driving the UI banner.
                    await send_safe({"type": "resume_status", "stage": "checkpointing"})
                    await asyncio.to_thread(_ss.checkpoint_session, session_id)
                    await send_safe({"type": "resume_status", "stage": "truncating"})
                    await asyncio.to_thread(
                        _ss.truncate_session_at_round,
                        session_id,
                        message_id,
                        drop_tasks=drop_tasks,
                        resume_blob=_info["blob"],
                    )
                    await send_safe({"type": "resume_status", "stage": "restoring"})
                    await _evict_and_send_session_init(
                        data_svc,
                        conv_svc,
                        session_id,
                        send_safe,
                        snapshot_store=getattr(
                            websocket.app.state,
                            "task_graph_snapshots",
                            None,
                        ),
                    )
                    # Drive the auto-forward re-run (no user re-injection).
                    if active_task and not active_task.done():
                        active_task.cancel()
                    active_task = asyncio.create_task(
                        _run_resume_from_round(
                            session_id,
                            int(_info["turn"]),
                            int(_info["round"]),
                            _info["blob"],
                        )
                    )
                except Exception as exc:
                    logger.error(
                        "resume_from_round failed (session=%s): %s",
                        session_id,
                        exc,
                        exc_info=True,
                    )
                    await send_safe(
                        {
                            "type": "error",
                            "message": f"resume_from_round failed: {exc}",
                        }
                    )

            elif msg_type == "request_graph_replay":
                # v4 Phase 4.1 — on-demand graph replay. Triggered by the UI
                # when the user opens a task subtab or drills into a node
                # whose sub-graph is missing from the local store (e.g. after
                # HMR or focus-context switch into a previously-unrendered
                # task). Optional task_id filters replay to just that task;
                # absent task_id replays every snapshot in the session.
                _snap_store = getattr(
                    websocket.app.state,
                    "task_graph_snapshots",
                    None,
                )
                requested_task_id = data.get("task_id")
                if _snap_store is None or not session_id:
                    continue
                if requested_task_id:
                    # Fix 3 — 3-tier resolution (in-memory → disk-persisted →
                    # reconstruct-from-disk) so a COMPLETED task opened after the
                    # 600s TTL / a server restart (or a legacy pre-fix task) still
                    # replays its graph. Resolve the task's on-disk workspace from
                    # its task_ref chip — the chip task_id (e.g. "task-142caa36")
                    # is NOT the workspace dir name — so tiers 2/3 can find it.
                    _task_ws = None
                    _dsvc = getattr(websocket.app.state, "data_service", None)
                    try:
                        _sess = _dsvc.get_session(session_id) if _dsvc else None
                    except Exception:
                        _sess = None
                    for _m in (_sess or {}).get("messages") or []:
                        if (
                            _m.get("id") == f"task-ref-{requested_task_id}"
                            or _m.get("taskId") == requested_task_id
                        ):
                            _task_ws = _m.get("workspace")
                            break
                    # get_or_load does blocking FS I/O (disk read / reconstruction
                    # walk) — run it OFF the WS event loop.
                    try:
                        snap = await asyncio.to_thread(
                            _snap_store.get_or_load,
                            session_id,
                            requested_task_id,
                            _task_ws,
                        )
                    except Exception as exc:
                        logger.warning(
                            "[replay] get_or_load failed (%s): %s",
                            requested_task_id,
                            exc,
                        )
                        snap = None
                    if snap is None:
                        continue
                    for ev in snap.to_replay_events():
                        await send_safe(ev)
                else:
                    await _replay_task_graph_snapshots(
                        _snap_store,
                        session_id,
                        send_safe,
                    )

            elif msg_type == "hub_command":
                _hub_cmd = str(data.get("command") or "")
                if _hub_cmd == "confirm_proposal_selection":
                    # R2 — in-hub "Confirm Selection & Start". Do BOTH atomically:
                    # (a) launch implementation via the hub's self-executing
                    # _exec_implement_hypothesis (same rail as `implement_hypothesis`),
                    # and (b) resolve the still-open Phase-2b pending input by
                    # putting {"selected_proposals": ids} to active_input_queue
                    # (exactly as the pending_input_response handler does), which
                    # resumes the parked turn → _continue_after_widget →
                    # _check_phase_completion advances 2b→3 with NO new sop_state
                    # mutation. Fall back to _maybe_recover_pending_widget if no
                    # live turn (post-reconnect).
                    _args = data.get("args") or {}
                    _raw_ids = (
                        _args.get("selected_ids") or data.get("selected_ids") or []
                    )
                    if isinstance(_raw_ids, str):
                        _confirm_ids = [
                            s.strip() for s in _raw_ids.split(",") if s.strip()
                        ]
                    else:
                        _confirm_ids = [
                            str(x).strip() for x in _raw_ids if str(x).strip()
                        ]
                    # (a) launch implementation (once) via the existing hub rail.
                    await _dispatch_hub_command(
                        websocket,
                        session_id,
                        send_safe,
                        {
                            "type": "hub_command",
                            "command": "implement_hypothesis",
                            "hub_id": data.get("hub_id") or data.get("multi_task_id"),
                            "selected_ids": _confirm_ids,
                        },
                    )
                    # (b) resolve the Phase-2b pending input on the conversation rail.
                    _resolution = {"selected_proposals": _confirm_ids}
                    if active_input_queue is not None:
                        await active_input_queue.put(_resolution)
                    else:
                        # No live turn (reconnect/restart) — recover deterministically
                        # from the durable marker (Layer 2, Piece 3).
                        active_task = await _maybe_recover_pending_widget(
                            session_id,
                            {"content": _json.dumps(_resolution)},
                            _resolution,
                            active_task,
                        )
                elif _hub_cmd == "evolution_complete":
                    # R4 — in-hub "Done — summarize & evolve". The codebase's FIRST
                    # out-of-turn sop_state write; run the full N6 sequence.
                    # Steps 1-4 (quiesce → advance sop_state → persist → mirror wc)
                    # live in the module-level helper; step 5 (render 3b) spawns a
                    # normal auto-advance turn HERE (process_message is loop-nested
                    # and reads the closure `data` for is_auto_advance).
                    _advanced = await _advance_phase3_to_3b(
                        websocket, session_id, active_task
                    )
                    if _advanced:
                        # Step 5 — render the compact Phase-3b summary via a normal
                        # turn. Mutate the closure `data` so process_message stamps
                        # the synthetic user message is_auto_advance (FE hides it)
                        # and mints a fresh message_id.
                        _note = (
                            "[System notification: The Experiment Hub evolution "
                            "cycle was marked complete by the user. Produce the "
                            "compact Phase-3b summary of results and decide whether "
                            "to continue evolving per <SOPNextStepGuidance>.]"
                        )
                        data["is_auto_advance"] = True
                        data.pop("message_id", None)
                        if active_task and not active_task.done():
                            active_task.cancel()
                        active_task = asyncio.create_task(
                            process_message(session_id, _note)
                        )
                else:
                    # Experiment Hub long-running actions (implement-hypothesis /
                    # resume / combos) arrive over this socket as `hub_command`
                    # frames (not REST); dispatch out-of-turn via the hub controller
                    # + run supervisor (events flow back as the dashboard_* protocol).
                    await _dispatch_hub_command(websocket, session_id, send_safe, data)

            elif msg_type == "open_dashboard":
                # R1 — chat "Go To Experiment Hub" open+seed handoff. A NET-NEW
                # inbound frame, SIBLING of `hub_command`. It deliberately does
                # NOT cancel `active_task` (the parked Phase-2b turn stays running)
                # and does NOT put to `active_input_queue` (the pending input stays
                # live; the SOP holds at Phase 2b until the in-hub confirm).
                await _dispatch_open_dashboard(websocket, session_id, send_safe, data)

            elif msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue
                # Cancel previous in-flight task
                if active_task and not active_task.done():
                    active_task.cancel()
                # Clear-point (c): a new user message supersedes any pending
                # widget (the user chose to move on rather than answer it). Drop
                # the marker BEFORE the fresh turn runs so its own widget (if any)
                # writes a new marker without racing this clear.
                _mstore = getattr(
                    websocket.app.state.data_service, "session_store", None
                )
                if _mstore is not None and hasattr(_mstore, "clear_pending_input"):
                    try:
                        _mstore.clear_pending_input(session_id)
                    except Exception as _mexc:
                        logger.warning(
                            "clear_pending_input (new message) failed: %s", _mexc
                        )
                active_task = asyncio.create_task(process_message(session_id, content))

    except WebSocketDisconnect:
        logger.info("Manager WebSocket disconnected (session=%s)", session_id)
    except Exception as e:
        logger.error(
            "Manager WebSocket error (session=%s): %s", session_id, e, exc_info=True
        )
    finally:
        heartbeat_task.cancel()
        if active_task and not active_task.done():
            active_task.cancel()
        # Deregister from the connection registry. A refresh/close just removes
        # this send-callback; in-flight out-of-turn hub runs are NOT cancelled
        # here — they continue server-side and reconcile on reconnect (#18).
        if session_id:
            _cr = getattr(websocket.app.state, "connection_registry", None)
            if _cr is not None:
                try:
                    await _cr.deregister(session_id, send_safe)
                except Exception as exc:
                    logger.warning("connection_registry.deregister failed: %s", exc)
