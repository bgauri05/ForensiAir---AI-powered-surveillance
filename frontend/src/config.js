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
