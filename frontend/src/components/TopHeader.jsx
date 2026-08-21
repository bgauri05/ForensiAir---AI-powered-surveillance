import React, { useState, useEffect, useRef } from 'react';
import { Search, Bell, LogOut } from 'lucide-react';
import { apiFetch } from '../config';

// QC FIX (2026-08): search had no onChange/submit handler at all (typing
// did nothing) and the notification bell had no onClick and rendered its
// badge unconditionally with no real count behind it. Both are now real,
// backed by the same /api/factories fetch this app already makes
// everywhere else -- one fetch here, reused for both, rather than two
// features each inventing their own data source. "sensor IDs" is dropped
// from the placeholder: there's no sensor-level identifier anywhere in
// the factory data model (only factory_id/factory_name), so implying a
// search that can't work would be its own small fabrication.
export function TopHeader({ currentUser, onLogout, onNavigate }) {
  const [factories, setFactories] = useState([]);
  const [factoriesError, setFactoriesError] = useState(false);
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef(null);

  useEffect(() => {
    apiFetch('/api/factories')
      .then((res) => {
        if (!res.ok) throw new Error('bad response');
        return res.json();
      })
      .then((data) => setFactories(Array.isArray(data) ? data : []))
      .catch(() => setFactoriesError(true));
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const role = currentUser?.role || 'inspector';
  const username = currentUser?.username || 'Not available';
  const initials = username.slice(0, 2).toUpperCase();
  // currentUser.exp is a JWT exp claim (unix seconds) from GET /api/me; the
  // literal admin_token/inspector_token test tokens carry no exp, so this
  // is null for those and the expiry line is simply omitted.
  const expiryLabel = currentUser?.exp
    ? new Date(currentUser.exp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  // Real Medium/High risk count -- same filter AlertsPage.jsx uses, reused
  // rather than a second, separate notion of "alerts".
  const alertCount = factories.filter((f) => f.risk_tier === 'High' || f.risk_tier === 'Medium').length;

  const trimmedQuery = query.trim().toLowerCase();
  const searchResults = trimmedQuery.length > 0
    ? factories.filter((f) =>
        (f.factory_name || f.name || '').toLowerCase().includes(trimmedQuery) ||
        (f.factory_id || '').toLowerCase().includes(trimmedQuery)
      ).slice(0, 8)
    : [];

  const handleSelectResult = (factoryId) => {
    setQuery('');
    setShowResults(false);
    onNavigate('factory-detail', factoryId);
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter' && searchResults.length > 0) {
      handleSelectResult(searchResults[0].factory_id);
    } else if (e.key === 'Escape') {
      setShowResults(false);
    }
  };

  return (
    // QC FIX (2026-08): matches Sidebar.jsx's md: breakpoint collapse
    // (w-16 below md, w-[280px] at md and up) -- this offset must track it
    // exactly or the header either overlaps the sidebar or leaves a gap.
    <header className="h-16 fixed top-0 right-0 w-[calc(100%-4rem)] md:w-[calc(100%-280px)] bg-[#f8f9fb] border-b border-[#E5E7EB] flex justify-between items-center px-6 z-40">
      {/* QC FIX (2026-08): neither the search bar nor the username/role
          text block had a responsive fallback, so below ~700px this row
          forced real horizontal page overflow -- confirmed live at 375px.
          Hidden below md rather than shrunk: username/role is still
          visible on Sidebar.jsx's collapsed rail avatar tooltip plus the
          Settings page, so nothing becomes unreachable, just not
          duplicated in a header too narrow to hold it. (Search is now a
          real feature, not a disabled placeholder, but a text input +
          results dropdown still doesn't fit a 64px-wide mobile header
          without redesigning it, which is out of scope here -- the same
          factory lookup is reachable via the Factories nav item.) */}
      <div className="hidden md:flex items-center flex-1 max-w-xl relative" ref={searchRef}>
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#727780]" size={18} />
          <input
            className="w-full bg-white border border-[#E5E7EB] rounded-lg py-2 pl-10 pr-4 font-body-sm text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
            placeholder="Search factories by name or ID..."
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setShowResults(true); }}
            onFocus={() => setShowResults(true)}
            onKeyDown={handleSearchKeyDown}
          />
        </div>

        {showResults && trimmedQuery.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[#E5E7EB] rounded-lg shadow-md max-h-80 overflow-y-auto z-50">
            {factoriesError ? (
              <div className="px-4 py-3 text-body-sm text-[#727780]">Search unavailable -- couldn't load factory data.</div>
            ) : searchResults.length === 0 ? (
              <div className="px-4 py-3 text-body-sm text-[#727780]">No factories match "{query}".</div>
            ) : (
              searchResults.map((f) => (
                <button
                  key={f.factory_id}
                  onClick={() => handleSelectResult(f.factory_id)}
                  className="w-full text-left px-4 py-2.5 hover:bg-[#f8f9fb] flex items-center justify-between gap-3 border-b border-[#E5E7EB] last:border-b-0"
                >
                  <div className="min-w-0">
                    <div className="font-bold text-body-sm text-[#191c1e] truncate">{f.factory_name || f.name}</div>
                    <div className="text-xs text-[#727780]">#{f.factory_id} · {f.region || f.district}</div>
                  </div>
                  <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                    f.risk_tier === 'High' ? 'bg-[#D32F2F]/10 text-[#D32F2F]' : f.risk_tier === 'Medium' ? 'bg-[#F57C00]/10 text-[#F57C00]' : 'bg-[#1b6d24]/10 text-[#1b6d24]'
                  }`}>
                    {f.risk_tier || 'Low'}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 md:gap-6 ml-auto">
        <div className="hidden md:flex items-center gap-4 border-r border-[#E5E7EB] pr-6">
          <button
            onClick={() => onNavigate('alerts')}
            title={alertCount > 0 ? `${alertCount} factories flagged Medium/High risk` : 'No factories currently flagged Medium or High risk'}
            className="relative text-[#42474f] hover:text-[#00355f] transition-colors"
          >
            <Bell size={20} />
            {alertCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-[#D32F2F] text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                {alertCount}
              </span>
            )}
          </button>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right hidden md:block">
            <p className="font-body-md text-[#191c1e] font-bold text-sm">{username}</p>
            <p className="text-[11px] text-[#42474f] font-medium uppercase">
              {role === 'admin' ? 'Administrator' : 'Field Inspector'}
              {expiryLabel && <span className="normal-case text-[#727780]"> · session expires {expiryLabel}</span>}
            </p>
          </div>
          <div className="w-10 h-10 rounded-full border-2 border-[#00355f]/20 bg-[#0f4c81] text-white flex items-center justify-center font-bold text-sm shrink-0" title={`${username} (${role})`}>
            {initials}
          </div>
          <button
            onClick={onLogout}
            title="Log out"
            className="p-2 text-[#727780] hover:text-[#D32F2F] hover:bg-[#D32F2F]/10 rounded-lg transition-colors shrink-0"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
