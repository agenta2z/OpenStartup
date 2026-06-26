"""§5 DoD(6): OpenStartup optional session-root adoption — the per-turn RunContext
isolates run-state across turns and across duplicate-session_id connections.

These assert the run_context primitives OpenStartup relies on for the optional
adoption (the wiring in ConversationService.run_conversation_turn). They use the
AgentFoundation run_context package directly (no server stack needed)."""

import pytest

rc = pytest.importorskip(
    "agent_foundation.common.inferencers.run_context",
    reason="AgentFoundation run_context package required",
)


def test_per_turn_child_contexts_are_isolated():
    """Two turns on one session get distinct child contexts (state isolation)."""
    RunContext = rc.RunContext
    root = RunContext.root(workspace=None)
    t1 = root.child("turn_1")
    t2 = root.child("turn_2")
    assert t1.path == "/turn_1" and t2.path == "/turn_2"
    t1.node().call = {"answer": "A"}
    t2.node().call = {"answer": "B"}
    assert root._store.node("/turn_1").call == {"answer": "A"}
    assert root._store.node("/turn_2").call == {"answer": "B"}


def test_same_session_shares_one_root_distinct_turns_isolated():
    """Session-root model: turns of one session share ONE root + in-memory store,
    and distinct turn numbers are isolated by their own turn node (no cross-talk in
    the common case). The same-user_turn collision under two concurrent connections
    is a pre-existing, out-of-scope race, not handled here."""
    RunContext = rc.RunContext
    root = RunContext.root(workspace=None)  # ONE root per session, reused across turns
    t5 = root.child("turn_5")
    t6 = root.child("turn_6")
    t5.node().call = {"answer": "A"}
    t6.node().call = {"answer": "B"}
    assert t5._store is t6._store is root._store  # shared in-memory store
    assert root._store.node("/turn_5").call == {"answer": "A"}
    assert root._store.node("/turn_6").call == {"answer": "B"}  # no cross-talk


def test_run_id_provenance_flows_into_child():
    """A session run-id minted at the root is visible to the turn's child node."""
    RunContext = rc.RunContext
    root = RunContext.root(workspace=None)
    root.node().provenance.append({"run_id": "sess-123"})
    turn = root.child("turn_1")
    # The child shares the same store; root provenance is reachable.
    assert root._store.node("/").provenance == [{"run_id": "sess-123"}]
    assert turn._store is root._store


# --- ConversationService session-root wiring (the refactor under test) ----------

def _bare_service():
    """A ConversationService with only the caches wired (skips the heavy __init__)."""
    from openteam.server.services.conversation_service import ConversationService

    svc = ConversationService.__new__(ConversationService)
    svc._session_roots = {}
    svc._inferencers = {}
    return svc


def test_get_session_root_is_cached_per_session(tmp_path):
    """ONE session-scoped root per session_id, reused across turns (not re-minted)."""
    svc = _bare_service()
    r1 = svc._get_session_root("sid", session_dir=tmp_path, cwd=str(tmp_path))
    r2 = svc._get_session_root("sid", session_dir=tmp_path, cwd=str(tmp_path))
    assert r1 is not None and r1 is r2
    assert list(svc._session_roots) == ["sid"]


def test_turn_children_share_tier2_and_have_distinct_paths(tmp_path):
    """Turn children off the session root share Tier-2 (safe — OS never mutates it)
    + the in-memory store, with distinct paths."""
    svc = _bare_service()
    root = svc._get_session_root("sid", session_dir=tmp_path, cwd=str(tmp_path))
    t1, t2 = root.child("turn_1"), root.child("turn_2")
    assert t1.runtime is t2.runtime is root.runtime
    assert t1._store is t2._store is root._store
    assert t1.path == "/turn_1" and t2.path == "/turn_2"


def test_eviction_clears_session_root(tmp_path):
    """evict_session_inferencer drops the session root in lock-step with the CI."""
    svc = _bare_service()
    r1 = svc._get_session_root("sid", session_dir=tmp_path, cwd=str(tmp_path))
    svc.evict_session_inferencer("sid")
    assert "sid" not in svc._session_roots
    r2 = svc._get_session_root("sid", session_dir=tmp_path, cwd=str(tmp_path))
    assert r2 is not r1  # a fresh root after eviction


def test_store_loaded_once_across_turns(tmp_path, monkeypatch):
    """The run-state store is read from disk ONCE (at session-root mint), not per
    turn — the efficiency win over the old per-turn RunStateStore.load."""
    store_dir = tmp_path / "run_state"
    store_dir.mkdir(parents=True)
    (store_dir / "store.json").write_text('{"nodes": {}}')

    real_load = rc.RunStateStore.load
    calls = {"n": 0}

    def _counting_load(path):
        calls["n"] += 1
        return real_load(path)

    monkeypatch.setattr(rc.RunStateStore, "load", _counting_load)

    svc = _bare_service()
    for n in range(1, 4):  # 3 turns, one session
        root = svc._get_session_root("sid", session_dir=tmp_path, cwd=str(tmp_path))
        root.child(f"turn_{n}")
    assert calls["n"] == 1  # loaded once, not 3x
