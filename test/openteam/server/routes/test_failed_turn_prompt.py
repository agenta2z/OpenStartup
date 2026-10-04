"""A turn that fails keeps its View Prompt data: the manager socket's error
bubble carries the turn's prompt data, and the turn's saved prompt — what View
Prompt fetches after a reload — says how the turn ended.

The route runs on a bare FastAPI app with the real ConversationService and a
native backend built by the real factory; only the vendor is scripted, and it
fails every turn before replying.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

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

import openteam.server as openteam_server
from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.backend import (
    BackendCapabilities,
    CallerTools,
    L2Channel,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openteam.server.backends import factories as factories_mod
from openteam.server.backends.registry import BackendDescriptor, BackendRegistry
from openteam.server.routes.manager_websocket_routes import router
from openteam.server.services.conversation_service import ConversationService
from openteam.server.services.data_service import RealSessionDataService
from openteam.server.services.session_store import SessionStore

_TEMPLATES_DIR = (
    Path(openteam_server.__file__).parent / "resources" / "prompt_templates"
)
_CAPABILITIES = BackendCapabilities(
    kind="claude_sdk",
    caller_tools=CallerTools.INPROCESS,
    l2_channels=(L2Channel.HOOK,),
    pinned_session_id=True,
    exact_fork=True,
    turn_stop_hook=True,
    subagent_attribution=True,
    compaction_signal=True,
    persistent_process=True,
)


class _FailingVendor:
    """A vendor session that takes each turn and fails it before replying."""

    capabilities = _CAPABILITIES

    def __init__(self, spec, **_runtime) -> None:
        self.spec = spec
        self._session_id = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    async def open(self, request) -> None:
        self._session_id = request.session_id or uuid.uuid4().hex

    async def run_turn(self, request):
        raise RuntimeError("the vendor stopped responding")
        yield  # an async generator, as vendor turns are

    def fork_message_map(self, source: str, forked: str) -> dict:
        return {}

    async def interrupt(self) -> None:
        pass

    async def set_model(self, model: str) -> None:
        self.spec.model = model

    async def close(self) -> None:
        pass


class FailedTurnPromptTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="os_failed_turn_prompt_"))
        (tmp / "fixtures").mkdir()
        self.store = SessionStore(tmp / "rt", resume_server="new")
        self.data = RealSessionDataService(tmp / "fixtures", self.store)
        self.sid = self.store.create_session("failed turn")["id"]
        native = factories_mod._NativeBackend(
            name="native_test",
            kind="claude_sdk",
            display_name="Native (test)",
            description="",
            binary="claude",
            modules=(),
        )

        def build(ctx):
            inferencer = factories_mod._build_native(native, ctx)
            inferencer.backend_factory = _FailingVendor
            return inferencer

        self.registry = BackendRegistry()
        self.registry.register(
            "native_test", build, BackendDescriptor("native_test", "", "", native=True)
        )
        self.conversation = ConversationService(
            templates_dir=_TEMPLATES_DIR,
            llm_backend="native_test",
            working_dir=str(tmp / "work"),
            session_store=self.store,
        )
        self.app = FastAPI()
        self.app.state.data_service = self.data
        self.app.state.conversation_service = self.conversation
        self.app.include_router(router, prefix="/ws")

    def _send(self, text: str) -> list[dict]:
        frames: list[dict] = []
        with (
            patch("openteam.server.backends.get_registry", return_value=self.registry),
            TestClient(self.app) as client,
            client.websocket_connect("/ws/manager") as ws,
        ):
            ws.send_json({"type": "init", "session_id": self.sid})
            self.assertEqual(ws.receive_json()["type"], "session_init")
            ws.send_json({"type": "message", "content": text})
            while not (frames and frames[-1].get("type") == "status"):
                frames.append(ws.receive_json())
            client.portal.call(self.conversation.aclose_all)
        return frames

    def test_the_error_bubble_carries_the_failed_turns_prompt(self) -> None:
        frames = self._send("Summarize the design doc")

        self.assertEqual(frames[-1], {"type": "status", "status": "error"})
        (end,) = [f for f in frames if f.get("type") == "message_end"]
        self.assertTrue(end["error"])
        self.assertIn("the vendor stopped responding", end["final_content"])
        self.assertEqual(end["turn_number"], 1)
        prompt = end["prompt_data"]
        self.assertIn("## Turn outcome — uncertain", prompt["rendered_prompt"])
        self.assertIn("Summarize the design doc", prompt["rendered_prompt"])
        self.assertEqual(prompt["template_feed"]["turn_outcome"], "uncertain")

    def test_the_failed_turns_saved_prompt_says_how_it_ended(self) -> None:
        frames = self._send("Summarize the design doc")

        (end,) = [f for f in frames if f.get("type") == "message_end"]
        bubble = next(
            m
            for m in self.store.get_session(self.sid)["messages"]
            if m.get("id") == end["message_id"]
        )
        self.assertTrue(bubble["error"])
        self.assertEqual(bubble["turn_number"], 1)
        self.assertEqual(bubble.get("round_index"), end.get("round_index"))
        # What View Prompt fetches for this bubble after a reload.
        saved = self.data.get_turn_data(
            self.sid, bubble["turn_number"], round=bubble.get("round_index")
        )
        self.assertIn("## Turn outcome — uncertain", saved["rendered_prompt"])
        self.assertEqual(saved["template_feed"]["turn_outcome"], "uncertain")
        self.assertEqual(saved["user_input"], "Summarize the design doc")
        self.assertIn("the vendor stopped responding", saved["error"])
        # Saved over the turn's own summary, not in place of it.
        self.assertEqual((saved["turn_number"], saved["session_id"]), (1, self.sid))


if __name__ == "__main__":
    unittest.main()
