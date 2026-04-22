/**
 * CommandAutocomplete — popup listing available slash commands.
 *
 * Adapted from RankEvolve's CommandAutocomplete.js.
 * Shows matching commands when the chat input starts with '/' and has no space.
 *
 * Props:
 *   input       - current input value (e.g. "/moc")
 *   onSelect(cmd) - called when user clicks a command (e.g. "/mock_task")
 */

import React from 'react';
import { Paper, Typography, List, ListItemButton, ListItemText } from '@mui/material';

const COMMANDS = [
  { command: '/mock_task', description: '[DEV] Run mocked BTA pipeline for graph visualization testing' },
  { command: '/mock_task --profile huge', description: '[DEV] 64-node stress test (8 inner BTAs × 8 workers)' },
  { command: '/mock_task --profile flat', description: '[DEV] 12 flat workers, no nesting' },
  { command: '/mock_task --profile error', description: '[DEV] One worker errors out (test error styling)' },
  { command: '/mock_task --profile slow', description: '[DEV] 60s sustained streaming test' },
];

export function CommandAutocomplete({ input, onSelect }) {
  const query = input.toLowerCase();
  const matches = COMMANDS.filter(cmd =>
    cmd.command.toLowerCase().startsWith(query)
  );

  if (matches.length === 0) return null;

  return (
    <Paper
      elevation={4}
      sx={{
        position: 'absolute',
        bottom: '100%',
        left: 0,
        right: 0,
        mb: 0.5,
        maxHeight: 240,
        overflow: 'auto',
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        zIndex: 10,
      }}
    >
      <List dense disablePadding>
        {matches.map((cmd) => (
          <ListItemButton
            key={cmd.command}
            onClick={() => onSelect(cmd.command)}
            sx={{
              py: 0.75,
              '&:hover': { backgroundColor: 'rgba(74, 144, 217, 0.1)' },
            }}
          >
            <ListItemText
              primary={
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600, fontSize: '0.82rem' }}>
                  {cmd.command}
                </Typography>
              }
              secondary={
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  {cmd.description}
                </Typography>
              }
            />
          </ListItemButton>
        ))}
      </List>
    </Paper>
  );
}

export default CommandAutocomplete;
