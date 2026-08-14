import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Activity, 
  PlayCircle, 
  Scale, 
  UserCheck, 
  Sliders, 
  FileLock2, 
  Presentation, 
  Cpu, 
  Server,
  Radio,
  Terminal,
  Clock
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingReviewsCount: number;
  wsConnected: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  pendingReviewsCount,
  wsConnected
}) => {
  const [timeString, setTimeString] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeString(now.toISOString().slice(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: 'pitch', label: 'Executive Pitch & Deck', icon: Presentation, badge: 'RESEARCH' },
    { id: 'live_feed', label: 'Live Telemetry & Traces', icon: Activity, badge: 'OTel GenAI' },
    { id: 'playground', label: 'Testing Sandbox', icon: PlayCircle, badge: null },
    { id: 'jury_panel', label: 'Multi-SLM Jury', icon: Scale, badge: 'govllm' },
    { id: 'human_review', label: 'Article 26 Oversight', icon: UserCheck, badge: pendingReviewsCount > 0 ? pendingReviewsCount : null },
    { id: 'profiles', label: 'Profiles & Routing', icon: Sliders, badge: null },
    { id: 'audit_vault', label: 'Cryptographic Vault', icon: FileLock2, badge: 'ECDSA' },
  ];

  return (
    <header className="border-b border-slate-800/80 bg-[#060912]/95 backdrop-blur-xl sticky top-0 z-50 shadow-2xl">
      {/* Top Banner Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center space-x-3.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-cyan-400 p-[1px] shadow-lg shadow-blue-500/20">
              <div className="h-full w-full bg-[#090d1a] rounded-[11px] flex items-center justify-center">
                <ShieldCheck className="h-5 w-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-base tracking-tight text-white font-sans">
                  CONTINUOUS AI GOVERNANCE
                </span>
                <span className="text-[9px] font-mono uppercase font-bold px-2 py-0.5 rounded bg-blue-500/10 text-cyan-400 border border-cyan-500/30 tracking-widest">
                  CONTROL PLANE
                </span>
              </div>
              <div className="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
                <span>EU AI Act (Art. 26)</span>
                <span>&bull;</span>
                <span>GDPR (Art. 44)</span>
                <span>&bull;</span>
                <span>ANSSI Security</span>
              </div>
            </div>
          </div>

          {/* Right Status HUD */}
          <div className="hidden lg:flex items-center space-x-3 text-xs font-mono">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-300">
              <Clock className="h-3.5 w-3.5 text-cyan-400" />
              <span>{timeString}</span>
            </div>

            <div className="flex items-center space-x-2 px-3 py-1 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-300">
              <Server className="h-3.5 w-3.5 text-indigo-400" />
              <span>SOVEREIGN ON-PREM</span>
            </div>

            <div className="flex items-center space-x-2 px-3 py-1 rounded-lg bg-slate-900/80 border border-slate-800">
              <span className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-cyan-400 live-indicator shadow-[0_0_8px_#06b6d4]' : 'bg-rose-500'}`} />
              <span className={wsConnected ? 'text-cyan-300 font-semibold' : 'text-rose-400'}>
                {wsConnected ? 'STREAM ACTIVE (:8000)' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Modern High-Density Nav Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-800/60">
        <nav className="flex space-x-1 overflow-x-auto scrollbar-none py-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600/15 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_-2px_rgba(6,182,212,0.25)] font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded ${
                      typeof tab.badge === 'number'
                        ? 'bg-rose-500 text-white'
                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
