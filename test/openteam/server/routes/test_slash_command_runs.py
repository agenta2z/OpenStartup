"""The manager socket hands a slash command's run to the session's background
tracking, so the session's delete, resume/restore and the server shutdown —
which cancel and await what is tracked — stop it.

The route runs on a bare FastAPI app with a real SessionStore; ``/mock_task``
is a real slash-command tool (a mock topology whose first step takes 15 s). The
conversation service records what it is handed and cancels it, as a delete
would.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class _Conversation:
    """The conversation service's background tracking: records each run and
    cancels it once it is under way."""

    def __init__(self) -> None:
        self.tracked: list[tuple[str, str]] = []

    def _get_session_inferencer(self, session_id, session=None):
        return object()

    def track_background_task(self, session_id, task_id, task) -> None:
        self.tracked.append((session_id, task_id))
        asyncio.get_running_loop().call_later(0.5, task.cancel)


class SlashCommandRunTest(unittest.TestCase):
    def test_a_slash_commands_run_is_tracked_as_the_sessions_background_task(
        self,
    ) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="os_slash_runs_"))
        (tmp / "fixtures").mkdir()
        store = SessionStore(tmp / "rt", resume_server="new")
        sid = store.create_session("slash")["id"]
        conversation = _Conversation()
        app = FastAPI()
        app.state.data_service = RealSessionDataService(tmp / "fixtures", store)
        app.state.conversation_service = conversation
        app.include_router(router, prefix="/ws")

        statuses: list[tuple[str, str]] = []
        with (
            mock.patch.dict(os.environ, {"OPENTEAM_DEV_MODE": "1"}),
            TestClient(app) as client,
            client.websocket_connect("/ws/manager") as ws,
        ):
            ws.send_json({"type": "init", "session_id": sid})
            self.assertEqual(ws.receive_json()["type"], "session_init")
            ws.send_json({"type": "message", "content": "/mock_task --speed 10"})
            while not statuses or statuses[-1][1] not in ("cancelled", "error", "done"):
                frame = ws.receive_json()
                if frame["type"] == "task_status":
                    statuses.append((frame["task_id"], frame["status"]))
                elif frame["type"] == "task_completed":
                    statuses.append((frame["task_id"], "done"))

        task_id = statuses[0][0]
        self.assertEqual(statuses[0][1], "starting")
        self.assertEqual(statuses[-1], (task_id, "cancelled"))
        self.assertEqual(conversation.tracked, [(sid, task_id)])


if __name__ == "__main__":
    unittest.main()
