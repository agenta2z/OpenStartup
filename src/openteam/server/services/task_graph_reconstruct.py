"""Reconstruct a task's graph from its on-disk workspace tree (Fix 3, tier 3).

For LEGACY tasks (completed before graph-snapshot persistence shipped) there is no
persisted `task_graphs/<id>.json`, so we rebuild a best-effort `GraphSnapshot`
from the workspace and feed it through the SAME replay pipeline
(`to_replay_events` → `useGraphState` → `GraphFlowView`/`NodeDetailPanel`) the live
and disk-persisted tiers use. The FE renders it identically; node-click →
`GET /api/view/{outputPath}` already works.

ROOT-CAUSE PRINCIPLE — the graph is DEFINED BY ORCHESTRATORS, not by the workspace
tree. `InferencerBase.ainfer` only seeds the graph-reporter sink; LEAF inferencers
emit NO node, and only orchestrators (PTI / Dual / BTA / MFI / MFDual / LWI) emit
topology. So a naive "every dir with children/ is a node" walk is WRONG — it would
invent `round_NN` wrapper nodes (workspace-only) and phantom `panelist_*` nodes
under a leaf `review`, and miss the virtual `breakdown` node (which has no dir). We
therefore reconstruct TOP-DOWN, driven by each container's ORCHESTRATOR CLASS
(detected from `logs/session/{ClassName}-*.jsonl`), emitting that class's canonical
topology. The dir tree supplies only: node COUNTS, DELIVERABLE paths, and the
round-collapse (review/fix take the final round's output). An unrecognized class
falls back to a best-effort logged-dir walk.

Fidelity: for the SOP orchestrators this matches the live graph (correct
containers-vs-leaves, flat review/fix, no phantom round_NN/panelist nodes, virtual
breakdown present). It MODELS AF's orchestrator set, so it is coupled to AF and is
strictly the LEGACY fallback — the authoritative faithful graph for any post-fix
task is the persisted snapshot. This runs blocking I/O (fs walk + reads); call it
OFF the event loop (`asyncio.to_thread`).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from openteam.server.services.task_graph_snapshot import GraphSnapshot

logger = logging.getLogger(__name__)

# Non-node sibling dirs that appear alongside `children/` at every workspace level
# (never graph nodes). Used only by the unknown-orchestrator fallback; the
# recognized-orchestrator path enumerates its OWN nodes and ignores these.
_INFRA_DIRS = frozenset(
    {"outputs", "artifacts", "checkpoints", "logs", "analysis", "results", "_runtime"}
)

_WORKER_RE = re.compile(r"worker_\d+$")
_FLOW_RE = re.compile(r"flow_\d+$")
_ROUND_RE = re.compile(r"round_\d+$")  # Dual per-consensus-round WORKSPACE wrappers
_LWI_ROUND_RE = re.compile(r"round\d+$")  # LWI dynamic steps: round01, round02, …

# A reconstructed graph is terminal, so every node is completed.
_COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def _detect_class(node_dir: Path) -> Optional[str]:
    """The inferencer ClassName that ran in ``node_dir`` (from its per-dir
    ``logs/session/{ClassName}-<uuid>.jsonl``), or None if no inferencer ran
    there (e.g. a `round_NN` workspace wrapper). This is the ground-truth signal
    for node-ness + is_container."""
    d = node_dir / "logs" / "session"
    if not d.is_dir():
        return None
    try:
        for f in sorted(d.iterdir()):
            # Match "<ClassName>-<uuid>.jsonl" (skip the ".jsonl.parts" siblings).
            if f.suffix == ".jsonl" and "-" in f.stem:
                return f.stem.split("-", 1)[0]
    except OSError:
        return None
    return None


def _resolve_output_path(node_dir: Optional[Path]) -> Optional[str]:
    """Absolute path to a node's canonical deliverable, resolved LIVE from the
    current dir (relocation-proof). Mirrors AgentFoundation's
    ``resolve_canonical_output_path`` cascade — deliverables live directly in
    ``outputs/`` (``output.md`` else first file) — without coupling this
    OpenStartup service to AF's ``InferencerWorkspace``. None if no output."""
    if node_dir is None:
        return None
    outputs = node_dir / "outputs"
    if not outputs.is_dir():
        return None
    primary = outputs / "output.md"
    if primary.is_file():
        return str(primary.resolve())
    try:
        files = sorted(
            f for f in outputs.iterdir() if f.is_file() and not f.name.startswith(".")
        )
    except OSError:
        files = []
    if files:
        return str(files[0].resolve())
    return None


def _titleize(name: str) -> str:
    """`worker_00` → "Worker 00"; `breakdown` → "Breakdown". Cosmetic display label
    (the live label — a subtask description — is not on disk); the id drives all
    lookups."""
    return name.replace("_", " ").title()


def _children_dir(container_dir: Path) -> Optional[Path]:
    d = container_dir / "children"
    return d if d.is_dir() else None


def _subdirs(children: Path) -> List[Path]:
    try:
        return sorted(c for c in children.iterdir() if c.is_dir())
    except OSError:
        return []


# A local (pre-qualification) node: name + label + is_container + its workspace dir.
# `dir` may be None for a virtual node (BTA/MFI `breakdown` with no workspace).
_LocalNode = Dict[str, Any]
# A shape = (local_nodes, edges[(src_name, tgt_name)], recursions[(local_name, dir)]).
_Shape = Tuple[List[_LocalNode], List[Tuple[str, str]], List[Tuple[str, Path]]]


# ---------------------------------------------------------------------------
# Per-orchestrator canonical shapes (authoritative node-set + edges + flags).
# ---------------------------------------------------------------------------
def _shape_pti(container_dir: Path) -> _Shape:
    """PTI root: phase nodes `planner`/`executor`/`analyzer` (each a container),
    present iff its `children/<phase>/` dir exists; linear edges."""
    nodes: List[_LocalNode] = []
    edges: List[Tuple[str, str]] = []
    recursions: List[Tuple[str, Path]] = []
    children = _children_dir(container_dir)
    prev: Optional[str] = None
    for slot, label in (
        ("planner", "Plan"),
        ("executor", "Implement"),
        ("analyzer", "Analysis"),
    ):
        d = children / slot if children is not None else None
        if d is None or not d.is_dir():
            continue
        nodes.append({"name": slot, "label": label, "is_container": True, "dir": d})
        if prev is not None:
            edges.append((prev, slot))
        prev = slot
        recursions.append((slot, d))
    return nodes, edges, recursions


def _shape_dual(container_dir: Path) -> _Shape:
    """Dual (and MFDual): `propose`(container) + `review`(leaf)/`fix`(leaf) with the
    `fix→review` back-edge. `round_NN` are workspace-only (NOT nodes); review/fix take
    the HIGHEST round's deliverable (= live's final node state). propose-only when no
    rounds ran."""
    nodes: List[_LocalNode] = []
    edges: List[Tuple[str, str]] = []
    recursions: List[Tuple[str, Path]] = []
    children = _children_dir(container_dir)
    if children is None:
        return nodes, edges, recursions
    propose = children / "propose"
    if propose.is_dir():
        nodes.append(
            {
                "name": "propose",
                "label": "Propose",
                "is_container": True,
                "dir": propose,
            }
        )
        recursions.append(("propose", propose))
    rounds = [c for c in _subdirs(children) if _ROUND_RE.match(c.name)]
    if rounds:
        last = rounds[-1]  # sorted → highest round_NN = final consensus iteration
        for stage in ("review", "fix"):
            sd = last / "children" / stage
            if sd.is_dir():
                nodes.append(
                    {
                        "name": stage,
                        "label": stage.capitalize(),
                        "is_container": False,
                        "dir": sd,
                    }
                )
    names = [n["name"] for n in nodes]
    prev = None
    for name in names:
        if prev is not None:
            edges.append((prev, name))
        prev = name
    if "fix" in names and "review" in names:
        edges.append(("fix", "review"))  # Dual consensus back-edge
    return nodes, edges, recursions


def _shape_diamond(
    container_dir: Path, worker_re: re.Pattern, flow_is_container: bool
) -> _Shape:
    """BTA / MFI diamond: a VIRTUAL `breakdown` (always present, may have no dir) →
    each `worker_NN`/`flow_NN` → `aggregator` (present iff its dir exists)."""
    nodes: List[_LocalNode] = []
    edges: List[Tuple[str, str]] = []
    recursions: List[Tuple[str, Path]] = []
    children = _children_dir(container_dir)
    bd = children / "breakdown" if children is not None else None
    nodes.append(
        {
            "name": "breakdown",
            "label": "Breakdown",
            "is_container": False,
            "dir": bd if (bd is not None and bd.is_dir()) else None,
        }
    )
    worker_names: List[str] = []
    if children is not None:
        for w in _subdirs(children):
            if not worker_re.match(w.name):
                continue
            is_c = flow_is_container or (_detect_class(w) in _ORCHESTRATORS)
            nodes.append(
                {
                    "name": w.name,
                    "label": _titleize(w.name),
                    "is_container": is_c,
                    "dir": w,
                }
            )
            edges.append(("breakdown", w.name))
            worker_names.append(w.name)
            if is_c:
                recursions.append((w.name, w))
    agg = children / "aggregator" if children is not None else None
    if agg is not None and agg.is_dir():
        nodes.append(
            {
                "name": "aggregator",
                "label": "Aggregator",
                "is_container": False,
                "dir": agg,
            }
        )
        for wn in worker_names:
            edges.append((wn, "aggregator"))
    return nodes, edges, recursions


def _shape_bta(container_dir: Path) -> _Shape:
    # worker container-ness is child-class-derived (a worker may be a Dual/MFDual/BTA/LWI or a leaf).
    return _shape_diamond(container_dir, _WORKER_RE, flow_is_container=False)


def _shape_mfi(container_dir: Path) -> _Shape:
    # each flow is always a (dynamic) LinearWorkflowInferencer → container.
    return _shape_diamond(container_dir, _FLOW_RE, flow_is_container=True)


def _shape_lwi(container_dir: Path) -> _Shape:
    """LWI steps in a linear chain. Dynamic mode: `initial`, `round01`, `round02`, …
    Static mode: each logged child dir. Steps are leaves unless a child is itself an
    orchestrator."""
    nodes: List[_LocalNode] = []
    edges: List[Tuple[str, str]] = []
    recursions: List[Tuple[str, Path]] = []
    children = _children_dir(container_dir)
    if children is None:
        return nodes, edges, recursions
    steps: List[Path] = []
    initial = children / "initial"
    if initial.is_dir():  # dynamic mode
        steps.append(initial)
        steps.extend(
            sorted(c for c in _subdirs(children) if _LWI_ROUND_RE.match(c.name))
        )
    else:  # static mode — every logged child is a step
        steps = [c for c in _subdirs(children) if _detect_class(c) is not None]
    prev: Optional[str] = None
    for d in steps:
        is_c = _detect_class(d) in _ORCHESTRATORS
        label = d.name if d.name.startswith("round") else d.name.capitalize()
        nodes.append({"name": d.name, "label": label, "is_container": is_c, "dir": d})
        if prev is not None:
            edges.append((prev, d.name))
        prev = d.name
        if is_c:
            recursions.append((d.name, d))
    return nodes, edges, recursions


def _shape_fallback(container_dir: Path) -> _Shape:
    """Unknown orchestrator → best-effort: node ⟺ a child dir where an inferencer
    ran (has a class log); skip log-less wrappers (round_NN); order-chain edges."""
    nodes: List[_LocalNode] = []
    edges: List[Tuple[str, str]] = []
    recursions: List[Tuple[str, Path]] = []
    children = _children_dir(container_dir)
    if children is None:
        return nodes, edges, recursions
    prev: Optional[str] = None
    for c in _subdirs(children):
        if c.name in _INFRA_DIRS:
            continue
        cls = _detect_class(c)
        if cls is None:
            continue  # log-less wrapper (e.g. round_NN) — not a node
        is_c = cls in _ORCHESTRATORS
        nodes.append(
            {"name": c.name, "label": _titleize(c.name), "is_container": is_c, "dir": c}
        )
        if prev is not None:
            edges.append((prev, c.name))
        prev = c.name
        if is_c:
            recursions.append((c.name, c))
    return nodes, edges, recursions


_SHAPES: Dict[str, Callable[[Path], _Shape]] = {
    "PlanThenImplementInferencer": _shape_pti,
    "DualInferencer": _shape_dual,
    "MultiFlowDualInferencer": _shape_dual,  # MFDual = Dual whose `propose` is an MFI
    "BreakdownThenAggregateInferencer": _shape_bta,
    "MultiFlowInferencer": _shape_mfi,
    "LinearWorkflowInferencer": _shape_lwi,
    "ReflectiveInferencer": _shape_lwi,  # LWI subclass
}
_ORCHESTRATORS = frozenset(_SHAPES.keys())


# ---------------------------------------------------------------------------
# Recursive builder
# ---------------------------------------------------------------------------
def _qualify(prefix: str, name: str) -> str:
    return f"{prefix}/{name}" if prefix else name


def _build(
    snap: GraphSnapshot,
    container_dir: Path,
    prefix: str,
    cls: Optional[str],
    reconcile: Dict[str, str],
    depth: int,
) -> bool:
    """Emit ``container_dir``'s canonical topology into ``snap`` (root_topology when
    prefix=="", else sub_graphs[prefix]) and recurse into container children.
    Returns True if any node was emitted at this level."""
    if depth > 24:  # defensive: cannot recurse forever (workspaces are finite)
        return False
    shape_fn = _SHAPES.get(cls or "") or _shape_fallback
    local_nodes, edges, recursions = shape_fn(container_dir)
    if not local_nodes:
        return False

    qnodes: List[Dict[str, Any]] = []
    for n in local_nodes:
        qid = _qualify(prefix, n["name"])
        node: Dict[str, Any] = {"id": qid, "label": n["label"], "status": _COMPLETED}
        if n.get("is_container"):
            node["is_container"] = True
        op = _resolve_output_path(n.get("dir"))
        if op:
            node["outputPath"] = op
        qnodes.append(node)
        reconcile[qid] = _COMPLETED

    payload = {
        "nodes": qnodes,
        "edges": [
            {"source": _qualify(prefix, s), "target": _qualify(prefix, t)}
            for (s, t) in edges
        ],
        "layout": "",
        "version": 1,
    }
    if prefix == "":
        snap.root_topology = payload
    else:
        snap.sub_graphs[prefix] = payload

    for local_name, child_dir in recursions:
        _build(
            snap,
            child_dir,
            _qualify(prefix, local_name),
            _detect_class(child_dir),
            reconcile,
            depth + 1,
        )
    return True


def reconstruct_graph_from_task_dir(task_dir: "str | Path") -> Optional[GraphSnapshot]:
    """Reconstruct a best-effort ``GraphSnapshot`` from a task's on-disk workspace,
    or None if there is nothing to reconstruct (no `children/` tree, e.g. a
    single-agent / graph-less task → caller shows the deliverable fallback). The
    returned snapshot's ``task_id`` is left empty; the caller (``get_or_load``) sets
    it to the chip id so replay events route correctly. Never raises."""
    try:
        root = Path(task_dir)
        if not root.is_dir():
            return None
        snap = GraphSnapshot("")  # task_id assigned by the caller
        reconcile: Dict[str, str] = {}
        ok = _build(snap, root, "", _detect_class(root), reconcile, depth=0)
        if not ok or snap.root_topology is None:
            return None
        snap.last_reconcile = reconcile
        return snap
    except Exception as exc:  # never let reconstruction break the WS path
        logger.warning("[reconstruct] failed for %s: %s", task_dir, exc)
        return None
