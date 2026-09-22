"""Unit tests for durable task-graph persistence + legacy reconstruction.

Covers the completed-task-graph feature backend (Fix 2/3):
  * GraphSnapshot.to_dict/from_dict round-trip (outputPath preserved, node_streams
    excluded, defensive on corrupt/version/partial blobs).
  * TaskGraphSnapshotStore.persist_task / load_task_from_disk / get_or_load (the
    3-tier in-memory→disk→reconstruct order, cache-marked-terminal) / drop_session
    disk cleanup.
  * reconstruct_graph_from_task_dir on a synthesized PTI→Dual→BTA workspace tree —
    the graph is defined by ORCHESTRATORS (class from logs/session/{ClassName}),
    NOT the raw dir tree: verifies containers-vs-leaves, flat review/fix (no
    round_NN wrapper nodes, no panelist phantoms), the virtual breakdown node, and
    per-node outputPath resolution.

Self-contained (builds its own tmp workspace) so it needs no live _runtime data.
"""

from __future__ import annotations

from pathlib import Path

from openteam.server.services.task_graph_reconstruct import (
    reconstruct_graph_from_task_dir,
)
from openteam.server.services.task_graph_snapshot import (
    GraphSnapshot,
    TaskGraphSnapshotStore,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mk_node(d: Path, cls: str | None, *, output: bool = True) -> Path:
    """Create a workspace node dir: a class log (→ makes it a graph node of that
    inferencer class) and, optionally, an ``outputs/output.md`` deliverable."""
    d.mkdir(parents=True, exist_ok=True)
    if cls is not None:
        sess = d / "logs" / "session"
        sess.mkdir(parents=True, exist_ok=True)
        (sess / f"{cls}-abc12345.jsonl").write_text("{}", encoding="utf-8")
    if output:
        outs = d / "outputs"
        outs.mkdir(parents=True, exist_ok=True)
        (outs / "output.md").write_text("# deliverable", encoding="utf-8")
    return d


def _build_pti_workspace(root: Path) -> Path:
    """PTI(planner=Dual{BTA}, executor=leaf-ish). Also exercises: a `round_NN`
    wrapper (workspace-only, NO class log) containing `review`/`fix`, and a
    `review` that ALSO has a logged `panelist_00` child (must NOT become a node)."""
    _mk_node(root, "PlanThenImplementInferencer")
    ch = root / "children"

    # planner = Dual → propose(=BTA) + round_01/{review, fix}
    planner = _mk_node(ch / "planner", "DualInferencer")
    pch = planner / "children"
    propose = _mk_node(pch / "propose", "BreakdownThenAggregateInferencer")
    prch = propose / "children"
    _mk_node(prch / "breakdown", "ClaudeCodeCliInferencer")
    _mk_node(prch / "worker_00", "ClaudeCodeCliInferencer")
    _mk_node(prch / "worker_01", "ClaudeCodeCliInferencer")
    _mk_node(prch / "aggregator", "ClaudeCodeCliInferencer")
    # round_01 is a WORKSPACE wrapper — NO class log (not a graph node).
    round01 = _mk_node(pch / "round_01", None, output=False)
    r_review = _mk_node(round01 / "children" / "review", "CodexCliInferencer")
    _mk_node(round01 / "children" / "fix", "ClaudeCodeCliInferencer")
    # review runs its own leaf CLI AND has logged panelist children — panelists
    # must NOT be emitted (review is a leaf; the live graph never had them).
    _mk_node(r_review / "children" / "panelist_00", "ClaudeCodeCliInferencer")
    _mk_node(r_review / "children" / "guardrail", "ClaudeCodeCliInferencer")

    # executor = leaf phase (a container per PTI, but its own child is a leaf).
    _mk_node(ch / "executor", "DualInferencer")
    _mk_node(ch / "executor" / "children" / "propose", "ClaudeCodeCliInferencer")
    return root


def _all_ids(snap: GraphSnapshot) -> set[str]:
    ids = {n["id"] for n in (snap.root_topology or {}).get("nodes", [])}
    for sg in snap.sub_graphs.values():
        ids.update(n["id"] for n in sg["nodes"])
    return ids


# ---------------------------------------------------------------------------
# Serialization round-trip (Fix 2)
# ---------------------------------------------------------------------------
def test_to_dict_from_dict_roundtrip_excludes_streams_keeps_outputpath():
    snap = GraphSnapshot("task-x")
    snap.root_topology = {
        "nodes": [
            {
                "id": "a",
                "label": "A",
                "status": "completed",
                "outputPath": "/x/a.md",
                "is_container": True,
            }
        ],
        "edges": [],
        "layout": "",
        "version": 1,
    }
    snap.sub_graphs = {
        "a": {
            "nodes": [
                {
                    "id": "a/b",
                    "label": "B",
                    "status": "completed",
                    "outputPath": "/x/b.md",
                }
            ],
            "edges": [{"source": "a", "target": "a/b"}],
            "layout": "",
            "version": 1,
        }
    }
    snap.last_reconcile = {"a": "completed", "a/b": "completed"}
    snap.node_streams = {"a": {"chunks": ["stream"], "is_final": True}}

    d = snap.to_dict()
    assert "node_streams" not in d  # excluded from disk

    revived = GraphSnapshot.from_dict(d)
    assert revived is not None
    assert revived.task_id == "task-x"
    assert revived.root_topology["nodes"][0]["outputPath"] == "/x/a.md"
    assert revived.root_topology["nodes"][0]["is_container"] is True
    assert revived.sub_graphs["a"]["nodes"][0]["id"] == "a/b"
    assert revived.last_reconcile == {"a": "completed", "a/b": "completed"}
    assert revived.node_streams == {}  # not persisted


def test_from_dict_defensive():
    assert GraphSnapshot.from_dict(None) is None
    assert GraphSnapshot.from_dict("garbage") is None
    assert GraphSnapshot.from_dict({"_schema_version": 999, "task_id": "x"}) is None
    assert GraphSnapshot.from_dict({"task_id": "x"}) is None  # missing version
    assert GraphSnapshot.from_dict({"_schema_version": 1}) is None  # missing task_id


# ---------------------------------------------------------------------------
# Store: persist / load / get_or_load / drop_session (Fix 2/3)
# ---------------------------------------------------------------------------
class _FakeSessionStore:
    def __init__(self, base: Path) -> None:
        self._base = Path(base)

    def get_session_dir(self, session_id: str) -> Path:
        d = self._base / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d


def _sample_snapshot(task_id: str = "task-x") -> GraphSnapshot:
    s = GraphSnapshot(task_id)
    s.root_topology = {
        "nodes": [
            {"id": "a", "label": "A", "status": "completed", "outputPath": "/x/a.md"}
        ],
        "edges": [],
        "layout": "",
        "version": 1,
    }
    s.last_reconcile = {"a": "completed"}
    return s


def test_persist_and_load_from_disk(tmp_path):
    store = TaskGraphSnapshotStore(session_store=_FakeSessionStore(tmp_path))
    snap = _sample_snapshot()
    store._sessions["s1"] = {"task-x": snap}
    store.persist_task("s1", "task-x")

    path = tmp_path / "s1" / "task_graphs" / "task-x.json"
    assert path.is_file()

    loaded = store.load_task_from_disk("s1", "task-x")
    assert loaded is not None
    assert loaded.root_topology["nodes"][0]["outputPath"] == "/x/a.md"


def test_get_or_load_three_tier(tmp_path):
    store = TaskGraphSnapshotStore(session_store=_FakeSessionStore(tmp_path))
    snap = _sample_snapshot()
    store._sessions["s1"] = {"task-x": snap}

    # Tier 1 — in-memory hit returns the same object.
    assert store.get_or_load("s1", "task-x") is snap

    # Tier 2 — persist, drop from memory, get_or_load loads from disk + caches it
    # MARKED TERMINAL (so prune_expired can evict it).
    store.persist_task("s1", "task-x")
    del store._sessions["s1"]["task-x"]
    got = store.get_or_load("s1", "task-x")
    assert got is not None
    assert got.task_id == "task-x"
    assert got._terminal_at is not None  # cached terminal → evictable
    assert store._sessions["s1"]["task-x"] is got


def test_drop_session_removes_disk(tmp_path):
    store = TaskGraphSnapshotStore(session_store=_FakeSessionStore(tmp_path))
    store._sessions["s1"] = {"task-x": _sample_snapshot()}
    store.persist_task("s1", "task-x")
    assert (tmp_path / "s1" / "task_graphs").is_dir()

    store.drop_session("s1")
    assert not (tmp_path / "s1" / "task_graphs").exists()
    assert "s1" not in store._sessions


def test_get_or_load_tier3_reconstruct(tmp_path):
    """Missing in-memory + disk → reconstruct from the workspace; the reconstructed
    snapshot gets the chip task_id and replays."""
    store = TaskGraphSnapshotStore(session_store=_FakeSessionStore(tmp_path))
    ws = _build_pti_workspace(tmp_path / "ws" / "task_dir")
    snap = store.get_or_load("s2", "task-uc", str(ws))
    assert snap is not None
    assert snap.task_id == "task-uc"
    events = snap.to_replay_events()
    assert any(
        e["type"] == "graph_topology" and e.get("task_id") == "task-uc" for e in events
    )


# ---------------------------------------------------------------------------
# Reconstruction fidelity (Fix 3) — orchestrator-defined, not dir-defined
# ---------------------------------------------------------------------------
def test_reconstruct_pti_dual_bta_structure(tmp_path):
    ws = _build_pti_workspace(tmp_path / "task_dir")
    snap = reconstruct_graph_from_task_dir(str(ws))
    assert snap is not None

    root_ids = [n["id"] for n in snap.root_topology["nodes"]]
    assert root_ids == ["planner", "executor"]  # PTI phases, in order
    assert all(n.get("is_container") for n in snap.root_topology["nodes"])
    assert {"source": "planner", "target": "executor"} in snap.root_topology["edges"]

    ids = _all_ids(snap)
    # Dual under planner: flat propose/review/fix (NO round_NN wrapper node).
    assert "planner/propose" in ids
    assert "planner/review" in ids
    assert "planner/fix" in ids
    # BTA under propose: virtual breakdown + workers + aggregator.
    assert "planner/propose/breakdown" in ids
    assert "planner/propose/worker_00" in ids
    assert "planner/propose/worker_01" in ids
    assert "planner/propose/aggregator" in ids

    # NO phantom nodes: no round_NN wrappers, no panelist/guardrail leaves.
    assert not [i for i in ids if "round_" in i], f"round phantom nodes: {ids}"
    assert not [i for i in ids if "panelist" in i or "guardrail" in i]

    # review is a LEAF — it must NOT have a sub-graph (no drill-in to panelists).
    assert "planner/review" not in snap.sub_graphs
    assert "planner/fix" not in snap.sub_graphs

    # breakdown is virtual (no dir) but present; edges form the diamond.
    prop_sg = snap.sub_graphs["planner/propose"]
    prop_edges = {(e["source"], e["target"]) for e in prop_sg["edges"]}
    assert ("planner/propose/breakdown", "planner/propose/worker_00") in prop_edges
    assert ("planner/propose/worker_00", "planner/propose/aggregator") in prop_edges

    # Dual back-edge fix→review is present.
    planner_edges = {
        (e["source"], e["target"]) for e in snap.sub_graphs["planner"]["edges"]
    }
    assert ("planner/fix", "planner/review") in planner_edges

    # Per-node outputPath resolved (review/fix take the round_01 dir's output).
    review_node = next(
        n for n in snap.sub_graphs["planner"]["nodes"] if n["id"] == "planner/review"
    )
    assert review_node.get("outputPath", "").endswith(
        "round_01/children/review/outputs/output.md"
    )


def test_reconstruct_no_children_returns_none(tmp_path):
    """A graph-less task (no children/) → None so the FE shows the deliverable
    fallback rather than an empty graph."""
    leaf = _mk_node(tmp_path / "leaf_task", "ConversationalInferencer")
    assert reconstruct_graph_from_task_dir(str(leaf)) is None
    assert reconstruct_graph_from_task_dir(str(tmp_path / "does_not_exist")) is None
