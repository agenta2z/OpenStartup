"""SessionStoreRecordAdapter: compare-and-swap of ``session["native_session"]``."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
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

from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.record import (
    NativeSessionRecord,
    StaleRecordError,
)
from openteam.server.services.native_session_store import (
    SESSION_KEY,
    SessionStoreRecordAdapter,
)
from openteam.server.services.session_store import SessionStore


def _store() -> tuple[SessionStore, str]:
    store = SessionStore(
        Path(tempfile.mkdtemp(prefix="os_native_record_")), resume_server="new"
    )
    return store, store.create_session("native")["id"]


class SessionStoreRecordAdapterCasTest(unittest.TestCase):
    def test_a_copy_loaded_before_another_adapters_save_loses(self) -> None:
        # E.g. an evicted inferencer still finishing while its rebuilt
        # successor (with a new adapter) already saved.
        store, sid = _store()
        old, new = (
            SessionStoreRecordAdapter(store, sid),
            SessionStoreRecordAdapter(store, sid),
        )
        old.save(NativeSessionRecord(conversation_key=sid, vendor_session_id="v1"))
        stale = old.load(sid)
        current = new.load(sid)
        current.last_turn = 3
        new.save(current)
        stale.last_turn = 7
        with self.assertRaises(StaleRecordError):
            old.save(stale)
        self.assertEqual(store.get_session(sid)[SESSION_KEY]["last_turn"], 3)
        self.assertEqual(old.load(sid).saved_at, current.saved_at)

    def test_adapters_over_one_session_store_share_their_lock(self) -> None:
        store, sid = _store()
        other, _ = _store()
        first = SessionStoreRecordAdapter(store, sid)
        self.assertIs(first._lock, SessionStoreRecordAdapter(store, sid)._lock)
        self.assertIsNot(first._lock, SessionStoreRecordAdapter(other, sid)._lock)

    def test_the_adapter_holds_the_lock_of_every_writer_of_the_session(
        self,
    ) -> None:
        store, sid = _store()
        self.assertIs(
            SessionStoreRecordAdapter(store, sid)._lock, store.session_lock(sid)
        )

    def test_concurrent_saves_of_one_copy_through_two_adapters_have_one_winner(
        self,
    ) -> None:
        store, sid = _store()
        SessionStoreRecordAdapter(store, sid).save(
            NativeSessionRecord(conversation_key=sid, vendor_session_id="v1")
        )

        class _SlowReads:
            """The session store, reading slowly to widen the race window."""

            def get_session(self, session_id):
                session = store.get_session(session_id)
                time.sleep(0.01)
                return session

            def update_session(self, session_id, updates):
                return store.update_session(session_id, updates)

        slow = _SlowReads()
        adapters = [SessionStoreRecordAdapter(slow, sid) for _ in range(2)]
        # One lock per store object: both adapters wrap the same one.
        self.assertIs(adapters[0]._lock, adapters[1]._lock)
        copies = [adapters[i % 2].load(sid) for i in range(6)]
        outcomes: list = []

        def save(adapter, copy) -> None:
            try:
                adapter.save(copy)
                outcomes.append("saved")
            except StaleRecordError:
                outcomes.append("stale")

        threads = [
            threading.Thread(target=save, args=(adapters[i % 2], copy))
            for i, copy in enumerate(copies)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(outcomes), ["saved"] + ["stale"] * 5)


class _SlowReadStore(SessionStore):
    """Reads session state slowly, widening every writer's window between
    reading the state and writing it back."""

    def get_session(self, session_id):
        session = super().get_session(session_id)
        time.sleep(0.002)
        return session


def _run_threads(*targets) -> None:
    threads = [threading.Thread(target=target) for target in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


class SessionWritersTest(unittest.TestCase):
    """Every read-modify-write of a session's state holds the session's lock,
    so concurrent writers — the native record's compare-and-swap included —
    never lose each other's updates."""

    def test_concurrent_writers_lose_no_update(self) -> None:
        store = _SlowReadStore(
            Path(tempfile.mkdtemp(prefix="os_native_record_")), resume_server="new"
        )
        sid = store.create_session("native")["id"]
        adapter = SessionStoreRecordAdapter(store, sid)
        adapter.save(NativeSessionRecord(conversation_key=sid, vendor_session_id="v1"))
        count = 12

        def append_messages() -> None:
            for i in range(count):
                store.append_message(sid, {"id": f"m{i}", "role": "user"})

        def save_records() -> None:
            for _ in range(count):
                record = adapter.load(sid)
                record.last_turn += 1
                adapter.save(record)

        def update_fields() -> None:
            for i in range(count):
                store.update_session(sid, {f"field_{i}": i})

        _run_threads(append_messages, save_records, update_fields)
        session = store.get_session(sid)
        ids = {m["id"] for m in session["messages"]}
        self.assertTrue({f"m{i}" for i in range(count)} <= ids)
        self.assertEqual(session[SESSION_KEY]["last_turn"], count)
        self.assertTrue(all(session.get(f"field_{i}") == i for i in range(count)))

    def test_a_write_during_a_checkpoint_restore_lands_after_it(self) -> None:
        store, sid = _store()
        name = store.checkpoint_session(sid)
        store.append_message(sid, {"id": "after-checkpoint", "role": "user"})
        snapshot = store.checkpoint_session
        writer = threading.Thread(
            target=store.update_session, args=(sid, {"late": True})
        )

        def checkpoint_while_writing(session_id: str) -> str:
            writer.start()
            time.sleep(0.1)  # the writer's turn, were the restore not locked
            return snapshot(session_id)

        store.checkpoint_session = checkpoint_while_writing
        restored = store.restore_checkpoint(sid, name, updates={"rewound": 1})
        writer.join()
        self.assertEqual(restored["rewound"], 1)
        self.assertNotIn("after-checkpoint", [m["id"] for m in restored["messages"]])
        session = store.get_session(sid)
        self.assertTrue(session["late"])
        self.assertEqual(session["rewound"], 1)

    def test_reading_a_checkpoint_never_writes_the_live_session(self) -> None:
        store, sid = _store()
        name = store.checkpoint_session(sid)
        state = store.get_session_dir(sid) / "checkpoints" / name / "session_state.json"
        legacy = json.loads(state.read_text(encoding="utf-8"))
        del legacy["workflow_context"]  # saved before workflow support
        state.write_text(json.dumps(legacy), encoding="utf-8")
        store.append_message(sid, {"id": "live", "role": "user"})

        checkpoint = store.read_checkpoint(sid, name)
        self.assertIn("workflow_context", checkpoint["session"])
        self.assertIn("live", [m["id"] for m in store.get_session(sid)["messages"]])


if __name__ == "__main__":
    unittest.main()
