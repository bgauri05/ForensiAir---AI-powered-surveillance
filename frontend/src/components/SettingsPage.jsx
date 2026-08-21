import React from 'react';
import { UserCircle, LogOut, Info } from 'lucide-react';

// Real account info only, sourced from the same currentUser session state
// App.jsx already hydrates from GET /api/me for Sidebar/TopHeader -- no
// second fetch here. No theme toggle, no notification preferences: no
// user-preferences table exists anywhere in the backend, confirmed this
// session. Rather than invent fields to fill space, this page says so.
export function SettingsPage({ currentUser, onLogout }) {
  const username = currentUser?.username || 'Not available';
  const role = currentUser?.role;
  const roleLabel = role === 'admin' ? 'Administrator' : role === 'inspector' ? 'Field Inspector' : 'Not available';
  const expiryLabel = currentUser?.exp
    ? new Date(currentUser.exp * 1000).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
    : 'Not available';

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="font-headline-lg text-headline-lg text-[#00355f]">Settings</h2>
        <p className="font-body-md text-body-md text-[#42474f] mt-1">Account and session information.</p>
      </div>

      <div className="card p-6">
        <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4 flex items-center gap-2">
          <UserCircle size={20} /> Account
        </h3>
        <div className="space-y-3.5 text-body-sm">
          <div className="flex justify-between border-b border-[#E5E7EB] pb-3">
            <span className="text-[#727780] font-label-caps uppercase text-[11px] font-bold">Username</span>
            <span className="font-bold text-[#191c1e]">{username}</span>
          </div>
          <div className="flex justify-between border-b border-[#E5E7EB] pb-3">
            <span className="text-[#727780] font-label-caps uppercase text-[11px] font-bold">Role</span>
            <span className="font-bold text-[#191c1e]">{roleLabel}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[#727780] font-label-caps uppercase text-[11px] font-bold">Session Expires</span>
            <span className="font-bold text-[#191c1e]">{expiryLabel}</span>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full mt-6 py-2.5 flex items-center justify-center gap-2 bg-[#fdecea] border border-[#D32F2F]/20 text-[#D32F2F] font-bold text-body-sm rounded-lg hover:bg-[#D32F2F]/10 transition-colors"
        >
          <LogOut size={16} /> Log Out
        </button>
      </div>

      <div className="flex items-start gap-2 px-4 py-3 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg text-body-sm text-[#727780]">
        <Info size={16} className="shrink-0 mt-0.5" />
        Additional preferences aren't available yet -- no user-preferences model exists on the backend.
      </div>
    </div>
  );
}
