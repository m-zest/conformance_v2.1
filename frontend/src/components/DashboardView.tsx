import React from 'react';
import { 
  Calendar, 
  Layers, 
  CheckCircle2, 
  Clock, 
  Activity, 
  Scan, 
  ShieldAlert, 
  Ban, 
  Gauge 
} from 'lucide-react';
import { MetricsSummary, GovernanceSpan } from '../types';

interface DashboardViewProps {
  metrics: MetricsSummary | null;
  spans: GovernanceSpan[];
  onNavigateTab: (tab: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  metrics,
  spans,
  onNavigateTab
}) => {
  const topMetrics = [
    {
      label: 'APPROVED TOOLS',
      value: '8',
      icon: Layers,
      change: '12%',
      changeText: 'in registry',
      positive: true,
      sparklineColor: '#14b8a6', // muted teal
      sparklinePath: 'M0 25 Q 15 15, 30 20 T 60 10 T 90 18 T 120 8'
    },
    {
      label: 'ACTIVE',
      value: '7',
      icon: CheckCircle2,
      change: '8%',
      changeText: 'online',
      positive: true,
      sparklineColor: '#22c55e', // muted green
      sparklinePath: 'M0 22 Q 20 28, 40 18 T 80 12 T 120 5'
    },
    {
      label: 'NEEDS REVIEW',
      value: '2',
      icon: Clock,
      change: '25%',
      changeText: 'expiring / overdue',
      positive: false,
      sparklineColor: '#f59e0b', // muted amber
      sparklinePath: 'M0 10 Q 25 15, 50 8 T 90 22 T 120 18'
    },
    {
      label: 'OPEN SIGNALS',
      value: `${metrics?.total_blocked_attacks ? metrics.total_blocked_attacks + 6 : 10}`,
      icon: Activity,
      change: '18%',
      changeText: 'awaiting action',
      positive: false,
      sparklineColor: '#0ea5e9', // muted cyan
      sparklinePath: 'M0 20 Q 30 8, 60 25 T 90 12 T 120 15'
    },
    {
      label: 'PROMPTS SCANNED',
      value: metrics ? `${(metrics.total_governed_spans * 1.4 + 14.1).toFixed(1)}K` : '14.1K',
      icon: Scan,
      change: '34%',
      changeText: 'vs last period',
      positive: true,
      sparklineColor: '#14b8a6',
      sparklinePath: 'M0 24 Q 25 18, 50 20 T 80 10 T 120 4'
    },
    {
      label: 'HIGH-RISK SIGNALS',
      value: `${metrics?.total_blocked_attacks ?? 6}`,
      icon: ShieldAlert,
      change: '9%',
      changeText: 'vs last period',
      positive: false,
      sparklineColor: '#f87171', // muted red
      sparklinePath: 'M0 18 Q 30 25, 60 12 T 90 20 T 120 8'
    },
    {
      label: 'BLOCK RATE',
      value: `${metrics?.violation_prevention_rate_vpr ? Math.round(metrics.violation_prevention_rate_vpr / 2) : 50}%`,
      icon: Ban,
      change: '4%',
      changeText: 'of all signals',
      positive: false,
      sparklineColor: '#f87171',
      sparklinePath: 'M0 15 Q 25 22, 50 14 T 80 25 T 120 12'
    },
    {
      label: 'AVG RISK SCORE',
      value: '52',
      icon: Gauge,
      change: '6%',
      changeText: '0-100 scale',
      positive: false,
      sparklineColor: '#38bdf8',
      sparklinePath: 'M0 22 Q 30 14, 60 24 T 90 10 T 120 16'
    }
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Governance Control Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Monitor and govern your AI fleet
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button className="flex items-center space-x-2.5 px-4 py-2 rounded-lg bg-[#111726] border border-[#1e293b] text-xs font-medium text-slate-300 hover:text-white transition-colors">
            <Calendar className="h-4 w-4 text-slate-400" />
            <span>Last 90 days</span>
            <span className="text-[10px] text-slate-400 ml-1">▾</span>
          </button>
        </div>
      </div>

      {/* 8 Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {topMetrics.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="p-5 rounded-xl bg-[#111726] border border-[#1e293b] flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase font-semibold text-slate-400 tracking-wider">
                  {item.label}
                </span>
                <Icon className="h-4 w-4 text-slate-400" />
              </div>

              <div className="flex items-end justify-between mt-4">
                <div className="text-3xl font-bold text-slate-100 tracking-tight">
                  {item.value}
                </div>

                {/* Clean SVG Sparkline */}
                <div className="w-24 h-8">
                  <svg viewBox="0 0 120 30" className="w-full h-full overflow-visible">
                    <path
                      d={item.sparklinePath}
                      fill="none"
                      stroke={item.sparklineColor}
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </div>

              <div className="flex items-center space-x-2 text-xs mt-4 pt-3 border-t border-[#1a2336]">
                <span className={`font-mono font-medium ${item.positive ? 'text-[#84cc16]' : 'text-[#f87171]'}`}>
                  ↗ {item.change}
                </span>
                <span className="text-slate-400 text-xs">{item.changeText}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 3 Donut Chart Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel 1: Signals by Tool */}
        <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-6">
          <div>
            <h3 className="font-semibold text-slate-100 text-base">Signals by Tool</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">12 signals</p>
          </div>

          <div className="flex items-center justify-center py-3">
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                <circle cx="50" cy="50" r="38" stroke="#10b981" strokeWidth="12" strokeDasharray="40 200" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#3b82f6" strokeWidth="12" strokeDasharray="40 200" strokeDashoffset="-40" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#8b5cf6" strokeWidth="12" strokeDasharray="40 200" strokeDashoffset="-80" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#f59e0b" strokeWidth="12" strokeDasharray="30 200" strokeDashoffset="-120" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#f97316" strokeWidth="12" strokeDasharray="30 200" strokeDashoffset="-150" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#ec4899" strokeWidth="12" strokeDasharray="60 200" strokeDashoffset="-180" fill="transparent" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-2xl font-bold text-slate-100 font-mono">12</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-semibold">TOTAL</span>
              </div>
            </div>
          </div>

          {/* Breakdown List */}
          <div className="space-y-3 text-xs">
            {[
              { label: 'Ad-hoc inspection', count: '2', pct: '17%', color: 'bg-emerald-500' },
              { label: 'ChatGPT Enterprise', count: '2', pct: '17%', color: 'bg-blue-500' },
              { label: 'Microsoft Copilot', count: '2', pct: '17%', color: 'bg-purple-500' },
              { label: 'Sales Email Assistant', count: '1', pct: '8%', color: 'bg-amber-500' },
              { label: 'Internal Invoice Categoriser', count: '1', pct: '8%', color: 'bg-orange-500' },
            ].map((row, i) => (
              <div key={i} className="flex items-center justify-between text-slate-300">
                <div className="flex items-center space-x-2.5">
                  <span className={`h-2.5 w-2.5 rounded-full ${row.color}`} />
                  <span className="truncate max-w-[160px]">{row.label}</span>
                </div>
                <div className="flex items-center space-x-4 font-mono text-slate-400 text-xs">
                  <span className="text-slate-100 font-medium">{row.count}</span>
                  <span className="w-8 text-right">{row.pct}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Panel 2: Signals by Category */}
        <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-6">
          <div>
            <h3 className="font-semibold text-slate-100 text-base">Signals by Category</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">6 categories</p>
          </div>

          <div className="flex items-center justify-center py-3">
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                <circle cx="50" cy="50" r="38" stroke="#10b981" strokeWidth="12" strokeDasharray="80 200" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#06b6d4" strokeWidth="12" strokeDasharray="40 200" strokeDashoffset="-80" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#3b82f6" strokeWidth="12" strokeDasharray="40 200" strokeDashoffset="-120" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#a855f7" strokeWidth="12" strokeDasharray="40 200" strokeDashoffset="-160" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#ec4899" strokeWidth="12" strokeDasharray="40 200" strokeDashoffset="-200" fill="transparent" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-2xl font-bold text-slate-100 font-mono">12</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-semibold">TOTAL</span>
              </div>
            </div>
          </div>

          {/* Breakdown List */}
          <div className="space-y-3 text-xs">
            {[
              { label: 'PII', count: '4', pct: '33%', color: 'bg-emerald-500' },
              { label: 'Injection', count: '2', pct: '17%', color: 'bg-cyan-500' },
              { label: 'Secret', count: '2', pct: '17%', color: 'bg-blue-500' },
              { label: 'Policy', count: '2', pct: '17%', color: 'bg-purple-500' },
              { label: 'Exfiltration', count: '1', pct: '8%', color: 'bg-pink-500' },
            ].map((row, i) => (
              <div key={i} className="flex items-center justify-between text-slate-300">
                <div className="flex items-center space-x-2.5">
                  <span className={`h-2.5 w-2.5 rounded-full ${row.color}`} />
                  <span>{row.label}</span>
                </div>
                <div className="flex items-center space-x-4 font-mono text-slate-400 text-xs">
                  <span className="text-slate-100 font-medium">{row.count}</span>
                  <span className="w-8 text-right">{row.pct}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Panel 3: Signals by Severity */}
        <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-6">
          <div>
            <h3 className="font-semibold text-slate-100 text-base">Signals by Severity</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">risk distribution</p>
          </div>

          <div className="flex items-center justify-center py-3">
            <div className="relative w-44 h-44 flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                <circle cx="50" cy="50" r="38" stroke="#f87171" strokeWidth="12" strokeDasharray="120 240" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#fbbf24" strokeWidth="12" strokeDasharray="100 240" strokeDashoffset="-120" fill="transparent" />
                <circle cx="50" cy="50" r="38" stroke="#38bdf8" strokeWidth="12" strokeDasharray="20 240" strokeDashoffset="-220" fill="transparent" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-2xl font-bold text-slate-100 font-mono">12</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-semibold">TOTAL</span>
              </div>
            </div>
          </div>

          {/* Breakdown List */}
          <div className="space-y-3 text-xs">
            {[
              { label: 'High', count: '6', pct: '50%', color: 'bg-rose-400' },
              { label: 'Medium', count: '5', pct: '42%', color: 'bg-amber-400' },
              { label: 'Low', count: '1', pct: '8%', color: 'bg-sky-400' },
            ].map((row, i) => (
              <div key={i} className="flex items-center justify-between text-slate-300">
                <div className="flex items-center space-x-2.5">
                  <span className={`h-2.5 w-2.5 rounded-full ${row.color}`} />
                  <span>{row.label}</span>
                </div>
                <div className="flex items-center space-x-4 font-mono text-slate-400 text-xs">
                  <span className="text-slate-100 font-medium">{row.count}</span>
                  <span className="w-8 text-right">{row.pct}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
