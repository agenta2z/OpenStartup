/**
 * SettingsDrawer — slide-out settings panel: theme + conversation-widget behavior.
 */
import React from 'react';
import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import { ThemeSwitcher } from '../../theme';
import { useUiPreferences, COMMITTED_WIDGET_MODES } from '../../preferences/UiPreferencesProvider';

const MODE_META = {
  readonly: { name: 'Interactive', desc: 'Keep the widget, frozen & disabled, showing your inputs' },
  summary: { name: 'Text summary', desc: 'Compact card: each question → your answer' },
};

/** Card selector for how a conversation widget renders after you respond. */
function CommittedWidgetModeSelector() {
  const { committedWidgetMode, setCommittedWidgetMode } = useUiPreferences();
  return (
    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
      {COMMITTED_WIDGET_MODES.map((mode) => {
        const meta = MODE_META[mode] || { name: mode, desc: '' };
        const isActive = mode === committedWidgetMode;
        return (
          <Box
            key={mode}
            role="button"
            tabIndex={0}
            aria-pressed={isActive}
            aria-label={`Use ${meta.name} mode after responding to a widget`}
            onClick={() => setCommittedWidgetMode(mode)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setCommittedWidgetMode(mode);
              }
            }}
            sx={{
              cursor: 'pointer',
              border: isActive ? 2 : 1,
              borderColor: isActive ? 'primary.main' : 'divider',
              borderRadius: 2,
              p: 1.5,
              flex: '1 1 0',
              minWidth: 130,
              transition: 'border-color 0.2s',
              '&:hover': { borderColor: 'primary.light' },
            }}
          >
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {meta.name}{isActive ? ' ✓' : ''}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.25 }}>
              {meta.desc}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

export default function SettingsDrawer({ open, onClose }) {
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 340,
          backgroundColor: 'background.paper',
          borderLeft: '1px solid',
          borderColor: 'divider',
          p: 3,
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          ⚙ Settings
        </Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
        Theme
      </Typography>
      <ThemeSwitcher variant="cards" />

      <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 4, mb: 1.5 }}>
        Conversation widget after you respond
      </Typography>
      <CommittedWidgetModeSelector />
    </Drawer>
  );
}
