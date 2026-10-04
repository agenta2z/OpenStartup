"""The manager socket tells the conversation who wrote each turn's text.

A user's message runs with ``origin="user"``; the UI's auto-advance after a
background task (``is_auto_advance``) with ``origin="host_event"``; the
server-side re-run of a resumed turn with ``origin="resumed_turn"``. The route
runs on a bare FastAPI app with a real SessionStore and a conversation service
that records each turn.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Bootstrap sys.path
_HERE = Path(__file__).resolve()
_OPENSTARTUP = _HERE.parents[4]
_REPO_ROOT = _OPENSTARTUP.parent
for _dep in [
    _OPENSTARTUP / "src",
    _REPO_ROOT / "AgentFoundation" / "src",
    _REPO_ROOT / "RichPythonUtils" / "src",
]:
    p = str(_dep)
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openteam.server.routes.manager_websocket_routes import router
from openteam.server.services.data_service import RealSessionDataService
from openteam.server.services.session_store import SessionStore

_NOTE = "[System notification: Task 'task' (task-1) completed successfully.]"


class _Conversation:
    """The conversation service surface a manager-socket turn uses."""

    def __init__(self) -> None:
        self.turns: list[tuple[str, str]] = []

    def _get_session_inferencer(self, session_id, session=None):
        return object()

    async def run_conversation_turn(
        self, session, text, *, interactive, data_service=None, origin="user"
    ):
        self.turns.append((text, origin))


class TurnOriginTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="os_turn_origin_"))
        (tmp / "fixtures").mkdir()
        self.store = SessionStore(tmp / "rt", resume_server="new")
        self.sid = self.store.create_session("origin")["id"]
        self.conversation = _Conversation()
        self.app = FastAPI()
        self.app.state.data_service = RealSessionDataService(
            tmp / "fixtures", self.store
        )
        self.app.state.conversation_service = self.conversation
        self.app.include_router(router, prefix="/ws")

    def _run(self, *frames: dict) -> None:
        """Send each frame on one connection; wait for the turn it starts."""
        with (
            TestClient(self.app) as client,
            client.websocket_connect("/ws/manager") as ws,
        ):
            ws.send_json({"type": "init", "session_id": self.sid})
            self.assertEqual(ws.receive_json()["type"], "session_init")
            for frame in frames:
                ws.send_json(frame)
                while ws.receive_json()["type"] != "status":
                    pass

    def _messages(self) -> list[dict]:
        return self.store.get_session(self.sid)["messages"]

    def test_a_user_message_runs_as_a_user_turn(self) -> None:
        self._run({"type": "message", "content": "hello", "message_id": "u1"})
        self.assertEqual(self.conversation.turns, [("hello", "user")])
        self.assertNotIn("metadata", self._messages()[-1])

    def test_an_auto_advance_runs_as_a_host_event_turn(self) -> None:
        self._run({"type": "message", "content": _NOTE, "is_auto_advance": True})
        self.assertEqual(self.conversation.turns, [(_NOTE, "host_event")])
        self.assertEqual(self._messages()[-1]["metadata"], {"is_auto_advance": True})

    def test_a_resumed_turn_runs_again_as_a_resumed_turn(self) -> None:
        self._run(
            {"type": "message", "content": "one", "message_id": "u1"},
            {"type": "resume_from_turn", "message_id": "u1"},
        )
        self.assertEqual(
            self.conversation.turns, [("one", "user"), ("one", "resumed_turn")]
        )
        self.assertEqual([m["id"] for m in self._messages()][-1], "u1")


if __name__ == "__main__":
    unittest.main()
