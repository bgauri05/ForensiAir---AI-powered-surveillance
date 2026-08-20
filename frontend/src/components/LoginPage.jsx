import React, { useState } from 'react';
import { Lock, AlertCircle } from 'lucide-react';
import { API_BASE_URL, setAuthToken } from '../config';

export function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Login failed.');
        return;
      }
      setAuthToken(data.access_token);
      onLoginSuccess();
    } catch (err) {
      setError(`Could not reach the backend at ${API_BASE_URL}.`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fb] flex items-center justify-center p-6">
      <div className="w-full max-w-sm bg-white border border-[#E5E7EB] rounded-xl shadow-md p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-[#00355f] rounded flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-2xl">cloud_done</span>
          </div>
          <div>
            <h1 className="font-headline-md text-headline-md font-bold text-[#00355f] leading-tight">ForensiAir</h1>
            <p className="text-[10px] text-[#727780] font-label-caps tracking-widest uppercase">Government Inspectorate</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-label-caps text-[#727780] uppercase font-bold mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
              className="w-full bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg px-3 py-2.5 text-body-sm text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
            />
          </div>
          <div>
            <label className="block text-[10px] font-label-caps text-[#727780] uppercase font-bold mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg px-3 py-2.5 text-body-sm text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 px-3 py-2.5 bg-[#fdecea] border border-[#D32F2F]/20 text-[#D32F2F] text-body-sm rounded-lg">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 bg-[#00355f] text-white py-2.5 rounded-lg font-bold text-body-sm hover:opacity-90 transition-all disabled:opacity-50"
          >
            <Lock size={16} />
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
