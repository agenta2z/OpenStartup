import React from 'react';
import ReactDOM from 'react-dom/client';
import { createTheme } from '@mui/material/styles';
import { AppThemeProvider, registerTheme } from './theme';
import { UiPreferencesProvider } from './preferences/UiPreferencesProvider';
// Bootstrap the shared-ui barrel BEFORE first render so the Dashboard framework
// (built-in widgets via registerBuiltins, plus the dashboard view/registry
// registrations — e.g. the experiment_hub views + ExperimentHubDashboard added
// by another agent) are registered before any <DashboardPanel> mounts. The
// barrel is side-effectful (auto-registers built-in widgets on import).
import '@agent-foundation/shared-ui';
import App from './App';
import './App.css';

// Task 8.11: Register custom OpenStartup brand theme (teal primary, extends dark)
registerTheme('openstartup', {
  id: 'openstartup',
  name: 'OpenStartup',
  extends: 'dark',
  palette: {
    primary: { main: '#00bcd4', light: '#4dd0e1', dark: '#00838f' },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AppThemeProvider createThemeFn={createTheme} defaultThemeId="dark">
      <UiPreferencesProvider>
        <App />
      </UiPreferencesProvider>
    </AppThemeProvider>
  </React.StrictMode>
);
