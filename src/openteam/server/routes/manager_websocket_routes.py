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


def _parse_slash_args(args_str: str) -> dict[str, str]:
    """Parse ``--key value`` pairs from a slash command's argument string."""
    result: dict[str, str] = {}
    parts = args_str.split()
    i = 0
    while i < len(parts):
        if parts[i].startswith("--") and i + 1 < len(parts):
            result[parts[i].lstrip("-")] = parts[i + 1]
            i += 2
        else:
            i += 1
    return result


async def _try_dev_slash_command(
    text: str, sid: str, send_safe: Any,
) -> bool:
    """Intercept ``/command-name --args`` dev slash commands.

    Returns True if the message was handled (caller should skip normal flow).
    Only processes tools with ``agent_enabled: false`` when ``OPENTEAM_DEV_MODE``
    is set in the environment. Hyphens in command names are normalized to
    underscores for tool registry lookup (e.g., /mock-task → mock_task).
    """
    m = _SLASH_CMD_RE.match(text.strip())
    if not m:
        return False

    cmd_name = m.group(1).replace("-", "_")
    args_str = m.group(2).strip()

    if not _os.environ.get("OPENTEAM_DEV_MODE"):
        await send_safe({
            "type": "error",
            "message": f"Dev commands require OPENTEAM_DEV_MODE=1 (got /{cmd_name})",
        })
        return True

    try:
        from agent_foundation.resources.tools.registry import load_all_tools

        tools_dir = _Path(__file__).resolve().parent.parent / "resources" / "tools"
        registry = load_all_tools(extra_dirs=[tools_dir])
        tool_def = registry.get(cmd_name)

        if not tool_def:
            available = [n for n, t in registry.items() if not t.agent_enabled]
            await send_safe({
                "type": "error",
                "message": f"Unknown command `/{cmd_name}`. Available: {', '.join(f'/{n}' for n in available) or '(none)'}",
            })
            return True

        if tool_def.agent_enabled:
            return False

        parsed_args = _parse_slash_args(args_str)
        task_id = f"dev-{uuid.uuid4().hex[:8]}"

        await send_safe({
            "type": "task_status",
            "task_id": task_id,
            "tool_name": cmd_name,
            "status": "starting",
            "request": f"/{cmd_name} {args_str}".strip(),
        })

        from openteam.server.services.websocket_interactive import WebSocketInteractive

        interactive = WebSocketInteractive(send_safe, asyncio.Queue())

        async def _run_dev_tool() -> None:
            try:
                # Resolve executor from tool.json via source_path
                # (ToolDefinition doesn't store the executor field;
                #  same pattern as ToolDispatcher._load_executors)
                tool_json_path = _Path(tool_def.source_path)
                tool_data = _json.loads(tool_json_path.read_text(encoding="utf-8"))
                executor_ref = tool_data.get("executor")
                if not executor_ref:
                    await send_safe({"type": "error", "message": f"No executor defined for /{cmd_name}"})
                    return

                module_path, func_name = executor_ref.rsplit(":", 1)
                import importlib
                mod = importlib.import_module(module_path)
                execute_fn = getattr(mod, func_name)

                session_context = {
                    "interactive": interactive,
                    "task_id": task_id,
                    "working_dir": str(tools_dir.parent.parent),
                }
                result = await execute_fn(parsed_args, session_context)
                result_text = result.get("output", str(result)) if isinstance(result, dict) else str(result)

                await send_safe({
                    "type": "task_completed",
                    "task_id": task_id,
                    "tool_name": cmd_name,
                    "result_summary": result_text[:500],
                })
            except Exception as exc:
                logger.exception("[dev_slash] /%s failed", cmd_name)
                await send_safe({
                    "type": "task_status",
                    "task_id": task_id,
                    "tool_name": cmd_name,
                    "status": "error",
                    "error": str(exc),
                })

        asyncio.create_task(_run_dev_tool())
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
        if await _try_dev_slash_command(text, sid, send_safe):
            return

        data_svc = websocket.app.state.data_service
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
        session = data_svc.append_message(sid, user_msg)
        if session is None:
            await send_safe({"type": "error", "message": f"Session {sid} not found"})
            return

        # 2. Signal streaming start
        await send_safe({"type": "message_start"})

        try:
            # Use workflow-controlled agentic loop when available
            if hasattr(conv_svc, "run_conversation_turn") and conv_svc._llm_backend == "rovodev":
                from openteam.server.services.websocket_interactive import (
                    WebSocketInteractive,
                )

                active_input_queue = asyncio.Queue()
                interactive = WebSocketInteractive(send_safe, active_input_queue)

                result = await conv_svc.run_conversation_turn(
                    session,
                    text,
                    interactive=interactive,
                    data_service=data_svc,
                )
                final_content = result.text if hasattr(result, "text") else str(result)
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

            # 3. Compute turn number (1-based: count of existing assistant messages before this one).
            # If the run_conversation_turn path attached a canonical turn_number on the
            # AgenticResult (set by ConversationService after run_agentic_loop), prefer
            # that — it accounts for multi-iteration agentic loops (widget interactions
            # internally count as turns) which the simple message-count heuristic misses.
            existing_session = data_svc.get_session(sid)
            turn_number = sum(
                1 for m in (existing_session or {}).get("messages", [])
                if m.get("role") in ("assistant", "agent")
            ) + 1
            try:
                _result_turn = getattr(result, "turn_number", None)
                if isinstance(_result_turn, int) and _result_turn > 0:
                    turn_number = _result_turn
            except (NameError, UnboundLocalError):
                pass  # Mock backend path doesn't set `result`

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

            # 5. Capture prompt data and persist to disk (survives server restarts)
            prompt_data = {}
            if hasattr(conv_svc, "get_last_prompt_data"):
                try:
                    prompt_data = conv_svc.get_last_prompt_data(sid)
                    logger.debug(
                        "get_last_prompt_data: rendered_prompt=%d chars, feed=%d keys",
                        len(prompt_data.get("rendered_prompt", "")),
                        len(prompt_data.get("template_feed", {})),
                    )
                except Exception as e:
                    logger.warning("get_last_prompt_data failed: %s", e)
                    prompt_data = {}

            if hasattr(data_svc, "save_turn_data"):
                try:
                    # Save rich turn data (prompt + response + input + history)
                    turn_data = dict(prompt_data) if prompt_data else {}
                    turn_data["inference_response"] = final_content
                    turn_data["user_input"] = text
                    turn_data["api_payload"] = {
                        "messages": (existing_session or {}).get("messages", []),
                    }
                    data_svc.save_turn_data(sid, turn_number, turn_data)
                    logger.debug("Saved turn %d data to disk", turn_number)
                except Exception as e:
                    logger.warning("save_turn_data failed: %s", e)

            # 6. Signal streaming end — include prompt_data inline (instant access)
            # and turn_number (for history fetch on page reload).
            # Verify prompt_data is JSON-safe before including — fall back to {} if not.
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
            # Persist error as assistant message
            error_msg = {
                "id": f"msg-{uuid.uuid4().hex[:8]}",
                "role": "assistant",
                "agent_name": "Orchestrator",
                "agent_id": "orchestrator",
                "content": f"I encountered an error: {e!s}",
                "timestamp": _make_timestamp(),
                "error": True,
            }
            data_svc.append_message(sid, error_msg)
            await send_safe({"type": "error", "message": str(e)})
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
                if active_task and not active_task.done():
                    active_task.cancel()
                await send_safe({"type": "status", "status": "complete", "detail": "Cancelled"})

            elif msg_type == "pending_input_response":
                # Route conversation tool responses to the active turn's input queue.
                # Try to parse JSON so the inferencer receives a dict for structured
                # responses (choice_index, variable_override, etc.) — plain strings
                # like "yes" / "no" will fail json.loads and pass through as-is.
                if active_input_queue is not None:
                    import json as _json
                    raw_content = data.get("content", "")
                    try:
                        parsed_content = _json.loads(raw_content)
                    except (ValueError, TypeError):
                        parsed_content = raw_content
                    await active_input_queue.put(parsed_content)

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
