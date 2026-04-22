/**
 * MultipleChoiceWidget — checkbox multi-select with optional "Select All" toggle.
 * Adapted from AgentFoundation/ui/webui/react/src/components/widgets/MultipleChoiceWidget.js
 *
 * Props:
 *   config.input_mode.prompt           - string
 *   config.input_mode.options          - [{label, value, description?}]
 *   config.input_mode.allow_custom     - bool (default: true)
 *   config.input_mode.show_select_all  - bool (default: true) — shows "All of above" toggle
 *   config.input_mode.select_all_text  - string (default: "All of above") — label for the toggle
 *   onSubmit({selections, custom?})    - selections is array of {choice_index}
 */

import React, { useState } from 'react';
import { Box, Button, Checkbox, TextField, Typography } from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';

export default function MultipleChoiceWidget({ config, onSubmit }) {
  const theme = useTheme();
  const options = config?.input_mode?.options || config?.options || [];
  const allowCustom = config?.input_mode?.allow_custom ?? true;
  const showSelectAll = config?.input_mode?.show_select_all ?? true;
  const selectAllText = config?.input_mode?.select_all_text || 'All of above';
  const prompt = config?.input_mode?.prompt || config?.prompt || '';

  const [selections, setSelections] = useState(new Set());
  const [customText, setCustomText] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const allSelected = options.length > 0 && selections.size === options.length;

  const toggle = (idx) => {
    const next = new Set(selections);
    if (next.has(idx)) next.delete(idx); else next.add(idx);
    setSelections(next);
  };

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelections(new Set()); // deselect all
    } else {
      setSelections(new Set(options.map((_, i) => i))); // select all
    }
  };

  const handleSubmit = () => {
    if (submitted) return; // double-submit guard
    setSubmitted(true);
    const result = [...selections].map(i => ({ choice_index: i }));
    if (customText.trim()) result.push({ custom_text: customText.trim() });
    onSubmit({ selections: result });
  };

  if (submitted) {
    const labels = [...selections].map(i => options[i]?.label || `Option ${i + 1}`);
    if (customText.trim()) labels.push(customText.trim());
    return (
      <Box sx={{ color: 'primary.main', fontWeight: 500, fontSize: '0.9rem', py: 0.5 }}>
        Selected: {labels.length > 0 ? labels.join(', ') : 'Submitted'}
      </Box>
    );
  }

  const canSubmit = selections.size > 0 || customText.trim().length > 0;

  const cardStyle = (selected) => ({
    display: 'flex', alignItems: 'flex-start', gap: 1,
    p: 1, borderRadius: 1, cursor: 'pointer',
    border: '1px solid',
    borderColor: selected ? 'primary.main' : theme.custom?.surfaces?.cardBorder || 'rgba(255,255,255,0.1)',
    backgroundColor: selected ? theme.custom?.surfaces?.activeHighlight || 'rgba(74,144,217,0.12)' : 'transparent',
    '&:hover': { backgroundColor: theme.custom?.surfaces?.hoverBg || 'rgba(255,255,255,0.04)' },
  });

  return (
    <Box>
      {prompt && (
        <Box sx={{ mb: 1.5, '& p': { m: 0 } }}>
          <MarkdownRenderer content={prompt} />
        </Box>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 1 }}>
        {options.map((opt, i) => (
          <Box key={i} onClick={() => toggle(i)} sx={cardStyle(selections.has(i))}>
            <Checkbox
              checked={selections.has(i)}
              size="small"
              sx={{ p: 0, color: 'text.disabled', '&.Mui-checked': { color: 'primary.main' } }}
              onClick={(e) => e.stopPropagation()}
              onChange={() => toggle(i)}
            />
            <Box>
              <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500 }}>
                {opt.label}
              </Typography>
              {opt.description && (
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  {opt.description}
                </Typography>
              )}
            </Box>
          </Box>
        ))}

        {/* Select All toggle — shown by default, hidden via show_select_all: false */}
        {showSelectAll && options.length > 1 && (
          <Box onClick={toggleSelectAll} sx={cardStyle(allSelected)}>
            <Checkbox
              checked={allSelected}
              indeterminate={selections.size > 0 && !allSelected}
              size="small"
              sx={{ p: 0, color: 'text.disabled', '&.Mui-checked': { color: 'primary.main' } }}
              onClick={(e) => e.stopPropagation()}
              onChange={toggleSelectAll}
            />
            <Typography variant="body2" sx={{ color: 'text.secondary', fontStyle: 'italic', fontWeight: 400 }}>
              {selectAllText}
            </Typography>
          </Box>
        )}
      </Box>

      {allowCustom && (
        <TextField
          fullWidth placeholder="Add custom option..." value={customText}
          onChange={(e) => setCustomText(e.target.value)} size="small" variant="outlined"
          sx={{
            mb: 1.5,
            '& .MuiOutlinedInput-root': {
              backgroundColor: theme.custom?.surfaces?.inputBg || 'rgba(0,0,0,0.2)',
              '& fieldset': { borderColor: theme.custom?.surfaces?.inputBorder || 'rgba(255,255,255,0.2)' },
              '&.Mui-focused fieldset': { borderColor: 'primary.main' },
            },
            '& .MuiInputBase-input': { color: 'text.primary' },
          }}
        />
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" size="small" onClick={handleSubmit} disabled={!canSubmit}
          endIcon={<SendIcon sx={{ fontSize: 16 }} />}
          sx={{ textTransform: 'none', px: 2, fontSize: '0.85rem' }}>
          Submit ({selections.size} selected)
        </Button>
      </Box>
    </Box>
  );
}
