import React, { useState } from 'react';
import { 
  Sliders, 
  Layers, 
  Cpu, 
  Check, 
  Save, 
  ShieldCheck, 
  ArrowRight,
  TrendingUp,
  Zap
} from 'lucide-react';
import { GovernanceProfile } from '../types';
import { api } from '../services/api';

interface ProfilesMatrixViewProps {
  profiles: GovernanceProfile[];
  onProfilesUpdated: () => void;
}

export const ProfilesMatrixView: React.FC<ProfilesMatrixViewProps> = ({
  profiles,
  onProfilesUpdated
}) => {
  const [selectedProfile, setSelectedProfile] = useState<GovernanceProfile>(profiles[0]);
  const [contextTemplate, setContextTemplate] = useState(selectedProfile?.context_injection_template || '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const matrixData = [
    {
      useCase: 'Public Customer Support',
      gpt4: '98.4%',
      claude: '97.2%',
      mistral: '96.1%',
      phi4: '94.0%',
      gemma: '95.3%',
      topPick: 'gpt-4o'
    },
    {
      useCase: 'Internal Developer Assistant',
      gpt4: '99.1%',
      claude: '98.5%',
      mistral: '97.4%',
      phi4: '93.2%',
      gemma: '94.8%',
      topPick: 'claude-3-5-sonnet'
    },
    {
      useCase: 'HR Screening (Annex III High Risk)',
      gpt4: '94.0%',
      claude: '96.2%',
      mistral: '91.5%',
      phi4: '95.8%',
      gemma: '92.1%',
      topPick: 'phi4-mini-local'
    },
    {
      useCase: 'Financial & Wealth Advisory',
      gpt4: '97.8%',
      claude: '98.6%',
      mistral: '95.0%',
      phi4: '96.1%',
      gemma: '93.7%',
      topPick: 'claude-3-5-sonnet'
    }
  ];

  const handleSelectProfile = (p: GovernanceProfile) => {
    setSelectedProfile(p);
    setContextTemplate(p.context_injection_template);
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const updated = { ...selectedProfile, context_injection_template: contextTemplate };
      await api.updateProfile(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      onProfilesUpdated();
    } catch (err) {
      console.error('Failed to save profile', err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-[#080d1a] border border-slate-800 space-y-2">
        <div className="flex items-center space-x-3">
          <Sliders className="h-6 w-6 text-cyan-400" />
          <h2 className="text-xl font-bold text-white tracking-tight font-sans">
            Governance Profiles & Model &times; Use Case Routing
          </h2>
        </div>
        <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
          Configure dynamic context switching and system prompt injection across distinct business units. 
          The proxy reads the active profile from in-memory cache and uses the <strong className="text-cyan-300">Model &times; Use Case matrix</strong> to dynamically route requests to the model with the highest historical compliance score.
        </p>
      </div>

      {/* Model x Use Case Compliance Matrix Table */}
      <div className="p-6 rounded-2xl bg-[#080d1a] border border-slate-800 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2 font-mono uppercase">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <span>MODEL &times; USE CASE REAL-TIME COMPLIANCE MATRIX</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">
            Automated Routing: <strong className="text-emerald-400">ACTIVE</strong>
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[10px] uppercase">
              <tr>
                <th className="py-3 px-4">Business Domain</th>
                <th className="py-3 px-4">GPT-4o</th>
                <th className="py-3 px-4">Claude 3.5</th>
                <th className="py-3 px-4">Mistral 7B</th>
                <th className="py-3 px-4">Phi-4 Mini</th>
                <th className="py-3 px-4">Gemma 3 4B</th>
                <th className="py-3 px-4 text-right">Optimal Route</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {matrixData.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-900/40">
                  <td className="py-3 px-4 font-sans font-medium text-slate-200">
                    {row.useCase}
                  </td>
                  <td className="py-3 px-4 text-emerald-400">{row.gpt4}</td>
                  <td className="py-3 px-4 text-emerald-400">{row.claude}</td>
                  <td className="py-3 px-4 text-cyan-400">{row.mistral}</td>
                  <td className="py-3 px-4 text-indigo-400">{row.phi4}</td>
                  <td className="py-3 px-4 text-cyan-400">{row.gemma}</td>
                  <td className="py-3 px-4 text-right">
                    <span className="px-2 py-0.5 rounded text-[11px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold">
                      {row.topPick}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Profiles & Context Injection Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Profile Selector */}
        <div className="lg:col-span-4 space-y-3">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">
            Active Profiles ({profiles.length})
          </h3>
          <div className="space-y-2">
            {profiles.map((p) => (
              <div
                key={p.profile_id}
                onClick={() => handleSelectProfile(p)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  selectedProfile?.profile_id === p.profile_id
                    ? 'bg-cyan-950/20 border-cyan-500/50 shadow-md'
                    : 'bg-[#080d1a] border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs text-slate-100 font-sans">{p.name}</span>
                  <span className="text-[10px] font-mono text-emerald-400 uppercase">{p.default_mode}</span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">{p.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Profile Editor */}
        <div className="lg:col-span-8">
          {selectedProfile && (
            <div className="p-6 rounded-2xl bg-[#080d1a] border border-slate-800 space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h3 className="font-bold text-slate-100 text-sm font-sans">{selectedProfile.name}</h3>
                  <span className="text-xs text-slate-400 font-mono">
                    ID: {selectedProfile.profile_id} &bull; Target: {selectedProfile.target_environment}
                  </span>
                </div>
                <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  PII: {selectedProfile.pii_policy}
                </span>
              </div>

              {/* Dynamic Context Injection Directive */}
              <div className="space-y-2">
                <label className="text-xs text-slate-300 font-medium font-mono flex items-center space-x-1.5">
                  <Layers className="h-4 w-4 text-cyan-400" />
                  <span>DYNAMIC CONTEXT DIRECTIVE (INJECTED INTO SYSTEM PROMPT):</span>
                </label>
                <textarea
                  rows={4}
                  value={contextTemplate}
                  onChange={(e) => setContextTemplate(e.target.value)}
                  className="w-full p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Injection Threshold:</span>
                  <div className="text-sm font-bold text-amber-400 mt-0.5">
                    {selectedProfile.injection_threshold.toFixed(2)}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Uncertainty Escalation:</span>
                  <div className="text-sm font-bold text-indigo-400 mt-0.5">
                    {selectedProfile.uncertainty_escalation_threshold.toFixed(2)}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-slate-400 font-mono">
                  In-memory cache synchronized with runtime proxy.
                </span>
                <button
                  onClick={handleSaveProfile}
                  disabled={isSaving}
                  className="flex items-center space-x-2 py-2 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-all shadow-lg shadow-blue-500/20"
                >
                  {saveSuccess ? (
                    <>
                      <Check className="h-4 w-4 text-emerald-300" />
                      <span>Updated!</span>
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      <span>Save Profile Directives</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
