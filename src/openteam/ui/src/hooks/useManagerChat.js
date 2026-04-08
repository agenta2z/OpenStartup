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

const WS_RECONNECT_BASE_MS = 1000;
const WS_RECONNECT_MAX_MS = 30000;

function getWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // In development, CRA proxy doesn't reliably forward WebSocket upgrades.
  // Connect directly to the backend port instead.
  const backendPort = process.env.REACT_APP_BACKEND_PORT || '8000';
  const host = window.location.hostname;
  const isDev = process.env.NODE_ENV === 'development';
  const wsHost = isDev ? `${host}:${backendPort}` : window.location.host;
  return `${proto}//${wsHost}/ws/manager`;
}

export function useManagerChat(sessionId) {
  const [messages, setMessages] = useState([]);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');

  const wsRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const streamingContentRef = useRef('');
  const streamingMetadataRef = useRef({});
  const connectRef = useRef(null);

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

  const handleServerMessage = useCallback((data) => {
    switch (data.type) {
      case 'token':
        streamingContentRef.current += data.content;
        if (data.metadata) {
          streamingMetadataRef.current = data.metadata;
        }
        // Parse <Response> tags to separate thinking from response
        const parsed = parseResponseTags(streamingContentRef.current);
        // Extract session context if present
        const ctx = parseSessionContext(streamingContentRef.current);
        setStreamingMessage({
          role: 'agent',
          content: streamingContentRef.current,
          metadata: streamingMetadataRef.current,
          thinkingContent: parsed.thinkingContent,
          responseContent: parsed.responseContent,
          responsePhase: parsed.phase,
          sessionContext: ctx,
        });
        setIsStreaming(true);
        break;

      case 'message_start':
        streamingContentRef.current = '';
        streamingMetadataRef.current = {};
        setStreamingMessage({ role: 'agent', content: '', metadata: {}, responsePhase: 'pre_response' });
        setIsStreaming(true);
        break;

      case 'message_end': {
        const finalContent = data.final_content || streamingContentRef.current;
        const finalParsed = parseResponseTags(finalContent);
        // If stream ended without <Response>, treat as no_tags
        const finalPhase = finalParsed.phase === 'pre_response' ? 'no_tags' : finalParsed.phase;
        const finalCtx = parseSessionContext(finalContent);

        // Clean up the display content
        let displayContent;
        if (finalPhase === 'no_tags') {
          displayContent = stripAnsi(stripAcliNoise(stripToolsToInvoke(finalContent)));
        } else {
          // Strip noise from the response portion too
          displayContent = stripSessionContext(stripAnsi(stripAcliNoise(finalParsed.responseContent)));
        }

        setMessages(prev => [...prev, {
          id: data.message_id || `msg-${Date.now()}`,
          role: 'agent',
          content: displayContent,
          timestamp: new Date().toISOString(),
          thinkingContent: finalParsed.thinkingContent,
          responsePhase: finalPhase,
          sessionContext: finalCtx,
        }]);
        setStreamingMessage(null);
        streamingContentRef.current = '';
        streamingMetadataRef.current = {};
        setIsStreaming(false);
        break;
      }

      case 'error':
        setMessages(prev => [...prev, {
          id: `err-${Date.now()}`,
          role: 'error',
          content: data.message,
          timestamp: new Date().toISOString(),
        }]);
        setIsStreaming(false);
        setStreamingMessage(null);
        break;

      case 'status':
        if (data.status === 'complete' || data.status === 'error') {
          setIsStreaming(false);
        }
        break;

      case 'session_init':
        // Load existing messages from session history,
        // parsing thinking/response phases for agent messages
        if (data.messages) {
          setMessages(data.messages.map((msg, i) => {
            const base = {
              id: msg.id || `loaded-${i}`,
              role: msg.role === 'manager' ? 'manager' : 'agent',
              content: msg.content,
              timestamp: msg.timestamp,
              agent_name: msg.agent_name,
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
          }));
        }
        break;

      case 'heartbeat':
      case 'pong':
        break;

      default:
        console.log('Unknown WS message type:', data.type);
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

  const cancelRequest = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }));
    }
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
    isConnected: connectionStatus === 'connected',
  };
}

export default useManagerChat;
