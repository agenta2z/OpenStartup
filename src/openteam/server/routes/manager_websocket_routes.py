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
import shlex as _shlex
_REPEATABLE_KEYS = {"override"}
_TASK_BOOL_FLAGS = {"plan", "execute", "full", "confirm",
                    "no_dual", "analysis", "multi_iter",
                    "in_place", "copy_workspace"}
# CANONICAL CONVENTION (Option D, 2026-05-18): `arguments` dict keys are
# ALWAYS underscored. _parse_slash_args normalizes incoming `--foo-bar`
# tokens via `.replace("-","_")` so this set MUST use underscore form too.

# Patch 3.1 — task-* alias mapping (cmd_name is post-`replace("-", "_")` so keys use _).
_TASK_MODE_ALIASES = {"task_plan": "plan", "task_execute": "execute",
                      "task_full": "full", "task_confirm": "confirm"}


def _parse_slash_args(args_str: str, bool_flags: set[str] = frozenset()) -> dict[str, Any]:
    """Parse ``--key value`` pairs + bare ``--flag`` + positional ``request``.

    R10 rules:
      - known bool-flag → {key: True}, advance 1
      - next token starts with `--` → bare flag, advance 1
      - otherwise consume next token as value
    Repeated keys in `_REPEATABLE_KEYS` accumulate into a list.
    All unconsumed non-flag tokens become the positional `request` (joined by space).
    """
    result: dict[str, Any] = {}
    try:
        parts = _shlex.split(args_str, posix=True)
    except ValueError:
        parts = args_str.split()
    consumed: set[int] = set()
    i = 0
    while i < len(parts):
        if parts[i].startswith("--"):
            # CANONICAL CONVENTION (Option D, 2026-05-18): normalize incoming
            # dash form to underscores so `arguments` dict keys are uniformly
            # underscored. Bool-flag set `_TASK_BOOL_FLAGS` is also stored in
            # underscore form (see line 55-57) so the `key in bool_flags` check
            # below works AFTER normalization.
            key = parts[i].lstrip("-").replace("-", "_")
            if key in bool_flags or i + 1 >= len(parts) or parts[i + 1].startswith("--"):
                result[key] = True
                consumed.add(i); i += 1
            else:
                val = parts[i + 1]
                if key in _REPEATABLE_KEYS:
                    result.setdefault(key, []).append(val)
                else:
                    result[key] = val
                consumed.update({i, i + 1}); i += 2
        else:
            i += 1
    positional = [parts[j] for j in range(len(parts))
                  if j not in consumed and not parts[j].startswith("--")]
    if positional:
        result.setdefault("request", " ".join(positional))
    return result


async def _try_dev_slash_command(
    text: str,
    sid: str,
    send_safe: Any,
    dev_tool_tasks: "dict[str, asyncio.Task[Any]]" = None,
    dev_tool_input_queues: "dict[str, asyncio.Queue[Any]]" = None,
    session_store=None,
    pending_input_cache: "dict[str, Any] | None" = None,
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
                if (
                    cmd_name in getattr(_t, "aliases", [])
                    or cmd_name == getattr(_t, "preferred_prompt_alias", "")
                ):
                    cmd_name = _name
                    tool_def = _t
                    break

        if not tool_def:
            available = [n for n, t in registry.items() if not t.agent_enabled]
            await send_safe({
                "type": "error",
                "message": f"Unknown command `/{cmd_name}`. Available: {', '.join(f'/{n}' for n in available) or '(none)'}",
            })
            return True

        # Patch 3.1 — gate via slash_enabled (corrected formula: inner default True
        # to match ToolDefinition.agent_enabled default).
        tool_json_path = _Path(tool_def.source_path)
        try:
            tool_data = _json.loads(tool_json_path.read_text(encoding="utf-8"))
        except OSError as exc:
            await send_safe({"type": "error", "message": f"Could not load tool.json for /{cmd_name}: {exc}"})
            return True

        slash_enabled = tool_data.get("slash_enabled", not tool_data.get("agent_enabled", True))
        if not slash_enabled:
            return False  # let the agent path (ToolDispatcher) handle it

        if tool_data.get("dev_mode_only", True) and not _os.environ.get("OPENTEAM_DEV_MODE"):
            await send_safe({
                "type": "error",
                "message": f"`/{cmd_name}` requires OPENTEAM_DEV_MODE=1",
            })
            return True

        # Patch 3.3 — pass /task's known bool flags so the parser handles --plan etc. correctly.
        bool_flags = _TASK_BOOL_FLAGS if cmd_name == "task" else frozenset()
        parsed_args = _parse_slash_args(args_str, bool_flags=bool_flags)
        if cmd_name == "task" and injected_mode and "mode" not in parsed_args:
            parsed_args["mode"] = injected_mode

        task_id = f"dev-{uuid.uuid4().hex[:8]}"

        await send_safe({
            "type": "task_status",
            "task_id": task_id,
            "tool_name": cmd_name,
            "status": "starting",
            "request": f"/{cmd_name} {args_str}".strip(),
        })

        from openteam.server.services.websocket_interactive import WebSocketInteractive

        # Patch 3.4 — register per-task input queue so pending_input_response can route to it.
        input_queue: "asyncio.Queue[Any]" = asyncio.Queue()
        interactive = WebSocketInteractive(
            send_safe, input_queue, task_input_queues=dev_tool_input_queues,
            pending_input_cache=pending_input_cache,
        )
        dev_tool_input_queues[task_id] = input_queue

        async def _run_dev_tool() -> None:
            try:
                executor_ref = tool_data.get("executor")
                if not executor_ref:
                    await send_safe({"type": "error", "message": f"No executor defined for /{cmd_name}"})
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
                            "falling back to standalone workspace", sid,
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

                await send_safe({
                    "type": "task_completed",
                    "task_id": task_id,
                    "tool_name": cmd_name,
                    "result_summary": result_text[:500],
                    "context_updates": context_updates,
                })
            except asyncio.CancelledError:
                # R7.4 — CancelledError is BaseException-derived; must be caught explicitly.
                try:
                    await send_safe({
                        "type": "task_status",
                        "task_id": task_id,
                        "tool_name": cmd_name,
                        "status": "cancelled",
                    })
                finally:
                    raise  # propagate so the asyncio task enters cancelled state
            except Exception as exc:
                logger.exception("[dev_slash] /%s failed", cmd_name)
                await send_safe({
                    "type": "task_status",
                    "task_id": task_id,
                    "tool_name": cmd_name,
                    "status": "error",
                    "error": str(exc),
                })

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

    async def process_message(sid: str, text: str) -> None:
        """Process a user message: persist, call LLM, stream tokens back.

        Uses run_conversation_turn() (workflow-controlled agentic loop) when
        available, falling back to astream_response() for mock backend.
        """
        nonlocal active_input_queue

        # Dev slash commands: intercept before conversation flow
        data_svc = websocket.app.state.data_service
        _ss = getattr(data_svc, "session_store", None)
        if await _try_dev_slash_command(
            text, sid, send_safe, dev_tool_tasks, dev_tool_input_queues,
            session_store=_ss, pending_input_cache=pending_input_cache,
        ):
            return
        conv_svc = getattr(websocket.app.state, "conversation_service", None)

        if not conv_svc or not hasattr(data_svc, "append_message"):
            await send_safe({"type": "error", "message": "Conversation service not available"})
            return

        # 1. Persist user message
        user_msg = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "role": "manager",
            "content": text,
            "timestamp": _make_timestamp(),
        }
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
            await send_safe({
                "type": "message_end",
                "error": True,
                "message_id": message_id,
                "final_content": err_text,
            })
            try:
                data_svc.append_message(sid, {
                    "id": message_id,
                    "role": "assistant",
                    "agent_name": "Orchestrator",
                    "agent_id": "orchestrator",
                    "content": err_text,
                    "timestamp": _make_timestamp(),
                    "error": True,
                })
            except Exception as persist_exc:
                logger.warning("error-message persist failed: %s", persist_exc)
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
                        conv_svc._get_session_inferencer(
                            sid, session=existing_session
                        )
                        is not None
                    )
                except Exception as build_exc:
                    logger.exception(
                        "Failed to build inferencer for session %s", sid
                    )
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
                    send_safe, active_input_queue,
                    task_input_queues=dev_tool_input_queues,
                    pending_input_cache=pending_input_cache,
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
                    await send_safe({
                        "type": "token",
                        "content": chunk,
                        "metadata": {"agent_name": "Orchestrator"},
                    })

                # ── Mock path: route still owns persistence + bubble commit ──
                # 3. Compute turn number (1-based: count of existing assistant
                # messages before this one).
                existing_session = data_svc.get_session(sid)
                turn_number = sum(
                    1 for m in (existing_session or {}).get("messages", [])
                    if m.get("role") in ("assistant", "agent")
                ) + 1

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
                        "prompt_data is not JSON-serializable (%s) — sending without it", e
                    )
                    prompt_data = {}

                await send_safe({
                    "type": "message_end",
                    "final_content": final_content,
                    "message_id": msg_id,
                    "turn_number": turn_number,
                    "prompt_data": prompt_data,
                })

        except asyncio.CancelledError:
            logger.info("Message processing cancelled (session=%s)", sid)
            await send_safe({"type": "status", "status": "complete", "detail": "Cancelled"})
        except Exception as e:
            logger.error("Error processing message (session=%s): %s", sid, e, exc_info=True)
            # Emit exactly ONE terminal message_end{error} + persist an error
            # assistant message, then status:error (busy off). message_id is the
            # active round id if a round is in flight, else a freshly minted id.
            await _emit_error_terminal(f"I encountered an error: {e!s}")
        finally:
            active_input_queue = None

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
            await send_safe({"type": "error", "message": "Expected init message with session_id"})
            return

        # Load existing session and send to client
        data_svc = websocket.app.state.data_service
        session = data_svc.get_session(session_id)
        if session:
            await send_safe({
                "type": "session_init",
                "session_id": session_id,
                "messages": session.get("messages", []),
            })
        else:
            await send_safe({
                "type": "session_init",
                "session_id": session_id,
                "messages": [],
            })

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
                await send_safe({"type": "status", "status": "complete", "detail": "Cancelled"})

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

                # Widget-card persist: ONLY for conversation-scoped pending
                # inputs (the dev-tool/task path has no cache entry and persists
                # nothing). Independent of task_id. Dedup is handled by
                # append_message (keyed by message id == pending_input_id).
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

            elif msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue
                # Cancel previous in-flight task
                if active_task and not active_task.done():
                    active_task.cancel()
                active_task = asyncio.create_task(
                    process_message(session_id, content)
                )

    except WebSocketDisconnect:
        logger.info("Manager WebSocket disconnected (session=%s)", session_id)
    except Exception as e:
        logger.error("Manager WebSocket error (session=%s): %s", session_id, e, exc_info=True)
    finally:
        heartbeat_task.cancel()
        if active_task and not active_task.done():
            active_task.cancel()
