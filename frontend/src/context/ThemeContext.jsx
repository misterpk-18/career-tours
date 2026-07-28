import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getThemePreference, setThemePreference } from '../lib/storage';

const ThemeContext = createContext(null);

const DARK_QUERY = '(prefers-color-scheme: dark)';

// Mirrors the fallback in the pre-paint script in index.html: if matchMedia is
// unavailable we assume dark, preserving the app's original appearance.
const readSystemTheme = () =>
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia(DARK_QUERY).matches
      ? 'dark'
      : 'light'
    : 'dark';

export const ThemeProvider = ({ children }) => {
  // The user's CHOICE: 'light' | 'dark' | 'system'. Absent storage means 'system'.
  const [preference, setPreference] = useState(() => getThemePreference() ?? 'system');
  // The OS setting, tracked separately so 'system' stays live.
  const [systemTheme, setSystemTheme] = useState(readSystemTheme);

  // Derived, never stored: storing the resolved value would desync from the OS
  // the moment the user changed their system theme.
  const resolvedTheme = preference === 'system' ? systemTheme : preference;

  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const query = window.matchMedia(DARK_QUERY);
    const onChange = (event) => setSystemTheme(event.matches ? 'dark' : 'light');
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    // The pre-paint script already wrote the correct value on first load, so
    // skip the no-op write (and its transition suppression) on mount.
    if (root.getAttribute('data-theme') === resolvedTheme) return undefined;

    root.setAttribute('data-theme-switching', '');
    root.setAttribute('data-theme', resolvedTheme);
    root.style.colorScheme = resolvedTheme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', resolvedTheme === 'dark' ? '#090d16' : '#fafbfd');

    const frame = requestAnimationFrame(() => root.removeAttribute('data-theme-switching'));
    return () => cancelAnimationFrame(frame);
  }, [resolvedTheme]);

  const setTheme = useCallback((next) => {
    setPreference(next);
    setThemePreference(next);
  }, []);

  const toggleTheme = useCallback(
    () => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark'),
    [resolvedTheme, setTheme]
  );

  const value = useMemo(
    () => ({
      theme: preference,
      resolvedTheme,
      isDark: resolvedTheme === 'dark',
      setTheme,
      toggleTheme,
    }),
    [preference, resolvedTheme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeProvider;
