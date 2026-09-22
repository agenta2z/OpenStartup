/**
 * TaskPanel — full-panel streaming view for a background async task.
 *
 * Two view modes:
 *   page-switch:    replaces graph on container click (breadcrumb navigation)
 *   focus-context:  unified canvas with viewport zoom + ghost outlines (§3.5)
 *
 * Props:
 *   task       - task object from useManagerChat's `tasks` state
 *   onBack     - called when user clicks the Back button
 *   graphState - from useGraphState hook
 */

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import { useTheme } from '@mui/material/styles';
import { MarkdownRenderer } from './MarkdownRenderer';
import { GraphFlowView } from './GraphFlowView';
import { NodeDetailPanel } from './NodeDetailPanel';
import { Breadcrumb } from './Breadcrumb';

const STATUS_CONFIG = {
  starting:  { label: 'Starting…', color: 'warning', showSpinner: true },
  running:   { label: 'Running',   color: 'info',    showSpinner: true },
  completed: { label: 'Complete',  color: 'success',  showSpinner: false },
  error:     { label: 'Error',     color: 'error',   showSpinner: false },
};

/**
 * Fix 5 — inline deliverable fallback for a graph-less task. Renders
 * `task.documentPath` via the existing `GET /api/view/{path}`: an `.html`
 * deliverable (e.g. Sphinx docs) in an `<iframe>`, otherwise via `MarkdownRenderer`.
 * Degrades to showing the path on a fetch failure (e.g. a path outside
 * `/api/view`'s allowed bases) — never a broken pane.
 */
function DeliverableView({ path }) {
  const [state, setState] = useState({ loading: true, content: null, error: null });
  const isHtml = /\.html?$/i.test(path || '');
  useEffect(() => {
    if (!path || isHtml) {
      setState({ loading: false, content: null, error: null });
      return;
    }
    let cancelled = false;
    setState({ loading: true, content: null, error: null });
    fetch(`/api/view/${path}`)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((t) => { if (!cancelled) setState({ loading: false, content: t, error: null }); })
      .catch((e) => { if (!cancelled) setState({ loading: false, content: null, error: e }); });
    return () => { cancelled = true; };
  }, [path, isHtml]);
  if (!path) return null;
  if (isHtml) {
    return (
      <Box component="iframe" title="deliverable" src={`/api/view/${path}`} sx={{ flex: 1, width: '100%', border: 0 }} />
    );
  }
  if (state.loading) {
    return <Typography variant="body2" sx={{ px: 3, py: 2, color: 'text.secondary' }}>Loading deliverable…</Typography>;
  }
  if (state.error) {
    return (
      <Typography variant="body2" sx={{ px: 3, py: 2, color: 'text.secondary' }}>
        Deliverable: {path} (could not load inline: {String(state.error.message || state.error)})
      </Typography>
    );
  }
  return <Box sx={{ overflow: 'auto', px: 3, py: 2 }}><MarkdownRenderer content={state.content || ''} /></Box>;
}

export function TaskPanel({ task, onBack, graphState }) {
  const theme = useTheme();
  const bottomRef = useRef(null);
  const tid = task?.id;

  // --- View mode ---
  const [viewMode, setViewMode] = useState('focus-context');
  const [focusedPath, setFocusedPath] = useState([]);
  const [containerOutputView, setContainerOutputView] = useState({});

  // Graph state from useGraphState (used for page-switch mode)
  const derived = useMemo(
    () => graphState?.getDerivedFor(tid, task) || {},
    [graphState, tid, task]
  );
  const {
    graphPath = [],
    selectedLeafId,
    currentGraph,
    expandableNodeIds = new Set(),
    nodeStreamKey: getNodeStreamKey,
    allComplete,
  } = derived;

  // For focus-context mode, the "active graph" is always the root graph
  const activeGraph = viewMode === 'focus-context' ? task?.graph : currentGraph;
  const activePath = viewMode === 'focus-context' ? focusedPath : graphPath;

  // Local UI state
  const [userSelectedNodeId, setUserSelectedNodeId] = useState(null);
  const [graphCollapsed, setGraphCollapsed] = useState(false);
  const [transitionDirection, setTransitionDirection] = useState('in');

  // Fix 4 — request the graph on task-open when it's missing (a completed task
  // reopened after the in-memory TTL / a server restart, or a legacy pre-fix
  // task). The backend resolves it via the 3-tier get_or_load (in-memory → disk
  // → reconstruct-from-disk). Uses an IN-FLIGHT guard (pendingReplayTidRef),
  // NOT a permanent per-tid flag, so a WS reconnect (which rebuilds task.graph as
  // undefined again) correctly re-requests.
  const [replayPending, setReplayPending] = useState(false);
  const pendingReplayTidRef = useRef(null);
  const replayTimerRef = useRef(null);
  // Fix 4.3 — gate the auto-collapse to a LIVE completion (running→complete)
  // watched in THIS view. A graph that ARRIVES already-complete (reopen / restore
  // / reconstruct) must stay expanded — else it would re-hide 1.5s after loading.
  const collapseGateRef = useRef({ tid: null, sawRunning: false });

  // Fix 5 (default-select) — for a terminal task opened with no live/user/sticky
  // selection, default to the LAST completed leaf that produced a deliverable so
  // the detail pane shows a real output on open, not the root container.
  // autoSelectedNodeId is set ONLY on a running→ transition (useGraphState), so a
  // replayed / reconstructed completed graph has none and would otherwise fall to
  // nodes[0] (the root container). Leaves = non-container nodes; prefer ones with
  // an outputPath (a real deliverable), newest first (topology/aggregator order).
  const lastCompletedLeafId = useMemo(() => {
    if (!task?.graph) return null;
    const all = [
      ...(task.graph.nodes || []),
      ...Object.values(task.subGraphs || {}).flatMap(sg => sg?.nodes || []),
    ];
    const leaves = all.filter(n => !n.is_container && n.status === 'completed');
    const withDeliverable = leaves.filter(n => n.outputPath);
    const pool = withDeliverable.length ? withDeliverable : leaves;
    return pool.length ? pool[pool.length - 1].id : null;
  }, [task?.graph, task?.subGraphs]);

  // Effective selected node
  const effectiveNodeId = userSelectedNodeId
    || selectedLeafId
    || task?.autoSelectedNodeId
    || lastCompletedLeafId
    || activeGraph?.nodes?.[0]?.id;

  // For focus-context: find selected node across all graphs.
  // Backend emits node ids already fully qualified by NamespacedGraphReporter,
  // and subGraphs are keyed by the fully-qualified parent_node_id — direct
  // equality on n.id is correct. The prior split('/').pop() + double-prefix
  // matching never matched and made every sub-graph node click render the
  // "Click a node" placeholder.
  const selectedNode = useMemo(() => {
    if (!effectiveNodeId) return null;
    if (viewMode === 'focus-context') {
      const rootNode = task?.graph?.nodes?.find(n => n.id === effectiveNodeId);
      if (rootNode) return rootNode;
      if (task?.subGraphs) {
        for (const sg of Object.values(task.subGraphs)) {
          const found = sg?.nodes?.find(n => n.id === effectiveNodeId);
          if (found) return found;
        }
      }
    }
    return currentGraph?.nodes?.find(n => n.id === effectiveNodeId);
  }, [effectiveNodeId, viewMode, task, currentGraph]);

  // Node content for detail panel
  const nodeStreamKeyStr = useMemo(() => {
    if (!effectiveNodeId) return '';
    if (viewMode === 'focus-context') return effectiveNodeId;
    return getNodeStreamKey ? getNodeStreamKey(effectiveNodeId) : effectiveNodeId;
  }, [effectiveNodeId, viewMode, getNodeStreamKey]);
  const nodeContent = task?.nodeStreams?.[nodeStreamKeyStr] || '';
  const isNodeStreaming = selectedNode?.status === 'running';

  // Container output content (§3.5.4)
  // focusedPath stores fully-qualified ids (handleNodeClick pushes node._qualifiedId);
  // the deepest entry IS the subGraphs key. Using .join('/') would double-prefix at
  // depth >= 2 (e.g. ["planner","planner/propose"].join('/') === "planner/planner/propose").
  const focusedContainerId = focusedPath.length > 0 ? focusedPath[focusedPath.length - 1] : null;
  const showContainerOutput = focusedContainerId && containerOutputView[focusedContainerId] === 'output';
  const containerOutputContent = useMemo(() => {
    if (!showContainerOutput || !focusedContainerId) return '';
    const bd = task?.nodeStreams?.[`${focusedContainerId}/breakdown`] || '';
    const ag = task?.nodeStreams?.[`${focusedContainerId}/aggregator`] || '';
    const parts = [];
    if (bd) parts.push(`## Breakdown\n\n${bd}`);
    if (ag) parts.push(`## Aggregation\n\n${ag}`);
    return parts.join('\n\n---\n\n') || '*No container output yet.*';
  }, [showContainerOutput, focusedContainerId, task?.nodeStreams]);

  // Status counts
  const statusCounts = useMemo(() => {
    if (!activeGraph?.nodes) return null;
    const c = { completed: 0, running: 0, pending: 0, error: 0 };
    activeGraph.nodes.forEach(n => { c[n.status] = (c[n.status] || 0) + 1; });
    return c;
  }, [activeGraph?.nodes]);

  // Resizable split between graph and detail panel
  const [splitRatio, setSplitRatio] = useState(0.45);
  const splitDragRef = useRef({ dragging: false, startY: 0, startRatio: 0 });
  const contentRef = useRef(null);

  const handleSplitMouseDown = useCallback((e) => {
    e.preventDefault();
    splitDragRef.current = { dragging: true, startY: e.clientY, startRatio: splitRatio };
    const onMove = (me) => {
      if (!splitDragRef.current.dragging || !contentRef.current) return;
      const rect = contentRef.current.getBoundingClientRect();
      const dy = me.clientY - splitDragRef.current.startY;
      const newRatio = splitDragRef.current.startRatio + dy / rect.height;
      setSplitRatio(Math.max(0.15, Math.min(0.85, newRatio)));
    };
    const onUp = () => {
      splitDragRef.current.dragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [splitRatio]);

  // Fix 4.1 — request the graph on open for a terminal task that has none. Fires
  // exactly once per (tid, in-flight window); clears on graph arrival or a ~4s
  // timeout (→ falls through to the deliverable fallback). Re-fires after a
  // reconnect because task.graph transitions back to undefined.
  useEffect(() => {
    const hasGraph = !!task?.graph;
    if (hasGraph) {
      if (pendingReplayTidRef.current === tid) {
        pendingReplayTidRef.current = null;
        setReplayPending(false);
        if (replayTimerRef.current) {
          clearTimeout(replayTimerRef.current);
          replayTimerRef.current = null;
        }
      }
      return;
    }
    const terminal = task?.status === 'completed' || task?.status === 'error';
    if (
      tid &&
      terminal &&
      graphState?.requestGraphReplay &&
      pendingReplayTidRef.current !== tid
    ) {
      pendingReplayTidRef.current = tid;
      setReplayPending(true);
      graphState.requestGraphReplay(tid);
      if (replayTimerRef.current) clearTimeout(replayTimerRef.current);
      replayTimerRef.current = setTimeout(() => {
        if (pendingReplayTidRef.current === tid) {
          pendingReplayTidRef.current = null;
          setReplayPending(false);
        }
      }, 4000);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tid, task?.status, !!task?.graph, graphState]);

  // Clear any pending replay timer on unmount.
  useEffect(() => () => {
    if (replayTimerRef.current) clearTimeout(replayTimerRef.current);
  }, []);

  // Auto-collapse when all complete — Fix 4.3: ONLY on a LIVE completion
  // transition (running→complete) watched in THIS view. A graph that arrived
  // already-complete (reopen / restore / reconstruct) stays expanded so the user
  // sees the graph structure they opened the task to inspect.
  useEffect(() => {
    const hasNodes = !!activeGraph?.nodes?.length;
    if (collapseGateRef.current.tid !== tid) {
      collapseGateRef.current = { tid, sawRunning: false };
    }
    if (!hasNodes) return;
    if (!allComplete) {
      collapseGateRef.current.sawRunning = true;  // observed it running here
      setGraphCollapsed(false);
      return;
    }
    if (collapseGateRef.current.sawRunning) {
      const timer = setTimeout(() => setGraphCollapsed(true), 1500);
      return () => clearTimeout(timer);
    }
    // Arrived already-complete (reopen) → keep expanded.
  }, [allComplete, activeGraph?.nodes?.length, tid]);

  // Reset selections on topology change
  const graphVersion = activeGraph?.version ?? activeGraph?.nodes?.length ?? 0;
  useEffect(() => { setUserSelectedNodeId(null); }, [graphVersion, activePath.length]);

  // Auto-scroll simple streaming view
  useEffect(() => {
    if (!task?.graph) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [task?.streamContent, task?.graph]);

  // --- Navigation handlers ---

  // v4 Phase 4.1 — find the clicked node across root + all sub-graphs so
  // handleNodeClick can detect "this should be expandable but its sub-graph
  // isn't loaded" via the backend-set is_container flag. Independent of
  // viewMode: focus-context renders every depth at once, page-switch shows
  // just the current level — in both cases the nodeId is fully qualified.
  const findNodeById = useCallback((nodeId) => {
    if (!nodeId) return null;
    const rootHit = task?.graph?.nodes?.find(n => n.id === nodeId);
    if (rootHit) return rootHit;
    if (task?.subGraphs) {
      for (const sub of Object.values(task.subGraphs)) {
        const hit = sub?.nodes?.find(n => n.id === nodeId);
        if (hit) return hit;
      }
    }
    return null;
  }, [task?.graph, task?.subGraphs]);

  const handleNodeClick = useCallback((nodeId) => {
    if (viewMode === 'focus-context') {
      const hasSubGraph = task?.subGraphs?.[nodeId];
      if (hasSubGraph) {
        setFocusedPath(prev => {
          // Collapse if clicking the currently-deepest focused container.
          if (prev.length && prev[prev.length - 1] === nodeId) {
            return prev.slice(0, -1);
          }
          // Jump up if clicking an ancestor already in the focused chain.
          const idx = prev.indexOf(nodeId);
          if (idx >= 0) return prev.slice(0, idx + 1);
          // Otherwise drill one level deeper into this container.
          return [...prev, nodeId];
        });
        setUserSelectedNodeId(null);
      } else {
        // v4 Phase 4.1 — if the clicked node is a container per the backend
        // (is_container=true set by BTA / Dual / MFDual / LWI containers)
        // but no sub-graph is locally known, the snapshot may have missed
        // this branch (e.g. HMR-interleaved session_init). Fire a defensive
        // replay so subsequent clicks can drill once the events hydrate.
        const clickedNode = findNodeById(nodeId);
        if (clickedNode?.is_container && graphState?.requestGraphReplay) {
          graphState.requestGraphReplay(tid);
        }
        setUserSelectedNodeId(nodeId === userSelectedNodeId ? null : nodeId);
        graphState?.setStickySelection(tid);
      }
    } else {
      if (expandableNodeIds.has(nodeId)) {
        setTransitionDirection('in');
        graphState?.setGraphPath(tid, [...graphPath, nodeId]);
        setUserSelectedNodeId(null);
      } else {
        // v4 Phase 4.1 — same defensive replay path in page-switch mode.
        const clickedNode = findNodeById(nodeId);
        if (clickedNode?.is_container && graphState?.requestGraphReplay) {
          graphState.requestGraphReplay(tid);
        }
        setUserSelectedNodeId(nodeId === userSelectedNodeId ? null : nodeId);
        graphState?.setStickySelection(tid);
      }
    }
  }, [viewMode, task?.subGraphs, expandableNodeIds, graphState, tid, graphPath, userSelectedNodeId, findNodeById]);

  const handleFocusChange = useCallback((path) => {
    setFocusedPath(path);
    setUserSelectedNodeId(null);
  }, []);

  const handleBreadcrumbNavigate = useCallback((depth) => {
    if (viewMode === 'focus-context') {
      setFocusedPath(prev => prev.slice(0, depth));
    } else {
      setTransitionDirection('out');
      graphState?.setGraphPath(tid, graphPath.slice(0, depth));
    }
    setUserSelectedNodeId(null);
  }, [viewMode, graphState, tid, graphPath]);

  // Keyboard: Esc chain, Space fit, arrows
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        if (userSelectedNodeId) {
          setUserSelectedNodeId(null);
        } else if (viewMode === 'focus-context' && focusedPath.length > 0) {
          setFocusedPath([]);
        } else if (viewMode === 'page-switch' && graphPath.length > 0) {
          handleBreadcrumbNavigate(graphPath.length - 1);
        }
      }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        if (!activeGraph?.nodes?.length || !effectiveNodeId) return;
        e.preventDefault();
        const siblings = activeGraph.nodes;
        const idx = siblings.findIndex(n => n.id === effectiveNodeId || `${focusedPath[0]}/${n.id}` === effectiveNodeId);
        if (idx < 0) return;
        const next = e.key === 'ArrowRight' ? (idx + 1) % siblings.length : (idx - 1 + siblings.length) % siblings.length;
        const nextId = viewMode === 'focus-context' && focusedPath.length > 0
          ? `${focusedPath[0]}/${siblings[next].id}`
          : siblings[next].id;
        setUserSelectedNodeId(nextId);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [viewMode, focusedPath, graphPath, handleBreadcrumbNavigate, userSelectedNodeId, activeGraph, effectiveNodeId]);

  if (!task) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>Task not found.</Typography>
      </Box>
    );
  }

  const cfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.starting;
  const summaryText = statusCounts
    ? (allComplete
        ? `Pipeline complete — ${activeGraph.nodes.length} nodes`
        : `Pipeline — ${statusCounts.completed}/${activeGraph.nodes.length} done${statusCounts.running ? `, ${statusCounts.running} running` : ''}${statusCounts.error ? `, ${statusCounts.error} errors` : ''}`)
    : `Pipeline — ${activeGraph?.nodes?.length || 0} nodes`;

  const hasSubGraphs = task?.subGraphs && Object.keys(task.subGraphs).length > 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, minWidth: 0 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, px: 2, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.06)', backgroundColor: 'background.paper', flexShrink: 0 }}>
        <IconButton onClick={onBack} size="small" sx={{ color: 'text.secondary' }}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {task.label || task.toolName || task.id}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>{task.toolName || 'Background Task'}</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
          {cfg.showSpinner && <CircularProgress size={14} color={cfg.color} />}
          {!cfg.showSpinner && task.status === 'completed' && <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />}
          {!cfg.showSpinner && task.status === 'error' && <ErrorIcon sx={{ fontSize: 16, color: 'error.main' }} />}
          <Chip label={cfg.label} color={cfg.color} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.72rem' }} />
        </Box>
      </Box>

      {/* Graph content */}
      {activeGraph ? (
        <Box ref={contentRef} sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          {/* Breadcrumb */}
          <Breadcrumb graphPath={activePath} task={task} onNavigate={handleBreadcrumbNavigate} />

          {/* Graph section — resizable via drag handle */}
          <Box sx={{ flexShrink: 0, height: graphCollapsed ? 40 : `${splitRatio * 100}%`, transition: graphCollapsed ? 'height 0.3s ease' : 'none', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Toggle bar */}
            <Box sx={{ display: 'flex', alignItems: 'center', px: 2, py: 0.5, cursor: 'pointer', backgroundColor: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.04)', '&:hover': { backgroundColor: 'rgba(255,255,255,0.05)' } }}>
              <Box onClick={() => setGraphCollapsed(c => !c)} sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                <Typography variant="caption" sx={{ color: 'text.disabled', flex: 1, fontSize: '0.68rem' }}>
                  {allComplete ? '✅' : '🔄'} {summaryText}
                </Typography>
                {graphCollapsed ? <ExpandMoreIcon sx={{ fontSize: 16, color: 'text.disabled' }} /> : <ExpandLessIcon sx={{ fontSize: 16, color: 'text.disabled' }} />}
              </Box>

              {/* View mode toggle */}
              {hasSubGraphs && (
                <Box sx={{ display: 'flex', ml: 1, gap: 0.25, borderLeft: '1px solid rgba(255,255,255,0.08)', pl: 0.5 }}>
                  <IconButton size="small" onClick={() => setViewMode('focus-context')} title="Focus+Context zoom"
                    sx={{ p: 0.25, color: viewMode === 'focus-context' ? 'primary.main' : 'text.disabled' }}>
                    <AccountTreeIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                  <IconButton size="small" onClick={() => setViewMode('page-switch')} title="Page switch"
                    sx={{ p: 0.25, color: viewMode === 'page-switch' ? 'primary.main' : 'text.disabled' }}>
                    <ViewModuleIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                </Box>
              )}

              {/* Container Output toggle (§3.5.4) */}
              {viewMode === 'focus-context' && focusedContainerId && (
                <Box sx={{ display: 'flex', ml: 1, gap: 0, borderLeft: '1px solid rgba(255,255,255,0.08)', pl: 0.5 }}>
                  <Chip label="Graph" size="small" variant={showContainerOutput ? 'outlined' : 'filled'}
                    onClick={() => setContainerOutputView(prev => ({ ...prev, [focusedContainerId]: 'graph' }))}
                    sx={{ height: 18, fontSize: '0.6rem', borderRadius: '4px 0 0 4px' }} />
                  <Chip label="Output" size="small" variant={showContainerOutput ? 'filled' : 'outlined'}
                    onClick={() => setContainerOutputView(prev => ({ ...prev, [focusedContainerId]: 'output' }))}
                    sx={{ height: 18, fontSize: '0.6rem', borderRadius: '0 4px 4px 0' }} />
                </Box>
              )}
            </Box>

            {/* Graph or Container Output */}
            {!graphCollapsed && (
              showContainerOutput ? (
                <Box sx={{ overflow: 'auto', p: 2, maxHeight: 400 }}>
                  <MarkdownRenderer content={containerOutputContent} />
                </Box>
              ) : (
                <Box
                  key={viewMode === 'focus-context' ? 'unified' : (graphPath[graphPath.length - 1] || 'root')}
                  sx={{
                    overflow: viewMode === 'focus-context' ? 'hidden' : 'auto',
                    p: 1.5, flex: 1, minHeight: 0,
                    ...(viewMode === 'page-switch' ? {
                      animation: transitionDirection === 'in' ? 'graphDrillDown 0.3s ease-out' : 'graphZoomOut 0.3s ease-out',
                      '@keyframes graphDrillDown': { from: { opacity: 0, transform: 'scale(1.05) translateY(-8px)' }, to: { opacity: 1, transform: 'scale(1) translateY(0)' } },
                      '@keyframes graphZoomOut': { from: { opacity: 0, transform: 'scale(0.92) translateY(8px)' }, to: { opacity: 1, transform: 'scale(1) translateY(0)' } },
                    } : {}),
                  }}
                >
                  <GraphFlowView
                    nodes={activeGraph.nodes}
                    edges={activeGraph.edges}
                    selectedNodeId={effectiveNodeId}
                    expandableNodeIds={expandableNodeIds}
                    onNodeClick={handleNodeClick}
                    viewMode={viewMode}
                    subGraphs={viewMode === 'focus-context' ? task?.subGraphs : undefined}
                    focusedPath={viewMode === 'focus-context' ? focusedPath : undefined}
                    onFocusChange={viewMode === 'focus-context' ? handleFocusChange : undefined}
                  />
                </Box>
              )
            )}
          </Box>

          {/* Drag handle */}
          {!graphCollapsed && (
            <Box
              onMouseDown={handleSplitMouseDown}
              sx={{
                height: 6, flexShrink: 0, cursor: 'row-resize',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                backgroundColor: 'transparent',
                borderTop: '1px solid rgba(255,255,255,0.08)',
                '&:hover': { backgroundColor: 'rgba(74, 144, 217, 0.15)' },
                '&:hover > div': { backgroundColor: 'primary.main' },
              }}
            >
              <Box sx={{ width: 32, height: 3, borderRadius: 1, backgroundColor: 'rgba(255,255,255,0.15)', transition: 'background-color 0.15s' }} />
            </Box>
          )}

          {/* Node detail panel */}
          <Box sx={{ flex: 1, overflow: 'hidden' }}>
            <NodeDetailPanel node={selectedNode} content={nodeContent} isStreaming={isNodeStreaming} />
          </Box>
        </Box>
      ) : (
        /* No graph: loading (replay in flight, Fix 4.2), live token stream,
           deliverable fallback (Fix 5.1), or a clean terminal message. */
        <Box sx={{ flexGrow: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {replayPending && !task.streamContent ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 3, py: 2, color: 'text.secondary' }}>
              <CircularProgress size={14} />
              <Typography variant="body2">Loading task graph…</Typography>
            </Box>
          ) : task.streamContent ? (
            <Box sx={{ overflow: 'auto', px: 3, py: 2, '& p': { m: 0 }, '& pre': { overflow: 'auto' } }}><MarkdownRenderer content={task.streamContent} /></Box>
          ) : task.status === 'starting' || task.status === 'running' ? (
            <Typography variant="body2" sx={{ px: 3, py: 2, color: 'text.secondary', fontStyle: 'italic', animation: 'pulse 1.5s ease-in-out infinite', '@keyframes pulse': { '0%, 100%': { opacity: 0.4 }, '50%': { opacity: 1 } } }}>
              {task.toolName || 'Task'} is running…
            </Typography>
          ) : task.error ? (
            <Typography variant="body2" sx={{ px: 3, py: 2, color: 'error.main' }}>
              Error{task.errorType ? ` (${task.errorType})` : ''}: {task.error}
            </Typography>
          ) : task.documentPath ? (
            <DeliverableView path={task.documentPath} />
          ) : (
            <Typography variant="body2" sx={{ px: 3, py: 2, color: 'text.secondary' }}>Task completed — no graph or deliverable was produced.</Typography>
          )}
          <div ref={bottomRef} />
        </Box>
      )}
    </Box>
  );
}

export default TaskPanel;
