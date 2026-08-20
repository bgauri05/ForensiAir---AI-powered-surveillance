import React from 'react';
import { Search, Bell, LogOut } from 'lucide-react';

export function TopHeader({ activeTab, currentUser, onLogout }) {
  const getSearchPlaceholder = () => {
    if (activeTab === 'dataset-quality') {
      return 'Search factory audits, sensor IDs, or quality metrics...';
    }
    return 'Search factories, alerts, or sensor IDs...';
  };

  const role = currentUser?.role || 'inspector';
  const username = currentUser?.username || 'Not available';
  const initials = username.slice(0, 2).toUpperCase();
  // currentUser.exp is a JWT exp claim (unix seconds) from GET /api/me; the
  // literal admin_token/inspector_token test tokens carry no exp, so this
  // is null for those and the expiry line is simply omitted.
  const expiryLabel = currentUser?.exp
    ? new Date(currentUser.exp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <header className="h-16 fixed top-0 right-0 w-[calc(100%-280px)] bg-[#f8f9fb] border-b border-[#E5E7EB] flex justify-between items-center px-6 z-40">
      <div className="flex items-center flex-1 max-w-xl">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#727780]" size={18} />
          <input
            className="w-full bg-[#f2f4f6] border border-[#E5E7EB] rounded-lg py-2 pl-10 pr-4 font-body-sm text-[#727780] cursor-not-allowed"
            placeholder={getSearchPlaceholder()}
            type="text"
            disabled
            title="Search isn't implemented yet"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 border-r border-[#E5E7EB] pr-6">
          <button disabled title="Notifications aren't implemented yet" className="text-[#c2c7d1] cursor-not-allowed">
            <Bell size={20} />
          </button>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="font-body-md text-[#191c1e] font-bold text-sm">{username}</p>
            <p className="text-[11px] text-[#42474f] font-medium uppercase">
              {role === 'admin' ? 'Administrator' : 'Field Inspector'}
              {expiryLabel && <span className="normal-case text-[#727780]"> · session expires {expiryLabel}</span>}
            </p>
          </div>
          <div className="w-10 h-10 rounded-full border-2 border-[#00355f]/20 bg-[#0f4c81] text-white flex items-center justify-center font-bold text-sm">
            {initials}
          </div>
          <button
            onClick={onLogout}
            title="Log out"
            className="p-2 text-[#727780] hover:text-[#D32F2F] hover:bg-[#D32F2F]/10 rounded-lg transition-colors"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
