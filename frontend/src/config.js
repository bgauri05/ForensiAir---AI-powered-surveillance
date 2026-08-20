// Central place for environment-dependent config.
// Previously every component hardcoded `http://127.0.0.1:8000` directly in
// its fetch() calls (23 occurrences across 9 files) -- that meant the app
// could only ever run against a backend on localhost:8000, and changing it
// meant editing every file individually.
//
// Set VITE_API_BASE_URL in a .env file (see .env.example) to point at a
// different backend (staging, a teammate's machine, a deployed instance).
// Falls back to the same localhost default that was hardcoded before, so
// local dev behavior is unchanged if no .env is present.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// sessionStorage over localStorage: cleared when the tab closes rather than
// persisting indefinitely, which shrinks the window an XSS payload could
// find a live token in. Real auth (Phase 5) -- previously no request in
// this app ever sent an Authorization header.
const TOKEN_KEY = 'forensiair_auth_token';

export function getAuthToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

// Dispatched whenever any apiFetch() call comes back 401 -- App.jsx listens
// for this and clears its session state, which is this app's "redirect to
// login" (no router exists; App.jsx already renders <LoginPage> whenever
// currentUser is null). A CustomEvent rather than a stored callback so
// config.js doesn't need to know App.jsx exists, and so this fires
// correctly even if apiFetch is ever called before App.jsx has mounted.
export const UNAUTHORIZED_EVENT = 'forensiair:unauthorized';

// Drop-in replacement for fetch(`${API_BASE_URL}${path}`, options) that
// attaches the real Authorization: Bearer header whenever a session token
// exists, so every request -- not just the admin-gated ones -- carries it.
//
// QC FIX (2026-08, Phase 5 completion): a 401 here used to fall straight
// through to the caller, which every page's own `if (res.ok) {...} else
// {show demo/fallback data}` logic then silently absorbed -- an expired
// session looked identical to "the backend endpoint isn't available."
// Confirmed live: swapping in an expired token left the sidebar/header
// showing a stale "logged in" session while Dataset Quality quietly
// switched to demo data with no indication the user needed to log back
// in. A 401 always means the session is dead (never "wrong role" -- that's
// a 403 from require_role(), which is left alone here on purpose since
// it's a legitimate, informative response, not an auth failure). Handling
// this once here, instead of in each of apiFetch's 22 call sites, is what
// makes it impossible for a page to individually forget it.
export function apiFetch(path, options = {}) {
  const token = getAuthToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers }).then((res) => {
    if (res.status === 401) {
      clearAuthToken();
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }
    return res;
  });
}
