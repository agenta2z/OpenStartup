/**
 * ManagerChatView — Phase 2: WebSocket streaming chat with AI team.
 *
 * Displays the selected Manager Session as a streaming chat interface with:
 * - Real-time token streaming from WebSocket
 * - Blinking cursor during streaming
 * - "Thinking..." indicator
 * - Agent metadata badges
 * - Cancel button for in-flight requests
 * - Connection status display
 * - Markdown rendering with syntax highlighting
 *
 * Adapted from rankevolve's AgentChatPanel pattern.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemText from '@mui/material/ListItemText';
import Tooltip from '@mui/material/Tooltip';
import { useTheme } from '@mui/material/styles';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PersonIcon from '@mui/icons-material/Person';
import HistoryIcon from '@mui/icons-material/History';
import RestoreIcon from '@mui/icons-material/Restore';
import { useApiData } from '../../hooks/useApiData';
import { useServerStatus } from '../../hooks/useServerStatus';
import { useManagerChat } from '../../hooks/useManagerChat';
import { usePromptViewer } from '../../hooks/usePromptViewer';
import { LoadingIndicator } from '../../shared';
import { DashboardPanel } from '@agent-foundation/shared-ui';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { StreamingMessage } from '../chat/StreamingMessage';
import { ChatInput } from '../chat/ChatInput';
import { AgentMessageBubble } from '../chat/AgentMessageBubble';
import { PromptViewerDrawer } from '../chat/PromptViewerDrawer';
import ConversationToolWidget from '../chat-widgets/ConversationToolWidget';
import { useFileViewer } from '../../hooks/useFileViewer';
import { FileViewer } from '../layout/FileViewer';
import ConnectionStatusBar from '../layout/ConnectionStatusBar';
import { TaskCard } from '../chat/TaskCard';
import { DashboardCard } from '../chat/DashboardCard';
import { TaskPanel } from '../chat/TaskPanel';
import { BackendSelector } from '../chat/BackendSelector';
import { useHubApiClient } from '../../hooks/useHubApiClient';
import { useUiPreferences } from '../../preferences/UiPreferencesProvider';


/**
 * Resolve a human label for a compound child output_var from the widget's
 * tools config (input_mode.metadata.tools[].output_var → prompt/tool_type).
 * Falls back to the raw key when no matching tool is found.
 */
function _compoundChildLabel(message, outputVar) {
  const md = message.inputMode?.metadata || message.inputMode?.input_mode?.metadata || {};
  const tools = md.tools || message.inputMode?.tools || [];
  const tool = tools.find((t) => (t.output_var || t.tool_type) === outputVar);
  const prompt = tool?.prompt || tool?.input_mode?.prompt || '';
  if (prompt) return prompt.length > 40 ? prompt.slice(0, 40) + '…' : prompt;
  return outputVar;
}

/**
 * Render one compound child's raw response as a readable value. `tool` (the
 * matching input_mode tool) lets us resolve a choice_index to its option label
 * (e.g. "Auto discover") instead of a bare "Option 1".
 */
function _compoundChildValue(childResponse, tool) {
  if (childResponse == null) return '';
  if (typeof childResponse === 'string') return childResponse;
  const opts = tool?.input_mode?.options || tool?.options || [];
  if (childResponse.content != null) {
    return Array.isArray(childResponse.content)
      ? childResponse.content.join(', ')
      : String(childResponse.content);
  }
  if (childResponse.custom_text) return childResponse.custom_text;
  if (childResponse.choice_index != null) {
    const label = opts[childResponse.choice_index]?.label || `Option ${childResponse.choice_index + 1}`;
    // A composite choice (e.g. "Specify paths") also carries a nested input value.
    const inputVals = childResponse.inputs && typeof childResponse.inputs === 'object'
      ? Object.values(childResponse.inputs).flat().filter(Boolean).join(', ')
      : '';
    return inputVals ? `${label}: ${inputVals}` : label;
  }
  if (childResponse.choice != null) return String(childResponse.choice);
  if (Array.isArray(childResponse.selections)) {
    return childResponse.selections
      .map((s) => s.custom_text || opts[s.choice_index]?.label || `Option ${(s.choice_index ?? 0) + 1}`)
      .join(', ');
  }
  return JSON.stringify(childResponse);
}

/**
 * Detect a compound DIRECT MAP response: a plain object whose keys are
 * output_vars mapping directly to each child's raw response — i.e. NOT one of
 * the known single-widget / envelope shapes (content/choice/selections/values/
 * submitted_child). Used to format the committed card per-tab instead of dumping
 * raw JSON.
 */
function _isCompoundDirectMap(response) {
  if (!response || typeof response !== 'object' || Array.isArray(response)) return false;
  const envelopeKeys = ['content', 'choice', 'choice_index', 'selections',
    'custom_text', 'values', 'submitted_child', 'payload'];
  if (envelopeKeys.some((k) => k in response)) return false;
  const keys = Object.keys(response).filter((k) => k !== 'variable_override');
  return keys.length > 0;
}

/**
 * Normalize a committed widget response. The compound widget commits a
 * JSON-stringified object; parse it so per-tab rendering (summary card OR
 * read-only widget) works. Non-compound widgets and backend-reloaded responses
 * are already objects; non-JSON strings (e.g. a confirmation 'yes') pass through.
 */
function normalizeWidgetResponse(response) {
  if (typeof response === 'string') {
    const trimmed = response.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try { return JSON.parse(response); } catch { /* keep original string */ }
    }
  }
  return response;
}

/**
 * CommittedWidgetMessage — text-summary record of a user's widget submission.
 * Rendered in message history after pendingInput is cleared (RankEvolve: widget_response role).
 */
function CommittedWidgetMessage({ message, onView, onViewFolder }) {
  const theme = useTheme();
  const { widgetType, prompt } = message;
  const response = normalizeWidgetResponse(message.response);

  console.debug('[CommittedWidgetMessage] widgetType:', widgetType, 'viewPath:', message.viewPath, 'response:', response);

  const containerSx = {
    px: 2, py: 1.5, borderRadius: 2,
    border: '1px solid',
    borderColor: theme.custom?.surfaces?.cardBorder || 'rgba(255,255,255,0.1)',
    backgroundColor: theme.custom?.surfaces?.overlayLight || 'rgba(255,255,255,0.03)',
    maxWidth: theme.custom?.layout?.widgetMaxWidth || '75%',
  };

  // Confirmation with View button (matches RankEvolve post-task review pattern)
  if (widgetType === 'confirmation') {
    const isApproved = response === 'yes' || response?.choice === 'yes';
    const viewPath = message.viewPath;
    const viewLabel = message.viewLabel || 'View Document';
    const viewType = message.viewType || 'file';

    const handleView = () => {
      if (viewType === 'folder' && onViewFolder) {
        onViewFolder(viewPath);
      } else if (onView) {
        onView(viewPath);
      }
    };

    return (
      <Box sx={containerSx}>
        {prompt && (
          <Typography variant="body2" sx={{ color: 'text.primary', mb: 1 }}>
            {prompt}
          </Typography>
        )}
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          {viewPath && (onView || onViewFolder) && (
            <Button variant="outlined" size="small"
              onClick={handleView}
              sx={{
                textTransform: 'none', fontSize: '0.85rem',
                borderColor: 'rgba(74,144,217,0.4)', color: 'primary.main',
                '&:hover': { borderColor: 'primary.main', backgroundColor: 'rgba(74,144,217,0.08)' },
              }}>
              {viewType === 'folder' ? '📁' : '📄'} {viewLabel}
            </Button>
          )}
          <Button variant="contained" size="small" disabled
            sx={{
              textTransform: 'none', fontSize: '0.85rem',
              '&.Mui-disabled': {
                backgroundColor: isApproved ? 'rgba(46,125,50,0.3)' : 'rgba(244,67,54,0.3)',
                color: 'rgba(255,255,255,0.7)',
              },
            }}>
            {isApproved ? '✅ Approved' : '❌ Declined'}
          </Button>
        </Box>
      </Box>
    );
  }

  // Compound DIRECT MAP {output_var: rawChildResponse} — format per-tab
  // (label/value) instead of raw JSON.stringify. Item 9: the round preamble is
  // its own committed bubble now, so this card renders ONLY the per-tab values
  // (no prompt preamble re-render).
  if (_isCompoundDirectMap(response)) {
    const md = message.inputMode?.metadata || message.inputMode?.input_mode?.metadata || {};
    const tools = md.tools || message.inputMode?.tools || [];
    const entries = Object.keys(response)
      .filter((k) => k !== 'variable_override')
      .map((k) => {
        const tool = tools.find((t) => (t.output_var || t.tool_type) === k);
        return { key: k, label: _compoundChildLabel(message, k), value: _compoundChildValue(response[k], tool) };
      });
    return (
      <Box sx={containerSx}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {entries.map((e) => (
            <Box key={e.key}>
              <Typography variant="caption" sx={{ color: 'text.disabled', display: 'block' }}>
                {e.label}
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500 }}>
                {e.value || '—'}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    );
  }

  // Other widget types
  let statusText = '';
  let statusColor = 'text.secondary';

  if (widgetType === 'single_choice') {
    const opts = message.inputMode?.options || [];
    const idx = response?.choice_index;
    const label = idx != null
      ? (opts[idx]?.label || `Option ${idx + 1}`)
      : (response?.custom_text || JSON.stringify(response));
    statusText = `Selected: ${label}`;
    statusColor = 'primary.main';
  } else if (widgetType === 'multiple_choice' || widgetType === 'multiple_choices') {
    const opts = message.inputMode?.options || [];
    const sels = response?.selections || [];
    const labels = sels.map(s =>
      s.custom_text || opts[s.choice_index]?.label || `Option ${s.choice_index + 1}`
    );
    statusText = labels.length > 0 ? `Selected: ${labels.join(', ')}` : 'Submitted';
    statusColor = 'primary.main';
  } else {
    const text = response?.content || (typeof response === 'string' ? response : JSON.stringify(response));
    statusText = text ? `"${text}"` : 'Submitted';
    statusColor = 'text.primary';
  }

  return (
    <Box sx={containerSx}>
      {prompt && (
        <Typography variant="caption" sx={{ color: 'text.disabled', display: 'block', mb: 0.5 }}>
          {prompt.length > 80 ? prompt.slice(0, 80) + '…' : prompt}
        </Typography>
      )}
      <Typography variant="body2" sx={{ color: statusColor, fontWeight: 500 }}>
        {statusText}
      </Typography>
    </Box>
  );
}

/**
 * ReadOnlyCommittedWidget — the ORIGINAL conversation widget, frozen & disabled,
 * still showing the user's submitted values (the "interactive" committed mode,
 * vs. CommittedWidgetMessage's text-summary mode). Reconstructed from the
 * widget_response message's inputMode + response.
 */
function ReadOnlyCommittedWidget({ message, onView, onViewFolder }) {
  const responseValues = normalizeWidgetResponse(message.response);
  const pendingLike = { inputMode: message.inputMode, content: message.prompt };
  return (
    <ConversationToolWidget
      pendingInput={pendingLike}
      readOnly
      responseValues={responseValues}
      onView={onView}
      onViewFolder={onViewFolder}
      pathAutocompleteProvider={pathAutocompleteProvider}
    />
  );
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}


function ManagerMessage({ message, onResumeFromTurn, disabled }) {
  // The Avatar doubles as a "resume from this turn" menu anchor. Only real human
  // turns render this bubble (the messages.map hides auto-advance manager msgs),
  // so the menu is always a valid resume point. Disabled while a turn streams.
  const [anchorEl, setAnchorEl] = useState(null);
  const menuOpen = Boolean(anchorEl);
  const canResume = Boolean(onResumeFromTurn) && !disabled;
  const handleOpen = (e) => { if (canResume) setAnchorEl(e.currentTarget); };
  const handleClose = () => setAnchorEl(null);
  const handleResume = (dropTasks) => {
    handleClose();
    onResumeFromTurn?.(message, dropTasks);
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
      <Box sx={{ maxWidth: '70%', display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
        <Box
          sx={{
            backgroundColor: 'primary.dark',
            color: 'white',
            px: 2,
            py: 1.5,
            borderRadius: '16px 16px 4px 16px',
            lineHeight: 1.5,
            fontSize: '0.9rem',
            '& p': { m: 0 },
            '& pre': { overflow: 'auto' },
          }}
        >
          <MarkdownRenderer content={message.content} />
        </Box>
        <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, mr: 0.5 }}>
          {formatTime(message.timestamp)}
        </Typography>
      </Box>
      <Tooltip title={canResume ? 'Resume conversation from this turn' : ''} placement="left">
        <Avatar
          onClick={handleOpen}
          sx={{
            ml: 1, width: 32, height: 32, bgcolor: 'primary.main', flexShrink: 0,
            cursor: canResume ? 'pointer' : 'default',
            transition: 'box-shadow 0.15s',
            '&:hover': canResume ? { boxShadow: '0 0 0 2px rgba(74,144,217,0.5)' } : undefined,
          }}
        >
          <PersonIcon sx={{ fontSize: 18 }} />
        </Avatar>
      </Tooltip>
      <Menu anchorEl={anchorEl} open={menuOpen} onClose={handleClose}>
        <MenuItem onClick={() => handleResume(false)}>
          Resume from this turn (keep tasks)
        </MenuItem>
        <MenuItem onClick={() => handleResume(true)}>
          Resume from this turn (also drop tasks)
        </MenuItem>
      </Menu>
    </Box>
  );
}




function ErrorMessage({ message }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
      <Box
        sx={{
          px: 2,
          py: 1,
          borderRadius: 2,
          backgroundColor: 'rgba(255, 50, 50, 0.1)',
          border: '1px solid rgba(255, 50, 50, 0.3)',
          maxWidth: '80%',
        }}
      >
        <Typography variant="body2" sx={{ color: 'error.main', fontSize: '0.85rem' }}>
          ⚠️ {message.content}
        </Typography>
      </Box>
    </Box>
  );
}


/**
 * Connection status indicator
 */
function WsStatusBadge({ status }) {
  const config = {
    connected: { color: '#4caf50', label: 'Connected' },
    connecting: { color: '#ff9800', label: 'Connecting...' },
    disconnected: { color: '#f44336', label: 'Disconnected' },
    error: { color: '#f44336', label: 'Error' },
  }[status] || { color: '#9e9e9e', label: status };

  return (
    <Chip
      size="small"
      label={config.label}
      sx={{
        height: 20,
        fontSize: '0.65rem',
        backgroundColor: `${config.color}22`,
        color: config.color,
        borderColor: config.color,
      }}
      variant="outlined"
    />
  );
}


/**
 * Format a checkpoint's created_at into a compact local timestamp for the menu.
 */
function formatCheckpointTime(createdAt) {
  if (!createdAt) return '';
  const d = new Date(createdAt);
  if (Number.isNaN(d.getTime())) return String(createdAt);
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}


/**
 * CheckpointsMenu — header control to list and restore session checkpoints.
 * Fetches the checkpoint list lazily on open (GET /sessions/{id}/checkpoints,
 * newest first) and restores a chosen one over the WebSocket. Disabled while a
 * turn is streaming so a restore can't race an in-flight response.
 */
function CheckpointsMenu({ sessionId, fetchCheckpoints, restoreCheckpoint, disabled }) {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [loading, setLoading] = useState(false);
  const open = Boolean(anchorEl);

  const handleOpen = useCallback(async (e) => {
    setAnchorEl(e.currentTarget);
    if (!sessionId || !fetchCheckpoints) return;
    setLoading(true);
    try {
      const list = await fetchCheckpoints(sessionId);
      setCheckpoints(Array.isArray(list) ? list : []);
    } finally {
      setLoading(false);
    }
  }, [sessionId, fetchCheckpoints]);

  const handleClose = () => setAnchorEl(null);
  const handleRestore = (name) => {
    handleClose();
    restoreCheckpoint?.(name);
  };

  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center' }}>
      <Tooltip title="Restore a saved checkpoint">
        <span>
          <Chip
            icon={<HistoryIcon sx={{ fontSize: 14 }} />}
            label="Checkpoints"
            size="small"
            variant="outlined"
            onClick={disabled ? undefined : handleOpen}
            disabled={disabled}
            sx={{
              height: 20,
              fontSize: '0.65rem',
              cursor: disabled ? 'default' : 'pointer',
              color: 'text.secondary',
              borderColor: theme.custom?.surfaces?.cardBorder || 'rgba(255,255,255,0.12)',
              '& .MuiChip-icon': { color: 'text.secondary', ml: 0.5 },
            }}
          />
        </span>
      </Tooltip>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose}>
        {loading && (
          <MenuItem disabled>Loading…</MenuItem>
        )}
        {!loading && checkpoints.length === 0 && (
          <MenuItem disabled>No checkpoints</MenuItem>
        )}
        {!loading && checkpoints.map((cp, i) => (
          <MenuItem key={cp.name || i} onClick={() => handleRestore(cp.name)}>
            <RestoreIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <ListItemText
              primary={cp.name}
              secondary={[
                formatCheckpointTime(cp.created_at),
                cp.message_count != null ? `${cp.message_count} msgs` : '',
              ].filter(Boolean).join(' · ')}
              primaryTypographyProps={{ variant: 'body2', sx: { fontSize: '0.8rem' } }}
              secondaryTypographyProps={{ variant: 'caption', sx: { fontSize: '0.65rem' } }}
            />
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
}


/**
 * Host-provided path-autocomplete for conversation-tool path inputs.
 * Calls the OpenStartup workspace route (mounted at /api/workspace/path-complete,
 * which validates the prefix against the session root). Returns [] on any error
 * so the widget degrades gracefully to manual text entry.
 */
async function pathAutocompleteProvider({ prefix, partial = '', dirsOnly = false, limit = 50 }) {
  try {
    const qs = new URLSearchParams({
      prefix: prefix || '',
      partial: partial || '',
      dirs_only: String(!!dirsOnly),
      limit: String(limit),
    });
    const res = await fetch(`/api/workspace/path-complete?${qs.toString()}`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.suggestions) ? data.suggestions : [];
  } catch (e) {
    return [];
  }
}

export default function ManagerChatView({ sessionId, onBack, onTasksChanged, onActiveTaskChanged, onDashboardsChanged, onActiveDashboardChanged, onSwitchTabRef, onSessionsShouldRefresh }) {
  // Load session metadata (title etc.) via REST
  const { data: sessionMeta, loading } = useApiData(
    sessionId ? `/sessions/${sessionId}` : null
  );
  const { status: serverStatus, serverInfo } = useServerStatus();
  const { committedWidgetMode } = useUiPreferences();

  // WebSocket streaming chat
  const {
    messages,
    streamingMessage,
    isStreaming,
    connectionStatus,
    sendMessage,
    cancelRequest,
    fetchTurnData,
    pendingInput,
    sendPendingInputResponse,
    isConnected,
    resumeFromTurn,
    resumeFromRound,
    isResuming,
    resumeStage,
    fetchCheckpoints,
    restoreCheckpoint,
    sessionsRefreshTick,
    tasks,
    activeTabType,
    activeTaskId,
    switchTab,
    graphState,
    dashboards,
    activeDashboardId,
    sendHubCommand,
    openDashboardFromWidget,
  } = useManagerChat(sessionId);

  // HubApiClient for the active dashboard. DashboardPanel is context-free, so
  // this is threaded purely via the `apiClient` prop. The long-running actions
  // ride the existing manager socket through `sendHubCommand`; switchTab focuses
  // the hub subtab. Built unconditionally (hook rules) — only used when a
  // dashboard tab is active.
  const hubApiClient = useHubApiClient({
    sessionId,
    hubId: activeDashboardId,
    sendHubCommand,
    switchTab,
  });

  const promptViewer = usePromptViewer();
  const {
    fileViewerOpen, fileContent, fileName, fileError, fileLoading,
    openFileViewer, closeFileViewer,
    isHtmlFile, htmlFilePath,
    folderTree, isFolderMode, selectedFilePath, openFolderViewer, selectFileInFolder,
  } = useFileViewer();

  // Handler for "View Prompt" — uses inline promptData if available (current session),
  // or fetches from REST API for history messages (after server restart).
  const handleViewPrompt = useCallback(async (message) => {
    console.log('[ViewPrompt] clicked', {
      hasPromptData: Boolean(message.promptData?.rendered_prompt),
      turnNumber: message.turnNumber,
      promptDataKeys: message.promptData ? Object.keys(message.promptData) : [],
      renderedPromptLen: message.promptData?.rendered_prompt?.length || 0,
    });
    if (message.promptData?.rendered_prompt) {
      // Fast path: inline prompt data from message_end
      console.log('[ViewPrompt] opening from inline promptData');
      promptViewer.openPrompt(message.promptData);
    } else if (message.turnNumber && fetchTurnData) {
      // Slow path: fetch from disk (history messages / after server restart).
      // r13: thread the round index so the fetch hits ?round=<m> and resolves
      // the specific round's prompt (turn_NNN/round_MMM), not the turn root.
      const round = message.roundIndex != null ? message.roundIndex
        : (message.roundNumber != null ? message.roundNumber : null);
      console.log('[ViewPrompt] fetching from disk, turnNumber=', message.turnNumber, 'round=', round);
      const data = await fetchTurnData(sessionId, message.turnNumber, round);
      console.log('[ViewPrompt] fetched data:', data ? Object.keys(data) : null);
      // Skip drawer if data is empty (no prompt content to show).
      // The server now returns 200 with note="..." for missing turns instead of 404,
      // so we explicitly check for usable content before opening the drawer.
      const hasContent = data && (data.rendered_prompt || data.template_source);
      if (hasContent) {
        promptViewer.openPrompt(data);
      } else {
        console.info('[ViewPrompt] no prompt data available for this turn');
      }
    } else {
      console.warn('[ViewPrompt] no promptData and no turnNumber — nothing to show');
    }
  }, [promptViewer, fetchTurnData, sessionId]);

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  // Auto-scroll on new messages or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  const handleSubmit = useCallback((e) => {
    e?.preventDefault();
    if (!inputValue.trim() || !isConnected) return;
    sendMessage(inputValue);
    setInputValue('');
  }, [inputValue, isConnected, sendMessage]);

  // Resume the conversation from a chosen human turn (optionally dropping the
  // tasks created after it). The hook truncates history AFTER message.id
  // (keeping that turn); the server re-sends session_init and re-runs the kept
  // turn server-side (no client replay).
  const handleResumeFromTurn = useCallback((message, dropTasks) => {
    resumeFromTurn?.(message.id, dropTasks);
  }, [resumeFromTurn]);

  // Resume from a chosen assistant ROUND — regenerate that round onward. The
  // server rewinds to the round + auto-forwards the loop (no client replay).
  const handleResumeFromRound = useCallback((message, dropTasks) => {
    resumeFromRound?.(message.id, dropTasks);
  }, [resumeFromRound]);

  // Back-out (R2/G7). Leaving the hub for the session view. When a Phase-2b
  // pending input is STILL open (the user opened the hub via "Go To Experiment
  // Hub" but never confirmed), R1 no longer resolves it on open — so the chat
  // composer is disabled (`disabled={... || !!pendingInput}`). Cancel the pending
  // widget on the way out (reusing the existing cancelRequest, which nulls
  // pendingInput + emits {type:'cancel'}; the server leaves the SOP at 2b) so
  // returning to chat re-enables the composer. No pending input → plain switch.
  const handleDashboardBack = useCallback(() => {
    if (pendingInput) {
      cancelRequest?.();
    }
    switchTab(null, 'session');
  }, [pendingInput, cancelRequest, switchTab]);

  const theme = useTheme();
  const widgetMaxWidth = theme.custom?.layout?.widgetMaxWidth || '75%';
  const isRealSessions = serverInfo?.real_sessions;

  // Sync tasks up to App so Sidebar can render task subtabs
  useEffect(() => {
    onTasksChanged?.(tasks);
  }, [tasks, onTasksChanged]);

  // Sync activeTaskId so Sidebar can highlight the active task subtab
  useEffect(() => {
    onActiveTaskChanged?.(activeTaskId);
  }, [activeTaskId, onActiveTaskChanged]);

  // Sync dashboards up to App so Sidebar can render dashboard subtabs
  useEffect(() => {
    onDashboardsChanged?.(dashboards);
  }, [dashboards, onDashboardsChanged]);

  // Sync activeDashboardId so Sidebar can highlight the active dashboard subtab
  useEffect(() => {
    onActiveDashboardChanged?.(activeDashboardId);
  }, [activeDashboardId, onActiveDashboardChanged]);

  // Expose switchTab to App so Sidebar clicks can drive it
  useEffect(() => {
    onSwitchTabRef?.(switchTab);
  }, [switchTab, onSwitchTabRef]);

  // Tell App to refetch the sidebar session list whenever the hook bumps its
  // freshness tick (connect / session_init / turn end / task_status). Skip the
  // initial 0 so we don't double-fetch on mount (Sidebar already fetches once).
  useEffect(() => {
    if (sessionsRefreshTick > 0) onSessionsShouldRefresh?.();
  }, [sessionsRefreshTick, onSessionsShouldRefresh]);

  if (loading) return <LoadingIndicator />;

  // Task panel view — replaces conversation when a task tab is open
  if (activeTabType === 'task' && activeTaskId) {
    return (
      <TaskPanel
        task={tasks[activeTaskId]}
        onBack={() => switchTab(null, 'session')}
        graphState={graphState}
      />
    );
  }

  // Dashboard panel view — replaces conversation when a dashboard tab is open.
  // Sibling panel-swap to the task branch above. DashboardPanel is context-free:
  // everything goes via props. The manifest + seed come from the stored hub
  // entry (delivered at runtime in dashboard_open / rehydrated from
  // dashboard_ref) so the panel renders even before the experiment_hub registry
  // entry is built in. wsEvents$ is the hub's per-hub live-update bus.
  if (activeTabType === 'dashboard' && activeDashboardId) {
    const dash = (dashboards || {})[activeDashboardId] || {};
    return (
      <DashboardPanel
        dashboardId="experiment_hub"
        manifest={dash.manifest || undefined}
        initialState={dash.seed || undefined}
        sessionId={sessionId}
        hubId={activeDashboardId}
        apiClient={hubApiClient}
        wsEvents$={dash.wsEvents$}
        onBack={handleDashboardBack}
      />
    );
  }

  const sessionTitle = sessionMeta?.title || 'Session';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, minWidth: 0 }}>
      {/* Connection Status */}
      <ConnectionStatusBar status={serverStatus} serverInfo={serverInfo} />

      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 2,
          py: 1.5,
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          backgroundColor: 'background.paper',
          flexShrink: 0,
        }}
      >
        <IconButton onClick={onBack} size="small" sx={{ color: 'text.secondary' }}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
            {sessionTitle}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {messages.length} messages
          </Typography>
        </Box>
        {isRealSessions && (
          <BackendSelector
            sessionId={sessionId}
            sessionLlmBackend={sessionMeta?.llm_backend}
            sessionLlmModel={sessionMeta?.llm_model}
          />
        )}
        {isRealSessions && (
          <CheckpointsMenu
            sessionId={sessionId}
            fetchCheckpoints={fetchCheckpoints}
            restoreCheckpoint={restoreCheckpoint}
            disabled={!isConnected || isStreaming}
          />
        )}
        {isRealSessions && <WsStatusBadge status={connectionStatus} />}
      </Box>

      {/* Messages */}
      <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'auto', px: 3, py: 2 }}>
        {messages.map((msg) => {
          // Hide auto-advance messages (server-driven continuation, not user-visible)
          if (msg.metadata?.is_auto_advance) return null;
          if (msg.role === 'manager') {
            return (
              <ManagerMessage
                key={msg.id}
                message={msg}
                onResumeFromTurn={isRealSessions ? handleResumeFromTurn : undefined}
                disabled={!isConnected || isStreaming}
              />
            );
          }
          if (msg.role === 'error') {
            return <ErrorMessage key={msg.id} message={msg} />;
          }
          if (msg.role === 'widget_response') {
            return (
              <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2, ml: 5 }}>
                {committedWidgetMode === 'readonly' ? (
                  <Box sx={{ maxWidth: widgetMaxWidth }}>
                    <ReadOnlyCommittedWidget message={msg} onView={openFileViewer} onViewFolder={openFolderViewer} />
                  </Box>
                ) : (
                  <CommittedWidgetMessage message={msg} onView={openFileViewer} onViewFolder={openFolderViewer} />
                )}
              </Box>
            );
          }
          if (msg.role === 'task_ref') {
            return (
              <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2, ml: 5 }}>
                <TaskCard
                  taskId={msg.taskId}
                  label={msg.label}
                  status={msg.status}
                  error={msg.error}
                  errorType={msg.errorType}
                  onOpenTask={(id) => switchTab(id, 'task')}
                />
              </Box>
            );
          }
          if (msg.role === 'dashboard_ref') {
            return (
              <Box key={msg.id} sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2, ml: 5 }}>
                <DashboardCard
                  hubId={msg.hubId}
                  label={msg.label}
                  icon={msg.icon}
                  status={msg.status}
                  onOpenDashboard={(id) => switchTab(id, 'dashboard')}
                />
              </Box>
            );
          }
          return (
            <AgentMessageBubble
              key={msg.id}
              message={msg}
              onViewPrompt={() => handleViewPrompt(msg)}
              onViewFullResponse={promptViewer.openFullResponse}
              onResumeFromRound={isRealSessions ? handleResumeFromRound : undefined}
              disabled={!isConnected || isStreaming || isResuming}
            />
          );
        })}

        {/* Streaming token display with blinking cursor */}
        {streamingMessage && (streamingMessage.content || streamingMessage.responsePhase === 'pre_response') && (
          <StreamingMessage
            content={streamingMessage.content}
            metadata={streamingMessage.metadata}
            thinkingContent={streamingMessage.thinkingContent}
            responseContent={streamingMessage.responseContent}
            responsePhase={streamingMessage.responsePhase}
            sessionContext={streamingMessage.sessionContext}
            onCancel={cancelRequest}
          />
        )}

        {/* Conversation tool widget — inside scroll area, aligned with AI messages.
            G5 — proposal_selection is a rich grid widget that needs full width
            (~46 hypothesis cards across 5 phase tabs); other widgets
            (confirmation/single-choice/text) keep the narrow 75%-indented mount. */}
        {pendingInput && (() => {
          // The widget type lives on the input_mode metadata (set in
          // useManagerChat from the `pending_input` frame), not as a top-level
          // `widget_type`/`widget.type` on pendingInput — the old paths were
          // always undefined, so the full-width branch never applied.
          const isProposalSelection =
            pendingInput?.inputMode?.metadata?.widget_type === 'proposal_selection';
          const boxSx = isProposalSelection
            ? { mb: 2, maxWidth: '100%' }  // full width for rich grid
            : { mb: 2, ml: 5, maxWidth: widgetMaxWidth };  // narrow default
          return (
            <Box sx={boxSx}>
              <ConversationToolWidget
                pendingInput={pendingInput}
                onSubmit={sendPendingInputResponse}
                onOpenDashboard={openDashboardFromWidget}
                onView={openFileViewer}
                onViewFolder={openFolderViewer}
                pathAutocompleteProvider={pathAutocompleteProvider}
              />
            </Box>
          );
        })()}

        {/* Non-blocking "Resuming…" banner during a round/turn resume prep.
            Sibling to the "Connecting…" block — keeps the conversation usable
            (scroll/menus), never a blocking overlay. Hands off to the normal
            streaming indicator once regeneration begins (message_start). */}
        {isResuming && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2, ml: 5 }}>
            <Typography
              variant="body2"
              sx={{
                color: 'text.secondary',
                fontStyle: 'italic',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 0.4 },
                  '50%': { opacity: 1 },
                },
              }}
            >
              {resumeStage ? `Resuming… (${resumeStage})` : 'Resuming…'}
            </Typography>
          </Box>
        )}

        {/* "Connecting..." when streaming started but no tokens yet */}
        {isStreaming && !streamingMessage && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2, ml: 5 }}>
            <Typography
              variant="body2"
              sx={{
                color: 'text.secondary',
                fontStyle: 'italic',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 0.4 },
                  '50%': { opacity: 1 },
                },
              }}
            >
              Connecting...
            </Typography>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Chat Input */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          backgroundColor: 'background.paper',
          flexShrink: 0,
        }}
      >
        {isRealSessions ? (
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSubmit}
            disabled={!isConnected || isStreaming || isResuming || !!pendingInput}
          />
        ) : (
          <ChatInput
            value=""
            onChange={() => {}}
            onSubmit={() => {}}
            disabled={true}
          />
        )}
      </Box>

      {/* Right-side slide panel: Prompt Inspector / Full Response */}
      {/* File Viewer — right-panel drawer for viewing role documents and task outputs */}
      <FileViewer
        open={fileViewerOpen}
        onClose={closeFileViewer}
        fileName={fileName}
        fileContent={fileContent}
        fileError={fileError}
        fileLoading={fileLoading}
        isHtmlFile={isHtmlFile}
        htmlFilePath={htmlFilePath}
        isFolderMode={isFolderMode}
        folderTree={folderTree}
        selectedFilePath={selectedFilePath}
        onFileSelect={selectFileInFolder}
      />

      <PromptViewerDrawer
        open={promptViewer.open}
        onClose={promptViewer.close}
        promptData={promptViewer.promptData}
        fullResponseContent={promptViewer.fullResponseContent}
      />
    </Box>
  );
}
