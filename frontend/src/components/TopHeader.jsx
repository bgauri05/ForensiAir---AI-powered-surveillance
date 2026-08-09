import React from 'react';
import { Search, Bell, User } from 'lucide-react';

export function TopHeader({ activeTab, userRole = 'admin', setUserRole }) {
  const getSearchPlaceholder = () => {
    if (activeTab === 'dataset-quality') {
      return 'Search factory audits, sensor IDs, or quality metrics...';
    }
    return 'Search factories, alerts, or sensor IDs...';
  };

  return (
    <header className="h-16 fixed top-0 right-0 w-[calc(100%-280px)] bg-[#f8f9fb] border-b border-[#E5E7EB] flex justify-between items-center px-6 z-40">
      <div className="flex items-center flex-1 max-w-xl">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#727780]" size={18} />
          <input 
            className="w-full bg-[#f2f4f6] border border-[#E5E7EB] rounded-lg py-2 pl-10 pr-4 font-body-sm text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]" 
            placeholder={getSearchPlaceholder()}
            type="text"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        {setUserRole && (
          <select 
            value={userRole} 
            onChange={(e) => setUserRole(e.target.value)}
            className="bg-white border border-[#E5E7EB] rounded px-3 py-1 text-xs font-bold text-[#00355f] cursor-pointer"
          >
            <option value="admin">Role: Admin</option>
            <option value="inspector">Role: Inspector</option>
          </select>
        )}

        <div className="flex items-center gap-4 border-r border-[#E5E7EB] pr-6">
          <button className="relative text-[#42474f] hover:text-[#00355f] transition-colors">
            <Bell size={20} />
            <span className="absolute top-0 right-0 w-2 h-2 bg-[#ba1a1a] rounded-full"></span>
          </button>
        </div>

        <div className="flex items-center gap-3 cursor-pointer">
          <div className="text-right">
            <p className="font-body-md text-[#191c1e] font-bold text-sm">
              {userRole === 'admin' ? 'Inspector Profile' : 'Field Inspector'}
            </p>
            <p className="text-[11px] text-[#42474f] font-medium">
              {userRole === 'admin' ? 'Environmental Unit B' : 'Field Division'}
            </p>
          </div>
          <div className="w-10 h-10 rounded-full border-2 border-[#00355f]/20 bg-[#0f4c81] text-white flex items-center justify-center font-bold text-sm">
            AD
          </div>
        </div>
      </div>
    </header>
  );
}
