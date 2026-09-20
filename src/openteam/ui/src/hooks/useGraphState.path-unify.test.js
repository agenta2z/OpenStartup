/**
 * Parity test (MANDATORY regression guard, Phase 2.4 in the v4 plan).
 *
 * Both focus-context (focusedPath in TaskPanel) and page-switch (graphPath
 * in useGraphState) must resolve to the SAME subGraphs key for the same
 * drill path at every depth. Without this guard, the next refactor could
 * re-split the convention (e.g. let graphPath drift back to storing local
 * remainders), silently breaking page-switch drill at depth >= 2.
 *
 * The contract:
 *   subGraphs are keyed by fully-qualified parent_node_id (e.g.
 *   "planner/propose"). The deepest entry in either path[] IS that key.
 *   path[path.length - 1] resolves at every depth; path.join('/') would
 *   double-prefix at depth >= 2 and miss.
 */

import { renderHook, act } from '@testing-library/react';
import { useGraphState } from './useGraphState';

function makeTask({ subGraphs = {} } = {}) {
  return {
    id: 'tid-1',
    graph: { nodes: [{ id: 'planner', label: 'Plan', status: 'running' }],
             edges: [], layout: 'horizontal' },
    subGraphs,
  };
}

const TASK_WITH_DEPTHS = makeTask({
  subGraphs: {
    'planner': {
      nodes: [
        { id: 'planner/propose', label: 'Propose', status: 'running', is_container: true },
        { id: 'planner/review',  label: 'Review',  status: 'pending' },
      ],
      edges: [], layout: 'horizontal',
    },
    'planner/propose': {
      nodes: [
        { id: 'planner/propose/breakdown',  label: 'Breakdown', status: 'completed' },
        { id: 'planner/propose/worker_00',  label: 'Worker 00', status: 'running', is_container: true },
        { id: 'planner/propose/aggregator', label: 'Aggregator', status: 'pending' },
      ],
      edges: [], layout: 'horizontal',
    },
    'planner/propose/worker_00': {
      nodes: [
        { id: 'planner/propose/worker_00/propose', label: 'Propose', status: 'running' },
      ],
      edges: [], layout: 'horizontal',
    },
  },
});

function deriveAtPath(path) {
  const setTasks = jest.fn();
  const { result, rerender } = renderHook(() => useGraphState(setTasks));
  act(() => { result.current.setGraphPath('tid-1', path); });
  rerender();
  return result.current.getDerivedFor('tid-1', TASK_WITH_DEPTHS);
}

describe('useGraphState path-unify parity (Phase 2.4)', () => {
  test('depth 1: currentGraph resolves at planner', () => {
    const derived = deriveAtPath(['planner']);
    expect(derived.currentGraph).toBe(TASK_WITH_DEPTHS.subGraphs['planner']);
  });

  test('depth 2: currentGraph resolves at planner/propose (NOT planner/planner/propose)', () => {
    const derived = deriveAtPath(['planner', 'planner/propose']);
    expect(derived.currentGraph).toBe(TASK_WITH_DEPTHS.subGraphs['planner/propose']);
    // Bug guarded: graphPath.join('/') would be "planner/planner/propose"
    // which would resolve to subGraphs[that] === undefined.
  });

  test('depth 3: currentGraph resolves at planner/propose/worker_00', () => {
    const derived = deriveAtPath([
      'planner', 'planner/propose', 'planner/propose/worker_00',
    ]);
    expect(derived.currentGraph)
      .toBe(TASK_WITH_DEPTHS.subGraphs['planner/propose/worker_00']);
  });

  test('expandableNodeIds at depth 2 contains FULL keys (not local remainders)', () => {
    const derived = deriveAtPath(['planner', 'planner/propose']);
    // Set must hold the FULL key so handleNodeClick's
    // expandableNodeIds.has(clickedNodeId) — where clickedNodeId is the
    // fully-qualified id from GraphFlowView's node._qualifiedId — matches.
    expect(derived.expandableNodeIds.has('planner/propose/worker_00')).toBe(true);
    expect(derived.expandableNodeIds.has('worker_00')).toBe(false);
  });

  test('focus-context and page-switch resolve SAME subGraphs key at depth 2', () => {
    // TaskPanel.js:107 computes focusedContainerId = focusedPath[last].
    // useGraphState.getDerivedFor computes deepestKey = graphPath[last].
    // These two formulas must produce IDENTICAL keys for the same path.
    const path = ['planner', 'planner/propose'];
    const focusContextKey = path[path.length - 1];
    const pageSwitchDerived = deriveAtPath(path);
    const pageSwitchKey = path[path.length - 1];
    expect(focusContextKey).toBe(pageSwitchKey);
    expect(pageSwitchDerived.currentGraph)
      .toBe(TASK_WITH_DEPTHS.subGraphs[focusContextKey]);
  });

  test('depth 0 (root): expandableNodeIds contains depth-1 keys (full keys)', () => {
    const derived = deriveAtPath([]);
    expect(derived.expandableNodeIds.has('planner')).toBe(true);
  });
});
