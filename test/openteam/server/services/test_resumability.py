"""Tests for the session-resumability machinery.

Covers the new SessionStore primitives (turn linkage, task sidecars, the
SOP-scoped reuse matcher, checkpoint/truncate/restore), the dispatcher's
primary-arg resolution, and the ConversationService background-task drain.

These are pure-filesystem / pure-logic units — no LLM or AgentFoundation
inferencer is involved.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from openteam.server.services.json_io import normalize_arg_value, write_json_atomic
from openteam.server.services.session_store import SessionStore


@pytest.fixture
def store(tmp_path):
    """Fresh SessionStore rooted at tmp_path (always a new server)."""
    return SessionStore(tmp_path, resume_server="new")


@pytest.fixture
def session(store):
    """A created session; returns (session_id, session_dir)."""
    sess = store.create_session(title="T")
    sid = sess["id"]
    return sid, store.get_session_dir(sid)


def _make_workspace(session_dir, name, meta):
    """Create <session_dir>/tasks/<name>/ with a task_meta.json sidecar."""
    ws = session_dir / "tasks" / name
    ws.mkdir(parents=True, exist_ok=True)
    SessionStore.write_task_meta(ws, meta)
    return ws


def _mark_complete(ws):
    """Drop the canonical full-completion marker into a workspace."""
    (ws / "checkpoints").mkdir(parents=True, exist_ok=True)
    write_json_atomic(ws / "checkpoints" / "final_result.json", {"ok": True})


def _make_legacy_workspace(session_dir, name, *, complete=True):
    """Create a PRE-FEATURE workspace: NO task_meta.json sidecar.

    ``name`` must follow the allocator pattern
    ``<tool>_<YYYYMMDD>_<HHMMSS>_<uuid8>`` so the tool is derivable from the dir.
    Optionally complete (AF phase markers).
    """
    ws = session_dir / "tasks" / name
    (ws / "artifacts").mkdir(parents=True, exist_ok=True)
    if complete:
        (ws / "artifacts" / ".plan_completed").write_text("{}")
        (ws / "artifacts" / ".impl_completed").write_text("{}")
    return ws


def _write_action_artifact(session_dir, turn, round_, tool, target):
    """Write a turn artifact whose ``inference_response.txt`` carries one
    ``ToolsToInvoke`` action for ``tool`` with ``arguments`` = the bare target
    string — the shape the engine parser + dispatcher coercion handle."""
    rd = session_dir / f"turn_{turn:03d}" / f"round_{round_:03d}"
    rd.mkdir(parents=True, exist_ok=True)
    block = (
        "Working on it.\n\n"
        "```json ToolsToInvoke\n"
        + json.dumps({"type": "action", "name": tool, "arguments": target})
        + "\n```\n"
    )
    (rd / "inference_response.txt").write_text(block, encoding="utf-8")


def _set_sop_state(store, sid, *, sop_name="model_optimization", tool_phase_map=None):
    """Persist a minimal ``sop_state`` (the source the backfill reads for
    ``sop_name`` + ``phase_index``)."""
    store.update_session(
        sid,
        {
            "sop_state": {
                "sop_name": sop_name,
                "tool_phase_map": tool_phase_map or {"understand_codebase": "1"},
            }
        },
    )


# ── json_io ─────────────────────────────────────────────────────────────


class TestJsonIo:
    def test_normalize_path_resolves(self, tmp_path):
        # Two spellings of the same dir normalize to one absolute path.
        a = normalize_arg_value(str(tmp_path / "x" / ".." / "y"), "path")
        b = normalize_arg_value(str(tmp_path / "y"), "path")
        assert a == b
        assert a == str((tmp_path / "y").resolve())

    def test_normalize_string_strips(self):
        assert normalize_arg_value("  hi  ", "string") == "hi"
        assert normalize_arg_value(None) == ""
        assert normalize_arg_value("") == ""

    def test_write_json_atomic_roundtrip(self, tmp_path):
        p = tmp_path / "sub" / "f.json"
        write_json_atomic(p, {"a": 1})
        assert json.loads(p.read_text()) == {"a": 1}
        # No leftover temp files in the dir.
        assert [c.name for c in p.parent.iterdir()] == ["f.json"]


# ── next_turn_number ────────────────────────────────────────────────────


class TestNextTurnNumber:
    def test_fresh_session_is_one(self, store, session):
        sid, _ = session
        assert store.next_turn_number(sid) == 1

    def test_counts_turn_dirs(self, store, session):
        sid, sdir = session
        (sdir / "turn_001").mkdir()
        (sdir / "turn_002").mkdir()
        assert store.next_turn_number(sid) == 3

    def test_ignores_non_turn_dirs(self, store, session):
        sid, sdir = session
        (sdir / "turn_001").mkdir()
        (sdir / "tasks").mkdir()
        (sdir / "checkpoints").mkdir()
        assert store.next_turn_number(sid) == 2


# ── update_message ──────────────────────────────────────────────────────


class TestUpdateMessage:
    def test_merges_and_persists(self, store, session):
        sid, _ = session
        store.append_message(
            sid, {"id": "m1", "role": "task_ref", "status": "starting"}
        )
        store.update_message(sid, "m1", {"status": "completed", "documentPath": "/d"})
        msgs = store.get_session(sid)["messages"]
        m = next(m for m in msgs if m["id"] == "m1")
        assert m["status"] == "completed"
        assert m["documentPath"] == "/d"

    def test_missing_message_returns_none(self, store, session):
        sid, _ = session
        assert store.update_message(sid, "nope", {"x": 1}) is None


# ── task sidecars ───────────────────────────────────────────────────────


class TestTaskMeta:
    def test_write_read_roundtrip(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        SessionStore.write_task_meta(ws, {"task_id": "t1", "status": "starting"})
        assert SessionStore.read_task_meta(ws) == {
            "task_id": "t1",
            "status": "starting",
        }

    def test_read_missing_is_none(self, tmp_path):
        assert SessionStore.read_task_meta(tmp_path) is None

    def test_update_preserves_other_fields(self, store, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        SessionStore.write_task_meta(
            ws, {"task_id": "t1", "created_at": "X", "status": "starting"}
        )
        store.update_task_meta(ws, {"status": "completed"})
        meta = SessionStore.read_task_meta(ws)
        assert meta["status"] == "completed"
        assert meta["created_at"] == "X"  # preserved


# ── is_workspace_complete ───────────────────────────────────────────────


class TestIsWorkspaceComplete:
    def test_final_result_json(self, tmp_path):
        ws = tmp_path / "ws"
        ws.mkdir()
        assert not SessionStore.is_workspace_complete(ws)
        _mark_complete(ws)
        assert SessionStore.is_workspace_complete(ws)

    def test_phase_markers_fallback(self, tmp_path):
        ws = tmp_path / "ws"
        (ws / "artifacts").mkdir(parents=True)
        (ws / "artifacts" / ".plan_completed").write_text("{}")
        assert not SessionStore.is_workspace_complete(ws)  # only plan
        (ws / "artifacts" / ".impl_completed").write_text("{}")
        assert SessionStore.is_workspace_complete(ws)  # both markers


# ── reconcile_task_ref_statuses ─────────────────────────────────────────


class TestReconcileTaskRef:
    def test_running_complete_to_completed(self, store, session):
        sid, sdir = session
        ws = _make_workspace(sdir, "uc_1", {"task_id": "t1"})
        _mark_complete(ws)
        store.append_message(
            sid,
            {
                "id": "task-ref-t1",
                "role": "task_ref",
                "status": "running",
                "workspace": str(ws),
            },
        )
        store.reconcile_task_ref_statuses(sid)
        m = next(
            m for m in store.get_session(sid)["messages"] if m["id"] == "task-ref-t1"
        )
        assert m["status"] == "completed"

    def test_running_incomplete_to_error(self, store, session):
        sid, sdir = session
        ws = _make_workspace(sdir, "uc_2", {"task_id": "t2"})  # no completion marker
        store.append_message(
            sid,
            {
                "id": "task-ref-t2",
                "role": "task_ref",
                "status": "running",
                "workspace": str(ws),
            },
        )
        store.reconcile_task_ref_statuses(sid)
        m = next(
            m for m in store.get_session(sid)["messages"] if m["id"] == "task-ref-t2"
        )
        assert m["status"] == "error"

    def test_completed_unchanged(self, store, session):
        sid, sdir = session
        ws = _make_workspace(sdir, "uc_3", {"task_id": "t3"})
        store.append_message(
            sid,
            {
                "id": "task-ref-t3",
                "role": "task_ref",
                "status": "completed",
                "workspace": str(ws),
            },
        )
        store.reconcile_task_ref_statuses(sid)
        m = next(
            m for m in store.get_session(sid)["messages"] if m["id"] == "task-ref-t3"
        )
        assert m["status"] == "completed"


# ── find_reusable_workspace ─────────────────────────────────────────────


class TestFindReusableWorkspace:
    def _meta(self, target, created_at, name="understand_codebase"):
        return {
            "tool_name": name,
            "sop_name": "model_optimization",
            "phase_index": "1",
            "primary_arg_value": target,
            "task_key": f"model_optimization/1/{name}/{target}",
            "created_at": created_at,
        }

    def test_matches_by_full_key(self, store, session):
        sid, sdir = session
        _make_workspace(sdir, "uc_a", self._meta("/path/A", "2026-01-01T00:00:00Z"))
        got = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", "/path/A"
        )
        assert got is not None and got.name == "uc_a"

    def test_distinct_targets_do_not_cross_match(self, store, session):
        sid, sdir = session
        _make_workspace(sdir, "uc_a", self._meta("/path/A", "2026-01-01T00:00:00Z"))
        _make_workspace(sdir, "uc_b", self._meta("/path/B", "2026-01-02T00:00:00Z"))
        a = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", "/path/A"
        )
        b = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", "/path/B"
        )
        assert a.name == "uc_a"
        assert b.name == "uc_b"

    def test_referenced_workspace_excluded(self, store, session):
        sid, sdir = session
        ws = _make_workspace(
            sdir, "uc_ref", self._meta("/path/A", "2026-01-01T00:00:00Z")
        )
        # A live task_ref references it → it is NOT an orphan → not reusable.
        store.append_message(
            sid,
            {
                "id": "task-ref-x",
                "role": "task_ref",
                "status": "completed",
                "workspace": str(ws),
            },
        )
        got = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", "/path/A"
        )
        assert got is None

    def test_oldest_orphan_first(self, store, session):
        sid, sdir = session
        _make_workspace(sdir, "uc_new", self._meta("/path/A", "2026-02-02T00:00:00Z"))
        _make_workspace(sdir, "uc_old", self._meta("/path/A", "2026-01-01T00:00:00Z"))
        got = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", "/path/A"
        )
        assert got.name == "uc_old"

    def test_empty_key_returns_none(self, store, session):
        sid, sdir = session
        _make_workspace(sdir, "uc_a", self._meta("/path/A", "2026-01-01T00:00:00Z"))
        # Ad-hoc (no SOP) → empty sop_name/phase → never reused.
        assert (
            store.find_reusable_workspace(
                sid, "understand_codebase", "", "1", "/path/A"
            )
            is None
        )
        assert (
            store.find_reusable_workspace(
                sid, "understand_codebase", "model_optimization", "", "/path/A"
            )
            is None
        )

    def test_sidecarless_workspace_not_matched(self, store, session):
        # find_reusable is precise-only: a workspace with NO task_meta.json is NOT
        # matched directly. Pre-feature workspaces are adopted by the backfill
        # first (see TestBackfillTaskSidecars); without a sidecar → no loose reuse.
        sid, sdir = session
        _make_legacy_workspace(
            sdir, "understand_codebase_20260628_170158_325cf412", complete=True
        )
        assert (
            store.find_reusable_workspace(
                sid, "understand_codebase", "model_optimization", "1", "/any/target"
            )
            is None
        )

    def test_complete_beats_partial(self, store, session):
        # Two orphans with the SAME key: the COMPLETE one (instant reuse) wins over
        # the PARTIAL one (which AF would only continue).
        sid, sdir = session
        partial = _make_workspace(
            sdir, "uc_partial", self._meta("/path/A", "2026-06-29T00:00:00Z")
        )
        complete = _make_workspace(
            sdir, "uc_complete", self._meta("/path/A", "2026-01-01T00:00:00Z")
        )
        _mark_complete(complete)
        assert not SessionStore.is_workspace_complete(partial)
        got = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", "/path/A"
        )
        assert got.name == "uc_complete"

    def test_dir_tool_name_extraction(self):
        assert (
            SessionStore._dir_tool_name("understand_codebase_20260628_170158_325cf412")
            == "understand_codebase"
        )
        assert (
            SessionStore._dir_tool_name("research_propose_20260629_035544_a4240a0f")
            == "research_propose"
        )
        # Non-matching names pass through unchanged (so they never match a tool).
        assert SessionStore._dir_tool_name("not_a_workspace") == "not_a_workspace"


# ── backfill (adopt pre-feature workspaces) ─────────────────────────────


class TestBackfillTaskSidecars:
    PMAP = {"understand_codebase": "target"}
    PTYPE = {"understand_codebase": "path"}

    def test_recovers_full_key_and_enables_reuse(self, store, session, tmp_path):
        # The user's scenario: a complete pre-feature workspace (no sidecar) +
        # the session's recorded action. Backfill reconstructs the full key from
        # the action + sop_state, and the precise matcher then reuses it.
        sid, sdir = session
        target = str(tmp_path / "codeA")
        expect = normalize_arg_value(target, "path")
        ws = _make_legacy_workspace(
            sdir, "understand_codebase_20260628_170158_325cf412", complete=True
        )
        _write_action_artifact(sdir, 1, 4, "understand_codebase", target)
        _set_sop_state(store, sid)

        assert store.backfill_task_sidecars(sid, self.PMAP, self.PTYPE) == 1
        meta = SessionStore.read_task_meta(ws)
        assert meta["tool_name"] == "understand_codebase"
        assert meta["sop_name"] == "model_optimization"
        assert str(meta["phase_index"]) == "1"
        assert meta["primary_arg_value"] == expect
        assert meta["status"] == "completed"
        assert meta.get("backfilled") is True
        got = store.find_reusable_workspace(
            sid, "understand_codebase", "model_optimization", "1", expect
        )
        assert got is not None and got.name == ws.name

    def test_skips_existing_sidecar(self, store, session):
        sid, sdir = session
        ws = _make_workspace(sdir, "uc_existing", {"task_id": "keep", "tool_name": "x"})
        _set_sop_state(store, sid)
        assert store.backfill_task_sidecars(sid, self.PMAP, self.PTYPE) == 0
        assert SessionStore.read_task_meta(ws)["task_id"] == "keep"  # untouched

    def test_multi_workspace_attribution_by_order(self, store, session, tmp_path):
        sid, sdir = session
        ta, tb = str(tmp_path / "codeA"), str(tmp_path / "codeB")
        a = _make_legacy_workspace(
            sdir, "understand_codebase_20260101_000000_aaaaaaaa", complete=True
        )
        b = _make_legacy_workspace(
            sdir, "understand_codebase_20260102_000000_bbbbbbbb", complete=True
        )
        _write_action_artifact(sdir, 1, 1, "understand_codebase", ta)  # 1st → oldest ws
        _write_action_artifact(sdir, 2, 1, "understand_codebase", tb)  # 2nd → newest ws
        _set_sop_state(store, sid)
        store.backfill_task_sidecars(sid, self.PMAP, self.PTYPE)
        assert SessionStore.read_task_meta(a)[
            "primary_arg_value"
        ] == normalize_arg_value(ta, "path")
        assert SessionStore.read_task_meta(b)[
            "primary_arg_value"
        ] == normalize_arg_value(tb, "path")

    def test_unrecoverable_target_writes_empty_and_does_not_match(self, store, session):
        sid, sdir = session
        ws = _make_legacy_workspace(
            sdir, "understand_codebase_20260628_170158_325cf412", complete=True
        )
        _set_sop_state(store, sid)  # no turn artifact → target unrecoverable
        store.backfill_task_sidecars(sid, self.PMAP, self.PTYPE)
        meta = SessionStore.read_task_meta(ws)
        assert meta["primary_arg_value"] == ""
        assert meta["task_key"] is None
        # An empty-primary_arg sidecar never matches a real request → fresh (safe).
        assert (
            store.find_reusable_workspace(
                sid, "understand_codebase", "model_optimization", "1", "/real/target"
            )
            is None
        )


# ── checkpoint / list / restore ─────────────────────────────────────────


class TestCheckpoint:
    def test_checkpoint_excludes_top_level_but_preserves_nested(self, store, session):
        sid, sdir = session
        (sdir / "turn_001").mkdir()
        (sdir / "turn_001" / "user_input.txt").write_text("hi")
        ws = _make_workspace(sdir, "uc_a", {"task_id": "t"})
        _mark_complete(ws)  # nested <ws>/checkpoints/final_result.json
        name = store.checkpoint_session(sid)
        snap = sdir / "checkpoints" / name
        assert (snap / "session_state.json").is_file()
        assert (snap / "turn_001" / "user_input.txt").read_text() == "hi"
        # nested task checkpoints/ preserved...
        assert (snap / "tasks" / "uc_a" / "checkpoints" / "final_result.json").is_file()
        # ...but the top-level checkpoints/ child was NOT recursively copied.
        assert not (snap / "checkpoints").exists()

    def test_list_checkpoints(self, store, session):
        sid, _ = session
        store.append_message(sid, {"id": "m", "role": "manager", "content": "x"})
        name = store.checkpoint_session(sid)
        cps = store.list_checkpoints(sid)
        assert [c["name"] for c in cps] == [name]
        assert cps[0]["message_count"] >= 2  # welcome + appended

    def test_restore_round_trip(self, store, session):
        sid, _ = session
        before = len(store.get_session(sid)["messages"])
        name = store.checkpoint_session(sid)
        store.append_message(
            sid, {"id": "extra", "role": "manager", "content": "later"}
        )
        assert len(store.get_session(sid)["messages"]) == before + 1
        store.restore_checkpoint(sid, name)
        assert len(store.get_session(sid)["messages"]) == before  # reverted
        # restore itself snapshots the pre-restore state first → 2 checkpoints now.
        assert len(store.list_checkpoints(sid)) == 2

    def test_restore_unknown_returns_none(self, store, session):
        sid, _ = session
        assert store.restore_checkpoint(sid, "nope") is None


# ── truncate_session_at_message ─────────────────────────────────────────


class TestTruncate:
    def _seed(self, store, sid, sdir):
        # welcome(0) already present; add manager/assistant for turns 1..3.
        for t in (1, 2, 3):
            store.append_message(
                sid,
                {
                    "id": f"u{t}",
                    "role": "manager",
                    "content": f"q{t}",
                    "turn_number": t,
                },
            )
            store.append_message(
                sid,
                {
                    "id": f"a{t}",
                    "role": "assistant",
                    "content": f"r{t}",
                    "turn_number": t,
                },
            )
            td = sdir / f"turn_{t:03d}"
            td.mkdir()
            write_json_atomic(
                td / "sop_state_in.json",
                {
                    "sop_state": {
                        "sop_name": "model_optimization",
                        "current_phase": str(t),
                    },
                    "suspended_sops": [],
                },
            )

    def test_truncates_messages_and_turn_dirs(self, store, session):
        sid, sdir = session
        self._seed(store, sid, sdir)
        store.truncate_session_at_message(sid, "u2", drop_tasks=False)
        ids = [m["id"] for m in store.get_session(sid)["messages"]]
        assert "u1" in ids and "a1" in ids
        assert "u2" not in ids and "a2" not in ids and "u3" not in ids
        assert (sdir / "turn_001").is_dir()
        assert not (sdir / "turn_002").exists()
        assert not (sdir / "turn_003").exists()

    def test_restores_pre_turn_sop_boundary(self, store, session):
        sid, sdir = session
        self._seed(store, sid, sdir)
        store.truncate_session_at_message(sid, "u2", drop_tasks=False)
        sess = store.get_session(sid)
        # boundary == turn_002/sop_state_in.json (state ENTERING turn 2)
        assert sess["sop_state"] == {
            "sop_name": "model_optimization",
            "current_phase": "2",
        }

    def test_drop_tasks_removes_at_or_after_cut(self, store, session):
        sid, sdir = session
        self._seed(store, sid, sdir)
        _make_workspace(sdir, "uc_t1", {"task_id": "t1", "turn_number": 1})
        _make_workspace(sdir, "uc_t2", {"task_id": "t2", "turn_number": 2})
        _make_workspace(sdir, "uc_t3", {"task_id": "t3", "turn_number": 3})
        res = store.truncate_session_at_message(sid, "u2", drop_tasks=True)
        assert (sdir / "tasks" / "uc_t1").is_dir()  # before cut → kept
        assert not (sdir / "tasks" / "uc_t2").exists()  # at cut → dropped
        assert not (sdir / "tasks" / "uc_t3").exists()  # after cut → dropped
        assert res["cut_turn"] == 2
        assert len(res["dropped_workspaces"]) == 2

    def test_keep_tasks_leaves_workspaces(self, store, session):
        sid, sdir = session
        self._seed(store, sid, sdir)
        _make_workspace(sdir, "uc_t2", {"task_id": "t2", "turn_number": 2})
        store.truncate_session_at_message(sid, "u2", drop_tasks=False)
        assert (sdir / "tasks" / "uc_t2").is_dir()  # kept → reusable orphan

    def test_cut_turn_fallback_without_stamp(self, store, session):
        sid, sdir = session
        # Messages without turn_number → fallback counts manager msgs before idx.
        store.append_message(sid, {"id": "u1", "role": "manager", "content": "q1"})
        store.append_message(sid, {"id": "u2", "role": "manager", "content": "q2"})
        res = store.truncate_session_at_message(sid, "u2", drop_tasks=False)
        assert res["cut_turn"] == 2  # 1 manager before u2, +1


# ── ToolDispatcher primary-arg resolution ───────────────────────────────


class TestPrimaryArgResolution:
    def _resolve(self, data):
        from openteam.server.services.tool_dispatcher import ToolDispatcher

        return ToolDispatcher._resolve_primary_arg(data)

    def test_explicit_primary_arg_wins(self):
        data = {
            "primary_arg": "request",
            "derived_from": {"target_path_arg": "workflow_target_path"},
        }
        assert self._resolve(data) == ("request", "string")

    def test_derived_target_path_arg(self):
        data = {
            "derived_from": {"target_path_arg": "target"},
            "parameters": [{"name": "target", "type": "path"}],
        }
        assert self._resolve(data) == ("target", "path")

    def test_single_required_positional_fallback(self):
        data = {
            "parameters": [
                {
                    "name": "request",
                    "type": "string",
                    "required": True,
                    "positional": True,
                },
                {"name": "--flag", "type": "flag"},
            ]
        }
        assert self._resolve(data) == ("request", "string")

    def test_none_when_unresolvable(self):
        data = {"parameters": [{"name": "--a"}, {"name": "--b"}]}
        assert self._resolve(data) == (None, "string")


# ── ConversationService background-task drain ───────────────────────────


class TestDrainBackgroundTasks:
    @pytest.fixture
    def conv_svc(self, tmp_path):
        from openteam.server.services.conversation_service import ConversationService

        return ConversationService(tmp_path)

    def test_register_then_drain_cancels_and_clears(self, conv_svc):
        async def _scenario():
            async def _long():
                await asyncio.sleep(60)

            t = asyncio.create_task(_long())
            conv_svc._register_bg_task("sid1", t)
            assert t in conv_svc._bg_tasks["sid1"]
            await conv_svc.drain_session_background_tasks("sid1")
            assert t.cancelled()
            assert "sid1" not in conv_svc._bg_tasks

        asyncio.run(_scenario())

    def test_done_task_self_evicts(self, conv_svc):
        async def _scenario():
            async def _quick():
                return 1

            t = asyncio.create_task(_quick())
            conv_svc._register_bg_task("sid2", t)
            await t  # let it finish → add_done_callback should evict it
            await asyncio.sleep(0)  # let callbacks run
            assert not conv_svc._bg_tasks.get("sid2")

        asyncio.run(_scenario())

    def test_drain_empty_is_noop(self, conv_svc):
        asyncio.run(conv_svc.drain_session_background_tasks("never-seen"))
