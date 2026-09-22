/**
 * DashboardCard — inline chat card for a dashboard subtab (a "hub", e.g. the
 * Experiment Hub). Cloned from TaskCard: appears in the conversation stream when
 * the server opens a dashboard (a `dashboard_ref` history entry, analogous to a
 * `task_ref`). Shows the hub label/icon + live status and an "Open Dashboard"
 * button to switch to the DashboardPanel.
 *
 * Props:
 *   hubId   - unique hub id (the dashboard's multiTaskId)
 *   label   - human-readable hub label (from the manifest)
 *   icon    - optional emoji/icon (from the manifest)
 *   status  - free-form status string from dashboard_status
 *   onOpenDashboard(hubId) - called when the user clicks "Open Dashboard"
 */

import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import DashboardIcon from '@mui/icons-material/Dashboard';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useTheme } from '@mui/material/styles';

// Status → chip styling. The status string is server-defined and free-form, so
// map the common ones and fall back to a neutral chip with the raw status.
const STATUS_CONFIG = {
  open:      { label: 'Open',     color: 'info',    showSpinner: false },
  idle:      { label: 'Idle',     color: 'default', showSpinner: false },
  running:   { label: 'Running',  color: 'info',    showSpinner: true },
  active:    { label: 'Active',   color: 'info',    showSpinner: true },
  completed: { label: 'Complete', color: 'success', showSpinner: false },
  error:     { label: 'Error',    color: 'error',   showSpinner: false },
};

export function DashboardCard({ hubId, label, icon, status, onOpenDashboard }) {
  const theme = useTheme();
  const cfg = STATUS_CONFIG[status] || { label: status || 'Open', color: 'default', showSpinner: false };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: 2,
        py: 1.25,
        borderRadius: 2,
        border: '1px solid',
        borderColor: theme.custom?.surfaces?.cardBorder || 'rgba(255,255,255,0.1)',
        backgroundColor: theme.custom?.surfaces?.overlayLight || 'rgba(255,255,255,0.03)',
        maxWidth: '80%',
      }}
    >
      {/* Status icon / spinner */}
      <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
        {cfg.showSpinner ? (
          <CircularProgress size={16} color={cfg.color === 'default' ? 'inherit' : cfg.color} />
        ) : status === 'completed' ? (
          <CheckCircleIcon sx={{ fontSize: 18, color: 'success.main' }} />
        ) : status === 'error' ? (
          <ErrorIcon sx={{ fontSize: 18, color: 'error.main' }} />
        ) : (
          <DashboardIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
        )}
      </Box>

      {/* Label */}
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Typography
          variant="body2"
          sx={{ fontWeight: 500, color: 'text.primary', mb: 0.25,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
        >
          {(icon ? `${icon} ` : '') + (label || hubId)}
        </Typography>
        <Chip
          label={cfg.label}
          color={cfg.color}
          size="small"
          variant="outlined"
          sx={{ height: 18, fontSize: '0.7rem' }}
        />
      </Box>

      {/* Open Dashboard button */}
      <Button
        size="small"
        variant="outlined"
        endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
        onClick={() => onOpenDashboard && onOpenDashboard(hubId)}
        sx={{
          flexShrink: 0,
          fontSize: '0.75rem',
          py: 0.25,
          px: 1,
          textTransform: 'none',
          borderColor: 'rgba(255,255,255,0.2)',
          color: 'text.secondary',
          '&:hover': { borderColor: 'primary.main', color: 'primary.main' },
        }}
      >
        Open Dashboard
      </Button>
    </Box>
  );
}

export default DashboardCard;
