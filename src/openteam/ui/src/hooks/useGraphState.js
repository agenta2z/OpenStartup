/**
 * useGraphState — manages graph visualization state for composing WorkGraphs.
 *
 * Extracted from useManagerChat to handle:
 * - Sub-graph topology splicing (parent_node_id routing)
 * - RAF-batched status/stream updates (reduces re-renders from 85/s to 60fps max)
 * - Bounded stream buffers (200KB cap per node)
 * - Sticky selection (no auto-switch within 5s of manual click)
 * - Recursive allComplete (traverses subGraphs)
 * - Per-task navigation state (graphPath, selectedLeafId, containerView)
 * - Race buffer for status events arriving before their sub-graph topology
 */

import { useState, useRef, useCallback, useMemo } from 'react';

const MAX_STREAM_SIZE = 200_000;
const TRIM_SIZE = 50_000;
const STICKY_DURATION_MS = 5_000;
// Raised from 200 (v4 Phase 5.4): a 30s WS reconnect on a 9-worker x 3-flow
// run can easily produce > 200 statuses on one hot parent. Memory cost is
// trivial (event objects are tiny); silent drop is the worse failure mode.
const RACE_BUFFER_MAX_PER_PARENT = 1000;
const MAX_TOTAL_STREAMS = 10_000_000;
const CLEANUP_KEEP_SIZE = 2_000;

/**
 * Check if all nodes across root graph and all sub-graphs are in a terminal state.
 */
function isAllComplete(graph, subGraphs) {
  if (!graph?.nodes?.length) return false;
  const terminal = ['completed', 'error', 'skipped'];
  if (!graph.nodes.every(n => terminal.includes(n.status))) return false;
  if (subGraphs) {
    for (const sg of Object.values(subGraphs)) {
      if (sg?.nodes && !sg.nodes.every(n => terminal.includes(n.status))) return false;
    }
  }
  return true;
}

/**
 * Apply a node_status event to the correct graph (root or sub-graph).
 * Returns updated task object.
 */
function applyStatusToTask(task, evt) {
  if (!task) return task;

  const nodeId = evt.node_id;
  // Route by the parent sub-graph key = the node id up to its LAST slash
  // (equivalently the longest matching subGraphs key). Node ids are fully
  // qualified by ctx path (e.g. "planner/propose/breakdown"), and a sub-graph
  // is keyed by its parent_node_id ("planner/propose"); local ids never contain
  // a slash, so lastIndexOf is exactly that parent key. (Using the FIRST slash
  // mis-routes any node at depth >= 2 to the wrong sub-graph → silent no-op.)
  const slashIdx = nodeId.lastIndexOf('/');
  const ts = evt.timestamp ?? Date.now() / 1000;

  const updateNode = (n) => {
    if (n.id !== nodeId) return n;
    return {
      ...n,
      status: evt.status,
      label: evt.label || n.label,
      error: evt.error || '',
      startedAt: evt.status === 'running' ? ts : n.startedAt,
      completedAt: (evt.status === 'completed' || evt.status === 'error') ? ts : n.completedAt,
      outputPath: evt.output_path || n.outputPath || '',
    };
  };

  if (slashIdx > 0) {
    // Inner node — route to subGraphs
    const parentId = nodeId.substring(0, slashIdx);
    const subGraph = task.subGraphs?.[parentId];
    if (!subGraph) return null; // signal: buffer this event (whole sub-graph missing)
    // Node-level race buffer: during BTA expansion the sub-graph exists with only
    // [breakdown], but worker_* statuses can arrive before the full diamond
    // re-emit. .map(updateNode) would silently no-op (returning the unchanged
    // node) and the event would be lost forever. Returning null here signals
    // handleNodeStatus to buffer the event; it replays when the sub-graph's
    // node set grows (in handleGraphTopology's merge path).
    if (!subGraph.nodes.some(n => n.id === nodeId)) return null;
    const nodes = subGraph.nodes.map(updateNode);
    const updatedSubGraphs = { ...task.subGraphs, [parentId]: { ...subGraph, nodes } };
    const update = { ...task, subGraphs: updatedSubGraphs };
    if (evt.status === 'running') update.autoSelectedNodeId = nodeId;
    return update;
  }

  // Root node
  if (!task.graph) return task;
  if (!task.graph.nodes.some(n => n.id === nodeId)) return null; // buffer if missing
  const nodes = task.graph.nodes.map(updateNode);
  const update = { ...task, graph: { ...task.graph, nodes } };
  if (evt.status === 'running' && !task._stickyUntil) {
    update.autoSelectedNodeId = nodeId;
  }
  return update;
}

/**
 * Merge an incoming topology snapshot into an existing one, node-by-node.
 * Preserves accumulated runtime state (status/timestamps/outputPath/error)
 * on nodes that already exist; adopts the incoming snapshot's structural
 * fields (label, group, is_container, _viz_label) plus its edges + layout.
 *
 * This makes BTA's two-stage emit (initial [breakdown] -> full diamond) and
 * Dual's consensus re-iteration non-destructive: any node_status events
 * received between the two emits are preserved rather than wiped back to
 * the snapshot's defaults.
 */
function mergeTopology(existing, incoming) {
  if (!existing) {
    return { nodes: incoming.nodes, edges: incoming.edges, layout: incoming.layout,
             version: incoming.version || 0 };
  }
  const existingByKey = Object.fromEntries(existing.nodes.map(n => [n.id, n]));
  const mergedNodes = incoming.nodes.map(n => {
    const old = existingByKey[n.id];
    if (!old) return n;
    return {
      ...n,
      status: old.status || n.status,
      label: old.label || n.label,
      error: old.error || '',
      startedAt: old.startedAt,
      completedAt: old.completedAt,
      outputPath: old.outputPath || n.outputPath || '',
    };
  });
  return { nodes: mergedNodes, edges: incoming.edges,
           layout: incoming.layout, version: incoming.version || 0 };
}

/**
 * Append-only merge (v4 Phase 5.2 — reset:false on GraphTopologyEvent).
 *
 * Used by orchestrators that grow their graph incrementally (LWI adding a
 * new round on each dynamic step). Adds nodes whose id is not yet present;
 * does NOT touch any field on existing nodes (status, timestamps, label,
 * outputPath). Appends new edges, deduped by (source, target). Layout +
 * version are taken from the incoming snapshot.
 */
function appendTopology(existing, incoming) {
  if (!existing) {
    return { nodes: incoming.nodes, edges: incoming.edges, layout: incoming.layout,
             version: incoming.version || 0 };
  }
  const existingIds = new Set(existing.nodes.map(n => n.id));
  const addedNodes = incoming.nodes.filter(n => !existingIds.has(n.id));
  const nodes = addedNodes.length ? [...existing.nodes, ...addedNodes] : existing.nodes;
  const existingEdgeKeys = new Set(
    (existing.edges || []).map(e => `${e.source}->${e.target}`)
  );
  const addedEdges = (incoming.edges || []).filter(
    e => !existingEdgeKeys.has(`${e.source}->${e.target}`)
  );
  const edges = addedEdges.length ? [...(existing.edges || []), ...addedEdges] : existing.edges;
  return { nodes, edges, layout: incoming.layout || existing.layout,
           version: incoming.version || existing.version || 0 };
}

/**
 * Apply a node_stream event — append content with bounded buffer.
 */
function applyStreamToTask(task, evt) {
  if (!task) return task;
  const nodeStreams = { ...(task.nodeStreams || {}) };
  let content = (nodeStreams[evt.node_id] || '') + evt.content;
  if (content.length > MAX_STREAM_SIZE) {
    content = content.slice(TRIM_SIZE);
  }
  nodeStreams[evt.node_id] = content;

  // Phase 5.5 — honor is_final. Track which streams have been declared
  // canonical so the detail panel can suppress its blinking cursor (and
  // future code can avoid treating partial chunks as "live" once final
  // has arrived). Backend sends is_final=true on the worker's terminal
  // emit (BTA _make_worker_fn) and on coalesced 200ms flushes that the
  // observer marks as final.
  const nodeStreamsFinal = { ...(task.nodeStreamsFinal || {}) };
  if (evt.is_final === true) nodeStreamsFinal[evt.node_id] = true;

  // Global cap: if total nodeStreams size exceeds limit, purge completed nodes
  let totalSize = 0;
  for (const v of Object.values(nodeStreams)) totalSize += v.length;
  if (totalSize > MAX_TOTAL_STREAMS) {
    const terminal = new Set(['completed', 'error', 'skipped']);
    const allNodes = [
      ...(task.graph?.nodes || []),
      ...Object.values(task.subGraphs || {}).flatMap(sg => sg?.nodes || []),
    ];
    for (const n of allNodes) {
      if (terminal.has(n.status) && nodeStreams[n.id] && nodeStreams[n.id].length > CLEANUP_KEEP_SIZE) {
        totalSize -= nodeStreams[n.id].length;
        nodeStreams[n.id] = '';
        if (totalSize <= MAX_TOTAL_STREAMS * 0.7) break;
      }
    }
  }

  const updated = { ...task, nodeStreams, nodeStreamsFinal };

  // Auto-correct: a node receiving stream data is clearly running.
  // If its status is still "pending" (the RUNNING event was lost due to
  // RAF batching race with topology), infer the correct status.
  if (updated.graph?.nodes) {
    const nodeId = evt.node_id;
    const slashIdx = nodeId.indexOf('/');
    if (slashIdx < 0) {
      const node = updated.graph.nodes.find(n => n.id === nodeId);
      if (node && node.status === 'pending') {
        updated.graph = {
          ...updated.graph,
          nodes: updated.graph.nodes.map(n =>
            n.id === nodeId ? { ...n, status: 'running' } : n
          ),
        };
      }
    }
  }
  return updated;
}

export function useGraphState(setTasks) {
  // Per-task navigation state
  const [graphPathByTid, setGraphPathByTid] = useState({});
  const [selectedLeafByTid, setSelectedLeafByTid] = useState({});
  const [containerViewByTid, setContainerViewByTid] = useState({});

  // RAF batching
  const pendingUpdates = useRef([]);
  const rafId = useRef(null);

  // Race buffer: status events that arrived before their sub-graph topology
  const raceBuffer = useRef({});

  // First-root-seen guard: prevents every root topology re-emit from clearing
  // user navigation. The intent of the reset is "this is a fresh task" — but
  // a re-emit is NOT a fresh task. Reset only on first-emit-per-task and on
  // explicit task_status: starting (cleared from useManagerChat).
  const seenRoot = useRef({});

  const enqueueTaskUpdate = useCallback((updater) => {
    pendingUpdates.current.push(updater);
    if (!rafId.current) {
      rafId.current = requestAnimationFrame(() => {
        const updates = pendingUpdates.current;
        setTasks(prev => {
          let state = prev;
          for (const fn of updates) {
            state = fn(state);
          }
          return state;
        });
        pendingUpdates.current = [];
        rafId.current = null;
      });
    }
  }, [setTasks]);

  // --- Event Handlers ---

  const handleGraphTopology = useCallback((tid, evt) => {
    // v4 Phase 5.2 — reset semantics. Default true = merge-preserving (Phase 2.1).
    // false = append-only (LWI dynamic round add).
    const isAppendOnly = evt.reset === false;
    if (!evt.parent_node_id) {
      // Root topology: MERGE node-by-node (preserve statuses + timestamps for
      // already-known nodes; add new ones). Apply IMMEDIATELY (non-RAF) so
      // sub-graph events arriving in the same tick can resolve.
      setTasks(prev => {
        const task = prev[tid];
        // Version ordering: ignore an out-of-order re-delivery (lower version)
        // so concurrent nested re-emits don't clobber newer state.
        if (task?.graph?.version != null && evt.version != null
            && evt.version < task.graph.version) {
          return prev;
        }
        const merger = isAppendOnly ? appendTopology : mergeTopology;
        const newRoot = merger(task?.graph || null, {
          nodes: evt.nodes, edges: evt.edges, layout: evt.layout,
          version: evt.version || 0,
        });
        return {
          ...prev,
          [tid]: {
            ...task,
            graph: newRoot,
            nodeStreams: task?.nodeStreams || {},
            subGraphs: task?.subGraphs || {},
          },
        };
      });
      // Nav-reset guard: only reset graphPath/selection/raceBuffer on the
      // FIRST root topology for this task. Re-emits are not fresh tasks.
      // (Explicit "new task" signals via task_status:starting are cleared
      // from useManagerChat through the resetTaskNavState helper below.)
      if (!seenRoot.current[tid]) {
        setGraphPathByTid(prev => ({ ...prev, [tid]: [] }));
        setSelectedLeafByTid(prev => ({ ...prev, [tid]: null }));
        raceBuffer.current[tid] = {};
        seenRoot.current[tid] = true;
      }
      // Replay any buffered root-level status events (parentId === "")
      const bufferedRoot = raceBuffer.current[tid]?.[''];
      if (bufferedRoot?.length) {
        for (const bufferedEvt of bufferedRoot) {
          enqueueTaskUpdate(prev => {
            const task = prev[tid];
            const updated = applyStatusToTask(task, bufferedEvt);
            return updated ? { ...prev, [tid]: updated } : prev;
          });
        }
        delete raceBuffer.current[tid][''];
      }
    } else {
      // Sub-graph topology: MERGE under parent node, preserve existing data.
      // Replays race-buffered status events for this parent whenever the
      // sub-graph's node set GROWS (the BTA two-stage emit case: initial
      // [breakdown] + worker_* statuses arriving early -> full diamond emit
      // adds workers -> replay buffered statuses to flip workers to running).
      let shouldReplay = false;
      enqueueTaskUpdate(prev => {
        const task = prev[tid];
        if (!task?.graph) return prev;
        const existing = task.subGraphs?.[evt.parent_node_id];
        // Version ordering on sub-graphs too: ignore stale re-deliveries.
        if (existing?.version != null && evt.version != null
            && evt.version < existing.version) {
          return prev;
        }
        const merger = isAppendOnly ? appendTopology : mergeTopology;
        const merged = merger(existing, {
          nodes: evt.nodes, edges: evt.edges, layout: evt.layout,
          version: evt.version || 0,
        });
        // Did the node set grow? Then replay the buffer below.
        const oldCount = existing?.nodes?.length || 0;
        if (merged.nodes.length > oldCount) shouldReplay = true;
        const subGraphs = { ...(task.subGraphs || {}), [evt.parent_node_id]: merged };
        return { ...prev, [tid]: { ...task, subGraphs } };
      });
      const buffered = raceBuffer.current[tid]?.[evt.parent_node_id];
      if (buffered?.length && shouldReplay) {
        for (const bufferedEvt of buffered) {
          enqueueTaskUpdate(prev => {
            const task = prev[tid];
            const updated = applyStatusToTask(task, bufferedEvt);
            // updated === null means STILL not found (node not yet in this
            // sub-graph) — re-buffer so a later growth can replay.
            return updated ? { ...prev, [tid]: updated } : prev;
          });
        }
        delete raceBuffer.current[tid][evt.parent_node_id];
      }
    }
  }, [setTasks, enqueueTaskUpdate]);

  const handleNodeStatus = useCallback((tid, evt) => {
    enqueueTaskUpdate(prev => {
      const task = prev[tid];
      const updated = applyStatusToTask(task, evt);
      if (updated === null) {
        // Sub-graph not yet present (or node missing from existing sub-graph,
        // post Phase 2.2) — buffer for replay. Same depth-safe parent key as
        // applyStatusToTask: split on the LAST slash so the buffer key matches
        // the sub-graph's parent_node_id used at replay time
        // (handleGraphTopology), for nodes at any nesting depth.
        const parentId = evt.node_id.substring(0, evt.node_id.lastIndexOf('/'));
        if (!raceBuffer.current[tid]) raceBuffer.current[tid] = {};
        if (!raceBuffer.current[tid][parentId]) {
          raceBuffer.current[tid][parentId] = [];
          raceBuffer.current[tid][parentId]._overflowCount = 0;
        }
        if (raceBuffer.current[tid][parentId].length < RACE_BUFFER_MAX_PER_PARENT) {
          raceBuffer.current[tid][parentId].push(evt);
        } else {
          // Phase 5.4 — make silent drops visible. With cap=1000 and a healthy
          // emit/replay loop this should never fire; if it does, something
          // upstream is genuinely broken (sub-graph topology never arriving,
          // backend stuck emitting status without topology, etc).
          raceBuffer.current[tid][parentId]._overflowCount++;
          console.warn(
            `[graph race-buffer] OVERFLOW parent='${parentId}' tid='${tid}' ` +
            `(dropped: ${raceBuffer.current[tid][parentId]._overflowCount}; ` +
            `node_id='${evt.node_id}', status='${evt.status}')`
          );
        }
        return prev;
      }
      return { ...prev, [tid]: updated };
    });
  }, [enqueueTaskUpdate]);

  const handleNodeStream = useCallback((tid, evt) => {
    enqueueTaskUpdate(prev => {
      const task = prev[tid];
      const updated = applyStreamToTask(task, evt);
      return { ...prev, [tid]: updated };
    });
  }, [enqueueTaskUpdate]);

  const handleGraphReconcile = useCallback((tid, data) => {
    setTasks(prev => {
      const task = prev[tid];
      if (!task?.graph?.nodes) return prev;
      const updated = { ...task, graph: { ...task.graph, nodes: [...task.graph.nodes] } };
      let corrected = 0;
      // Reconcile root nodes.
      for (const node of updated.graph.nodes) {
        const serverStatus = data.nodes?.[node.id];
        if (serverStatus && node.status !== serverStatus) {
          console.warn(
            `[graph_reconcile] Gap detected: node '${node.id}' was '${node.status}' ` +
            `on UI but server reports '${serverStatus}' — auto-correcting`
          );
          node.status = serverStatus;
          corrected++;
        }
      }
      // Recursive reconcile across all sub-graphs at any depth. Sub-graph
      // nodes are stored under task.subGraphs[parent_node_id].nodes with
      // fully-qualified ids matching data.nodes keys; without this loop,
      // status events dropped during reconnect (or before a sub-graph
      // topology arrived) would leave sub-graph nodes stuck on stale
      // statuses forever.
      if (updated.subGraphs) {
        const newSubGraphs = { ...updated.subGraphs };
        let anySubChanged = false;
        for (const [parentId, sg] of Object.entries(updated.subGraphs)) {
          if (!sg?.nodes) continue;
          let subChanged = false;
          const newNodes = sg.nodes.map(node => {
            const serverStatus = data.nodes?.[node.id];
            if (serverStatus && node.status !== serverStatus) {
              console.warn(
                `[graph_reconcile] Sub-graph gap: node '${node.id}' was '${node.status}' ` +
                `on UI but server reports '${serverStatus}' — auto-correcting`
              );
              subChanged = true;
              corrected++;
              return { ...node, status: serverStatus };
            }
            return node;
          });
          if (subChanged) {
            newSubGraphs[parentId] = { ...sg, nodes: newNodes };
            anySubChanged = true;
          }
        }
        if (anySubChanged) updated.subGraphs = newSubGraphs;
      }

      // Free memory: trim nodeStreams for completed graphs.
      // Completed nodes' full output is available via the detail panel's
      // file fetch (outputPath); keeping large stream buffers is wasteful.
      if (isAllComplete(updated.graph, updated.subGraphs) && updated.nodeStreams) {
        const trimmed = {};
        let freed = 0;
        for (const [nodeId, content] of Object.entries(updated.nodeStreams)) {
          if (content.length > CLEANUP_KEEP_SIZE) {
            trimmed[nodeId] = content.slice(0, CLEANUP_KEEP_SIZE);
            freed += content.length - CLEANUP_KEEP_SIZE;
          } else {
            trimmed[nodeId] = content;
          }
        }
        if (freed > 0) {
          updated.nodeStreams = trimmed;
          console.info(`[graph_reconcile] Freed ~${(freed / 1024).toFixed(0)}KB of completed stream data for task ${tid}`);
        }
      }

      if (corrected === 0 && !updated.nodeStreams) return prev;
      return { ...prev, [tid]: updated };
    });
  }, [setTasks]);

  // --- Per-task navigation helpers ---

  const setGraphPath = useCallback((tid, path) => {
    setGraphPathByTid(prev => ({ ...prev, [tid]: path }));
  }, []);

  const setSelectedLeaf = useCallback((tid, leafId) => {
    setSelectedLeafByTid(prev => ({ ...prev, [tid]: leafId }));
  }, []);

  const setStickySelection = useCallback((tid) => {
    setTasks(prev => {
      const task = prev[tid];
      if (!task) return prev;
      return { ...prev, [tid]: { ...task, _stickyUntil: Date.now() + STICKY_DURATION_MS } };
    });
  }, [setTasks]);

  const setContainerView = useCallback((tid, containerId, view) => {
    setContainerViewByTid(prev => ({
      ...prev,
      [tid]: { ...(prev[tid] || {}), [containerId]: view },
    }));
  }, []);

  /**
   * Get derived graph state for a specific task.
   *
   * Path convention (unified, v4 Phase 2.4):
   *   Both focus-context's `focusedPath` (in TaskPanel) and page-switch's
   *   `graphPath` (here) store FULLY-QUALIFIED node ids. The deepest entry
   *   IS the subGraphs key. `path.join('/')` would double-prefix at depth
   *   >= 2 (e.g. ["planner","planner/propose"].join('/') === "planner/planner/propose"
   *   which matches no subGraphs key). Use `path[path.length - 1]` instead.
   *
   *   `expandableNodeIds` must also store FULL keys, not local remainders,
   *   so `TaskPanel.handleNodeClick`'s `expandableNodeIds.has(nodeId)` —
   *   where `nodeId` is the fully-qualified clicked id — actually matches.
   *   Previously this set held remainders ("propose") while clicks sent
   *   fully-qualified ids ("planner/propose"), silently blocking page-switch
   *   drill at depth >= 2.
   */
  const getDerivedFor = useCallback((tid, task) => {
    const graphPath = graphPathByTid[tid] || [];
    const selectedLeafId = selectedLeafByTid[tid] || null;
    const containerView = containerViewByTid[tid] || {};

    // Current graph at the drill-down depth — the deepest fully-qualified id.
    const deepestKey = graphPath.length > 0 ? graphPath[graphPath.length - 1] : '';
    let currentGraph;
    if (graphPath.length === 0) {
      currentGraph = task?.graph || null;
    } else {
      currentGraph = task?.subGraphs?.[deepestKey] || null;
    }

    // Which nodes at current level are expandable (have sub-graphs). Store
    // FULL keys in the set so `expandableNodeIds.has(fullyQualifiedNodeId)`
    // matches the clicked id from GraphFlowView's node._qualifiedId.
    const expandableNodeIds = new Set();
    if (task?.subGraphs) {
      const prefix = graphPath.length > 0 ? deepestKey + '/' : '';
      for (const key of Object.keys(task.subGraphs)) {
        if (key.startsWith(prefix)) {
          const remainder = key.substring(prefix.length);
          if (!remainder.includes('/')) expandableNodeIds.add(key);
        }
      }
    }

    // Content key for the detail panel — node ids are already fully qualified
    // by NamespacedGraphReporter, so no path-derived prefix is needed.
    const nodeStreamKey = (nodeId) => nodeId;

    const allComplete = isAllComplete(task?.graph, task?.subGraphs);

    return {
      graphPath,
      selectedLeafId,
      containerView,
      currentGraph,
      expandableNodeIds,
      nodeStreamKey,
      allComplete,
    };
  }, [graphPathByTid, selectedLeafByTid, containerViewByTid]);

  // Called from useManagerChat on task_status:starting so a re-start of the
  // SAME task_id genuinely resets navigation (rather than relying on the
  // first-root-seen guard which would persist across re-starts).
  const resetTaskNavState = useCallback((tid) => {
    setGraphPathByTid(prev => ({ ...prev, [tid]: [] }));
    setSelectedLeafByTid(prev => ({ ...prev, [tid]: null }));
    raceBuffer.current[tid] = {};
    seenRoot.current[tid] = false;
  }, []);

  return {
    handleGraphTopology,
    handleNodeStatus,
    handleNodeStream,
    handleGraphReconcile,
    setGraphPath,
    setSelectedLeaf,
    setStickySelection,
    setContainerView,
    getDerivedFor,
    isAllComplete,
    resetTaskNavState,
  };
}

export default useGraphState;
