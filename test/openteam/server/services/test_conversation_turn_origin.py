"""ConversationService passes each turn's origin to the conversational host:
the caller's for a fresh turn, ``resumed_turn`` for a round resume and
``widget_answer`` for a recovered widget answer."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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
from openteam.server.services.conversation_service import ConversationService
from openteam.server.services.session_store import SessionStore

_TEMPLATES_DIR = (
    Path(openteam_server.__file__).parent / "resources" / "prompt_templates"
)


class _RecordingHost:
    """A conversational host that records each ``run_agentic_loop`` call."""

    supports_round_resume = True
    tool_dispatcher = None
    effective_cwd = ""
    sop_state = None
    suspended_sops: list = []

    def __init__(self) -> None:
        self.prior_context: dict = {}
        self.turns: list[tuple[str, str]] = []
        self.widget_answer = None

    def set_prior_context(self, context: dict) -> None:
        self.prior_context = dict(context)

    def set_messages(self, messages: list) -> None:
        pass

    def restore_state(self, blob: dict, *, reattach_sop: bool = True) -> None:
        pass

    def set_pending_widget_answer(self, answer: dict) -> None:
        self.widget_answer = answer

    async def run_agentic_loop(self, content: str, **kwargs):
        self.turns.append((content, kwargs["origin"]))
        return SimpleNamespace(text="")


class ConversationTurnOriginTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="os_turn_origin_"))
        self.store = SessionStore(tmp, resume_server="new")
        self.session = self.store.create_session("origin")
        self.svc = ConversationService(
            templates_dir=_TEMPLATES_DIR,
            llm_backend="claude_cli",
            working_dir=str(tmp / "work"),
            session_store=self.store,
        )
        self.host = _RecordingHost()
        self.svc._inferencers[self.session["id"]] = self.host

    def test_a_fresh_turn_runs_with_the_callers_origin(self) -> None:
        asyncio.run(
            self.svc.run_conversation_turn(
                self.session, "note", interactive=None, origin="host_event"
            )
        )
        asyncio.run(
            self.svc.run_conversation_turn(self.session, "hi", interactive=None)
        )
        self.assertEqual(self.host.turns, [("note", "host_event"), ("hi", "user")])

    def test_a_round_resume_runs_as_a_resumed_turn(self) -> None:
        asyncio.run(
            self.svc.resume_conversation_from_round(
                self.session,
                target_turn=1,
                target_round=2,
                resume_blob={"content": "continue"},
                interactive=None,
            )
        )
        self.assertEqual(self.host.turns, [("continue", "resumed_turn")])

    def test_a_recovered_widget_answer_runs_as_a_widget_answer(self) -> None:
        asyncio.run(
            self.svc.resume_conversation_from_widget(
                self.session,
                marker={"turn_number": 1, "tools": []},
                blob={},
                raw_value="yes",
                interactive=None,
            )
        )
        [(_content, origin)] = self.host.turns
        self.assertEqual(origin, "widget_answer")
        self.assertEqual(self.host.widget_answer["raw_value"], "yes")


if __name__ == "__main__":
    unittest.main()
