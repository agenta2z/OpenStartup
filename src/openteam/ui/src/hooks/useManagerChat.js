/**
 * useManagerChat — WebSocket-based hook for Manager ↔ AI streaming chat.
 *
 * Adapted from rankevolve's useAgentChat.js.
 * Manages connection to /ws/manager, token streaming, auto-reconnect.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
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

const WS_RECONNECT_BASE_MS = 1000;
const WS_RECONNECT_MAX_MS = 30000;

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
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [pendingInput, setPendingInput] = useState(null);
  // Task subtab state
  const [tasks, setTasks] = useState({});
  const [activeTabType, setActiveTabType] = useState('session');
  const [activeTaskId, setActiveTaskId] = useState(null);

  // Graph visualization state (sub-graphs, drill-down, batching)
  const graphState = useGraphState(setTasks);

  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
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
      // Send init with session_id so server can resume correct conversation
      ws.send(JSON.stringify({ type: 'init', session_id: sessionId }));
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      setConnectionStatus('error');
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

  const handleServerMessage = useCallback((data) => {
    switch (data.type) {
      case 'task_status': {
        const { task_id, status, request, tool_name, error: taskError } = data;
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
          setTasks(prev => ({
            ...prev,
            [task_id]: {
              id: task_id, label, toolName: tool_name,
              status: 'starting', streamContent: '', isStreaming: false, error: null,
            },
          }));
          setMessages(prev => [...prev, {
            id: `task-ref-${task_id}`, role: 'task_ref',
            taskId: task_id, label, status: 'starting',
            timestamp: new Date().toISOString(),
          }]);
        } else {
          setTasks(prev => prev[task_id]
            ? { ...prev, [task_id]: { ...prev[task_id], status, error: taskError || null } }
            : prev
          );
          setMessages(prev => prev.map(msg =>
            msg.role === 'task_ref' && msg.taskId === task_id ? { ...msg, status } : msg
          ));
        }
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
        const { task_id: cTaskId, tool_name: cToolName, result_summary, workspace, document_path } = data;
        // Auto-advance: send a new WS message to trigger next conversation turn
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const parts = [
            `[System notification: Task '${cToolName || cTaskId}' (${cTaskId}) completed successfully.`,
            workspace ? `Workspace: ${workspace}.` : '',
            document_path ? `Generated document: ${document_path}.` : '',
            result_summary ? `Summary: ${result_summary.slice(0, 300)}.` : '',
            `CRITICAL: Present 3-5 bullet points summarizing the key aspects of the document, then`,
            `you MUST respond with a "confirmation" conversation tool (NOT "clarification" or "free_text").`,
            document_path
              ? `Set metadata.view to "${document_path}", metadata.view_label to "View Role Document",`
                + ` metadata.yes_label to "✅ Approve & Proceed", metadata.no_label to "❌ Request Changes".`
              : `Set metadata.yes_label to "✅ Approve & Proceed", metadata.no_label to "❌ Request Changes".`,
            `Example ToolsToInvoke block:`,
            '```json ToolsToInvoke',
            JSON.stringify({
              type: 'conversation',
              name: 'confirmation',
              arguments: {
                prompt: 'Review and approve the role document to proceed to Phase 2?',
                metadata: {
                  view: document_path || '',
                  view_label: 'View Role Document',
                  yes_label: '✅ Approve & Proceed',
                  no_label: '❌ Request Changes',
                },
              },
            }),
            '```]',
          ].filter(Boolean).join(' ');
          wsRef.current.send(JSON.stringify({ type: 'message', content: parts, is_auto_advance: true }));
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
        }
        break;

      case 'pending_input': {
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
        }
        break;

      case 'session_init':
        setPendingInput(null);
        pendingInputRef.current = null;
        submittedRef.current = false;
        setIsStreaming(false);
        setStreamingMessage(null);
        setTasks({});
        setActiveTabType('session');
        setActiveTaskId(null);
        // Reset per-round bubble lifecycle state for the (re)loaded session.
        streamingContentRef.current = '';
        streamingMetadataRef.current = {};
        currentRoundIdRef.current = null;
        currentRoundIndexRef.current = null;
        committedRoundIdsRef.current = new Set();
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
        break;

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
    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'manager',
      content: text,
      timestamp: new Date().toISOString(),
    }]);
    wsRef.current.send(JSON.stringify({ type: 'message', content: text }));
  }, []);

  // Switch between session conversation and a task panel
  const switchTab = useCallback((tabId, tabType) => {
    setActiveTabType(tabType || 'session');
    setActiveTaskId(tabType === 'task' ? tabId : null);
  }, []);

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

  // Connect on mount, reconnect if sessionId changes
  useEffect(() => {
    if (!sessionId) return;
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
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
    pendingInput,
    sendPendingInputResponse,
    isConnected: connectionStatus === 'connected',
    // Task subtab state
    tasks,
    activeTabType,
    activeTaskId,
    switchTab,
    // Graph visualization state (sub-graphs, drill-down, navigation)
    graphState,
  };
}

export default useManagerChat;
