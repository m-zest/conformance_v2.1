import React from 'react';
import { 
  Layers, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ExternalLink,
  Plus
} from 'lucide-react';

export const RegistryView: React.FC = () => {
  const tools = [
    {
      name: 'ChatGPT Enterprise',
      provider: 'OpenAI (Sovereign Endpoint)',
      category: 'Customer Support & Research',
      model: 'gpt-4o',
      piiPolicy: 'Strict Mask & Redact',
      riskScore: 18,
      status: 'ACTIVE',
      expiry: '2027-01-15'
    },
    {
      name: 'Microsoft Copilot',
      provider: 'Microsoft Azure AI',
      category: 'Developer Assistant & IDE',
      model: 'claude-3-5-sonnet',
      piiPolicy: 'Tokenize',
      riskScore: 24,
      status: 'ACTIVE',
      expiry: '2026-11-30'
    },
    {
      name: 'TalentMatch HR Screening',
      provider: 'Internal Local SLM',
      category: 'High-Risk Annex III (Recruitment)',
      model: 'phi4-mini-local',
      piiPolicy: 'Strict Redact + Human Oversight',
      riskScore: 48,
      status: 'NEEDS REVIEW',
      expiry: '2026-08-30'
    },
    {
      name: 'Sales Email Assistant',
      provider: 'On-Premise Mistral',
      category: 'Marketing & Outbound',
      model: 'local-mistral-7b',
      piiPolicy: 'Strict Mask',
      riskScore: 12,
      status: 'ACTIVE',
      expiry: '2027-04-10'
    },
    {
      name: 'Internal Invoice Categoriser',
      provider: 'On-Premise Gemma',
      category: 'Finance & Accounts',
      model: 'gemma-3-4b',
      piiPolicy: 'Tokenize & Mask',
      riskScore: 15,
      status: 'ACTIVE',
      expiry: '2027-02-28'
    },
    {
      name: 'DevSecOps CLI Tool',
      provider: 'Internal Python SDK (@govern)',
      category: 'Infrastructure & Automation',
      model: 'gpt-4o',
      piiPolicy: 'Zero-Trust Block',
      riskScore: 22,
      status: 'ACTIVE',
      expiry: '2027-06-15'
    }
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight font-sans">
            AI Fleet Tool Registry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Approved tools, compliance profiles, and operational lifecycles
          </p>
        </div>

        <button className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-[#84cc16] hover:bg-[#65a30d] text-[#07090e] text-xs font-bold transition-all shadow-sm">
          <Plus className="h-4 w-4" />
          <span>Register New Tool</span>
        </button>
      </div>

      {/* Registry Table */}
      <div className="rounded-xl border border-[#1b2436] bg-[#0e131d] overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#090d16] text-slate-400 border-b border-[#1b2436] font-mono text-[10px] uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Tool Name & Provider</th>
                <th className="py-3.5 px-4">Category & Scope</th>
                <th className="py-3.5 px-4">Governed Model</th>
                <th className="py-3.5 px-4">PII Policy</th>
                <th className="py-3.5 px-4">Risk Score</th>
                <th className="py-3.5 px-4">Audit Expiry</th>
                <th className="py-3.5 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#162030] font-sans">
              {tools.map((tool, idx) => (
                <tr key={idx} className="hover:bg-[#131a28] transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-white text-xs">{tool.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5">{tool.provider}</div>
                  </td>

                  <td className="py-3.5 px-4 text-slate-300">
                    {tool.category}
                  </td>

                  <td className="py-3.5 px-4 font-mono text-slate-200">
                    {tool.model}
                  </td>

                  <td className="py-3.5 px-4 text-slate-300">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-[#090d16] border border-[#1b2436] font-mono">
                      {tool.piiPolicy}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 font-mono font-bold text-white">
                    {tool.riskScore}/100
                  </td>

                  <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                    {tool.expiry}
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                      tool.status === 'ACTIVE'
                        ? 'bg-[#84cc16]/10 text-[#84cc16] border border-[#84cc16]/30'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}>
                      &bull; {tool.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
