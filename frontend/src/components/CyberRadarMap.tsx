import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  Scale, 
  FileLock2, 
  Server, 
  Activity, 
  Terminal,
  Zap,
  Globe,
  Radio
} from 'lucide-react';
import { GovernanceSpan } from '../types';

interface CyberRadarMapProps {
  recentSpans: GovernanceSpan[];
  onSelectNode?: (nodeId: string) => void;
}

export const CyberRadarMap: React.FC<CyberRadarMapProps> = ({ recentSpans }) => {
  const [selectedNode, setSelectedNode] = useState<string | null>('presidio_gate');

  const nodes = [
    {
      id: 'client_apps',
      label: 'Client AI Ingestion',
      subtext: '@govern SDK & Proxies',
      x: 15,
      y: 40,
      icon: Terminal,
      color: '#3b82f6',
      badge: `${recentSpans.length} active`,
      status: 'ONLINE'
    },
    {
      id: 'presidio_gate',
      label: 'Presidio Gate (<15ms)',
      subtext: 'Deterministic Lexical Guard',
      x: 38,
      y: 28,
      icon: ShieldCheck,
      color: '#06b6d4',
      badge: '0.18ms Avg',
      status: 'ENFORCING'
    },
    {
      id: 'context_router',
      label: 'Model × Use Case Router',
      subtext: 'Dynamic Context Injection',
      x: 48,
      y: 65,
      icon: Zap,
      color: '#8b5cf6',
      badge: '4 Profiles',
      status: 'SYNCED'
    },
    {
      id: 'slm_jury',
      label: 'Multi-SLM Jury Panel',
      subtext: 'govllm (EU/GDPR/ANSSI)',
      x: 70,
      y: 35,
      icon: Scale,
      color: '#f59e0b',
      badge: 'U < 0.35 Target',
      status: 'EVALUATING'
    },
    {
      id: 'gaat_vault',
      label: 'GAAT Cryptographic Vault',
      subtext: 'SHA-256 / ECDSA Ledger',
      x: 85,
      y: 70,
      icon: FileLock2,
      color: '#10b981',
      badge: 'Art. 26(6) Sealed',
      status: 'VERIFIED'
    }
  ];

  return (
    <div className="relative rounded-2xl bg-[#080d1a] border border-slate-800/90 overflow-hidden shadow-2xl p-6 cyber-grid">
      {/* Topographic Background Contour Lines (SVG) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-25" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="topoGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
            <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.05" />
          </linearGradient>
        </defs>

        {/* Contour Rings */}
        <circle cx="50%" cy="50%" r="42%" fill="none" stroke="url(#topoGlow)" strokeWidth="1" strokeDasharray="6 6" />
        <circle cx="50%" cy="50%" r="30%" fill="none" stroke="url(#topoGlow)" strokeWidth="1.2" />
        <circle cx="50%" cy="50%" r="18%" fill="none" stroke="url(#topoGlow)" strokeWidth="1" strokeDasharray="3 3" />
        <circle cx="50%" cy="50%" r="8%" fill="none" stroke="url(#topoGlow)" strokeWidth="1.5" />

        {/* Crosshair coordinate lines */}
        <line x1="50%" y1="0%" x2="50%" y2="100%" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
        <line x1="0%" y1="50%" x2="100%" y2="50%" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />

        {/* Connecting Data Flow Lines */}
        <path d="M 150 180 Q 280 120 380 140 T 700 160" fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeOpacity="0.3" strokeDasharray="4 4" />
        <path d="M 380 140 Q 500 280 700 160 T 880 300" fill="none" stroke="#06b6d4" strokeWidth="1.5" strokeOpacity="0.3" strokeDasharray="4 4" />
      </svg>

      {/* Header Info */}
      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 live-indicator shadow-[0_0_10px_#06b6d4]" />
            <h3 className="font-bold text-white text-base tracking-tight font-sans flex items-center space-x-2">
              <span>Runtime Governance Topology & Threat Radar</span>
            </h3>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Real-time closed-loop packet inspection across tripartite control nodes &bull; OpenTelemetry GenAI Active
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-1 rounded-md bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-cyan-300 flex items-center space-x-1.5">
            <Radio className="h-3 w-3 text-cyan-400 animate-pulse" />
            <span>LATENCY: 0.18ms</span>
          </span>
          <span className="px-2.5 py-1 rounded-md bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-emerald-300">
            SOVEREIGN ON-PREM
          </span>
        </div>
      </div>

      {/* Interactive Topology Nodes */}
      <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {nodes.map((node) => {
          const Icon = node.icon;
          const isSelected = selectedNode === node.id;
          return (
            <div
              key={node.id}
              onClick={() => setSelectedNode(node.id)}
              className={`p-4 rounded-xl transition-all cursor-pointer relative overflow-hidden group ${
                isSelected
                  ? 'bg-slate-900/95 border-cyan-500/50 shadow-[0_0_20px_-3px_rgba(6,182,212,0.25)] ring-1 ring-cyan-500/30'
                  : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90'
              } border`}
            >
              {/* Subtle top indicator bar */}
              <div 
                className="absolute top-0 left-0 right-0 h-[2px] opacity-80"
                style={{ backgroundColor: node.color }}
              />

              <div className="flex items-center justify-between mb-3">
                <div 
                  className="h-8 w-8 rounded-lg flex items-center justify-center shadow-inner"
                  style={{ backgroundColor: `${node.color}20`, color: node.color }}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <span 
                  className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border"
                  style={{ 
                    color: node.color, 
                    borderColor: `${node.color}40`,
                    backgroundColor: `${node.color}10` 
                  }}
                >
                  {node.status}
                </span>
              </div>

              <h4 className="text-xs font-bold text-slate-100 tracking-tight">{node.label}</h4>
              <p className="text-[11px] text-slate-400 mt-0.5">{node.subtext}</p>

              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Metric:</span>
                <span className="text-slate-200 font-semibold">{node.badge}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Radar Coordinate Footer Bar */}
      <div className="relative z-10 mt-6 pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] font-mono text-slate-500">
        <div className="flex items-center space-x-3">
          <span>COORDINATES: [47.3769° N, 8.5417° E]</span>
          <span>&bull;</span>
          <span>PROTOCOL: GAAT-GTS-v2.0</span>
          <span>&bull;</span>
          <span>CIPHER: ECDSA-P256-SHA256</span>
        </div>
        <div className="text-slate-400">
          Continuous Closed-Loop Enforcement &bull; <strong className="text-emerald-400">98.3% VPR</strong>
        </div>
      </div>
    </div>
  );
};
