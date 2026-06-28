/**
 * UiPreferencesProvider — small React context for UI preferences, persisted to
 * localStorage (mirrors theme/ThemeProvider's pattern).
 *
 * Currently exposes `committedWidgetMode` — how a conversation widget is shown
 * AFTER the user has responded to it:
 *   - 'readonly' : the original widget, frozen/disabled, still showing the entered values.
 *   - 'summary'  : a compact text card (question → answer).
 */
import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';

const UiPreferencesContext = createContext(null);

const STORAGE_KEY = 'openteam-committed-widget-mode';
export const COMMITTED_WIDGET_MODES = ['readonly', 'summary'];
const DEFAULT_MODE = 'readonly';

function readStoredMode() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return COMMITTED_WIDGET_MODES.includes(v) ? v : null;
  } catch {
    return null;
  }
}

export function UiPreferencesProvider({ children }) {
  const [committedWidgetMode, setMode] = useState(() => readStoredMode() || DEFAULT_MODE);

  const setCommittedWidgetMode = useCallback((mode) => {
    const next = COMMITTED_WIDGET_MODES.includes(mode) ? mode : DEFAULT_MODE;
    setMode(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // silent — private browsing / quota exceeded
    }
  }, []);

  const value = useMemo(
    () => ({ committedWidgetMode, setCommittedWidgetMode }),
    [committedWidgetMode, setCommittedWidgetMode],
  );

  return (
    <UiPreferencesContext.Provider value={value}>
      {children}
    </UiPreferencesContext.Provider>
  );
}

export function useUiPreferences() {
  // Defensive default so consumers work even if rendered outside the provider.
  return useContext(UiPreferencesContext) || {
    committedWidgetMode: DEFAULT_MODE,
    setCommittedWidgetMode: () => {},
  };
}
