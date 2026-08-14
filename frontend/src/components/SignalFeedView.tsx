import React, { useState } from 'react';
import { 
  Filter, 
  Calendar, 
  Fingerprint, 
  Lock, 
  ChevronDown, 
  ChevronUp,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { GovernanceSpan } from '../types';

interface SignalFeedViewProps {
  spans: GovernanceSpan[];
}

export const SignalFeedView: React.FC<SignalFeedViewProps> = ({ spans }) => {
  const [selectedSeverity, setSelectedSeverity] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [expandedSignalId, setExpandedSignalId] = useState<string>('');
  const [committeeActions, setCommitteeActions] = useState<Record<string, string>>({});

  // Map real live incoming spans to Signal items
  const dynamicSignals = spans.map((span, idx) => {
    const hasPII = span.pii_entities.length > 0;
    const isInj = span.injection_result?.is_injection;
    const isQuar = span.verdict.includes('QUARANTINED');
    const isBlock = span.verdict.includes('BLOCKED');

    let sigType = 'CLEAN';
    let riskScore = 12;
    let severity = 'Low';

    if (isInj) {
      sigType = 'INJECTION';
      riskScore = Math.round((span.injection_result?.risk_score || 0.95) * 100);
      severity = 'High';
    } else if (hasPII) {
      sigType = 'PII';
      riskScore = 81;
      severity = 'High';
    } else if (isQuar) {
      sigType = 'BIAS / POLICY';
      riskScore = Math.round((span.jury_evaluation?.regulatory_uncertainty_signal || 0.48) * 100);
      severity = 'Medium';
    } else if (isBlock) {
      sigType = 'BLOCKED';
      riskScore = 75;
      severity = 'High';
    }

    const detected = span.pii_entities.map((p) => ({
      label: p.entity_type.replace(/_/g, ' '),
      token: `[${p.entity_type}]`,
      color: p.entity_type.includes('CARD') || p.entity_type.includes('SSN') ? 'text-[#f87171]' : 'text-[#fbbf24]'
    }));

    if (span.raw_prompt.toLowerCase().includes('confidential') || span.raw_prompt.toLowerCase().includes('internal only')) {
      detected.push({
        label: 'Confidential / policy',
        token: 'confidential',
        color: 'text-[#fbbf24]'
      });
    }

    if (detected.length === 0 && isInj) {
      detected.push({
        label: 'Adversarial Prompt Override',
        token: `[${span.injection_result.attack_category || 'INJECTION'}]`,
        color: 'text-[#f87171]'
      });
    }

    return {
      id: `SIG-${span.span_id.replace('span_', '').slice(0, 5).toUpperCase()}`,
      spanId: span.span_id,
      type: sigType,
      source: `${span.application_name} · ${span.client_type}`,
      timestamp: new Date(span.timestamp).toLocaleTimeString(),
      riskScore,
      severity,
      capturedPrompt: span.sanitized_prompt || span.raw_prompt,
      rawPrompt: span.raw_prompt,
      response: span.response_text,
      verdict: span.verdict,
      detected
    };
  });

  // Set default expanded to first signal if not set
  const activeExpandedId = expandedSignalId || (dynamicSignals[0]?.id ?? '');

  const filteredSignals = dynamicSignals.filter((sig) => {
    if (selectedSeverity !== 'All' && sig.severity !== selectedSeverity) return false;
    const currentAction = committeeActions[sig.id] || 'New';
    if (selectedStatus !== 'All' && currentAction !== selectedStatus) return false;
    return true;
  });

  const handleActionSelect = (sigId: string, action: string) => {
    setCommitteeActions(prev => ({ ...prev, [sigId]: action }));
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-sans">
            Signal Feed
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Flagged usage awaiting review, meeting, or resolution
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

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-6 p-4 rounded-xl bg-[#111726] border border-[#1e293b]">
        <div className="flex flex-wrap items-center gap-8">
          {/* Severity Filters */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-medium">
              <Filter className="h-4 w-4 text-slate-400" />
              <span>severity</span>
            </div>
            <div className="flex items-center space-x-1.5">
              {['All', 'High', 'Medium', 'Low'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSelectedSeverity(sev)}
                  className={`px-3 py-1 rounded-full text-xs transition-all ${
                    selectedSeverity === sev
                      ? 'bg-[#84cc16] text-[#0d121d] font-bold'
                      : 'text-slate-400 hover:text-slate-200 bg-[#0d121d] border border-[#1e293b]'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* Status Filters */}
          <div className="flex items-center space-x-3">
            <span className="text-slate-400 text-xs font-medium">status</span>
            <div className="flex items-center space-x-1.5">
              {['All', 'New', 'Under review', 'Meeting scheduled', 'Resolved'].map((st) => (
                <button
                  key={st}
                  onClick={() => setSelectedStatus(st)}
                  className={`px-3 py-1 rounded-full text-xs transition-all ${
                    selectedStatus === st
                      ? 'bg-[#84cc16] text-[#0d121d] font-bold'
                      : 'text-slate-400 hover:text-slate-200 bg-[#0d121d] border border-[#1e293b]'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        <span className="text-xs text-slate-400 font-mono">
          {filteredSignals.length} shown
        </span>
      </div>

      {/* Feed Cards */}
      <div className="space-y-4">
        {filteredSignals.length === 0 ? (
          <div className="p-12 text-center text-slate-400 bg-[#111726] border border-[#1e293b] rounded-xl font-mono text-xs">
            No signals found matching current filter criteria.
          </div>
        ) : (
          filteredSignals.map((sig) => {
            const isExpanded = activeExpandedId === sig.id;
            const currentAction = committeeActions[sig.id] || 'New';

            return (
              <div
                key={sig.id}
                className="rounded-xl bg-[#111726] border border-[#1e293b] transition-all overflow-hidden"
              >
                {/* Card Header Bar */}
                <div 
                  onClick={() => setExpandedSignalId(isExpanded ? '' : sig.id)}
                  className="p-5 flex items-center justify-between cursor-pointer hover:bg-[#161f33] transition-colors"
                >
                  <div className="flex items-center space-x-4">
                    <div className="h-10 w-10 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center justify-center">
                      <Fingerprint className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2.5">
                        <span className="font-bold text-slate-100 text-xs font-mono uppercase">{sig.type}</span>
                        <span className="text-xs text-slate-400 font-mono">{sig.id}</span>
                      </div>
                      <p className="text-xs text-slate-400 font-sans mt-0.5">
                        {sig.source} &bull; {sig.timestamp}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-5">
                    <div className="text-right">
                      <div className="flex items-center space-x-2 justify-end">
                        <span className="text-base font-bold text-slate-100 font-mono">{sig.riskScore}</span>
                        <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">RISK</span>
                      </div>
                    </div>

                    <span className={`px-2.5 py-1 rounded text-xs font-semibold font-mono ${
                      currentAction === 'Resolved' 
                        ? 'bg-emerald-500/15 text-emerald-400' 
                        : 'bg-rose-500/15 text-rose-400'
                    }`}>
                      &bull; {currentAction}
                    </span>

                    <div className="text-slate-400">
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Card Body */}
                {isExpanded && (
                  <div className="p-6 pt-2 border-t border-[#1a2336] space-y-6">
                    {/* Captured Prompt Box */}
                    <div className="p-5 rounded-xl bg-[#0c101a] border border-[#1a2336] space-y-2.5">
                      <div className="flex items-center space-x-2 text-[10px] font-mono uppercase font-bold text-slate-400 tracking-wider">
                        <Lock className="h-3.5 w-3.5 text-slate-400" />
                        <span>CAPTURED PROMPT &bull; SENSITIVE DATA MASKED</span>
                      </div>
                      <p className="text-xs text-slate-200 font-mono leading-relaxed">
                        {sig.capturedPrompt}
                      </p>
                    </div>

                    {/* Two Column Layout: Detected Table + Committee Actions */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-2">
                      {/* Column 1: WHAT WAS DETECTED */}
                      <div className="space-y-3">
                        <div className="text-[11px] font-mono uppercase font-bold text-slate-400 tracking-wider">
                          WHAT WAS DETECTED
                        </div>
                        <div className="divide-y divide-[#1a2336] rounded-xl bg-[#0c101a] border border-[#1a2336] overflow-hidden">
                          {sig.detected.length > 0 ? (
                            sig.detected.map((d, dIdx) => (
                              <div key={dIdx} className="p-3.5 flex items-center justify-between text-xs font-mono">
                                <span className="text-slate-300 font-sans">{d.label}</span>
                                <span className={`font-semibold ${d.color}`}>{d.token}</span>
                              </div>
                            ))
                          ) : (
                            <div className="p-3.5 text-xs text-slate-400 font-mono">
                              Compliant payload. No sensitive tokens detected.
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Column 2: COMMITTEE ACTION */}
                      <div className="space-y-3">
                        <div className="text-[11px] font-mono uppercase font-bold text-slate-400 tracking-wider">
                          COMMITTEE ACTION
                        </div>
                        <div className="space-y-2">
                          {[
                            { id: 'New', label: 'New' },
                            { id: 'Under review', label: 'Under review' },
                            { id: 'Meeting scheduled', label: 'Meeting scheduled' },
                            { id: 'Resolved', label: 'Resolved' },
                          ].map((act) => {
                            const isSelected = currentAction === act.id;
                            return (
                              <div
                                key={act.id}
                                onClick={() => handleActionSelect(sig.id, act.id)}
                                className={`p-3 rounded-lg border transition-all cursor-pointer flex items-center space-x-3 text-xs font-sans ${
                                  isSelected
                                    ? 'bg-[#151d2d] border-rose-500/70 text-white'
                                    : 'bg-[#0c101a] border-[#1a2336] text-slate-400 hover:text-slate-200'
                                }`}
                              >
                                <div className={`h-4 w-4 rounded-full border flex items-center justify-center ${
                                  isSelected ? 'border-rose-500' : 'border-slate-600'
                                }`}>
                                  {isSelected && <div className="h-2 w-2 rounded-full bg-rose-500" />}
                                </div>
                                <span className="font-medium">{act.label}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
