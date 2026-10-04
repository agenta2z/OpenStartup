"""ConversationService with a native backend: turns, eviction, backend switch,
rewind before truncation, checkpoint restore and shutdown.

The native inferencer is built by the real factory (``_build_native``) and
driven by the real service; only the vendor is replaced by a scripted
backend, so the session record, runtime manager and lifecycle code under test
are production code.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

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
from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.events import (
    MessageEnd,
    TextDelta,
    TurnEnd,
)
from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.backend import (
    BackendCapabilities,
    CallerTools,
    L2Channel,
)
from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.record import (
    StaleRecordError,
)
from openteam.server.backends import factories as factories_mod
from openteam.server.backends.registry import BackendDescriptor, BackendRegistry
from openteam.server.routes.manager_websocket_routes import (
    _rewind_and_truncate,
    _try_dev_slash_command,
    _turn_resume_for_round,
)
from openteam.server.routes.session_routes import delete_session
from openteam.server.services import conversation_service as conversation_service_mod
from openteam.server.services.conversation_service import ConversationService
from openteam.server.services.data_service import RealSessionDataService
from openteam.server.services.native_session_store import (
    SESSION_KEY,
    SessionStoreRecordAdapter,
)
from openteam.server.services.session_store import SessionStore
from openteam.server.services.task_graph_snapshot import TaskGraphSnapshotStore

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
    slash_passthrough=("compact",),
)


class _ScriptedBackend:
    """A vendor session that answers every turn with ``reply N``; a turn whose
    text starts with ``long`` runs until the vendor is interrupted. ``on_open``
    sees every open request first (and may fail it)."""

    capabilities = _CAPABILITIES

    def __init__(self, spec, on_open=None, **_runtime) -> None:
        self.spec = spec
        self._on_open = on_open
        self.open_request = None
        self.turns: list = []
        self.l2_seen: list[str] = []
        self.closed = False
        self.interrupted = False
        self.long_turn_started = asyncio.Event()
        self._interrupt = asyncio.Event()
        self._session_id = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    async def open(self, request) -> None:
        self.open_request = request
        if self._on_open is not None:
            self._on_open(request)
        if request.fork_from is not None:
            self._session_id = f"fork-{uuid.uuid4().hex[:6]}"
        else:
            self._session_id = request.session_id or uuid.uuid4().hex

    async def run_turn(self, request):
        self.turns.append(request)
        self.l2_seen.append(self.open_request.hooks.l2_for_turn())
        n = len(self.turns)
        reply = f"reply {request.text}"
        yield TextDelta(message_id=f"m{n}", text=reply)
        if request.text.startswith("long"):
            self.long_turn_started.set()
            await self._interrupt.wait()
            yield TurnEnd(session_id=self._session_id, stop_reason="interrupted")
            return
        yield MessageEnd(
            message_id=f"m{n}", text=reply, message_uuid=f"{self._session_id}:u{n}"
        )
        yield TurnEnd(session_id=self._session_id, stop_reason="end_turn", num_turns=1)

    def fork_message_map(self, source: str, forked: str) -> dict:
        return {}

    async def interrupt(self) -> None:
        self.interrupted = True
        self._interrupt.set()

    async def set_model(self, model: str) -> None:
        self.spec.model = model

    async def close(self) -> None:
        self.closed = True


class _ScriptedFactory:
    capabilities = _CAPABILITIES

    def __init__(self) -> None:
        self.instances: list[_ScriptedBackend] = []
        self.on_open = None

    def __call__(self, spec, **runtime) -> _ScriptedBackend:
        backend = _ScriptedBackend(spec, on_open=self.on_open, **runtime)
        self.instances.append(backend)
        return backend


class _Interactive:
    async def stream_token_batches(
        self, tokens, session_id, send_stream_end=False, turn_number=0
    ):
        return "".join([chunk async for chunk, _meta in tokens])

    async def send_round_message_end(self, **_kw) -> None:
        pass

    def set_round_context(self, ctx) -> None:
        pass

    async def send_turn_boundary(self, *_a, **_kw) -> None:
        pass


class _Harness:
    def __init__(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="os_native_turn_"))
        self.store = SessionStore(tmp, resume_server="new")
        self.data = RealSessionDataService(tmp / "no_fixtures", self.store)
        self.sid = self.store.create_session("native")["id"]
        self.vendor = _ScriptedFactory()
        self.registry = BackendRegistry()
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
            inferencer.backend_factory = self.vendor
            return inferencer

        def classic(_ctx):
            raise AssertionError("the classic backend is not built in these tests")

        self.registry.register(
            "native_test", build, BackendDescriptor("native_test", "", "", native=True)
        )
        self.registry.register(
            "claude_cli", classic, BackendDescriptor("claude_cli", "", "")
        )
        self.svc = ConversationService(
            templates_dir=_TEMPLATES_DIR,
            llm_backend="native_test",
            working_dir=str(tmp / "work"),
            session_store=self.store,
        )
        self.user_ids: dict[int, str] = {}

    def record(self) -> dict:
        return self.store.get_session(self.sid).get(SESSION_KEY) or {}

    async def turn(
        self, text: str, message_id: str | None = None, origin: str = "user"
    ):
        turn_number = self.store.next_turn_number(self.sid)
        message_id = message_id or f"user-{uuid.uuid4().hex[:6]}"
        self.user_ids[turn_number] = message_id
        session = self.data.append_message(
            self.sid,
            {
                "id": message_id,
                "role": "user",
                "content": text,
                "turn_number": turn_number,
            },
        )
        return await self.svc.run_conversation_turn(
            session,
            text,
            interactive=_Interactive(),
            data_service=self.data,
            origin=origin,
        )

    async def settle(self) -> None:
        if self.svc._retiring:
            await asyncio.gather(*list(self.svc._retiring))


def _vendor_unavailable(_request) -> None:
    raise RuntimeError("vendor unavailable")


def _session_snapshot(h: _Harness) -> tuple:
    """The session as the host stores it: state, turn dirs, checkpoints."""
    session_dir = h.store.get_session_dir(h.sid)
    return (
        h.store.get_session(h.sid),
        sorted(p.name for p in session_dir.iterdir()),
        [c["name"] for c in h.store.list_checkpoints(h.sid)],
    )


def _app(h: _Harness) -> SimpleNamespace:
    """The app state the session routes read."""
    return SimpleNamespace(
        state=SimpleNamespace(
            data_service=h.data,
            conversation_service=h.svc,
            task_graph_snapshots=TaskGraphSnapshotStore(session_store=h.store),
        )
    )


def _run(scenario) -> None:
    async def main() -> None:
        harness = _Harness()
        with patch(
            "openteam.server.backends.get_registry", return_value=harness.registry
        ):
            try:
                await scenario(harness)
            finally:
                await harness.svc.aclose_all()

    asyncio.run(main())


class NativeTurnTests(unittest.TestCase):
    def test_turns_continue_one_vendor_session_and_persist_its_record(self):
        async def scenario(h: _Harness) -> None:
            result = await h.turn("hello")
            await h.turn("again")
            self.assertEqual(len(h.vendor.instances), 1)
            vendor = h.vendor.instances[0]
            self.assertFalse(vendor.open_request.resume)
            self.assertEqual([t.text for t in vendor.turns], ["hello", "again"])
            self.assertEqual(result.turn_number, 1)
            record = h.record()
            self.assertEqual(record["vendor_session_id"], vendor.session_id)
            self.assertEqual(record["last_turn"], 2)
            contents = [m["content"] for m in h.store.get_session(h.sid)["messages"]]
            self.assertIn("reply again", contents)

        _run(scenario)

    def test_eviction_keeps_the_live_vendor_session(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            first = h.svc._inferencers[h.sid]
            await h.svc.evict_session_inferencer(h.sid)
            await h.turn("again")
            self.assertIsNot(h.svc._inferencers[h.sid], first)
            self.assertEqual(len(h.vendor.instances), 1)
            self.assertFalse(h.vendor.instances[0].closed)
            self.assertEqual(len(h.vendor.instances[0].turns), 2)

        _run(scenario)

    def test_deleting_a_session_closes_its_vendor_session(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            await h.svc.evict_session_inferencer(h.sid, close_sessions=True)
            self.assertTrue(h.vendor.instances[0].closed)

        _run(scenario)

    def test_backend_switch_ends_the_vendor_session_and_recaps_on_return(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            await h.svc.set_session_backend(h.sid, "claude_cli")
            self.assertTrue(h.vendor.instances[0].closed)
            record = h.record()
            self.assertEqual(record["generation"], 1)
            self.assertEqual(record["vendor_session_id"], "")
            self.assertEqual([n["type"] for n in record["outbox"]], ["recap"])

            await h.svc.set_session_backend(h.sid, "native_test")
            await h.turn("back")
            fresh = h.vendor.instances[-1]
            self.assertEqual(len(h.vendor.instances), 2)
            self.assertFalse(fresh.open_request.resume)
            self.assertIn("hello", fresh.l2_seen[0])
            self.assertEqual(h.record()["outbox"], [])

        _run(scenario)


class NativeTurnOriginTests(unittest.TestCase):
    def test_a_host_event_turn_carries_turn_context_naming_its_origin(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            await h.turn(
                "[System notification: Task 't1' completed.]", "auto-1", "host_event"
            )
            vendor = h.vendor.instances[0]
            self.assertIn('origin="host_event"', vendor.l2_seen[1])

        _run(scenario)

    def test_a_user_turn_with_unchanged_state_carries_no_turn_context(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            await h.turn("again")
            self.assertEqual(h.vendor.instances[0].l2_seen[1], "")

        _run(scenario)

    def test_resuming_a_turn_runs_it_as_a_resumed_turn(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("one")
            await h.turn("two")
            await h.svc.prepare_rewind(h.sid, 2)
            h.store.truncate_session_at_message(h.sid, h.user_ids[2], drop_tasks=False)
            await h.svc.evict_session_inferencer(h.sid)
            await h.turn("two", message_id=h.user_ids[2], origin="resumed_turn")
            forked = h.vendor.instances[-1]
            self.assertEqual([t.text for t in forked.turns], ["two"])
            self.assertIn('origin="resumed_turn"', forked.l2_seen[0])

        _run(scenario)


class NativeEvictionDuringTurnTests(unittest.TestCase):
    def test_backend_switch_cancels_the_running_turn_and_closes_its_session(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            turn = asyncio.create_task(h.turn("long task"))
            vendor = h.vendor.instances[0]
            await asyncio.wait_for(vendor.long_turn_started.wait(), 10)

            updated = await asyncio.wait_for(
                h.svc.set_session_backend(h.sid, "claude_cli"), 10
            )
            self.assertTrue(turn.cancelled())
            self.assertTrue(vendor.interrupted)
            self.assertTrue(vendor.closed)
            self.assertEqual(updated["llm_backend"], "claude_cli")
            self.assertNotIn(h.sid, h.svc._inferencers)
            record = h.record()
            self.assertEqual(record["vendor_session_id"], "")
            self.assertEqual(
                [n["type"] for n in record["outbox"]], ["interrupted", "recap"]
            )

        _run(scenario)

    def test_deleting_a_session_during_a_turn_stops_it_before_removing_it(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            turn = asyncio.create_task(h.turn("long task"))
            vendor = h.vendor.instances[0]
            await asyncio.wait_for(vendor.long_turn_started.wait(), 10)
            background = asyncio.create_task(asyncio.sleep(3600))
            h.svc._register_bg_task(h.sid, "task-1", background)
            result = await asyncio.wait_for(
                delete_session(SimpleNamespace(app=_app(h)), h.sid), 10
            )
            self.assertEqual(result, {"data": {"deleted": True}})
            self.assertTrue(turn.cancelled())
            self.assertTrue(background.cancelled())
            self.assertTrue(vendor.interrupted)
            self.assertTrue(vendor.closed)
            self.assertIsNone(h.store.find_session_dir(h.sid))
            self.assertNotIn(h.sid, h.svc._inferencers)

        _run(scenario)

    def test_deleting_an_unknown_session_is_a_404_that_creates_nothing(self):
        async def scenario(h: _Harness) -> None:
            with self.assertRaises(HTTPException) as raised:
                await delete_session(SimpleNamespace(app=_app(h)), "session-unknown")
            self.assertEqual(raised.exception.status_code, 404)
            self.assertIsNone(h.store.find_session_dir("session-unknown"))

        _run(scenario)

    def test_eviction_cancels_the_turn_but_keeps_the_live_vendor_session(self):
        async def scenario(h: _Harness) -> None:
            turn = asyncio.create_task(h.turn("long task"))
            vendor = h.vendor.instances[0] if h.vendor.instances else None
            while vendor is None:
                await asyncio.sleep(0.01)
                vendor = h.vendor.instances[0] if h.vendor.instances else None
            await asyncio.wait_for(vendor.long_turn_started.wait(), 10)

            await asyncio.wait_for(h.svc.evict_session_inferencer(h.sid), 10)
            self.assertTrue(turn.cancelled())
            self.assertTrue(vendor.interrupted)
            self.assertFalse(vendor.closed)
            await h.turn("again")
            self.assertEqual(len(h.vendor.instances), 1)
            self.assertEqual([t.text for t in vendor.turns], ["long task", "again"])

        _run(scenario)

    def test_eviction_is_bounded_when_a_turn_ignores_cancellation(self):
        async def scenario(h: _Harness) -> None:
            closed: list[str] = []

            class _Inferencer:
                async def aclose(self) -> None:
                    closed.append(h.sid)

            h.svc._inferencers[h.sid] = _Inferencer()
            entered, release = asyncio.Event(), asyncio.Event()

            async def stubborn_turn() -> None:
                async with h.svc._session_turn(h.sid):
                    entered.set()
                    while not release.is_set():
                        try:
                            await release.wait()
                        except asyncio.CancelledError:
                            pass

            turn = asyncio.create_task(stubborn_turn())
            await entered.wait()
            with patch.object(conversation_service_mod, "_RETIRE_TIMEOUT_S", 0.05):
                await asyncio.wait_for(h.svc.evict_session_inferencer(h.sid), 5)
            self.assertNotIn(h.sid, h.svc._inferencers)
            self.assertEqual(closed, [])  # not under the running turn

            release.set()
            await turn
            await h.settle()
            self.assertEqual(closed, [h.sid])

        _run(scenario)


class NativeCommandTests(unittest.TestCase):
    def test_slash_new_is_the_conversations_and_its_reply_is_a_bubble(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            self.assertTrue(h.svc.accepts_slash_command(h.sid, "/new"))
            self.assertTrue(h.svc.accepts_slash_command(h.sid, "/compact"))
            self.assertFalse(h.svc.accepts_slash_command(h.sid, "/nonsense"))
            generation = h.record()["generation"]
            await h.turn("/new")
            self.assertEqual(h.record()["generation"], generation + 1)
            bubble = h.store.get_session(h.sid)["messages"][-1]
            self.assertEqual(bubble["role"], "assistant")
            self.assertIn("new agent session", bubble["content"])
            self.assertEqual(bubble["turn_number"], 2)
            await h.turn("again")
            self.assertEqual(len(h.vendor.instances), 2)
            self.assertFalse(h.vendor.instances[-1].open_request.resume)

        _run(scenario)

    def test_route_leaves_conversation_commands_to_the_conversation(self):
        sent: list = []

        async def send(frame) -> None:
            sent.append(frame)

        async def scenario() -> None:
            handled = await _try_dev_slash_command(
                "/new", "sid", send, accepts_command=lambda text: text == "/new"
            )
            self.assertFalse(handled)
            self.assertEqual(sent, [])
            handled = await _try_dev_slash_command(
                "/nonsense", "sid", send, accepts_command=lambda text: False
            )
            self.assertTrue(handled)
            self.assertEqual(sent[-1]["type"], "error")

        asyncio.run(scenario())


class NativeRewindTests(unittest.TestCase):
    def test_prepare_rewind_forks_before_the_session_is_truncated(self):
        async def scenario(h: _Harness) -> None:
            for text in ("one", "two", "three"):
                await h.turn(text)
            source = h.record()["vendor_session_id"]
            boundary = h.record()["turn_boundaries"]["1"]

            await h.svc.prepare_rewind(h.sid, 2)
            forked = h.vendor.instances[-1]
            self.assertEqual(forked.open_request.fork_from, (source, boundary))
            self.assertEqual(h.record()["last_turn"], 1)

            # The route then truncates and re-runs the kept user message.
            h.store.truncate_session_at_message(h.sid, h.user_ids[2], drop_tasks=False)
            await h.svc.evict_session_inferencer(h.sid)
            await h.turn("two", message_id=h.user_ids[2])
            self.assertEqual(len(h.vendor.instances), 2)  # no second fork
            self.assertEqual([t.text for t in forked.turns], ["two"])
            self.assertEqual(h.record()["last_turn"], 2)

        _run(scenario)

    def test_prepare_rewind_never_overwrites_a_record_saved_meanwhile(self):
        async def scenario(h: _Harness) -> None:
            for text in ("one", "two", "three"):
                await h.turn(text)
            source = h.record()["vendor_session_id"]

            def save_during_fork(request) -> None:
                if request.fork_from is not None:
                    adapter = SessionStoreRecordAdapter(h.store, h.sid)
                    record = adapter.load(h.sid)
                    record.add_notice("interrupted")
                    adapter.save(record)

            h.vendor.on_open = save_during_fork
            with self.assertRaises(StaleRecordError):
                await h.svc.prepare_rewind(h.sid, 2)
            record = h.record()
            self.assertEqual(record["vendor_session_id"], source)
            self.assertEqual(record["last_turn"], 3)
            self.assertEqual([n["type"] for n in record["outbox"]], ["interrupted"])

        _run(scenario)

    def test_prepare_rewind_without_rewind_support_is_a_no_op(self):
        async def scenario(h: _Harness) -> None:
            h.svc._inferencers[h.sid] = SimpleNamespace(supports_rewind=False)
            await h.svc.prepare_rewind(h.sid, 2)
            self.assertEqual(h.vendor.instances, [])

        _run(scenario)

    def test_restore_forks_the_vendor_session_back_to_the_checkpoint(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("one")
            checkpoint = h.store.checkpoint_session(h.sid)
            source = h.record()["vendor_session_id"]
            boundary = h.record()["turn_boundaries"]["1"]
            await h.turn("two")

            restored = await h.svc.restore_checkpoint(h.sid, checkpoint)
            self.assertNotIn("two", [m["content"] for m in restored["messages"]])
            self.assertTrue(h.vendor.instances[0].closed)
            forked = h.vendor.instances[-1]
            self.assertEqual(forked.open_request.fork_from, (source, boundary))

            await h.svc.evict_session_inferencer(h.sid)
            await h.turn("two again")
            self.assertEqual([t.text for t in forked.turns], ["two again"])

        _run(scenario)

    def test_restore_forks_before_the_session_is_restored(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("one")
            checkpoint = h.store.checkpoint_session(h.sid)
            await h.turn("two")
            at_fork: list[list[str]] = []

            def record_history(request) -> None:
                if request.fork_from is not None:
                    messages = h.store.get_session(h.sid)["messages"]
                    at_fork.append([m["content"] for m in messages])

            h.vendor.on_open = record_history
            await h.svc.restore_checkpoint(h.sid, checkpoint)
            self.assertEqual(len(at_fork), 1)
            self.assertIn("two", at_fork[0])  # nothing restored yet
            forked = h.vendor.instances[-1]
            record = h.record()
            self.assertEqual(record["vendor_session_id"], forked.session_id)
            self.assertEqual(record["last_turn"], 1)
            native_dir = h.store.get_session_dir(h.sid) / "native"
            self.assertTrue((native_dir / f"l1_{record['generation']}.md").is_file())

        _run(scenario)

    def test_restore_with_a_failing_fork_leaves_the_session_untouched(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("one")
            checkpoint = h.store.checkpoint_session(h.sid)
            await h.turn("two")
            before = _session_snapshot(h)

            h.vendor.on_open = _vendor_unavailable
            with self.assertRaisesRegex(RuntimeError, "vendor unavailable"):
                await h.svc.restore_checkpoint(h.sid, checkpoint)
            self.assertEqual(_session_snapshot(h), before)

        _run(scenario)

    def test_resume_from_turn_with_a_failing_fork_leaves_the_session_untouched(self):
        async def scenario(h: _Harness) -> None:
            for text in ("one", "two", "three"):
                await h.turn(text)
            before = _session_snapshot(h)

            h.vendor.on_open = _vendor_unavailable
            with self.assertRaisesRegex(RuntimeError, "vendor unavailable"):
                await _rewind_and_truncate(
                    h.svc, h.store, h.sid, h.user_ids[2], drop_tasks=False
                )
            self.assertEqual(_session_snapshot(h), before)

        _run(scenario)

    def test_restore_without_vendor_progress_resumes_without_a_fork(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("one")
            checkpoint = h.store.checkpoint_session(h.sid)
            await h.svc.restore_checkpoint(h.sid, checkpoint)
            self.assertEqual(len(h.vendor.instances), 1)
            await h.turn("two")
            resumed = h.vendor.instances[-1]
            self.assertEqual(len(h.vendor.instances), 2)
            self.assertTrue(resumed.open_request.resume)
            self.assertIsNone(resumed.open_request.fork_from)

        _run(scenario)

    def test_round_resume_becomes_a_turn_resume(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("one")
            self.assertFalse(h.svc.supports_round_resume(h.sid))
            bubble = next(
                m
                for m in h.store.get_session(h.sid)["messages"]
                if m.get("role") == "assistant" and m.get("turn_number") == 1
            )
            app_state = SimpleNamespace(
                conversation_service=h.svc,
                data_service=SimpleNamespace(session_store=h.store),
            )
            msg_type, data = _turn_resume_for_round(
                app_state,
                h.sid,
                {"type": "resume_from_round", "message_id": bubble["id"]},
            )
            self.assertEqual(msg_type, "resume_from_turn")
            self.assertEqual(data["message_id"], h.user_ids[1])
            with self.assertRaises(RuntimeError):
                await h.svc.resume_conversation_from_round(
                    h.store.get_session(h.sid),
                    target_turn=1,
                    target_round=1,
                    resume_blob={},
                    interactive=_Interactive(),
                    data_service=h.data,
                )

        _run(scenario)


class NativeShutdownTests(unittest.TestCase):
    def test_aclose_all_closes_live_vendor_sessions(self):
        async def scenario(h: _Harness) -> None:
            await h.turn("hello")
            await h.svc.aclose_all()
            self.assertTrue(h.vendor.instances[0].closed)
            self.assertEqual(h.svc._inferencers, {})
            self.assertIsNone(h.svc._native_runtime)

        _run(scenario)


if __name__ == "__main__":
    unittest.main()
