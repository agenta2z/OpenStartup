"""TaskGraphSnapshotStore — server-side graph state mirror for replay on reconnect.

v4 Phase 4.1 — proper root fix for V5 ("graph state wiped on reconnect").

Why this exists
---------------
Browser refresh / WS reconnect / HMR all rebuild the per-connection
``useGraphState`` from scratch. ``session_init`` (the historical "rehydrate"
hook) only rebuilds tasks from ``task_ref`` history messages — it carries no
``graph`` / ``subGraphs`` / ``nodeStreams``. Before this module, every
disconnect-reconnect pair would silently drop the entire live graph and any
in-flight node status would be lost forever (since the inferencer's own emits
are live-only via ``WebSocketInteractive.send_graph_event``).

The fix is a per-(session_id, task_id) snapshot that mutates inside the SAME
emit point that already serializes to WS (``send_graph_event``). The snapshot
is the single source of truth on the server for whatever the client SHOULD
see; replay on ``session_init`` (and on-demand via ``request_graph_replay``)
re-emits the snapshot as ordinary ``graph_topology`` / ``node_status`` /
``node_stream`` / ``graph_reconcile`` events so the client's existing handlers
hydrate it transparently — no new client-side code path is needed.

Lifetime
--------
In-memory only (per server process). The plan v4 deliberately scopes this to
"survive browser refresh / WS reconnect to the same server", not server
restart — cross-process recovery would require disk persistence with no
material UX gain (a server restart already evicts the running inferencer).

After a task reaches a terminal status (``completed`` / ``error``) the
snapshot is marked for TTL eviction (600s default); the next prune call
removes it. Active snapshots have no TTL.

Merge semantics
---------------
Mirrors the client's ``useGraphState.handleGraphTopology`` merge logic (v4
Phase 2.1) so a snapshot-driven replay produces the SAME post-merge state as
the live event stream did. This is load-bearing: if the merge diverges, a
disconnect-reconnect mid-run would silently corrupt graph state.

* ``GraphTopologyEvent`` with ``reset=True`` (default) — node-by-node merge:
  preserve runtime status / startedAt / completedAt / outputPath / error on
  nodes that already exist; add new ones; replace edges + layout.
* ``GraphTopologyEvent`` with ``reset=False`` — append-only: add nodes/edges
  that don't already exist; never overwrite any field on existing nodes. Used
  by LWI to cheaply append a new round (v4 Phase 5.1 / 5.2).
* ``NodeStatusEvent`` — search root nodes then all sub-graph nodes for an id
  match; update in place. Routing parity with the JS reducer's
  ``applyStatusToTask`` (which routes by ``id`` after qualification).
* ``NodeStreamEvent`` — bounded ring buffer of chunks per node_id (default
  cap 500 chunks; oldest dropped on overflow). ``is_final`` is sticky.
* ``GraphReconcileEvent`` — bulk-apply terminal statuses; mirrors the
  client's ``handleGraphReconcile`` (post-Phase 1.5 recursive walk).
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from openteam.server.services.json_io import write_json_atomic

logger = logging.getLogger(__name__)


# Bounded per-node stream buffer — same cap shape as Phase 5.4's raceBuffer
# rise to 1000 on the client; keeping it slightly lower here because the
# snapshot replay only ships the buffered tail anyway (not every chunk ever
# emitted) and a 500-chunk replay is plenty for a NodeDetailPanel that the
# user opens after a long run.
_STREAM_BUFFER_CAP = 500

# Field set whose values are preserved on already-known nodes during a
# ``reset=True`` topology merge. These are the fields that carry RUNTIME state
# (set by NodeStatusEvent / output-path resolution) — they must survive when
# the inferencer re-emits the topology after Phase 1's pending diamond grows
# to the full diamond.
_PRESERVED_NODE_FIELDS = (
    "status",
    "startedAt",
    "completedAt",
    "outputPath",
    "error",
    "label",  # dynamic label updates from NodeStatusEvent are kept
)

# Default TTL after a task terminates before its snapshot is pruned. 600s
# matches the plan v4 spec — long enough to survive an "I had to grab lunch"
# refresh, short enough that a dev hammering refresh doesn't accumulate
# unbounded snapshots.
_DEFAULT_TERMINAL_TTL_S = 600.0

# Schema version for the durable on-disk snapshot (Fix 2). Bump on any breaking
# change to GraphSnapshot.to_dict(); from_dict() rejects mismatched versions
# (→ falls back to reconstruction), so a stale on-disk blob is never mis-parsed.
_SNAPSHOT_SCHEMA_VERSION = 1


def _merge_node_fields(existing_node: dict, incoming_node: dict) -> dict:
    """Carry runtime fields from existing onto incoming. Pure function.

    Mirrors the client merge at ``useGraphState.handleGraphTopology`` (v4
    Phase 2.1): the incoming snapshot is canonical for topology fields
    (id, group, is_container, position-affecting fields) while the existing
    state is canonical for runtime fields (status, timestamps, output path,
    error). Identity-preserving merge avoids the "BTA re-emit wipes status"
    class of bug (V4a in the plan).
    """
    merged = dict(incoming_node)
    for field_name in _PRESERVED_NODE_FIELDS:
        if field_name in existing_node and existing_node[field_name] is not None:
            # Only carry forward when existing has a non-None value; this
            # avoids stomping the incoming default (e.g. PENDING) with an
            # earlier PENDING on a node we've only seen once.
            if field_name == "label":
                # Label is special: only override the incoming label when the
                # existing one is a non-empty dynamic update (NodeStatusEvent
                # sets it). Otherwise prefer the fresh topology label.
                if existing_node.get(field_name):
                    merged[field_name] = existing_node[field_name]
            else:
                merged[field_name] = existing_node[field_name]
    return merged


class GraphSnapshot:
    """In-memory mirror of a single task's graph state.

    All mutations go through ``apply_event`` so the merge logic stays in one
    place; ``to_replay_events`` serializes the current state back to the
    wire-format event dicts that the WS handler already knows how to send
    (same payload shape as ``WebSocketInteractive.send_graph_event``).
    """

    __slots__ = (
        "task_id",
        "root_topology",
        "sub_graphs",
        "node_streams",
        "last_reconcile",
        "_terminal_at",
        "last_updated",
    )

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        # Root-level topology: {"nodes": [...], "edges": [...], "layout": str,
        # "version": int}. None until the first root topology event arrives.
        self.root_topology: Optional[Dict[str, Any]] = None
        # Sub-graph topologies keyed by parent_node_id. Same shape as
        # root_topology. New entries created lazily on first per-parent topology.
        self.sub_graphs: Dict[str, Dict[str, Any]] = {}
        # Per-node streaming chunks: {node_id: {"chunks": list[str],
        # "is_final": bool}}. Bounded ring buffer.
        self.node_streams: Dict[str, Dict[str, Any]] = {}
        # Final reconcile payload, if any. Stored so replay can re-emit the
        # canonical terminal statuses.
        self.last_reconcile: Optional[Dict[str, str]] = None
        # Timestamp when the task entered a terminal status, or None while
        # active. Used by ``TaskGraphSnapshotStore.prune_expired``.
        self._terminal_at: Optional[float] = None
        self.last_updated: float = time.time()

    # ------------------------------------------------------------------
    # Mutation — called from WebSocketInteractive.send_graph_event so any
    # event the server emits is mirrored into the snapshot before the wire
    # send.
    # ------------------------------------------------------------------
    def apply_event(self, event: Any) -> None:
        """Update the snapshot for one graph event. Never raises.

        Robustness contract: visualization must never abort inference. Any
        exception in the merge logic is logged + swallowed; the snapshot may
        be slightly stale until the next event but the live WS dispatch
        still happens.
        """
        try:
            self._apply_event_inner(event)
            self.last_updated = time.time()
        except Exception as exc:
            logger.warning(
                "[GraphSnapshot] apply_event failed (task_id=%s, event=%s): %s",
                self.task_id,
                type(event).__name__,
                exc,
            )

    def _apply_event_inner(self, event: Any) -> None:
        # Late import to avoid making this module depend on agent_foundation
        # at import time (services import order is sensitive in main.py).
        from agent_foundation.common.inferencers.graph_events import (
            GraphReconcileEvent,
            GraphTopologyEvent,
            NodeStatusEvent,
            NodeStreamEvent,
        )

        if isinstance(event, GraphTopologyEvent):
            self._apply_topology(event)
        elif isinstance(event, NodeStatusEvent):
            self._apply_node_status(event)
        elif isinstance(event, NodeStreamEvent):
            self._apply_node_stream(event)
        elif isinstance(event, GraphReconcileEvent):
            self._apply_reconcile(event)
        # Unknown event types are silently ignored — visualizations are
        # additive; a future event type without a snapshot handler simply
        # won't be mirrored (replay still works for what we know about).

    def _apply_topology(self, event: Any) -> None:
        # Parent_node_id == "" means root topology; non-empty means sub-graph.
        target_key = event.parent_node_id or ""
        existing = (
            self.root_topology if not target_key else self.sub_graphs.get(target_key)
        )
        # Stale-version guard (Phase 2.3 parity): drop events whose version
        # is older than what we already have, since they would regress UI
        # state. ``version == 0`` is treated as "unversioned" and always
        # accepted (the inferencer side doesn't always set version).
        if existing is not None and event.version and existing.get("version", 0):
            if event.version < existing["version"]:
                return

        if existing is None:
            # Fresh — no merge needed; deep copy the incoming lists so later
            # status updates don't mutate the inferencer's own dataclasses.
            payload = {
                "nodes": [dict(n) for n in event.nodes],
                "edges": [dict(e) for e in event.edges],
                "layout": event.layout,
                "version": event.version or 0,
            }
            if target_key:
                self.sub_graphs[target_key] = payload
            else:
                self.root_topology = payload
            return

        # Existing — merge.
        existing_by_id = {n["id"]: n for n in existing["nodes"]}
        reset_flag = getattr(event, "reset", True)
        if reset_flag is False:
            # Append-only: keep existing nodes verbatim, add only nodes that
            # don't already exist. Same shape as the client's append branch
            # in Phase 5.2.
            merged_nodes = list(existing["nodes"])
            for incoming in event.nodes:
                if incoming["id"] not in existing_by_id:
                    merged_nodes.append(dict(incoming))
            # Edges: union (preserve existing, add new). De-dupe on the
            # (source, target) tuple.
            existing_edge_keys = {(e["source"], e["target"]) for e in existing["edges"]}
            merged_edges = list(existing["edges"])
            for incoming_edge in event.edges:
                key = (incoming_edge["source"], incoming_edge["target"])
                if key not in existing_edge_keys:
                    merged_edges.append(dict(incoming_edge))
                    existing_edge_keys.add(key)
        else:
            # Default merge (Phase 2.1): replace edges/layout, but carry
            # runtime fields onto already-known nodes.
            merged_nodes = []
            for incoming in event.nodes:
                if incoming["id"] in existing_by_id:
                    merged_nodes.append(
                        _merge_node_fields(existing_by_id[incoming["id"]], incoming)
                    )
                else:
                    merged_nodes.append(dict(incoming))
            merged_edges = [dict(e) for e in event.edges]
        payload = {
            "nodes": merged_nodes,
            "edges": merged_edges,
            "layout": event.layout,
            "version": event.version or existing.get("version", 0),
        }
        if target_key:
            self.sub_graphs[target_key] = payload
        else:
            self.root_topology = payload

    def _apply_node_status(self, event: Any) -> None:
        # The wire format carries fully-qualified node_id (e.g.
        # "plan/propose/worker_0/flow_0/initial"). The reducer-side routing
        # walks root + all sub-graphs; the first id match wins. This mirrors
        # the JS reducer's ``applyStatusToTask`` after Phase 1.5's recursive
        # extension.
        updated = False
        if self.root_topology is not None:
            for n in self.root_topology["nodes"]:
                if n["id"] == event.node_id:
                    self._stamp_status(n, event)
                    updated = True
                    break
        if not updated:
            for sub in self.sub_graphs.values():
                for n in sub["nodes"]:
                    if n["id"] == event.node_id:
                        self._stamp_status(n, event)
                        updated = True
                        break
                if updated:
                    break
        # If neither root nor any sub-graph contains the node yet, the topology
        # for the container hasn't arrived. The client-side race buffer
        # handles this for live events; on the snapshot side we just drop —
        # the apparent loss is fine because the topology event will arrive
        # shortly (often in the same emit batch) and the live event will
        # replay the status via the buffer. If the topology arrives AFTER
        # the snapshot is replayed, the worst case is one missing terminal
        # status, which the GraphReconcileEvent (always emitted last) repairs.

    @staticmethod
    def _stamp_status(node: dict, event: Any) -> None:
        node["status"] = event.status
        if event.label:
            node["label"] = event.label
        if event.error:
            node["error"] = event.error
        if event.timestamp:
            # The JS reducer sets startedAt on first running, completedAt on
            # any terminal; we mirror.
            if event.status == "running" and not node.get("startedAt"):
                node["startedAt"] = event.timestamp
            if event.status in ("completed", "error", "skipped"):
                node["completedAt"] = event.timestamp
        if event.output_path:
            node["outputPath"] = event.output_path

    def _apply_node_stream(self, event: Any) -> None:
        entry = self.node_streams.get(event.node_id)
        if entry is None:
            entry = {"chunks": [], "is_final": False}
            self.node_streams[event.node_id] = entry
        chunks: List[str] = entry["chunks"]
        chunks.append(event.content)
        if len(chunks) > _STREAM_BUFFER_CAP:
            # Drop oldest. The replay will be missing the prefix — acceptable
            # for long-running streams; we keep the tail which is what a user
            # opening NodeDetailPanel actually cares about.
            del chunks[:-_STREAM_BUFFER_CAP]
        if event.is_final:
            entry["is_final"] = True

    def _apply_reconcile(self, event: Any) -> None:
        # Store the canonical final-truth map. Replay re-emits this AFTER the
        # topology + status events so the client's existing
        # ``handleGraphReconcile`` (recursive, post-Phase 1.5) does the
        # terminal repair work in the same code path it uses for live runs.
        self.last_reconcile = dict(event.node_statuses)
        # Also stamp into the snapshot's own node statuses so a freshly-opened
        # tab without a prior reconcile shows the right terminal state even
        # if it doesn't trigger a fresh reconcile event.
        for node_id, status in (event.node_statuses or {}).items():
            if self.root_topology is not None:
                for n in self.root_topology["nodes"]:
                    if n["id"] == node_id:
                        n["status"] = status
                        break
            for sub in self.sub_graphs.values():
                for n in sub["nodes"]:
                    if n["id"] == node_id:
                        n["status"] = status
                        break

    # ------------------------------------------------------------------
    # Replay — serialize state back into wire-format events. Caller iterates
    # the returned list and sends each event over the existing WS connection.
    # ------------------------------------------------------------------
    def to_replay_events(self) -> List[Dict[str, Any]]:
        """Return wire-format event dicts that, when re-played in order, will
        bring a fresh ``useGraphState`` to this snapshot's state.

        Ordering invariants:
          1. Root topology FIRST (so subsequent sub-graph events have a parent
             to attach to under the new ``expandableNodeIds`` book-keeping).
          2. Sub-graph topologies, in insertion order (matches the order the
             live inferencer emitted them; first-seen parent first).
          3. Node streams (bulk-replay the tail of each buffer).
          4. Reconcile (final-truth pass — always last so it can repair any
             status that the client may have inferred differently from the
             topology defaults during merge).
        """
        events: List[Dict[str, Any]] = []
        if self.root_topology is not None:
            events.append(
                {
                    "type": "graph_topology",
                    "task_id": self.task_id,
                    "nodes": self.root_topology["nodes"],
                    "edges": self.root_topology["edges"],
                    "layout": self.root_topology["layout"],
                    # Snapshot replay is always a fresh "this is the full state"
                    # — the client should merge (Phase 2.1) NOT append. We omit
                    # reset so the client uses the default (True == merge).
                }
            )
        for parent_id, sub in self.sub_graphs.items():
            events.append(
                {
                    "type": "graph_topology",
                    "task_id": self.task_id,
                    "parent_node_id": parent_id,
                    "nodes": sub["nodes"],
                    "edges": sub["edges"],
                    "layout": sub["layout"],
                }
            )
        for node_id, stream in self.node_streams.items():
            if not stream["chunks"]:
                continue
            events.append(
                {
                    "type": "node_stream",
                    "task_id": self.task_id,
                    "node_id": node_id,
                    # Concatenate the buffered chunks into one payload. The
                    # client appends; one big append is equivalent to N small
                    # appends and saves wire bytes.
                    "content": "".join(stream["chunks"]),
                    "is_final": stream["is_final"],
                }
            )
        if self.last_reconcile:
            events.append(
                {
                    "type": "graph_reconcile",
                    "task_id": self.task_id,
                    "nodes": self.last_reconcile,
                }
            )
        return events

    # ------------------------------------------------------------------
    # TTL management
    # ------------------------------------------------------------------
    def mark_terminal(self) -> None:
        """Stamp the snapshot for TTL eviction after a terminal task_status.

        Idempotent — repeated calls don't extend the TTL window. Active
        snapshots have ``_terminal_at is None`` and never expire.
        """
        if self._terminal_at is None:
            self._terminal_at = time.time()

    def is_expired(self, now: float, ttl_s: float) -> bool:
        return self._terminal_at is not None and (now - self._terminal_at) > ttl_s

    # ------------------------------------------------------------------
    # Durable serialization (Fix 2) — persist a terminal snapshot to disk so it
    # survives the 600s in-memory TTL AND a server restart. Reuses the same
    # to_replay_events() wire pipeline on the way back out (via from_dict).
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for durable disk persistence. Captures the topology + node
        statuses + per-node ``outputPath`` (the deliverable pointer) + the
        terminal reconcile. **Excludes ``node_streams``** — completed nodes render
        from ``outputPath`` → ``/api/view``, so the (bounded but sizeable) live
        stream tails are not needed on disk (verified: every SOP node writes
        ``outputs/output.md``)."""
        return {
            "_schema_version": _SNAPSHOT_SCHEMA_VERSION,
            "task_id": self.task_id,
            "root_topology": self.root_topology,
            "sub_graphs": self.sub_graphs,
            "last_reconcile": self.last_reconcile,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Optional[GraphSnapshot]":
        """Reconstruct a snapshot from ``to_dict()`` output. DEFENSIVE: returns
        ``None`` on a corrupt / partial / unknown-version blob so the caller
        cleanly falls through to reconstruction (never raises, never mis-parses a
        stale schema)."""
        try:
            if not isinstance(data, dict):
                return None
            if data.get("_schema_version") != _SNAPSHOT_SCHEMA_VERSION:
                return None
            task_id = data.get("task_id")
            if not task_id:
                return None
            snap = cls(str(task_id))
            rt = data.get("root_topology")
            snap.root_topology = rt if isinstance(rt, dict) else None
            sg = data.get("sub_graphs")
            snap.sub_graphs = sg if isinstance(sg, dict) else {}
            lr = data.get("last_reconcile")
            snap.last_reconcile = lr if isinstance(lr, dict) else None
            # node_streams intentionally NOT persisted → left empty; a restored
            # completed node renders from its outputPath file.
            return snap
        except Exception:
            return None


class TaskGraphSnapshotStore:
    """App-level dict[session_id][task_id] -> GraphSnapshot.

    Thread-safe enough for FastAPI's typical asyncio + occasional thread
    callback usage. The lock is acquired only for dict mutations (insert /
    delete / lookup); the per-snapshot mutations are uncontended because
    each task_id is touched by only one inferencer at a time.
    """

    def __init__(
        self,
        terminal_ttl_s: float = _DEFAULT_TERMINAL_TTL_S,
        session_store: "Any | None" = None,
    ) -> None:
        self._sessions: Dict[str, Dict[str, GraphSnapshot]] = {}
        self._lock = Lock()
        self._terminal_ttl_s = terminal_ttl_s
        # Optional SessionStore handle for DURABLE disk persistence (Fix 2/3).
        # When set: terminal snapshots are written to
        # ``<session_dir>/task_graphs/<task_id>.json`` and ``get_or_load`` can
        # hydrate them (or reconstruct) after TTL eviction / a server restart.
        # None on the CLI/dev path (no persistence — in-memory only, as before).
        self._session_store = session_store

    def get_or_create(self, session_id: str, task_id: str) -> GraphSnapshot:
        with self._lock:
            session_map = self._sessions.setdefault(session_id, {})
            snap = session_map.get(task_id)
            if snap is None:
                snap = GraphSnapshot(task_id)
                session_map[task_id] = snap
            return snap

    def get_session_snapshots(self, session_id: str) -> List[GraphSnapshot]:
        """Return a snapshot-list copy for replay. Caller is free to iterate."""
        with self._lock:
            session_map = self._sessions.get(session_id, {})
            return list(session_map.values())

    def get_task_snapshot(
        self, session_id: str, task_id: str
    ) -> Optional[GraphSnapshot]:
        with self._lock:
            return self._sessions.get(session_id, {}).get(task_id)

    # ------------------------------------------------------------------
    # Durable disk persistence (Fix 2). Layout: <session_dir>/task_graphs/
    # <task_id>.json — one file per terminal task, written atomically.
    # ------------------------------------------------------------------
    def _task_graphs_dir(self, session_id: str) -> Optional[Path]:
        if self._session_store is None:
            return None
        try:
            return self._session_store.get_session_dir(session_id) / "task_graphs"
        except Exception:
            return None

    def _task_graph_path(self, session_id: str, task_id: str) -> Optional[Path]:
        d = self._task_graphs_dir(session_id)
        return None if d is None else d / f"{task_id}.json"

    def persist_task(self, session_id: str, task_id: str) -> None:
        """Durably write a task's snapshot to disk (atomic). Best-effort — never
        raises. No-op without a session_store or a snapshot. Called at terminal
        time (see ``mark_task_terminal``)."""
        path = self._task_graph_path(session_id, task_id)
        if path is None:
            return
        snap = self.get_task_snapshot(session_id, task_id)
        if snap is None:
            return
        try:
            write_json_atomic(path, snap.to_dict())
        except Exception as exc:  # never let persistence break the WS path
            logger.warning(
                "[GraphSnapshot] persist_task failed (%s/%s): %s",
                session_id,
                task_id,
                exc,
            )

    def load_task_from_disk(
        self, session_id: str, task_id: str
    ) -> Optional[GraphSnapshot]:
        """Load a persisted snapshot from disk, or None if absent/corrupt."""
        path = self._task_graph_path(session_id, task_id)
        if path is None or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return GraphSnapshot.from_dict(data)

    def get_or_load(
        self,
        session_id: str,
        task_id: str,
        task_dir: "str | Path | None" = None,
    ) -> Optional[GraphSnapshot]:
        """Resolve a task's graph via the 3-tier order: **in-memory → disk-persisted
        → reconstructed-from-disk** (Fix 3). All three produce the same
        ``GraphSnapshot`` shape, replayed through the same pipeline. The
        loaded/reconstructed result is cached in memory (MARKED TERMINAL so
        ``prune_expired`` evicts it after TTL; reloaded on the next miss) — this
        keeps a large session's memory bounded. The live ``get_or_create`` emit
        path is untouched. Returns None when nothing is resolvable (→ FE deliverable
        fallback).

        NOTE: tiers 2/3 do blocking filesystem I/O (disk read / reconstruction
        walk) — call this OFF the event loop (``asyncio.to_thread``) from async
        handlers so it never stalls the shared WS loop.
        """
        # Tier 1 — live/recent in-memory snapshot.
        snap = self.get_task_snapshot(session_id, task_id)
        if snap is not None:
            return snap
        # Tier 2 — durable disk-persisted snapshot (faithful; post-Fix-2 tasks).
        snap = self.load_task_from_disk(session_id, task_id)
        # Tier 3 — reconstruct from the workspace tree (legacy / pre-fix tasks).
        if snap is None and task_dir:
            try:
                from openteam.server.services.task_graph_reconstruct import (
                    reconstruct_graph_from_task_dir,
                )

                snap = reconstruct_graph_from_task_dir(task_dir)
            except Exception as exc:  # never break the WS path
                logger.warning(
                    "[GraphSnapshot] reconstruct failed (%s/%s): %s",
                    session_id,
                    task_id,
                    exc,
                )
                snap = None
        if snap is None:
            return None
        # Ensure replay events carry the CHIP task_id (a reconstructed snapshot has
        # an empty task_id; a disk one already matches). Cache MARKED TERMINAL so
        # prune_expired can evict it; the disk/reconstruct source stays durable.
        snap.task_id = task_id
        snap.mark_terminal()
        with self._lock:
            self._sessions.setdefault(session_id, {})[task_id] = snap
        return snap

    def mark_task_terminal(self, session_id: str, task_id: str) -> None:
        """Stamp the snapshot for TTL eviction, then DURABLY persist it to disk
        (Fix 2) so it survives the in-memory TTL + a server restart. No-op if the
        snapshot doesn't exist. Persist is disconnect-robust: it runs regardless
        of whether the terminal WS frame reached the client (send_safe no-ops on a
        dead socket), so a task completing while the user is away still persists."""
        with self._lock:
            snap = self._sessions.get(session_id, {}).get(task_id)
        if snap is not None:
            snap.mark_terminal()
            self.persist_task(session_id, task_id)

    def prune_expired(self) -> int:
        """Remove snapshots whose terminal TTL has elapsed. Returns evict count.

        Cheap O(N) sweep — N is bounded by concurrent recent task count per
        server. Safe to call on a timer or opportunistically (e.g. on each
        WS connect).
        """
        now = time.time()
        evicted = 0
        with self._lock:
            for session_id, session_map in list(self._sessions.items()):
                for task_id, snap in list(session_map.items()):
                    if snap.is_expired(now, self._terminal_ttl_s):
                        del session_map[task_id]
                        evicted += 1
                if not session_map:
                    del self._sessions[session_id]
        if evicted:
            logger.debug(
                "[GraphSnapshot] pruned %d expired task snapshots",
                evicted,
            )
        return evicted

    def drop_session(self, session_id: str) -> None:
        """Remove all snapshots for a session — called ONLY on genuine session
        deletion (the ``DELETE /sessions/{id}`` route). Drops the in-memory map
        and the durable ``<session_dir>/task_graphs/`` dir so disk snapshots
        don't outlive their session. MUST NOT be called on inferencer eviction or
        resume/truncate — those keep the session (and its durable graphs) alive
        for replay; dropping there would destroy graphs meant to survive.
        """
        with self._lock:
            self._sessions.pop(session_id, None)
        d = self._task_graphs_dir(session_id)
        if d is not None and d.is_dir():
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception as exc:  # best-effort cleanup
                logger.warning(
                    "[GraphSnapshot] drop_session disk cleanup failed (%s): %s",
                    session_id,
                    exc,
                )
