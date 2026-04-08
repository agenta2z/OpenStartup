/**
 * StreamingMessage — Renders partial content with Response-tag-aware display.
 *
 * Three phases:
 * - pre_response:  No <Response> tag yet → show thinking in muted style + cursor
 * - in_response:   <Response> seen, streaming response → ThinkingFold + response + cursor
 * - post_response: Both tags seen → ThinkingFold + clean response
 *
 * Adapted from rankevolve's AgentStreamSection.js.
 */

import React from 'react';
import { Box, Paper, Chip } from '@mui/material';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ThinkingFold, stripToolsToInvoke, stripAnsi, stripAcliNoise } from './ThinkingFold';
import { SessionContextBar } from './SessionContextBar';

/** Blinking cursor shown during active streaming. */
function BlinkingCursor() {
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        width: 8,
        height: 16,
        backgroundColor: 'primary.main',
        ml: 0.5,
        verticalAlign: 'text-bottom',
        animation: 'blink 1s step-end infinite',
        '@keyframes blink': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 },
        },
      }}
    />
  );
}


export function StreamingMessage({ content, metadata, thinkingContent, responseContent, responsePhase, sessionContext }) {
  const agentLabel = metadata?.agent_name || null;
  const isThinking = responsePhase === 'pre_response';
  const hasResponse = responsePhase === 'in_response' || responsePhase === 'post_response';
  const isResponseStreaming = responsePhase === 'in_response';

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
      <Paper
        elevation={0}
        sx={{
          p: 2,
          maxWidth: '80%',
          backgroundColor: 'background.paper',
          borderRadius: 2,
          border: '1px solid',
          borderColor: 'primary.main',
        }}
      >
        {agentLabel && (
          <Box sx={{ mb: 1, display: 'flex', gap: 1 }}>
            <Chip
              label={`🤖 ${agentLabel}`}
              size="small"
              variant="outlined"
              sx={{ height: 20, fontSize: '0.65rem', borderColor: 'rgba(255,255,255,0.3)' }}
            />
            {isThinking && (
              <Chip
                label="🧠 Thinking..."
                size="small"
                variant="outlined"
                sx={{ height: 20, fontSize: '0.65rem', borderColor: 'warning.main', color: 'warning.main' }}
              />
            )}
          </Box>
        )}

        <Box sx={{ '& p': { m: 0 }, '& pre': { overflow: 'auto' } }}>
          {/* Phase: pre_response — show thinking in muted style */}
          {isThinking && (
            <>
              <Box sx={{ opacity: 0.5, color: 'text.secondary', fontSize: '0.85rem' }}>
                <MarkdownRenderer content={stripAnsi(stripAcliNoise(stripToolsToInvoke(thinkingContent || '')))} />
              </Box>
              <BlinkingCursor />
            </>
          )}

          {/* Phase: in_response or post_response — ThinkingFold + response */}
          {hasResponse && (
            <>
              <ThinkingFold thinkingContent={thinkingContent} />
              <MarkdownRenderer content={stripToolsToInvoke(responseContent || '')} />
              {isResponseStreaming && <BlinkingCursor />}
            </>
          )}

          {/* Phase: no_tags — fallback */}
          {!isThinking && !hasResponse && content && (
            <>
              <MarkdownRenderer content={stripAnsi(stripAcliNoise(stripToolsToInvoke(content || '')))} />
              <BlinkingCursor />
            </>
          )}
        </Box>

        {/* Session Context Bar */}
        {sessionContext && (
          <Box sx={{ mt: 1.5 }}>
            <SessionContextBar
              usedLabel={sessionContext.usedLabel}
              totalLabel={sessionContext.totalLabel}
              percentage={sessionContext.percentage}
            />
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default StreamingMessage;
