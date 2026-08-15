/**
 * The ONLY module permitted to touch window.localStorage.
 *
 * PROJECT RULE: no SERVER data in localStorage. Server-owned data must be
 * fetched from the API on mount — a client cache of it goes stale, and two
 * sources of truth previously made 188 extracted skills unreachable in the UI
 * while they sat in the database.
 *
 * Every key below is device-local state with no server-side counterpart.
 * Adding a key requires justifying it against that rule.
 */
export const KEYS = {
  // Auth credential, issued at login. Device-local by nature.
  token: 'career_tours_token',
  // Session identity returned alongside the token.
  student: 'career_tours_student',
  // DEVICE PREFERENCE — deliberately exempt from the rule above. It originates
  // on this device, has no server-side record, cannot go stale against any API,
  // is never sent to the API, and survives logout by design.
  theme: 'career_tours_theme',
  // DEVICE PREFERENCE, same exemption as `theme`: whether the nav rail is
  // collapsed to icons. A layout choice made with the mouse on this screen —
  // re-expanding it on every navigation would make the control useless.
  sidebar: 'career_tours_sidebar',
};

// localStorage throws in Safari private mode and when the quota is exhausted,
// so every access is guarded. Failing to persist is never fatal here.
const safeGet = (key) => {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
};

const safeSet = (key, value) => {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* private mode / quota exceeded — preference simply won't persist */
  }
};

const safeRemove = (key) => {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* see safeSet */
  }
};

/* ---------------------------------------------------------------- auth ---- */

export const getToken = () => safeGet(KEYS.token);

export const getStudent = () => {
  const raw = safeGet(KEYS.student);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    // Corrupt entry: clear it so the app doesn't retry parsing forever.
    clearSession();
    return null;
  }
};

export const setSession = (token, student) => {
  safeSet(KEYS.token, token);
  safeSet(KEYS.student, JSON.stringify(student));
};

/** Clears ONLY the auth keys. Never use localStorage.clear() — it would also
 *  wipe the theme preference, which should outlive a logout. */
export const clearSession = () => {
  safeRemove(KEYS.token);
  safeRemove(KEYS.student);
};

/* --------------------------------------------------------------- theme ---- */

// Keep this list in sync with the pre-paint script in index.html, which cannot
// import from here because it must run before any module loads.
export const THEME_PREFERENCES = ['light', 'dark', 'system'];

/** Returns 'light' | 'dark' | null. `null` means "no stored preference", which
 *  callers should treat as 'system'. */
export const getThemePreference = () => {
  const value = safeGet(KEYS.theme);
  return value === 'light' || value === 'dark' ? value : null;
};

export const setThemePreference = (preference) => {
  if (!THEME_PREFERENCES.includes(preference)) return;
  // 'system' removes the key rather than storing the string: the absence of a
  // key is the honest representation of "I have no preference", and it keeps the
  // no-stored-value path the one that is exercised by default.
  if (preference === 'system') {
    safeRemove(KEYS.theme);
    return;
  }
  safeSet(KEYS.theme, preference);
};

/* ------------------------------------------------------------- sidebar ---- */

/** Whether the nav rail was left collapsed. Defaults to expanded. */
export const getSidebarCollapsed = () => safeGet(KEYS.sidebar) === 'collapsed';

export const setSidebarCollapsed = (collapsed) => {
  // Absent means expanded, so the default state stores nothing at all.
  if (collapsed) {
    safeSet(KEYS.sidebar, 'collapsed');
    return;
  }
  safeRemove(KEYS.sidebar);
};
