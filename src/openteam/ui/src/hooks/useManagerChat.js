/**
 * useManagerChat — WebSocket-based hook for Manager ↔ AI streaming chat.
 *
 * Adapted from rankevolve's useAgentChat.js.
 * Manages connection to /ws/manager, token streaming, auto-reconnect.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import {
  parseResponseTags,
  parseSessionContext,
  stripSessionContext,
  stripResponseTags,
  stripAnsi,
  stripAcliNoise,
  stripToolsToInvoke,
} from '../components/chat/ThinkingFold';
import { useGraphState } from './useGraphState';
import { makeWsEvents } from './useDashboardEvents';
import { fetchJson } from '../utils/api';

const WS_RECONNECT_BASE_MS = 1000;
const WS_RECONNECT_MAX_MS = 30000;
// Client keepalive ping interval (Layer 1). Must be < any reasonable proxy idle
// timeout and < the 30s server heartbeat so idle connections stay alive.
const WS_KEEPALIVE_MS = 20000;

/**
 * Persist / restore the active tab selection per session. The task subtab triad
 * historically did NOT persist the active tab (it always reopened to 'session');
 * dashboards add this small convention so a hub stays focused across a reload.
 * Mirrors the safe try/catch localStorage idiom used by ThemeProvider.
 */
function _activeTabKey(sid) {
  return `ot_active_tab_${sid || 'na'}`;
}
function readActiveTab(sid) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return null;
    const raw = window.localStorage.getItem(_activeTabKey(sid));
    return raw ? JSON.parse(raw) : null;
  } catch (_e) {
    return null;
  }
}
function saveActiveTab(sid, tabType, id) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    window.localStorage.setItem(
      _activeTabKey(sid),
      JSON.stringify({ tabType: tabType || 'session', id: id != null ? id : null }),
    );
  } catch (_e) {
    /* ignore */
  }
}

/**
 * Resolve the widgetType string from a pendingInput object.
 * Used when inserting a committed widget_response message into history.
 */
function _resolveWidgetType(pendingInput) {
  const inputMode = pendingInput?.inputMode || {};
  return inputMode.metadata?.widget_type || inputMode.mode || 'free_text';
}

/**
 * Compute the user-facing display text for a raw round buffer using the same
 * strip chain message_end uses today (stripToolsToInvoke → parseResponseTags
 * responseContent → stripResponseTags + noise strips). Returns '' when the
 * round has no displayable content (pure thinking / pure tool-call round).
 */
function _displayFromBuffer(raw) {
  const content = raw || '';
  if (!content.trim()) return '';
  const parsed = parseResponseTags(content);
  const phase = parsed.phase === 'pre_response' ? 'no_tags' : parsed.phase;
  let display;
  if (phase === 'no_tags') {
    display = stripAnsi(stripAcliNoise(stripToolsToInvoke(content)));
  } else {
    display = stripSessionContext(
      stripResponseTags(
        stripAnsi(stripAcliNoise(stripToolsToInvoke(parsed.responseContent || '')))
      )
    );
  }
  return (display || '').trim();
}

function getWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Always connect SAME-ORIGIN (the exact host:port the page was served from) and
  // let the CRA dev-server proxy forward /ws/manager to the backend (setupProxy.js
  // proxies /ws/manager with ws:true). Do NOT dial the backend port (e.g. :8089)
  // directly: in many environments the browser can reach the UI's port but NOT a
  // separate backend port — a corp→devserver path that only exposes the navigated
  // port, an SSH tunnel/port-forward, or a reverse proxy. A direct dial to such a
  // port silently hangs (the SYN is dropped, not refused) and the socket sits in
  // CONNECTING forever → a permanent "Connecting…" badge. The page itself and every
  // /api request already ride this same-origin path, so the WebSocket must too. In
  // production FastAPI serves the built UI and /ws/manager from one origin, so
  // same-origin is correct there as well (and yields wss: automatically over HTTPS).
  return `${proto}//${window.location.host}/ws/manager`;
}

export function useManagerChat(sessionId) {
  const [messages, setMessages] = useState([]);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  // Resume-in-progress UI lock (round/turn resume). Set on send, cleared on the
  // first of message_start / terminal status / error / a safety timeout. Purely a
  // UI flag — resume is server-authoritative. resumeStage drives the banner text.
  const [isResuming, setIsResuming] = useState(false);
  const [resumeStage, setResumeStage] = useState(null);
  const resumeTimeoutRef = useRef(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [pendingInput, setPendingInput] = useState(null);
  // Task subtab state
  const [tasks, setTasks] = useState({});
  const [activeTabType, setActiveTabType] = useState('session');
  const [activeTaskId, setActiveTaskId] = useState(null);
  // Dashboard subtab state — mirror of the task triad, keyed by hubId. Each
  // entry is {manifest, seed, status, wsEvents$}. Multiple dashboards per
  // session are possible (the map must not assume exactly one); one is active
  // at a time via activeDashboardId. The per-hub wsEvents$ bus is the live
  // dashboard_event stream DashboardPanel subscribes to.
  const [dashboards, setDashboards] = useState({});
  const [activeDashboardId, setActiveDashboardId] = useState(null);
  // Stable per-hub bus registry. Buses live outside React state (kept in a ref)
  // so a re-render never re-creates a hub's stream and drops its subscribers;
  // the `dashboards` map only stores a reference to the same object.
  const dashboardBusesRef = useRef({});
  // Monotonic counter bumped on events that change the sidebar session list
  // (connect / session_init / turn completion / task_status transitions). The
  // view forwards it up so App can refetch('/sessions') and keep counts fresh —
  // the list is otherwise fetched once on mount and goes stale after a restart.
  const [sessionsRefreshTick, setSessionsRefreshTick] = useState(0);

  // Graph visualization state (sub-graphs, drill-down, batching)
  const graphState = useGraphState(setTasks);

  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  // Client→server WebSocket keepalive (Layer 1). During idle the client
  // otherwise transmits nothing (the server heartbeat is server→client only),
  // so a proxy/NAT with a bidirectional/client-idle policy silently drops the
  // socket — the reconnect then clears the pending widget. A periodic client
  // ping (server already replies `pong`) keeps the connection alive. Cleared on
  // close/error/unmount so no duplicate timers accumulate across reconnects.
  const pingTimerRef = useRef(null);
  const streamingContentRef = useRef('');
  const streamingMetadataRef = useRef({});
  const connectRef = useRef(null);
  const submittedRef = useRef(false);      // double-submit guard
  const pendingInputRef = useRef(null);    // stable ref to current pendingInput (avoids stale closure)
  const turnCountRef = useRef(0);          // tracks current turn number for live messages
  // r12/r13 per-round bubble lifecycle (RoundContext from AF on_round_start):
  //   currentRoundIdRef  — message_id of the round currently buffering tokens
  //   committedRoundIdsRef — message_ids already committed (dedupe; a round commits at most once)
  // The route's per-turn message_start/status drives isStreaming (turn-level busy);
  // per-round message_id on token/stream_correction/message_end/pending_input drives bubbles.
  const currentRoundIdRef = useRef(null);
  const currentRoundIndexRef = useRef(null);  // round_index of the round currently buffering
  const committedRoundIdsRef = useRef(new Set());
  // Most-recent task_status task_id that is still in flight ("starting"/"running" but not
  // "completed"/"error"/"cancelled"). Routed through cancelRequest + sendPendingInputResponse
  // so dev-tool cancels and Approve/Reject widget responses reach the right per-task queue
  // (see manager_websocket_routes.py Patch 3.4 / R9b).
  const currentTaskIdRef = useRef(null);
  // Resume re-injection is SERVER-AUTHORITATIVE (manager_websocket_routes.py:
  // resume_from_turn keeps the clicked turn, then re-runs it via process_message).
  // The client does NOT replay it — the old pendingResumeReplayRef/sendMessageRef
  // round-trip was fragile: it nulled the token before a setTimeout→sendMessage
  // that silently no-ops on a non-OPEN socket, so a WS reconnect during the
  // resume's blocking FS ops permanently dropped the turn.

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    const delay = Math.min(
      WS_RECONNECT_BASE_MS * Math.pow(2, reconnectAttemptRef.current),
      WS_RECONNECT_MAX_MS
    );
    reconnectAttemptRef.current += 1;
    reconnectTimerRef.current = setTimeout(() => {
      if (connectRef.current) connectRef.current();
    }, delay);
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const url = getWsUrl();
    setConnectionStatus('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttemptRef.current = 0;
      // Refresh the sidebar session list on (re)connect — counts/rows may have
      // changed (e.g. after a server restart) since it was fetched on mount.
      setSessionsRefreshTick((n) => n + 1);
      // Send init with session_id so server can resume correct conversation
      ws.send(JSON.stringify({ type: 'init', session_id: sessionId }));
      // Start the client keepalive ping (Layer 1). 20s < any reasonable proxy
      // idle timeout and < the 30s server heartbeat. Replace any prior timer
      // (defensive — a reconnect should never leave two running).
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, WS_KEEPALIVE_MS);
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      wsRef.current = null;
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }
      scheduleReconnect();
    };

    ws.onerror = () => {
      setConnectionStatus('error');
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        handleServerMessage(JSON.parse(event.data));
      } catch (e) {
        console.error('Failed to parse WS message:', e);
      }
    };
  }, [sessionId, scheduleReconnect]);

  // Keep connectRef up to date
  connectRef.current = connect;

  // Commit a per-round bubble (dedupe by message_id). `display` must already be
  // the cleaned, display-facing text; if empty, nothing is committed/persisted.
  // `raw` (optional) is kept as rawContent for the "Full Response" RAW tab.
  const commitRoundBubble = useCallback((messageId, display, opts = {}) => {
    if (!messageId) return;
    if (committedRoundIdsRef.current.has(messageId)) return;
    const displayText = (display || '').trim();
    if (!displayText) return; // empty round → never committed/persisted
    committedRoundIdsRef.current.add(messageId);
    const raw = opts.raw != null ? opts.raw : display;
    const parsed = parseResponseTags(raw || '');
    const finalPhase = parsed.phase === 'pre_response' ? 'no_tags' : parsed.phase;
    setMessages(prev => [...prev, {
      id: messageId,
      role: 'agent',
      content: displayText,
      rawContent: raw || '',
      timestamp: new Date().toISOString(),
      thinkingContent: opts.thinkingContent != null ? opts.thinkingContent : (parsed.thinkingContent || ''),
      responsePhase: finalPhase,
      sessionContext: opts.sessionContext != null ? opts.sessionContext : parseSessionContext(raw || ''),
      promptData: opts.promptData || null,
      turnNumber: opts.turnNumber != null ? opts.turnNumber : (turnCountRef.current || 0) + 1,
      roundIndex: opts.roundIndex != null ? opts.roundIndex : null,
      roundNumber: opts.roundIndex != null ? opts.roundIndex : null,
      agent_name: opts.agent_name
        || streamingMetadataRef.current?.agent_name
        || 'Orchestrator',
    }]);
  }, []);

  // Get (or lazily create) the stable per-hub event bus. handleServerMessage is
  // an empty-deps closure, so it must reach the bus registry through this ref-
  // backed helper rather than capturing `dashboards` (which would go stale).
  const getOrCreateBus = useCallback((hubId) => {
    if (!hubId) return null;
    let bus = dashboardBusesRef.current[hubId];
    if (!bus) {
      bus = makeWsEvents();
      dashboardBusesRef.current[hubId] = bus;
    }
    return bus;
  }, []);

  const handleServerMessage = useCallback((data) => {
    switch (data.type) {
      case 'task_status': {
        const {
          task_id, status, request, tool_name,
          error: taskError,
          error_type: taskErrorType,
        } = data;
        // Track currently in-flight dev-tool task_id so cancelRequest +
        // sendPendingInputResponse can route by task_id (manager_websocket_routes
        // Patch 3.4 / R9b). Clear on terminal states.
        if (status === 'starting' || status === 'running') {
          currentTaskIdRef.current = task_id;
        } else if (currentTaskIdRef.current === task_id &&
                   (status === 'completed' || status === 'error' || status === 'cancelled')) {
          currentTaskIdRef.current = null;
        }
        if (status === 'starting') {
          const label = request || tool_name || 'Task';
          // Clear any prior graph nav state for this task_id so a re-start
          // genuinely resets (rather than inheriting the prior run's drill
          // path / sticky selection / race buffer / first-root-seen flag).
          // Phase 2.5 nav-reset guard.
          if (graphState?.resetTaskNavState) graphState.resetTaskNavState(task_id);
          setTasks(prev => ({
            ...prev,
            [task_id]: {
              id: task_id, label, toolName: tool_name,
              status: 'starting', streamContent: '', isStreaming: false,
              error: null, errorType: null,
            },
          }));
          setMessages(prev => [...prev, {
            id: `task-ref-${task_id}`, role: 'task_ref',
            taskId: task_id, label, status: 'starting',
            timestamp: new Date().toISOString(),
          }]);
        } else {
          // A clean terminal ("completed"/"cancelled") should CLEAR any prior
          // error metadata — mirrors reconcile's behavior in session_store.py
          // which .pop()s errorType/error when healing to "completed". This
          // keeps the tasks[] / messages[] shape consistent with the on-disk
          // state (backend _run success branch also clears these fields).
          //
          // For non-terminal-clean transitions (running, error): if the WS
          // event carries new error info, use it; else preserve prior detail
          // so a status-only re-broadcast doesn't wipe context.
          const isCleanTerminal = status === 'completed' || status === 'cancelled';
          setTasks(prev => prev[task_id]
            ? {
                ...prev,
                [task_id]: {
                  ...prev[task_id],
                  status,
                  error: taskError !== undefined
                    ? (taskError || null)
                    : isCleanTerminal
                      ? null
                      : (prev[task_id].error ?? null),
                  errorType: taskErrorType !== undefined
                    ? (taskErrorType || null)
                    : isCleanTerminal
                      ? null
                      : (prev[task_id].errorType ?? null),
                },
              }
            : prev
          );
          // BUG FIX: the pre-fix line dropped taskError/taskErrorType when writing
          // to messages[], so a reload/re-render lost the detail even though the
          // tasks[] map had it. Preserve both when the WS event carries them.
          // On clean-terminal, explicitly clear (mirrors tasks[] above).
          setMessages(prev => prev.map(msg =>
            msg.role === 'task_ref' && msg.taskId === task_id
              ? {
                  ...msg,
                  status,
                  ...(taskError !== undefined
                    ? { error: taskError }
                    : isCleanTerminal
                      ? { error: null }
                      : {}),
                  ...(taskErrorType !== undefined
                    ? { errorType: taskErrorType }
                    : isCleanTerminal
                      ? { errorType: null }
                      : {}),
                }
              : msg
          ));
        }
        // A task transition (start or terminal) changes what the sidebar should
        // show for this session — nudge App to refetch the session list.
        setSessionsRefreshTick((n) => n + 1);
        break;
      }

      case 'graph_topology': {
        const tid = data.task_id;
        if (tid) graphState.handleGraphTopology(tid, data);
        break;
      }

      case 'node_status': {
        if (data.task_id) graphState.handleNodeStatus(data.task_id, data);
        break;
      }

      case 'node_stream': {
        if (data.task_id) graphState.handleNodeStream(data.task_id, data);
        break;
      }

      case 'graph_reconcile': {
        if (data.task_id) graphState.handleGraphReconcile(data.task_id, data);
        break;
      }

      case 'task_completed': {
        const {
          task_id: cTaskId,
          tool_name: cToolName,
          result_summary,
          workspace,
          document_path,
          next_step_tool, // backend-supplied (Conversation-tool-only guard); may be undefined
        } = data;
        // Persist the completed task's deliverable pointer + workspace onto the
        // task map so the detail panel's graph-less fallback (DeliverableView)
        // renders on the LIVE path too — not only after a reload (the
        // session_init restore path already sets documentPath). Merge-only, so a
        // graph already hydrated (and the sibling task_status 'completed' status)
        // is preserved.
        if (cTaskId && (document_path || workspace)) {
          setTasks(prev => prev[cTaskId]
            ? {
                ...prev,
                [cTaskId]: {
                  ...prev[cTaskId],
                  ...(document_path ? { documentPath: document_path } : {}),
                  ...(workspace ? { workspace } : {}),
                },
              }
            : prev
          );
        }
        // Auto-advance: send a new WS message to trigger the next conversation
        // turn. Facts-only synthesis — the SOP's <SOPNextStepGuidance> is the
        // single source of truth for the required next tool. Prior versions
        // hardcoded a "you MUST respond with confirmation" directive + example
        // JSON that dominated the SOP guidance and misfired for phases whose
        // required tool wasn't confirmation (e.g. Phase 2b requires
        // proposal_selection). If the backend attaches `next_step_tool`
        // (deterministic Conversation-tool naming derived from
        // SOPState.phase_required_tools), name it explicitly. If not, defer
        // generically to the guidance block.
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const parts = [
            `[System notification: Task '${cToolName || cTaskId}' (${cTaskId}) completed successfully.`,
            workspace ? `Workspace: ${workspace}.` : '',
            document_path ? `Generated document: ${document_path}.` : '',
            result_summary ? `Summary: ${result_summary.slice(0, 300)}.` : '',
            next_step_tool
              ? `Invoke the required \`${next_step_tool}\` conversation tool as specified in <SOPNextStepGuidance> above; do not default to a confirmation tool.`
              : `Refer to <SOPNextStepGuidance> above for the required next tool call; do not default to a confirmation tool.`,
            // Preserve the polished confirmation-button labels ONLY when the
            // next required tool actually IS `confirmation` — keeps Phase 1b's
            // UX intact without forcing `confirmation` on Phase 2b.
            next_step_tool === 'confirmation' && document_path
              ? `If invoking confirmation: set view to "${document_path}", view_label to "View Documentation", yes_label to "✅ Approve & Proceed", no_label to "❌ Request Changes".`
              : '',
            ']',
          ].filter(Boolean).join(' ');
          wsRef.current.send(JSON.stringify({ type: 'message', content: parts, is_auto_advance: true }));
        }
        break;
      }

      case 'dashboard_open': {
        // Create/activate a dashboard subtab for hub_id, storing its manifest +
        // seed and a stable per-hub event bus. Mirrors task_status:'starting'
        // (which seeds tasks[task_id] + a task_ref message). We also drop a
        // dashboard_ref message so the chat stream shows a card and a restore
        // has a marker even though the server persists its own dashboard_ref.
        const openHubId = data.hub_id;
        if (openHubId) {
          const bus = getOrCreateBus(openHubId);
          setDashboards(prev => ({
            ...prev,
            [openHubId]: {
              hubId: openHubId,
              manifest: data.manifest || null,
              seed: data.seed || {},
              status: (prev[openHubId] && prev[openHubId].status) || 'open',
              wsEvents$: bus,
            },
          }));
          // Switch to it (matches dashboard_open semantics: "switch to it").
          setActiveTabType('dashboard');
          setActiveDashboardId(openHubId);
          setActiveTaskId(null);
          saveActiveTab(sessionId, 'dashboard', openHubId);
          // Drop a dashboard_ref card if one isn't already present for this hub.
          const label = (data.manifest && data.manifest.label) || 'Dashboard';
          const icon = (data.manifest && data.manifest.icon) || '';
          setMessages(prev => (
            prev.some(m => m.role === 'dashboard_ref' && m.hubId === openHubId)
              ? prev
              : [...prev, {
                id: `dashboard-ref-${openHubId}`, role: 'dashboard_ref',
                hubId: openHubId, label, icon, status: 'open',
                timestamp: new Date().toISOString(),
              }]
          ));
          // The sidebar's subtab list changed — nudge the session-list refresh.
          setSessionsRefreshTick((n) => n + 1);
        }
        break;
      }

      case 'dashboard_status': {
        // Update a hub's status chip (sidebar + dashboard_ref card). `status` is
        // required; any extra fields ride along on the entry for the chip.
        const statusHubId = data.hub_id;
        if (statusHubId) {
          const { type: _t, hub_id: _h, status, ...extra } = data;
          setDashboards(prev => prev[statusHubId]
            ? { ...prev, [statusHubId]: { ...prev[statusHubId], status, ...extra } }
            : prev
          );
          setMessages(prev => prev.map(msg =>
            msg.role === 'dashboard_ref' && msg.hubId === statusHubId
              ? { ...msg, status }
              : msg
          ));
        }
        break;
      }

      case 'dashboard_event': {
        // Push a live update into the target hub's wsEvents$ bus. DashboardPanel
        // subscribed to that bus dispatches {type:'DASHBOARD_EVENT', event} into
        // its own reducer. Route STRICTLY by hub_id so hub A's run_progress
        // never leaks into hub B. The forwarded event keeps event_type + payload
        // (the shape the dashboard reducer/views consume).
        const evtHubId = data.hub_id;
        if (evtHubId) {
          const bus = getOrCreateBus(evtHubId);
          if (bus) {
            bus.next({ event_type: data.event_type, payload: data.payload || {} });
          }
        }
        break;
      }

      case 'token': {
        // Route task tokens to task panel — do NOT add to conversation stream
        const tokenTaskId = data.task_id || data.metadata?.task_id;
        if (tokenTaskId) {
          setTasks(prev => {
            const t = prev[tokenTaskId];
            if (!t) return prev;
            let sc = (t.streamContent || '') + data.content;
            if (sc.length > 200_000) sc = sc.slice(50_000);
            return { ...prev, [tokenTaskId]: { ...t, isStreaming: true, streamContent: sc } };
          });
          break;
        }
        // Conversation streaming (existing behaviour) + r12 per-round identity.
        // RoundContext message_id changes each AF round. When the id rolls over,
        // commit the PRIOR round's transient buffer as a bubble IF its cleaned
        // display text is non-empty, then reset the buffer for the new round.
        const roundId = data.message_id;
        if (roundId && roundId !== currentRoundIdRef.current) {
          const priorRaw = streamingContentRef.current;
          const priorId = currentRoundIdRef.current;
          if (priorId) {
            commitRoundBubble(priorId, _displayFromBuffer(priorRaw), {
              raw: priorRaw,
              roundIndex: currentRoundIndexRef.current,
              turnNumber: data.turn_number,
            });
          }
          streamingContentRef.current = '';
          currentRoundIdRef.current = roundId;
          currentRoundIndexRef.current = data.round_index != null ? data.round_index : null;
        }
        streamingContentRef.current += data.content;
        if (data.metadata) {
          streamingMetadataRef.current = data.metadata;
        }
        // Parse <Response> tags to separate thinking from response
        const parsedToken = parseResponseTags(streamingContentRef.current);
        // Extract session context if present
        const ctxToken = parseSessionContext(streamingContentRef.current);
        setStreamingMessage({
          role: 'agent',
          content: streamingContentRef.current,
          metadata: streamingMetadataRef.current,
          thinkingContent: parsedToken.thinkingContent,
          responseContent: parsedToken.responseContent,
          responsePhase: parsedToken.phase,
          sessionContext: ctxToken,
          roundIndex: currentRoundIndexRef.current,
          roundNumber: currentRoundIndexRef.current,
        });
        setIsStreaming(true);
        break;
      }

      case 'message_start':
        // Route-level (per-turn) message_start has no message_id → this is the
        // "request_in_flight ON" signal. Mark the turn busy. Do NOT open a
        // committed bubble here (bubbles are per-round, keyed by RoundContext
        // message_id from token/message_end). Reset round buffers for a fresh turn.
        if (!data.message_id) {
          streamingContentRef.current = '';
          streamingMetadataRef.current = {};
          currentRoundIdRef.current = null;
          currentRoundIndexRef.current = null;
          committedRoundIdsRef.current = new Set();
          setStreamingMessage({ role: 'agent', content: '', metadata: {}, responsePhase: 'pre_response' });
          setIsStreaming(true);
          // Resume handoff: streaming has begun → drop the "Resuming…" lock (the
          // isStreaming lock now covers input) and cancel the safety timeout.
          if (resumeTimeoutRef.current) { clearTimeout(resumeTimeoutRef.current); resumeTimeoutRef.current = null; }
          setIsResuming(false);
          setResumeStage(null);
        }
        break;

      case 'pending_input': {
        // Layer 2, Piece 2 (re-display) idempotency guard. A `restored` re-emit
        // fires on (re)connect to bring back a persisted, still-unanswered
        // widget. If we are ALREADY showing that exact widget (same
        // pending_input_id), keep it as-is — rebuilding would remount the widget
        // component and discard any in-progress local input (half-typed text,
        // a pending selection) and reset the submit guard. Only a fresh (live)
        // pending_input or a different id rebuilds. (On a real reconnect,
        // session_init has already nulled pendingInput first, so this is a
        // no-op there; it protects any re-emit that is NOT preceded by a reset.)
        if (
          data.restored &&
          pendingInputRef.current &&
          pendingInputRef.current.pendingInputId &&
          pendingInputRef.current.pendingInputId === data.pending_input_id
        ) {
          break;
        }
        // r13: commit the matching round's preamble bubble (the AI's text before
        // the conversation tool invocation) IF non-empty, deduped by the
        // RoundContext message_id, then show the widget. The committed bubble is
        // keyed by message_id (same as the per-round message_end), so a later
        // message_end for the same round is a no-op (already committed).
        const preMsgId = data.message_id;
        const preRaw = streamingContentRef.current;
        commitRoundBubble(preMsgId, _displayFromBuffer(preRaw), {
          raw: preRaw,
          promptData: data.prompt_data || null,
          roundIndex: data.round_index != null ? data.round_index : currentRoundIndexRef.current,
          turnNumber: data.turn_number != null ? data.turn_number : (turnCountRef.current || 0) + 1,
        });
        // Clear streaming state (turn is still active — don't set isStreaming=false)
        setStreamingMessage(null);
        streamingContentRef.current = '';
        streamingMetadataRef.current = {};
        // Show the conversation tool widget; reset submit guard for fresh widget
        submittedRef.current = false;
        console.debug('[pending_input] input_mode:', JSON.stringify(data.input_mode, null, 2));
        const newPending = {
          content: data.content,
          inputMode: data.input_mode || null,
          // pending_input_id is the stable id minted by the server for this
          // widget round; the optimistic widget_response card keys off it and
          // the response echoes it back (see sendPendingInputResponse).
          pendingInputId: data.pending_input_id || null,
          messageId: preMsgId || null,
          roundIndex: data.round_index != null ? data.round_index : currentRoundIndexRef.current,
          turnNumber: data.turn_number != null ? data.turn_number : null,
        };
        pendingInputRef.current = newPending;
        setPendingInput(newPending);
        break;
      }

      case 'stream_correction': {
        // Server has clean output from --output-file (no TUI noise, intact code fences).
        // Replace the in-progress streaming display with the clean version before
        // message_end commits it. streamingContentRef is updated so message_end
        // uses clean content as the fallback if final_content is empty.
        const rawClean = data.content || '';
        // r12 per-round identity: stream_correction carries the RoundContext
        // {message_id}. Adopt it as the current round (so a correction that
        // arrives before any token for this round still buffers correctly) and
        // replace this round's transient buffer with the clean version.
        if (data.message_id && data.message_id !== currentRoundIdRef.current) {
          currentRoundIdRef.current = data.message_id;
          if (data.round_index != null) currentRoundIndexRef.current = data.round_index;
        }
        streamingContentRef.current = rawClean;

        const corrParsed = parseResponseTags(rawClean);
        const corrPhase = corrParsed.phase === 'pre_response' ? 'no_tags' : corrParsed.phase;
        let corrDisplay;
        if (corrPhase === 'no_tags') {
          corrDisplay = stripAnsi(stripAcliNoise(stripToolsToInvoke(rawClean)));
        } else {
          corrDisplay = stripSessionContext(
            stripAnsi(stripAcliNoise(stripToolsToInvoke(corrParsed.responseContent)))
          );
        }

        setStreamingMessage(prev => prev ? {
          ...prev,
          content: rawClean,
          displayContent: corrDisplay,
          thinkingContent: corrParsed.thinkingContent,
          responsePhase: corrPhase,
        } : prev);
        break;
      }

      case 'message_end': {
        console.debug('[useManagerChat] message_end — message_id:', data.message_id,
          '| round_index:', data.round_index, '| turn_number:', data.turn_number,
          '| final_content len:', (data.final_content || '').length,
          '| prompt_data keys:', Object.keys(data.prompt_data || {}));
        // r13: PER-ROUND message_end. final_content is already display-clean from
        // the server; commit/persist a bubble ONLY when it is non-empty, keyed by
        // message_id, deduped (a round commits at most once — e.g. if a preamble
        // already committed it via pending_input/token-rollover, this is a no-op).
        // Empty round → balanced terminal message_end with final_content:'' →
        // nothing committed. Do NOT clear isStreaming here: turn-level busy is
        // owned by the route's message_start / status terminal.
        const finalContent = data.final_content != null ? data.final_content : '';
        const roundMsgId = data.message_id;
        // Reuse the raw buffer (if this round is the one currently streaming) for
        // the RAW "Full Response" tab and thinking extraction; final_content from
        // the server is already cleaned, so use it directly as the display text.
        const isCurrentRound = roundMsgId && roundMsgId === currentRoundIdRef.current;
        const rawForRound = isCurrentRound ? streamingContentRef.current : finalContent;
        commitRoundBubble(roundMsgId, finalContent, {
          raw: rawForRound,
          promptData: data.prompt_data || null,
          roundIndex: data.round_index != null ? data.round_index : (isCurrentRound ? currentRoundIndexRef.current : null),
          turnNumber: data.turn_number != null ? data.turn_number : (turnCountRef.current || 0) + 1,
          agent_name: data.agent_name || streamingMetadataRef.current?.agent_name || 'Orchestrator',
        });
        // This round is done buffering — clear the transient display + buffer so
        // the live StreamingMessage doesn't keep showing the just-committed text.
        if (isCurrentRound || !roundMsgId) {
          setStreamingMessage(null);
          streamingContentRef.current = '';
          streamingMetadataRef.current = {};
          currentRoundIdRef.current = null;
          currentRoundIndexRef.current = null;
        }
        break;
      }

      case 'turn_boundary': {
        // Server signals a turn boundary (e.g. after a conversation tool interaction).
        // Update turn counter; cache_folder may be used by PromptViewer.
        const tbTurnNumber = data.turn_number;
        const tbCacheFolder = data.cache_folder;
        if (tbTurnNumber != null) {
          turnCountRef.current = tbTurnNumber;
        }
        // Attach cache_folder to the most recent agent message so View Prompt works
        if (tbCacheFolder) {
          setMessages(prev => {
            const idx = [...prev].reverse().findIndex(m => m.role === 'agent');
            if (idx === -1) return prev;
            const realIdx = prev.length - 1 - idx;
            return prev.map((m, i) => i === realIdx
              ? { ...m, turnNumber: tbTurnNumber || m.turnNumber, cacheFolder: tbCacheFolder }
              : m
            );
          });
        }
        break;
      }

      case 'auto_advance':
        // Server auto-continues without user input (e.g. async tool completion).
        // Don't add to message list — next message_start/token/message_end follows.
        break;

      case 'resume_status':
        // Progress frame during a resume (checkpointing → truncating → restoring).
        // Updates the non-blocking "Resuming…" banner text; does not gate input.
        setResumeStage(data.stage || null);
        break;

      case 'error':
        // Clear any stuck widget on error
        setPendingInput(null);
        pendingInputRef.current = null;
        submittedRef.current = false;
        setMessages(prev => [...prev, {
          id: `err-${Date.now()}`,
          role: 'error',
          content: data.message,
          timestamp: new Date().toISOString(),
        }]);
        setIsStreaming(false);
        setStreamingMessage(null);
        streamingContentRef.current = '';
        streamingMetadataRef.current = {};
        currentRoundIdRef.current = null;
        currentRoundIndexRef.current = null;
        // Resume rejected/failed before streaming → drop the lock + timeout.
        if (resumeTimeoutRef.current) { clearTimeout(resumeTimeoutRef.current); resumeTimeoutRef.current = null; }
        setIsResuming(false);
        setResumeStage(null);
        break;

      case 'status':
        // Turn-level terminal: clears the per-turn busy flag set by message_start.
        // Per-round bubbles are committed by their own message_end handlers, so we
        // only need to drop any leftover transient streaming display + round refs.
        if (data.status === 'complete' || data.status === 'error') {
          setIsStreaming(false);
          setStreamingMessage(null);
          streamingContentRef.current = '';
          streamingMetadataRef.current = {};
          currentRoundIdRef.current = null;
          currentRoundIndexRef.current = null;
          // Turn finished — its message_count changed, so refresh the sidebar.
          setSessionsRefreshTick((n) => n + 1);
          // Terminal → drop any resume lock + safety timeout (covers a resume that
          // finished/errored without emitting a message_start).
          if (resumeTimeoutRef.current) { clearTimeout(resumeTimeoutRef.current); resumeTimeoutRef.current = null; }
          setIsResuming(false);
          setResumeStage(null);
        }
        break;

      case 'session_init': {
        setPendingInput(null);
        pendingInputRef.current = null;
        submittedRef.current = false;
        setIsStreaming(false);
        setStreamingMessage(null);
        // Keep activeTabType='session' / activeTaskId=null on (re)load — do NOT
        // auto-open a task tab even when persisted task_ref messages rebuild tabs.
        // Same policy for dashboards: rebuild the subtab list but stay on the
        // session conversation (no auto-open).
        setActiveTabType('session');
        setActiveTaskId(null);
        setActiveDashboardId(null);
        // Reset per-round bubble lifecycle state for the (re)loaded session.
        streamingContentRef.current = '';
        streamingMetadataRef.current = {};
        currentRoundIdRef.current = null;
        currentRoundIndexRef.current = null;
        committedRoundIdsRef.current = new Set();
        // Rebuild the tasks map from persisted task_ref messages as we map them
        // (there is NO separate tasks payload — the task subtabs/panel rehydrate
        // entirely from history). Replaces the old setTasks({}).
        const tasksAcc = {};
        // Same for dashboards: rebuild the per-hub map from persisted
        // dashboard_ref history entries (the "a hub exists" marker, analogous to
        // task_ref). Each restored hub gets its stable wsEvents$ bus back.
        const dashboardsAcc = {};
        // Load existing messages from session history (r13 round-aware reload).
        if (data.messages) {
          let maxTurn = 0;
          setMessages(data.messages.map((msg, i) => {
            // Hide auto-advance system messages (RankEvolve pattern)
            if (msg.metadata?.is_auto_advance) return null;
            // r13: derive next turn from max(persisted turn_number), EXCLUDING the
            // seeded welcome message (turn_number === 0). Only count real turns.
            const persistedTurn = msg.turn_number != null ? msg.turn_number : null;
            if (persistedTurn != null && persistedTurn > maxTurn) maxTurn = persistedTurn;
            // round identity carried onto reloaded bubbles (accept camel + snake)
            const roundIndex = msg.round_index != null ? msg.round_index
              : (msg.roundIndex != null ? msg.roundIndex : null);

            // PRESERVE persisted task_ref messages BEFORE the generic role
            // coercion, so they re-hydrate as TaskCards (not blank agent bubbles)
            // AND repopulate the tasks map for the Sidebar subtabs / TaskPanel.
            // Accept camel + snake field names (matches widget_response handling).
            if (msg.role === 'task_ref') {
              const taskId = msg.taskId != null ? msg.taskId : msg.task_id;
              const toolName = msg.toolName || msg.tool_name || null;
              const label = msg.label || toolName || 'Task';
              const status = msg.status || 'completed';
              const workspace = msg.workspace != null ? msg.workspace : null;
              const documentPath = msg.documentPath != null ? msg.documentPath
                : (msg.document_path != null ? msg.document_path : null);
              // Accept camel + snake naming for errorType (persisted state uses
              // camelCase in session_state.messages; task_meta.json uses snake).
              const errorType = msg.errorType != null ? msg.errorType
                : (msg.error_type != null ? msg.error_type : null);
              // Mirror the live task_status:'starting' tasks[task_id] shape so
              // Sidebar/TaskPanel render restored tabs identically.
              if (taskId != null) {
                tasksAcc[taskId] = {
                  id: taskId,
                  label,
                  toolName,
                  status,
                  workspace,
                  documentPath,
                  streamContent: '',
                  isStreaming: false,
                  error: status === 'error' ? (msg.error || 'Task failed') : (msg.error || null),
                  errorType,
                };
              }
              // Mirror the live task_status:'starting' task_ref message shape so
              // TaskCard renders this restored ref identically to a live one.
              // Also carry error+errorType so a chip tooltip works after reload.
              return {
                id: msg.id || `task-ref-${taskId || i}`,
                role: 'task_ref',
                taskId,
                label,
                status,
                timestamp: msg.timestamp,
                turnNumber: persistedTurn,
                roundIndex,
                roundNumber: roundIndex,
                ...(msg.error != null ? { error: msg.error } : {}),
                ...(errorType != null ? { errorType } : {}),
              };
            }

            // PRESERVE persisted dashboard_ref markers BEFORE the generic role
            // coercion, so they re-hydrate as DashboardCards AND repopulate the
            // dashboards map for the Sidebar subtabs / DashboardPanel. Accept
            // camel + snake field names (matches task_ref handling). There is NO
            // separate dashboards payload — the subtabs rehydrate from history.
            if (msg.role === 'dashboard_ref') {
              const hubId = msg.hubId != null ? msg.hubId : msg.hub_id;
              const label = msg.label || 'Dashboard';
              const icon = msg.icon || '';
              const status = msg.status || 'open';
              const manifest = msg.manifest != null ? msg.manifest : null;
              const seed = msg.seed != null ? msg.seed : (msg.seed_state != null ? msg.seed_state : {});
              if (hubId != null) {
                dashboardsAcc[hubId] = {
                  hubId,
                  manifest,
                  seed: seed || {},
                  status,
                  wsEvents$: getOrCreateBus(hubId),
                };
              }
              return {
                id: msg.id || `dashboard-ref-${hubId || i}`,
                role: 'dashboard_ref',
                hubId,
                label,
                icon,
                status,
                timestamp: msg.timestamp,
                turnNumber: persistedTurn,
                roundIndex,
                roundNumber: roundIndex,
              };
            }

            // PRESERVE persisted widget_response cards BEFORE the generic role
            // coercion, so they re-hydrate as cards (not blank agent bubbles).
            if (msg.role === 'widget_response') {
              const im = msg.inputMode || msg.input_mode || null;
              return {
                id: msg.id || `loaded-${i}`,
                role: 'widget_response',
                widgetType: msg.widgetType || msg.widget_type || _resolveWidgetType({ inputMode: im }),
                prompt: msg.prompt || '',
                response: msg.response,
                inputMode: im,
                viewPath: msg.viewPath != null ? msg.viewPath : (msg.view_path != null ? msg.view_path : null),
                viewLabel: msg.viewLabel || msg.view_label || 'View Document',
                viewType: msg.viewType || msg.view_type || 'file',
                timestamp: msg.timestamp,
                turnNumber: persistedTurn,
                roundIndex,
                roundNumber: roundIndex,
              };
            }

            const isManager = msg.role === 'manager';
            const base = {
              id: msg.id || `loaded-${i}`,
              role: isManager ? 'manager' : 'agent',
              content: msg.content,
              timestamp: msg.timestamp,
              agent_name: msg.agent_name,
              // key/turn off the persisted turn_number (server-stamped); welcome
              // message is turn_number 0 and stays 0 here.
              turnNumber: persistedTurn,
              roundIndex,
              roundNumber: roundIndex,
            };
            // For agent messages, parse out thinking vs response content
            if (msg.role === 'assistant' || msg.role === 'agent') {
              const { phase, thinkingContent, responseContent } = parseResponseTags(msg.content);
              const sessionContext = parseSessionContext(msg.content);
              if (phase === 'post_response' || phase === 'in_response') {
                // Clean the display content — show only the response portion
                let cleaned = stripResponseTags(responseContent);
                cleaned = stripSessionContext(cleaned);
                cleaned = stripAnsi(cleaned);
                cleaned = stripAcliNoise(cleaned);
                base.content = cleaned;
                base.thinkingContent = thinkingContent;
                base.responsePhase = phase;
              } else if (phase === 'pre_response') {
                // No <Response> tag — still clean up noise
                base.content = stripSessionContext(stripAnsi(stripAcliNoise(msg.content)));
                base.responsePhase = 'no_tags';
              }
              if (sessionContext) {
                base.sessionContext = sessionContext;
              }
            }
            return base;
          }).filter(Boolean));
          // Sync turnCountRef so live messages continue from the right turn number
          // (next user turn = maxTurn + 1). Welcome (turn 0) doesn't bump this.
          turnCountRef.current = maxTurn;
        }
        // Rebuild the tasks map from the accumulated task_ref messages (replaces
        // the old setTasks({})). Restored tabs render identically to live ones.
        setTasks(tasksAcc);
        // Rebuild the dashboards map from accumulated dashboard_ref markers.
        // Drop buses for hubs that no longer exist after this (re)load so a
        // resume that discarded a hub doesn't keep a dangling stream.
        dashboardBusesRef.current = Object.keys(dashboardsAcc).reduce((acc, hubId) => {
          acc[hubId] = dashboardsAcc[hubId].wsEvents$;
          return acc;
        }, {});
        setDashboards(dashboardsAcc);
        // session_init (initial load, reconnect, or post-resume/restore re-send)
        // can change the sidebar's session rows/counts — refresh the list.
        setSessionsRefreshTick((n) => n + 1);
        // No client-side resume replay here. After resume_from_turn the server
        // keeps the clicked turn (this session_init already renders it) AND
        // re-runs it server-side, streaming the result — replaying it here would
        // double-run the turn.
        break;
      }

      case 'heartbeat':
      case 'pong':
        break;

      default:
        console.log('Unknown WS message type:', data.type);
    }
  }, []);

  const fetchTurnData = useCallback(async (sid, turnNum, round = null) => {
    try {
      // r13 round-aware: when a round index is known, hit ?round=<m> so the
      // server returns that round's prompt data (turn_NNN/round_MMM) instead of
      // the turn root summary.
      const qs = round != null ? `?round=${encodeURIComponent(round)}` : '';
      const res = await fetch(`/api/sessions/${sid}/turns/${turnNum}${qs}`);
      if (!res.ok) return null;
      const json = await res.json();
      return json.data || null;
    } catch (e) {
      console.warn('Failed to fetch turn data:', e);
      return null;
    }
  }, []);

  const sendMessage = useCallback((text) => {
    if (!text.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    // Stable id shared by the optimistic bubble AND the persisted message (the
    // server reuses message_id), so "resume from this turn" can target a turn
    // sent in the current session without waiting for a session_init reload.
    const messageId = `msg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    setMessages(prev => [...prev, {
      id: messageId,
      role: 'manager',
      content: text,
      timestamp: new Date().toISOString(),
    }]);
    wsRef.current.send(JSON.stringify({ type: 'message', content: text, message_id: messageId }));
  }, []);

  // Arm the resume-in-progress UI lock: set the flag + a safety timeout so a lost
  // session_init / status frame can't strand the banner + input-lock forever.
  // Shared by resumeFromTurn and resumeFromRound.
  const armResumeTimeout = useCallback(() => {
    if (resumeTimeoutRef.current) clearTimeout(resumeTimeoutRef.current);
    setIsResuming(true);
    setResumeStage(null);
    resumeTimeoutRef.current = setTimeout(() => {
      resumeTimeoutRef.current = null;
      setIsResuming(false);
      setResumeStage(null);
      setMessages((prev) => [...prev, {
        id: `resume-timeout-${Date.now()}`,
        role: 'error',
        content: 'Resume timed out waiting for the server. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    }, 30000);
  }, []);

  // Resume the conversation from a chosen human turn. The server truncates
  // history AFTER message_id (keeping that turn), restores the pre-turn SOP
  // state, re-sends a session_init frame, and re-runs the kept turn server-side.
  // The client just sends the request — no text stashing / replay.
  // drop_tasks=true also discards any task subtabs/artifacts created after it.
  const resumeFromTurn = useCallback((messageId, dropTasks) => {
    if (!messageId || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    armResumeTimeout();
    wsRef.current.send(JSON.stringify({
      type: 'resume_from_turn',
      message_id: messageId,
      drop_tasks: !!dropTasks,
    }));
  }, [armResumeTimeout]);

  // Resume from a chosen ASSISTANT round (regenerate that round onward). The
  // server rewinds to the round, checkpoints, truncates, re-sends session_init,
  // and auto-forwards the loop (NO user re-injection). drop_tasks discards tasks
  // created at/after that round; otherwise they are kept + reused on re-dispatch.
  const resumeFromRound = useCallback((messageId, dropTasks) => {
    if (!messageId || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    armResumeTimeout();
    wsRef.current.send(JSON.stringify({
      type: 'resume_from_round',
      message_id: messageId,
      drop_tasks: !!dropTasks,
    }));
  }, [armResumeTimeout]);

  // Fetch the list of restorable checkpoints for a session (newest first).
  // fetchJson already unwraps a top-level {data:…} envelope, so the GET
  // /sessions/{id}/checkpoints → {data:[…]} response comes back as the array
  // directly; tolerate both the unwrapped array and a {data} object defensively.
  const fetchCheckpoints = useCallback(async (sid) => {
    if (!sid) return [];
    try {
      const result = await fetchJson(`/sessions/${sid}/checkpoints`);
      if (Array.isArray(result)) return result;
      return result?.data || [];
    } catch (e) {
      console.warn('Failed to fetch checkpoints:', e);
      return [];
    }
  }, []);

  // Restore a named checkpoint. The server rolls session state back and re-sends
  // a session_init frame (truncated messages + rebuilt tasks); no replay here.
  const restoreCheckpoint = useCallback((name) => {
    if (!name || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: 'restore_checkpoint', checkpoint: name }));
  }, []);

  // Switch between the session conversation, a task panel, and a dashboard
  // subtab. Signature is switchTab(tabId, tabType) — id FIRST (kept from the
  // task triad; the dashboard branch follows the same order). Only one of
  // activeTaskId / activeDashboardId is non-null at a time. The active tab is
  // persisted per session so a reload reopens the same surface.
  const switchTab = useCallback((tabId, tabType) => {
    const type = tabType || 'session';
    setActiveTabType(type);
    setActiveTaskId(type === 'task' ? tabId : null);
    setActiveDashboardId(type === 'dashboard' ? tabId : null);
    saveActiveTab(sessionId, type, tabType === 'task' || tabType === 'dashboard' ? tabId : null);
  }, [sessionId]);

  const sendPendingInputResponse = useCallback((response) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[PendingInput] WebSocket not open — cannot send response');
      return;
    }
    // Double-submit guard — prevents two widget_response messages on rapid clicks
    if (submittedRef.current) return;
    submittedRef.current = true;

    // Insert committed widget_response message into history (RankEvolve: ADD_WIDGET_MESSAGE).
    // This persists the user's choice visually after the widget unmounts.
    const currentPending = pendingInputRef.current;
    // pending_input_id is the stable server-minted id for this widget round.
    // r13: the optimistic widget_response card keys off it (NOT Date.now()) so a
    // later session_init reload re-hydrates the SAME card id, and the response
    // echoes it back so the server can look up its pending_input_cache entry.
    const _pendingInputId = currentPending?.pendingInputId || null;
    if (currentPending) {
      const _widgetType = _resolveWidgetType(currentPending);
      const _viewPath = currentPending.inputMode?.metadata?.view || null;
      const _viewLabel = currentPending.inputMode?.metadata?.view_label || 'View Document';
      const _viewType = currentPending.inputMode?.metadata?.view_type || 'file';
      console.debug('[sendPendingInputResponse] widgetType:', _widgetType,
        'pendingInputId:', _pendingInputId, 'viewPath:', _viewPath, 'viewType:', _viewType,
        'response:', typeof response === 'string' ? response : JSON.stringify(response).slice(0, 100));
      setMessages(prev => [...prev, {
        id: _pendingInputId || `widget-resp-${Date.now()}`,
        role: 'widget_response',
        widgetType: _widgetType,
        prompt: currentPending.inputMode?.prompt || currentPending.content || '',
        response,
        inputMode: currentPending.inputMode,
        viewPath: _viewPath,
        viewLabel: _viewLabel,
        viewType: _viewType,
        timestamp: new Date().toISOString(),
        turnNumber: currentPending.turnNumber != null ? currentPending.turnNumber : (turnCountRef.current || 0) + 1,
        roundIndex: currentPending.roundIndex != null ? currentPending.roundIndex : null,
        roundNumber: currentPending.roundIndex != null ? currentPending.roundIndex : null,
      }]);
    }

    // Clear pendingInput immediately (RankEvolve: CLEAR_PENDING_INPUT).
    // widget_response message above preserves the user's choice in history.
    // Immediate clear re-enables chat input and puts widget_response above AI streaming.
    setPendingInput(null);
    pendingInputRef.current = null;

    // Send to server. Echo pending_input_id so the server can look up its
    // pending_input_cache entry and persist the widget_response history message
    // (r13). For a CONVERSATION pending input (pendingInputId present) do NOT
    // attach the global currentTaskIdRef — that routes to the per-task input
    // queue and is only for the dev-tool/task widget path (manager_websocket
    // R9b). A dev-tool widget has no pendingInputId, so it still routes by task.
    const content = typeof response === 'string' ? response : JSON.stringify(response);
    const payload = { type: 'pending_input_response', content };
    if (_pendingInputId) {
      payload.pending_input_id = _pendingInputId;
    } else if (currentTaskIdRef.current) {
      payload.task_id = currentTaskIdRef.current;
    }
    wsRef.current.send(JSON.stringify(payload));
  }, []);

  const cancelRequest = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Include task_id so the dispatcher cancels the matching dev-tool task
      // (manager_websocket_routes Patch 3.4); omitted falls through to
      // active_task cancel (existing behavior).
      const payload = { type: 'cancel' };
      if (currentTaskIdRef.current) payload.task_id = currentTaskIdRef.current;
      wsRef.current.send(JSON.stringify(payload));
    }
    setPendingInput(null);
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setStreamingMessage(null);
    setIsStreaming(false);
  }, []);

  // Emit a `hub_command` frame over the EXISTING manager socket. This is the
  // transport for the dashboard's three long-running actions
  // (implement_hypothesis / resume_implement_task / run_experiment_combos) —
  // the server streams progress back as `dashboard_event`s into the hub bus.
  // Passed to useHubApiClient so the WS send stays inside the one socket.
  const sendHubCommand = useCallback((command, payload = {}) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[useManagerChat] hub_command dropped — socket not open:', command);
      return;
    }
    wsRef.current.send(JSON.stringify({ type: 'hub_command', command, ...payload }));
  }, []);

  // R1 — chat "Go To Experiment Hub" handoff. Sends a NET-NEW `open_dashboard`
  // frame that OPENS + SEEDS the Experiment Hub subtab out-of-turn (server
  // builds the hub controller, seeds proposals from
  // phase_outputs.research_propose__proposals_path, auto_implement=False, and
  // emits the one-shot `dashboard_open` that `case 'dashboard_open'` renders).
  // CRITICAL: this does NOT call sendPendingInputResponse — the Phase-2b pending
  // input stays LIVE (the SOP holds at 2b); the in-hub confirm advances it later.
  const openDashboardFromWidget = useCallback((payload) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[useManagerChat] open_dashboard dropped — socket not open');
      return;
    }
    const p = payload || {};
    wsRef.current.send(JSON.stringify({
      type: 'open_dashboard',
      dashboard_id: 'experiment_hub',
      selected_ids: Array.isArray(p.selected_proposals) ? p.selected_proposals : [],
    }));
  }, []);

  // v4 Phase 4.1 — ask the server to re-emit the snapshot for a task (or
  // every task in the session when ``taskId`` is omitted). Used by TaskPanel
  // when the user drills into a node whose sub-graph isn't loaded yet —
  // a defensive backup to the session_init replay, covering HMR / focus
  // shifts that race the initial hydrate.
  const requestGraphReplay = useCallback((taskId) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const payload = { type: 'request_graph_replay' };
    if (taskId) payload.task_id = taskId;
    wsRef.current.send(JSON.stringify(payload));
  }, []);

  // Bundle requestGraphReplay onto the graphState reference so consumers
  // (TaskPanel, NodeDetailPanel) only need a single prop. Memoized so a
  // stable identity flows through React.memo / hook deps.
  const graphStateWithReplay = useMemo(
    () => graphState ? { ...graphState, requestGraphReplay } : graphState,
    [graphState, requestGraphReplay],
  );

  // Defensive viewPath fallback: when the LLM emits a `confirmation` widget
  // WITHOUT `metadata.view` (it sometimes drops the field even though the
  // auto-advance instruction explicitly tells it to set it), augment the
  // outgoing pendingInput with the document path from the most recent
  // task-completed system notification still present in `messages`. This
  // guarantees the "View Documentation" button appears whenever the chat
  // history records a Generated document — independent of LLM compliance,
  // and works retroactively across hot-reload because messages survives.
  const augmentedPendingInput = useMemo(() => {
    if (!pendingInput) return pendingInput;
    const mode = pendingInput.inputMode;
    if (!mode || typeof mode !== 'object') return pendingInput;
    const meta = (mode.metadata && typeof mode.metadata === 'object') ? mode.metadata : {};
    if (meta.view) return pendingInput;  // LLM already set it — no fallback needed
    // Scan messages backwards for the most recent system-notification
    // emitted by task_completed; extract `Generated document: <path>.`
    let fallbackPath = null;
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m && m.role === 'manager' && typeof m.content === 'string'
          && m.content.startsWith('[System notification:')
          && m.content.includes('Generated document:')) {
        const match = m.content.match(/Generated document:\s*(\S+?)\.\s/);
        if (match && match[1]) {
          fallbackPath = match[1];
          break;
        }
      }
    }
    if (!fallbackPath) return pendingInput;
    return {
      ...pendingInput,
      inputMode: {
        ...mode,
        metadata: {
          ...meta,
          view: fallbackPath,
          view_label: meta.view_label || 'View Documentation',
        },
      },
    };
  }, [pendingInput, messages]);

  // Connect on mount, reconnect if sessionId changes
  useEffect(() => {
    if (!sessionId) return;
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect, sessionId]);

  return {
    messages,
    streamingMessage,
    isStreaming,
    connectionStatus,
    sendMessage,
    cancelRequest,
    clearMessages,
    fetchTurnData,
    pendingInput: augmentedPendingInput,
    sendPendingInputResponse,
    isConnected: connectionStatus === 'connected',
    // Session resumability (resume from a human turn or an assistant round +
    // checkpoint restore) plus the non-blocking resume-in-progress UI lock.
    resumeFromTurn,
    resumeFromRound,
    isResuming,
    resumeStage,
    fetchCheckpoints,
    restoreCheckpoint,
    // Sidebar freshness — bumps on connect / session_init / turn end / task_status
    sessionsRefreshTick,
    // Task subtab state
    tasks,
    activeTabType,
    activeTaskId,
    switchTab,
    // Dashboard subtab state (mirror of the task triad, keyed by hubId).
    dashboards,
    activeDashboardId,
    // WS transport for the dashboard's long-running hub_command actions.
    sendHubCommand,
    // R1 — chat "Go To Experiment Hub" open+seed handoff (no pending-input resolve).
    openDashboardFromWidget,
    // Graph visualization state (sub-graphs, drill-down, navigation)
    // Wrapped to include requestGraphReplay for on-demand snapshot hydrate.
    graphState: graphStateWithReplay,
  };
}

export default useManagerChat;
