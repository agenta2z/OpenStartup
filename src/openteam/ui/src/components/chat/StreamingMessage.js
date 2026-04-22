/**
 * StreamingMessage -- Renders partial content with Response-tag-aware display.
 *
 * Three phases:
 * - pre_response:  No <Response> tag yet -> show thinking in muted style + cursor
 * - in_response:   <Response> seen, streaming response -> ThinkingFold + response + cursor
 * - post_response: Both tags seen -> ThinkingFold + clean response
 *
 * Has a foldable header bar (fold toggle only during streaming -- no prompt/full-response
 * buttons, since prompt data is only available after message_end).
 */

import React, { useState } from 'react';
import { Box, Chip, CircularProgress, Collapse, IconButton, Paper, Typography } from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
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


export function StreamingMessage({ content, metadata, thinkingContent, responseContent, responsePhase, sessionContext, onCancel }) {
  const [folded, setFolded] = useState(false);
  const agentLabel = metadata?.agent_name || null;
  const isThinking = responsePhase === 'pre_response';
  const hasResponse = responsePhase === 'in_response' || responsePhase === 'post_response';
  const isResponseStreaming = responsePhase === 'in_response';

  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
      <Paper
        elevation={0}
        sx={{
          maxWidth: '80%',
          backgroundColor: 'background.paper',
          borderRadius: 2,
          border: '1px solid',
          borderColor: 'primary.main',
          overflow: 'hidden',
        }}
      >
        {/* Header bar: agent chip + thinking status + fold toggle */}
        <Box
          onClick={() => setFolded(f => !f)}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            px: 2,
            py: 0.75,
            cursor: 'pointer',
            backgroundColor: 'rgba(255,255,255,0.03)',
            borderBottom: folded ? 'none' : '1px solid rgba(255,255,255,0.06)',
            '&:hover': { backgroundColor: 'rgba(255,255,255,0.06)' },
          }}
        >
          {agentLabel && (
            <Chip
              label={'Robot ' + agentLabel}
              size="small"
              variant="outlined"
              sx={{ height: 20, fontSize: '0.65rem', borderColor: 'rgba(255,255,255,0.3)' }}
            />
          )}
          {isThinking && (
            <Chip
              label="Thinking..."
              size="small"
              variant="outlined"
              sx={{ height: 20, fontSize: '0.65rem', borderColor: 'warning.main', color: 'warning.main' }}
            />
          )}
          <Box sx={{ flex: 1 }} />
          <CircularProgress size={14} thickness={4} sx={{ color: 'primary.light' }} />
          {onCancel && (
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); onCancel(); }}
              sx={{ p: 0.25, ml: 0.5, color: 'error.light' }}
            >
              <CloseIcon sx={{ fontSize: 16 }} />
            </IconButton>
          )}
          <Typography sx={{ color: 'text.disabled', fontSize: '0.7rem', userSelect: 'none', ml: 0.5 }}>
            {folded ? '>' : 'v'}
          </Typography>
        </Box>

        {/* Collapsible body */}
        <Collapse in={!folded}>
          <Box sx={{
            p: 2,
            '& p': { m: 0 },              // top-level paragraphs: no margin (keeps simple replies tight)
            '& p:last-child': { mb: 0 },  // no trailing gap below last paragraph
            '& li p': { m: 0 },           // p inside li: keep tight (li provides spacing)
            '& li': { mb: 0.25 },         // gentle gap between list items
            '& ul, & ol': { pl: 2.5, mt: 0.5, mb: 0.5 },  // indent + breathing room
            '& pre': { overflow: 'auto' },
          }}>
            {/* Phase: pre_response -- show thinking in muted style */}
            {isThinking && (
              <Box>
                <Box sx={{ opacity: 0.5, color: 'text.secondary', fontSize: '0.85rem' }}>
                  <MarkdownRenderer content={stripAnsi(stripAcliNoise(stripToolsToInvoke(thinkingContent || '')))} />
                </Box>
                <BlinkingCursor />
              </Box>
            )}

            {/* Phase: in_response or post_response -- ThinkingFold + response */}
            {hasResponse && (
              <Box>
                <ThinkingFold thinkingContent={thinkingContent} />
                <MarkdownRenderer content={stripToolsToInvoke(responseContent || '')} />
                {isResponseStreaming && <BlinkingCursor />}
              </Box>
            )}

            {/* Phase: no_tags -- fallback */}
            {!isThinking && !hasResponse && content && (
              <Box>
                <MarkdownRenderer content={stripAnsi(stripAcliNoise(stripToolsToInvoke(content || '')))} />
                <BlinkingCursor />
              </Box>
            )}

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
          </Box>
        </Collapse>
      </Paper>
    </Box>
  );
}

export default StreamingMessage;
