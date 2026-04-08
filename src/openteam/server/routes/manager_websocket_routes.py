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


@router.websocket("/manager")
async def manager_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id: str | None = None
    active_task: asyncio.Task[Any] | None = None

    async def send_safe(msg: dict[str, Any]) -> None:
        """Send JSON to client, silently ignoring errors."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(msg)
        except Exception:
            pass

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
        """Process a user message: persist, call LLM, stream tokens back."""
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
            # 3. Stream response tokens
            metadata = {"agent_name": "Orchestrator"}
            final_content = ""

            async for chunk in conv_svc.astream_response(session, text):
                final_content += chunk
                await send_safe({
                    "type": "token",
                    "content": chunk,
                    "metadata": metadata,
                })

            # 4. Persist assistant response
            msg_id = f"msg-{uuid.uuid4().hex[:8]}"
            assistant_msg = {
                "id": msg_id,
                "role": "assistant",
                "agent_name": "Orchestrator",
                "agent_id": "orchestrator",
                "content": final_content,
                "timestamp": _make_timestamp(),
            }
            data_svc.append_message(sid, assistant_msg)

            # 5. Signal streaming end
            await send_safe({
                "type": "message_end",
                "final_content": final_content,
                "message_id": msg_id,
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
