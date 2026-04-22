/**
 * Chat input form component with slash command autocomplete.
 */

import React, { useState, useCallback } from 'react';
import { Box, Paper, TextField, IconButton } from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { CommandAutocomplete } from './CommandAutocomplete';

export function ChatInput({ value, onChange, onSubmit, disabled }) {
  const [showAutocomplete, setShowAutocomplete] = useState(false);

  const handleChange = useCallback((e) => {
    const val = e.target.value;
    onChange(val);
    setShowAutocomplete(val.startsWith('/') && !val.includes(' '));
  }, [onChange]);

  const handleSelect = useCallback((cmd) => {
    onChange(cmd.includes(' ') ? cmd : cmd + ' ');
    setShowAutocomplete(false);
  }, [onChange]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setShowAutocomplete(false);
    onSubmit(e);
  };

  return (
    <Box sx={{ position: 'relative' }}>
      {showAutocomplete && (
        <CommandAutocomplete input={value} onSelect={handleSelect} />
      )}
      <Paper
        component="form"
        onSubmit={handleSubmit}
        elevation={0}
        sx={{
          p: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          backgroundColor: 'background.paper',
          borderRadius: 2,
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <TextField
          fullWidth
          placeholder="Type your message or / for commands..."
          value={value}
          onChange={handleChange}
          disabled={disabled}
          variant="standard"
          InputProps={{ disableUnderline: true }}
          sx={{ px: 1 }}
        />
        <IconButton
          type="submit"
          color="primary"
          disabled={!value.trim() || disabled}
        >
          <SendIcon />
        </IconButton>
      </Paper>
    </Box>
  );
}

export default ChatInput;
