import React from 'react';
import { Settings } from 'lucide-react';

// Previously a dead end (no case in App.jsx's switch, silently fell through
// to Dashboard). There's no user-settings backend yet -- rather than
// inventing controls that don't do anything, this is an honest placeholder
// so the nav item goes somewhere and says what's actually true.
export function SettingsPage() {
  return (
    <div className="p-8 max-w-2xl">
      <div className="card p-10 text-center">
        <Settings size={40} className="mx-auto mb-4 text-[#727780]" />
        <h2 className="font-headline-md text-headline-md text-[#191c1e] mb-2">Settings — Coming Soon</h2>
        <p className="text-body-sm text-[#727780]">
          User-level preferences aren't implemented yet. This page is a placeholder so the nav
          item leads somewhere real instead of silently reopening the Dashboard.
        </p>
      </div>
    </div>
  );
}
