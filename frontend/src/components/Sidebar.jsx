import React from 'react';
import {
  LayoutDashboard,
  Building2,
  BrainCircuit,
  AlertTriangle,
  FileText,
  Database, 
  ShieldAlert, 
  Settings 
} from 'lucide-react';

export function Sidebar({ activeTab, setActiveTab, currentUser }) {
  const username = currentUser?.username || 'Not available';
  const role = currentUser?.role;
  const initials = username.slice(0, 2).toUpperCase();
  const surveillanceItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'factories', label: 'Factories', icon: Building2 },
    { id: 'ai-analysis', label: 'AI Analysis', icon: BrainCircuit },
    { id: 'institutional-oversight', label: 'Institutional Oversight', icon: ShieldAlert },
    { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'dataset-quality', label: 'Dataset Quality', icon: Database },
  ];

  const adminItems = [
    { id: 'administration', label: 'Administration', icon: ShieldAlert },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-[280px] h-screen fixed left-0 top-0 bg-[#00355f] text-white border-r border-[#c2c7d1] flex flex-col py-6 z-50 overflow-y-auto">
      {/* Brand Header */}
      <div className="px-6 mb-8 flex items-center gap-3">
        <div className="w-10 h-10 bg-white/10 rounded flex items-center justify-center font-bold text-white text-xl">
          <span className="material-symbols-outlined text-white text-2xl">cloud_done</span>
        </div>
        <div>
          <h1 className="font-headline-md text-headline-md font-bold text-white leading-tight">ForensiAir</h1>
          <p className="text-[10px] text-white/60 font-label-caps tracking-widest uppercase">Government Inspectorate</p>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 space-y-1">
        <div className="px-6 text-[10px] font-label-caps text-white/40 tracking-wider uppercase mb-2">
          Surveillance Modules
        </div>
        {surveillanceItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id || (item.id === 'factories' && activeTab === 'factory-detail');
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full px-6 py-3 flex items-center gap-3 transition-colors duration-200 ease-in-out text-left ${
                isActive 
                  ? 'bg-[#0f4c81] text-[#8ebdf9] border-l-4 border-[#8ebdf9] font-bold' 
                  : 'text-white/70 hover:text-white hover:bg-white/10'
              }`}
            >
              <Icon size={18} className={isActive ? 'text-[#8ebdf9]' : 'text-white/70'} />
              <span className="font-label-caps text-[13px]">{item.label}</span>
            </button>
          );
        })}

        <div className="px-6 text-[10px] font-label-caps text-white/40 tracking-wider uppercase mt-6 mb-2">
          Administrative
        </div>
        {adminItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full px-6 py-3 flex items-center gap-3 transition-colors duration-200 ease-in-out text-left ${
                isActive 
                  ? 'bg-[#0f4c81] text-[#8ebdf9] border-l-4 border-[#8ebdf9] font-bold' 
                  : 'text-white/70 hover:text-white hover:bg-white/10'
              }`}
            >
              <Icon size={18} className={isActive ? 'text-[#8ebdf9]' : 'text-white/70'} />
              <span className="font-label-caps text-[13px]">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* User / Inspector Profile -- real logged-in session, not a
          hardcoded name swapped by which page happened to be open */}
      <div className="px-6 pt-4 mt-auto border-t border-white/10 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-[#0f4c81] text-white flex items-center justify-center font-bold text-xs shrink-0 border border-white/20">
          {initials}
        </div>
        <div className="overflow-hidden">
          <div className="text-xs font-bold text-white truncate">{username}</div>
          <div className="text-[10px] text-white/60 truncate uppercase">{role === 'admin' ? 'Administrator' : 'Field Inspector'}</div>
        </div>
      </div>
    </aside>
  );
}
