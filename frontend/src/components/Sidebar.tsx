import React from 'react';
import { 
  LayoutGrid, 
  Layers, 
  Activity, 
  SearchCode, 
  Scale, 
  FileLock2, 
  Presentation, 
  Settings, 
  LifeBuoy, 
  Sparkles, 
  Shield 
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  openSignalsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  openSignalsCount = 10
}) => {
  const mainNav = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutGrid, badge: null },
    { id: 'registry', label: 'Registry', icon: Layers, badge: null },
    { id: 'signal_feed', label: 'Signal feed', icon: Activity, badge: openSignalsCount },
    { id: 'inspector', label: 'Inspector', icon: SearchCode, badge: null },
    { id: 'jury', label: 'Jury & Policies', icon: Scale, badge: null },
    { id: 'vault', label: 'Audit Vault', icon: FileLock2, badge: null },
    { id: 'pitch', label: 'Pitch & Architecture', icon: Presentation, badge: null },
  ];

  const generalNav = [
    { id: 'settings', label: 'Account Settings', icon: Settings },
    { id: 'help', label: 'Help Center', icon: LifeBuoy },
  ];

  return (
    <aside className="w-64 bg-[#0d121d] border-r border-[#1e293b] flex flex-col justify-between h-screen sticky top-0 shrink-0 select-none">
      {/* Brand Header */}
      <div>
        <div className="p-6 flex items-center justify-between border-b border-[#1e293b]">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-[#84cc16] flex items-center justify-center">
              <Shield className="h-5 w-5 text-[#0d121d] fill-current" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-100 tracking-tight leading-none">
                Conformance
              </div>
              <div className="text-[10px] text-slate-400 font-mono tracking-wider uppercase font-semibold mt-1">
                GOVERNANCE OS
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Sections */}
        <div className="p-4 space-y-7">
          {/* MAIN */}
          <div>
            <div className="px-3 text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2.5">
              MAIN
            </div>
            <nav className="space-y-1.5">
              {mainNav.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-[#182234] text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-[#131b2a]'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className={`h-4 w-4 ${isActive ? 'text-[#a3e635]' : 'text-slate-400'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge !== null && (
                      <span
                        className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#f87171]/20 text-[#f87171] font-mono"
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* GENERAL */}
          <div>
            <div className="px-3 text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2.5">
              GENERAL
            </div>
            <nav className="space-y-1.5">
              {generalNav.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => {}}
                    className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-[#131b2a] transition-all"
                  >
                    <Icon className="h-4 w-4 text-slate-400" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Bottom Footer Section */}
      <div className="p-5 border-t border-[#1e293b] space-y-3.5">
        <div className="flex items-center space-x-2.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer transition-colors px-1">
          <Sparkles className="h-4 w-4 text-[#84cc16]" />
          <span>Upcoming Features</span>
        </div>

        <div className="px-3 py-2 rounded-lg bg-[#111726] border border-[#1e293b] flex items-center space-x-2.5 text-xs text-slate-300">
          <span className="h-2 w-2 rounded-full bg-[#84cc16]" />
          <span className="font-medium">Scanner online</span>
        </div>
      </div>
    </aside>
  );
};
