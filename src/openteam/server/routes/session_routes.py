"""Manager session endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: str | None = None


class SendMessageRequest(BaseModel):
    message: str


def _make_timestamp() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("")
@router.get("/")
async def list_sessions(request: Request):
    svc = request.app.state.data_service
    return {"data": svc.get_sessions()}


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str):
    svc = request.app.state.data_service
    session = svc.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    return {"data": session}


@router.post("")
@router.post("/")
async def create_session(
    request: Request, body: CreateSessionRequest = CreateSessionRequest()
):
    svc = request.app.state.data_service
    if not hasattr(svc, "create_session"):
        raise HTTPException(400, "Session creation not available in mock mode")
    session = svc.create_session(title=body.title)
    return {"data": session}


@router.delete("/{session_id}")
async def delete_session(request: Request, session_id: str):
    svc = request.app.state.data_service
    if not hasattr(svc, "delete_session"):
        raise HTTPException(400, "Session deletion not available in mock mode")
    if not svc.delete_session(session_id):
        raise HTTPException(404, f"Session {session_id} not found")
    # Evict per-session inferencer to free memory
    conv_svc = getattr(request.app.state, "conversation_service", None)
    if conv_svc and hasattr(conv_svc, "evict_session_inferencer"):
        conv_svc.evict_session_inferencer(session_id)
    return {"data": {"deleted": True}}


@router.get("/{session_id}/turns/{turn_number}")
async def get_turn_data(request: Request, session_id: str, turn_number: int):
    """Fetch per-turn prompt metadata (template, feed, rendered prompt).

    Used by the frontend "View Prompt" button for history messages.
    turn_number is 1-based (first assistant message = turn 1).
    """
    svc = request.app.state.data_service
    if not hasattr(svc, "get_turn_data"):
        raise HTTPException(400, "Turn data not available in mock mode")
    data = svc.get_turn_data(session_id, turn_number)
    # Welcome message (turn 1) and other non-LLM turns have no saved prompt data.
    # Return graceful empty payload instead of 404 so the UI can show a friendly
    # "no prompt data" message rather than a console error.
    if data is None:
        return {"data": {
            "rendered_prompt": "",
            "template_source": "",
            "note": f"No prompt data for turn {turn_number} (likely a welcome or non-LLM turn)",
        }}
    return {"data": data}


@router.post("/{session_id}/messages")
async def send_message(request: Request, session_id: str, body: SendMessageRequest):
    """Send a user message to a session and get an AI response.

    Flow:
    1. Validate session exists
    2. Append user message to session
    3. Call ConversationService.get_response()
    4. Append assistant response to session
    5. Return both messages

    User message is persisted BEFORE calling LLM — if the LLM call fails,
    the user's message is still saved and an error message is appended.
    """
    svc = request.app.state.data_service
    conversation_svc = getattr(request.app.state, "conversation_service", None)

    # Check capabilities
    if not hasattr(svc, "append_message"):
        raise HTTPException(400, "Messaging not available in mock mode")
    if not conversation_svc:
        raise HTTPException(503, "Conversation service not initialized")

    # 1. Get current session
    session = svc.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")

    # 2. Build and append user message
    user_msg = {
        "id": f"msg-{uuid4().hex[:8]}",
        "role": "manager",
        "content": body.message,
        "timestamp": _make_timestamp(),
    }
    session = svc.append_message(session_id, user_msg)

    # 3. Get AI response
    try:
        response_text = await conversation_svc.get_response(session, body.message)
    except Exception as e:
        # Still saved the user message — append error as system message
        error_msg = {
            "id": f"msg-{uuid4().hex[:8]}",
            "role": "assistant",
            "agent_name": "Orchestrator",
            "agent_id": "orchestrator",
            "content": f"I encountered an error processing your request: {e!s}",
            "timestamp": _make_timestamp(),
            "error": True,
        }
        svc.append_message(session_id, error_msg)
        return {
            "data": {
                "user_message": user_msg,
                "assistant_message": error_msg,
                "error": True,
            }
        }

    # 4. Append assistant response
    assistant_msg = {
        "id": f"msg-{uuid4().hex[:8]}",
        "role": "assistant",
        "agent_name": "Orchestrator",
        "agent_id": "orchestrator",
        "content": response_text,
        "timestamp": _make_timestamp(),
    }
    svc.append_message(session_id, assistant_msg)

    # 5. Return both messages
    return {"data": {"user_message": user_msg, "assistant_message": assistant_msg}}
