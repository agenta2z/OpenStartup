/**
 * theme/index.js — re-exports from @agent-foundation/shared-ui/theme.
 *
 * The canonical theme module now lives in the shared library.
 * OpenStartup-specific themes (openstartup) are registered at app bootstrap.
 */

import { registerTheme as _registerTheme } from './themeRegistry';

export { AppThemeProvider, useAppTheme } from './ThemeProvider';
export { ThemeSwitcher } from './ThemeSwitcher';
export { createAppTheme } from './createAppTheme';
export { getTheme, listThemes, registerTheme, mergeTheme } from './themeRegistry';
export { applyCssVariables } from './cssVariableBridge';

// Register OpenStartup-specific theme
const openstartupTheme = {
  id: 'openstartup',
  name: 'OpenStartup',
  extends: 'dark',
  palette: {
    primary: { main: '#00bcd4', light: '#4dd0e1', dark: '#00838f' },
  },
};
try { _registerTheme('openstartup', openstartupTheme); } catch (e) { /* already registered */ }
