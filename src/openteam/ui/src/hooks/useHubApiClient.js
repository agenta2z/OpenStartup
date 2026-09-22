/**
 * useHubApiClient — the REST/WS wrapper that satisfies the `HubApiClient`
 * interface consumed by the generic Dashboard views (DashboardPanel threads it
 * to every view as the `apiClient` prop). It is the OpenTeam-side concrete
 * implementation of the actions the Experiment Hub views call.
 *
 * Two transports:
 *   1. REST — session/hub-scoped reads + mutations hit
 *        /api/sessions/${sessionId}/hubs/${hubId}/...
 *      (the OpenTeam hub routers are mounted server-side later; the client is
 *      defined against that URL shape now so it is wire-ready). All REST goes
 *      through `fetchJson`/`postJson` so the `/api` base + `{data}` unwrap +
 *      error handling stay centralized (utils/api).
 *   2. WebSocket — the THREE long-running actions
 *        runImplementHypothesis · resumeImplementTask · runExperimentCombos
 *      do NOT block on REST; they emit a `hub_command` frame over the EXISTING
 *      manager socket (passed in as `sendHubCommand` from useManagerChat) so the
 *      server can stream progress back as `dashboard_event`s into the hub's bus.
 *
 * Orchestration lives INSIDE the client (per the verified contract):
 *   - runImplementHypothesis → switches to the hub tab + refetches submissions,
 *     and returns a synchronous `launchInfo` ({launchedAt, multiTaskId,
 *     selectedIds}) that useAutopilot correlates with the resulting impl chip.
 *   - setBaseline → REST mutate, then refetch submissions so the baseline badge
 *     updates without waiting for a round-trip event.
 *
 * `DashboardPanel` is context-free: this hook returns a plain object and is
 * passed down purely via props — it never installs a React context.
 */

import { useMemo } from 'react';
import { fetchJson, postJson } from '../utils/api';

/**
 * Build the REST base for a hub under a session. Mirrors the
 * `/api/sessions/${sid}/hubs/${hubId}` shape the prompt pins (fetchJson prepends
 * the `/api` prefix, so we return the path AFTER `/api`).
 */
function hubBase(sessionId, hubId) {
  return `/sessions/${encodeURIComponent(sessionId)}/hubs/${encodeURIComponent(hubId)}`;
}

/**
 * @param {object} opts
 * @param {string} opts.sessionId           active session id
 * @param {string} opts.hubId               this dashboard's hub id (multiTaskId)
 * @param {(command:string, payload?:object)=>void} opts.sendHubCommand
 *        emits a `hub_command` frame over the existing manager WebSocket
 * @param {(id:any, type:string)=>void} [opts.switchTab]
 *        the useManagerChat switchTab(id, type) — used to focus the hub tab
 * @param {()=>Promise<any>} [opts.refetchHubSubmissions]
 *        re-pull this hub's submissions (also exposed on the returned client)
 */
export function useHubApiClient({
  sessionId,
  hubId,
  sendHubCommand,
  switchTab,
  refetchHubSubmissions,
}) {
  return useMemo(() => {
    const base = () => hubBase(sessionId, hubId);

    // Default submissions refetch: a session/hub-scoped GET. Callers may inject
    // their own (e.g. a hook's refetch) via `refetchHubSubmissions`; otherwise
    // this REST GET is the fallback so the method is always callable.
    const _refetchHubSubmissions = async () => {
      if (typeof refetchHubSubmissions === 'function') {
        return refetchHubSubmissions();
      }
      if (!sessionId || !hubId) return null;
      try {
        return await fetchJson(`${base()}/submissions`);
      } catch (e) {
        console.warn('[useHubApiClient] refetchHubSubmissions failed:', e);
        return null;
      }
    };

    // The dashboard views expect switchTab to focus THIS hub's subtab. Bind the
    // hub id so callers in the views can call `apiClient.switchTab()` with no
    // args (the host-level switchTab signature is switchTab(id, type)).
    const _switchTab = (target) => {
      if (typeof switchTab !== 'function') return;
      if (target === 'chat' || target === 'session') {
        switchTab(null, 'session');
      } else {
        switchTab(hubId, 'dashboard');
      }
    };

    return {
      // ---- Submission CRUD (REST) ---------------------------------------
      addSubmission: (submission) =>
        postJson(`${base()}/submissions`, submission || {}),

      updateSubmission: (submissionId, patch) =>
        postJson(
          `${base()}/submissions/${encodeURIComponent(submissionId)}`,
          patch || {},
        ),

      refetchHubSubmissions: _refetchHubSubmissions,

      // ---- Single-run lifecycle (REST) ----------------------------------
      runSubmission: (submissionId, opts) =>
        postJson(
          `${base()}/submissions/${encodeURIComponent(submissionId)}/run`,
          opts || {},
        ),

      cancelSubmissionRun: (submissionId, opts) =>
        postJson(
          `${base()}/submissions/${encodeURIComponent(submissionId)}/cancel`,
          opts || {},
        ),

      // ---- Baseline (REST + internal orchestration) ---------------------
      // Set the baseline submission, then refetch so the baseline badge flips
      // immediately (orchestration kept inside the client per the contract).
      setBaseline: async (submissionId, opts) => {
        const result = await postJson(`${base()}/baseline`, {
          submission_id: submissionId,
          ...(opts || {}),
        });
        await _refetchHubSubmissions();
        return result;
      },

      // ---- Setup + scripts (REST) ---------------------------------------
      setupSubmission: (submissionId, opts) =>
        postJson(
          `${base()}/submissions/${encodeURIComponent(submissionId)}/setup`,
          opts || {},
        ),

      saveScriptVersion: (submissionId, script) =>
        postJson(
          `${base()}/submissions/${encodeURIComponent(submissionId)}/script`,
          typeof script === 'string' ? { content: script } : (script || {}),
        ),

      // ---- Long-running actions (WS `hub_command`) ----------------------
      // runImplementHypothesis: fire-and-correlate. Emit the WS command, focus
      // the hub tab + refetch submissions, and return a synchronous launchInfo
      // ({launchedAt, multiTaskId, selectedIds}) that useAutopilot matches to
      // the resulting implhyp-* chip (see _autopilotChipFinders.findImplChipByLaunch).
      runImplementHypothesis: (multiTaskId, opts) => {
        const o = opts || {};
        const launchedAt = Date.now();
        const selectedIds = Array.isArray(o.selectedIds) ? o.selectedIds : [];
        sendHubCommand('implement_hypothesis', {
          multi_task_id: multiTaskId,
          selected_ids: selectedIds,
          ...o,
        });
        // Orchestrate: make sure the hub tab is visible + submissions fresh.
        _switchTab('dashboard');
        _refetchHubSubmissions();
        return { launchedAt, multiTaskId, selectedIds };
      },

      // resumeImplementTask: views call it with an entry-shaped object
      // ({id, ...}); forward the sub-task id over the socket.
      resumeImplementTask: (entry) => {
        const o = entry || {};
        sendHubCommand('resume_implement_task', {
          multi_task_id: hubId,
          sub_task_id: o.id != null ? o.id : o.subTaskId,
          ...o,
        });
      },

      // runExperimentCombos: aggregate-only refresh or a full combo run.
      runExperimentCombos: (multiTaskId, opts) => {
        const o = opts || {};
        sendHubCommand('run_experiment_combos', {
          multi_task_id: multiTaskId,
          aggregate_only: !!o.aggregateOnly,
          ...o,
        });
      },

      // R2 — in-hub "Confirm Selection & Start" when the hub was opened from a
      // live conversation. ONE atomic host-agnostic command: the server both
      // launches implementation (via _exec_implement_hypothesis) AND resolves the
      // still-open Phase-2b pending input (active_input_queue) → the SOP advances
      // 2b→3 in the resumed turn with no new sop_state-mutation code.
      confirmProposalSelection: (multiTaskId, opts) => {
        const o = opts || {};
        const selectedIds = Array.isArray(o.selectedIds) ? o.selectedIds : [];
        sendHubCommand('confirm_proposal_selection', {
          hub_id: multiTaskId,
          multi_task_id: multiTaskId,
          args: { selected_ids: selectedIds },
        });
        return { launchedAt: Date.now(), multiTaskId, selectedIds };
      },

      // R4 — in-hub "Done — summarize & evolve". Generic terminal signal; the
      // HOST maps it to the real Phase-3 completion (writes the declared Phase-3
      // output + _check_phase_completion → advances 3→3b out-of-turn).
      completeEvolution: (multiTaskId) => {
        sendHubCommand('evolution_complete', {
          hub_id: multiTaskId,
          multi_task_id: multiTaskId,
        });
      },

      // ---- Navigation (delegates to host switchTab) ---------------------
      switchTab: _switchTab,
    };
  }, [sessionId, hubId, sendHubCommand, switchTab, refetchHubSubmissions]);
}

export default useHubApiClient;
