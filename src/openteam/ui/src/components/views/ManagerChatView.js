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
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import { useApiData } from '../../hooks/useApiData';
import { useServerStatus } from '../../hooks/useServerStatus';
import { useManagerChat } from '../../hooks/useManagerChat';
import { LoadingIndicator } from '../../shared';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { StreamingMessage } from '../chat/StreamingMessage';
import { ChatInput } from '../chat/ChatInput';
import { ThinkingFold } from '../chat/ThinkingFold';
import { SessionContextBar } from '../chat/SessionContextBar';
import ChatWidgetRenderer from '../chat-widgets/ChatWidgetRenderer';
import ConnectionStatusBar from '../layout/ConnectionStatusBar';


function formatTime(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}


function ManagerMessage({ message }) {
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
      <Avatar sx={{ ml: 1, width: 32, height: 32, bgcolor: 'primary.main', flexShrink: 0 }}>
        <PersonIcon sx={{ fontSize: 18 }} />
      </Avatar>
    </Box>
  );
}


function AgentMessage({ message }) {
  const agentName = message.agent_name || 'AI Assistant';
  const hasThinking = message.thinkingContent && message.responsePhase !== 'no_tags';

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
      <Avatar sx={{ mr: 1, width: 32, height: 32, bgcolor: '#4a90d9', flexShrink: 0 }}>
        <SmartToyIcon sx={{ fontSize: 18 }} />
      </Avatar>
      <Box sx={{ maxWidth: '75%', display: 'flex', flexDirection: 'column' }}>
        <Typography variant="caption" sx={{ fontWeight: 600, color: '#4a90d9', mb: 0.5 }}>
          {agentName}
        </Typography>
        <Box
          sx={{
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            px: 2,
            py: 1.5,
            borderRadius: '4px 16px 16px 16px',
            lineHeight: 1.6,
            fontSize: '0.9rem',
            color: 'text.primary',
            '& p': { m: 0 },
            '& pre': { overflow: 'auto' },
          }}
        >
          {/* Collapsible thinking section */}
          {hasThinking && (
            <ThinkingFold thinkingContent={message.thinkingContent} />
          )}

          {/* Main response content */}
          <MarkdownRenderer content={message.content} />

          {/* Widgets */}
          {message.widgets?.length > 0 && (
            <Box sx={{ mt: 1.5 }}>
              <ChatWidgetRenderer widgets={message.widgets} />
            </Box>
          )}

          {/* Session context bar */}
          {message.sessionContext && (
            <Box sx={{ mt: 1.5 }}>
              <SessionContextBar
                usedLabel={message.sessionContext.usedLabel}
                totalLabel={message.sessionContext.totalLabel}
                percentage={message.sessionContext.percentage}
              />
            </Box>
          )}
        </Box>
        <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, ml: 0.5 }}>
          {formatTime(message.timestamp)}
        </Typography>
      </Box>
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


export default function ManagerChatView({ sessionId, onBack }) {
  // Load session metadata (title etc.) via REST
  const { data: sessionMeta, loading } = useApiData(
    sessionId ? `/sessions/${sessionId}` : null
  );
  const { status: serverStatus, serverInfo } = useServerStatus();

  // WebSocket streaming chat
  const {
    messages,
    streamingMessage,
    isStreaming,
    connectionStatus,
    sendMessage,
    cancelRequest,
    isConnected,
  } = useManagerChat(sessionId);

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

  const isRealSessions = serverInfo?.real_sessions;

  if (loading) return <LoadingIndicator />;

  const sessionTitle = sessionMeta?.title || 'Session';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', mx: -3, mt: -3, mb: -3 }}>
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
        {isRealSessions && <WsStatusBadge status={connectionStatus} />}
      </Box>

      {/* Messages */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', px: 3, py: 2 }}>
        {messages.map((msg) => {
          if (msg.role === 'manager') {
            return <ManagerMessage key={msg.id} message={msg} />;
          }
          if (msg.role === 'error') {
            return <ErrorMessage key={msg.id} message={msg} />;
          }
          return <AgentMessage key={msg.id} message={msg} />;
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
          />
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
              🤖 Connecting...
            </Typography>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Cancel button — only shown during streaming */}
      {isStreaming && (
        <Box sx={{ px: 2, pb: 1, display: 'flex', justifyContent: 'center' }}>
          <Button
            size="small"
            variant="outlined"
            color="warning"
            onClick={cancelRequest}
            sx={{ fontSize: '0.75rem' }}
          >
            Cancel
          </Button>
        </Box>
      )}

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
            disabled={!isConnected || isStreaming}
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
    </Box>
  );
}
