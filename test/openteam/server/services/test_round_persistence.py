"""Tests for the round-lifecycle persistence layer.

Covers SessionStore round-awareness (save_turn_data/get_turn_data with a
``round=`` argument, update_turn_root_summary merge semantics, append_message
index update + id-dedupe, the seeded welcome message turn_number==0) and the
DataService forwarding of ``round`` through to the store.

Mirrors the setup in the sibling test_session_store_attach.py (a fresh
SessionStore rooted at tmp_path with resume_server="new").
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openteam.server.services.data_service import RealSessionDataService
from openteam.server.services.session_store import SessionStore


@pytest.fixture
def store(tmp_path):
    """Fresh SessionStore rooted at tmp_path."""
    return SessionStore(tmp_path, resume_server="new")


@pytest.fixture
def session(store):
    """A created session; returns (store, session_id)."""
    s = store.attach_or_create_session(external_id="rovodev-roundtest")
    return store, s["id"]


def _session_dir(store: SessionStore, session_id: str) -> Path:
    sd = store.find_session_dir(session_id)
    assert sd is not None
    return sd


class TestSaveTurnDataRoundAwareness:
    def test_round_writes_per_round_subdir(self, session):
        store, sid = session
        store.save_turn_data(sid, 1, {"inference_response": "round-one"}, round=1)

        sd = _session_dir(store, sid)
        round_combined = sd / "turn_001" / "round_001" / "turn.json"
        assert round_combined.is_file()
        data = json.loads(round_combined.read_text(encoding="utf-8"))
        assert data["inference_response"] == "round-one"

    def test_round_two_writes_round_002(self, session):
        store, sid = session
        store.save_turn_data(sid, 1, {"inference_response": "r1"}, round=1)
        store.save_turn_data(sid, 1, {"inference_response": "r2"}, round=2)

        sd = _session_dir(store, sid)
        assert (sd / "turn_001" / "round_001" / "turn.json").is_file()
        assert (sd / "turn_001" / "round_002" / "turn.json").is_file()
        r2 = json.loads(
            (sd / "turn_001" / "round_002" / "turn.json").read_text(encoding="utf-8")
        )
        assert r2["inference_response"] == "r2"

    def test_get_turn_data_round_round_trip(self, session):
        store, sid = session
        store.save_turn_data(sid, 1, {"inference_response": "round-one"}, round=1)
        got = store.get_turn_data(sid, 1, round=1)
        assert got is not None
        assert got["inference_response"] == "round-one"

    def test_get_turn_data_round_missing_returns_none(self, session):
        store, sid = session
        # Nothing written for round 5
        assert store.get_turn_data(sid, 1, round=5) is None

    def test_round_none_writes_and_reads_root(self, session):
        store, sid = session
        store.save_turn_data(sid, 1, {"inference_response": "root-level"})

        sd = _session_dir(store, sid)
        root_combined = sd / "turn_001" / "turn.json"
        assert root_combined.is_file()
        # And no round subdir was created by the round=None write.
        assert not (sd / "turn_001" / "round_001").exists()

        got = store.get_turn_data(sid, 1)  # round=None
        assert got is not None
        assert got["inference_response"] == "root-level"

    def test_round_and_root_are_independent(self, session):
        """A per-round write must not overwrite the turn root, and vice versa."""
        store, sid = session
        store.save_turn_data(sid, 1, {"inference_response": "ROOT"})
        store.save_turn_data(sid, 1, {"inference_response": "R1"}, round=1)

        root = store.get_turn_data(sid, 1)
        r1 = store.get_turn_data(sid, 1, round=1)
        assert root["inference_response"] == "ROOT"
        assert r1["inference_response"] == "R1"


class TestUpdateTurnRootSummary:
    def test_creates_root_turn_json(self, session):
        store, sid = session
        store.update_turn_root_summary(sid, 1, {"user_input": "hello", "latest_round": 1})

        sd = _session_dir(store, sid)
        root = sd / "turn_001" / "turn.json"
        assert root.is_file()
        data = json.loads(root.read_text(encoding="utf-8"))
        assert data["user_input"] == "hello"
        assert data["latest_round"] == 1

    def test_merges_into_existing_root(self, session):
        store, sid = session
        store.update_turn_root_summary(sid, 1, {"user_input": "hello", "latest_round": 1})
        # Second call across a later round accumulates rather than clobbers.
        store.update_turn_root_summary(sid, 1, {"latest_round": 2, "assembled": "summary"})

        got = store.get_turn_data(sid, 1)
        assert got["user_input"] == "hello"     # preserved from first call
        assert got["latest_round"] == 2          # overwritten by second call
        assert got["assembled"] == "summary"     # added by second call

    def test_summary_merge_does_not_disturb_round_dirs(self, session):
        store, sid = session
        store.save_turn_data(sid, 1, {"inference_response": "R1"}, round=1)
        store.update_turn_root_summary(sid, 1, {"user_input": "u", "latest_round": 1})

        # Round artifact still intact and distinct from the merged root.
        r1 = store.get_turn_data(sid, 1, round=1)
        root = store.get_turn_data(sid, 1)
        assert r1["inference_response"] == "R1"
        assert root["user_input"] == "u"
        assert "inference_response" not in root


class TestAppendMessageIndexAndDedupe:
    def test_append_updates_sessions_index_count(self, session):
        store, sid = session
        # Welcome message seeded at creation → message_count == 1.
        before = next(s for s in store.list_sessions() if s["id"] == sid)
        assert before["message_count"] == 1

        store.append_message(sid, {"id": "m-100", "role": "user", "content": "hi"})

        # sessions_index.json reflects the new count.
        index = json.loads(
            (store._dir / "sessions_index.json").read_text(encoding="utf-8")
        )
        entry = next(s for s in index["sessions"] if s["id"] == sid)
        assert entry["message_count"] == 2

    def test_append_dedupes_duplicate_id(self, session):
        store, sid = session
        msg = {"id": "dup-1", "role": "user", "content": "first"}
        store.append_message(sid, msg)
        # Re-delivery of the same id is idempotent.
        store.append_message(sid, {"id": "dup-1", "role": "user", "content": "second"})

        full = store.get_session(sid)
        matches = [m for m in full["messages"] if m.get("id") == "dup-1"]
        assert len(matches) == 1
        assert matches[0]["content"] == "first"  # the original, not the retry

    def test_append_missing_session_returns_none(self, store):
        assert store.append_message("rovodev-nope", {"id": "x", "content": "y"}) is None


class TestWelcomeMessageTurnNumber:
    def test_seeded_welcome_is_turn_zero(self, session):
        store, sid = session
        full = store.get_session(sid)
        welcome = full["messages"][0]
        assert welcome["role"] == "assistant"
        assert welcome["agent_name"] == "Orchestrator"
        assert welcome["turn_number"] == 0


class TestDataServiceRoundForwarding:
    """RealSessionDataService must forward ``round`` through to the store."""

    @pytest.fixture
    def svc(self, tmp_path):
        store = SessionStore(tmp_path / "runtime", resume_server="new")
        # Point fixtures at a non-existent dir; MockDataService logs warnings and
        # uses empty collections — fine, we only exercise the session methods.
        svc = RealSessionDataService(tmp_path / "no_fixtures", store)
        sess = store.attach_or_create_session(external_id="rovodev-svc")
        return svc, sess["id"]

    def test_save_and_get_turn_data_round(self, svc):
        service, sid = svc
        service.save_turn_data(sid, 2, {"inference_response": "via-svc"}, round=3)
        got = service.get_turn_data(sid, 2, round=3)
        assert got is not None
        assert got["inference_response"] == "via-svc"

        # And it landed in the per-round subdir, proving round was forwarded.
        sd = service.get_session_dir(sid)
        assert (sd / "turn_002" / "round_003" / "turn.json").is_file()

    def test_save_turn_data_round_none_goes_to_root(self, svc):
        service, sid = svc
        service.save_turn_data(sid, 2, {"inference_response": "root-via-svc"})
        sd = service.get_session_dir(sid)
        assert (sd / "turn_002" / "turn.json").is_file()
        assert not (sd / "turn_002" / "round_001").exists()

    def test_update_turn_root_summary_forwarded(self, svc):
        service, sid = svc
        service.update_turn_root_summary(sid, 2, {"user_input": "forwarded"})
        got = service.get_turn_data(sid, 2)
        assert got["user_input"] == "forwarded"
