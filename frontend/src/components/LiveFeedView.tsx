import React, { useState } from 'react';
import { 
  Activity, 
  Search, 
  Filter, 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  Clock, 
  DollarSign, 
  ChevronRight, 
  X, 
  Cpu, 
  Scale, 
  FileLock, 
  Layers, 
  Database,
  RefreshCw,
  Terminal,
  FileText
} from 'lucide-react';
import { GovernanceSpan, MetricsSummary } from '../types';

interface LiveFeedViewProps {
  spans: GovernanceSpan[];
  metrics: MetricsSummary | null;
  onRefresh: () => void;
}

export const LiveFeedView: React.FC<LiveFeedViewProps> = ({
  spans,
  metrics,
  onRefresh
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedVerdictFilter, setSelectedVerdictFilter] = useState('ALL');
  const [selectedSpan, setSelectedSpan] = useState<GovernanceSpan | null>(null);

  const filteredSpans = spans.filter((span) => {
    const matchesSearch = 
      span.raw_prompt.toLowerCase().includes(searchQuery.toLowerCase()) ||
      span.application_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      span.span_id.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (selectedVerdictFilter === 'ALL') return true;
    if (selectedVerdictFilter === 'BLOCKED') return span.verdict.includes('BLOCKED');
    if (selectedVerdictFilter === 'REDACTED') return span.verdict.includes('REDACTED');
    if (selectedVerdictFilter === 'QUARANTINED') return span.verdict.includes('QUARANTINED');
    if (selectedVerdictFilter === 'APPROVED') return span.verdict === 'APPROVED';

    return true;
  });

  const getVerdictBadge = (verdict: string) => {
    if (verdict.includes('BLOCKED')) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <ShieldAlert className="h-3 w-3 mr-1" />
          {verdict}
        </span>
      );
    }
    if (verdict.includes('QUARANTINED')) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="h-3 w-3 mr-1" />
          {verdict}
        </span>
      );
    }
    if (verdict.includes('REDACTED')) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
          <ShieldCheck className="h-3 w-3 mr-1" />
          {verdict}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
        <ShieldCheck className="h-3 w-3 mr-1" />
        APPROVED
      </span>
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Telemetry HUD KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">Total Governed</span>
          <div className="text-xl font-bold text-white font-mono mt-1">
            {metrics?.total_governed_spans ?? spans.length}
          </div>
          <span className="text-[10px] text-cyan-400 flex items-center mt-1 font-mono">
            <span>&bull; LIVE STREAM</span>
          </span>
        </div>

        <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">Prevention Rate</span>
          <div className="text-xl font-bold text-cyan-400 font-mono mt-1">
            {metrics?.violation_prevention_rate_vpr ?? 98.3}%
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1">VPR CLOSED-LOOP</span>
        </div>

        <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">Mean Det. Latency</span>
          <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">
            {metrics?.mean_deterministic_latency_ms ?? 0.18}ms
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1">SUB-15MS PASS</span>
        </div>

        <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">PII Redactions</span>
          <div className="text-xl font-bold text-blue-400 font-mono mt-1">
            {metrics?.total_pii_redactions ?? 4}
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1">PRESIDIO ENGINE</span>
        </div>

        <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">Human Escalations</span>
          <div className="text-xl font-bold text-amber-400 font-mono mt-1">
            {metrics?.pending_human_reviews ?? 1}
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1">ART. 26(2) QUEUE</span>
        </div>

        <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono font-medium">EU AI Act Vault</span>
          <div className="text-xs font-bold text-emerald-400 mt-1.5 flex items-center font-mono">
            <span className="h-2 w-2 rounded-full bg-emerald-400 mr-1.5" />
            <span>OPERATIONAL</span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1">SIGNED HASH CHAIN</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-[#080d1a] border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="h-4 w-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search trace, prompt, application..."
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto overflow-x-auto">
          <Filter className="h-4 w-4 text-slate-400 hidden sm:block mr-1" />
          {['ALL', 'APPROVED', 'BLOCKED', 'REDACTED', 'QUARANTINED'].map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedVerdictFilter(filter)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                selectedVerdictFilter === filter
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-950 border border-slate-800'
              }`}
            >
              {filter}
            </button>
          ))}
          <button
            onClick={onRefresh}
            title="Refresh feed"
            className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Telemetry Stream Table */}
      <div className="rounded-xl border border-slate-800 bg-[#080d1a] overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/90 text-slate-400 border-b border-slate-800 font-mono uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Time & Span</th>
                <th className="py-3 px-4">Client & App</th>
                <th className="py-3 px-4">Prompt Payload</th>
                <th className="py-3 px-4">Verdict & Risk</th>
                <th className="py-3 px-4">Model & Cost</th>
                <th className="py-3 px-4">Waterfall Latency</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredSpans.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-mono">
                    No governance spans found matching current filters.
                  </td>
                </tr>
              ) : (
                filteredSpans.map((span) => (
                  <tr
                    key={span.span_id}
                    onClick={() => setSelectedSpan(span)}
                    className="hover:bg-slate-800/50 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="text-slate-200 font-bold">
                        {new Date(span.timestamp).toLocaleTimeString()}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        {span.span_id}
                      </div>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="text-slate-200 font-sans font-medium flex items-center space-x-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                        <span>{span.application_name}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {span.client_type}
                      </span>
                    </td>

                    <td className="py-3 px-4 max-w-xs truncate font-sans">
                      <div className="text-slate-200 truncate text-xs" title={span.raw_prompt}>
                        {span.raw_prompt}
                      </div>
                      {span.pii_entities.length > 0 && (
                        <div className="text-[10px] text-cyan-400 font-mono">
                          {span.pii_entities.length} PII redacted
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      {getVerdictBadge(span.verdict)}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap font-mono">
                      <div className="text-slate-300">{span.gen_ai_response_model}</div>
                      <div className="text-[10px] text-slate-500">
                        ${span.gen_ai_total_cost_usd.toFixed(4)}
                      </div>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-slate-950 rounded-full h-1.5 overflow-hidden flex border border-slate-800">
                          <div
                            style={{ width: `${Math.min(100, (span.latency_deterministic_ms / Math.max(0.1, span.latency_total_ms)) * 100)}%` }}
                            className="bg-cyan-400 h-full"
                          />
                          <div
                            style={{ width: `${Math.min(100, (span.latency_jury_ms / Math.max(0.1, span.latency_total_ms)) * 100)}%` }}
                            className="bg-indigo-500 h-full"
                          />
                          <div
                            style={{ width: `${Math.min(100, (span.latency_upstream_ms / Math.max(0.1, span.latency_total_ms)) * 100)}%` }}
                            className="bg-emerald-500 h-full"
                          />
                        </div>
                        <span className="font-mono text-[10px] text-slate-400">
                          {span.latency_total_ms.toFixed(1)}ms
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button className="p-1 rounded text-slate-400 group-hover:text-cyan-400 transition-colors">
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-in Execution Drawer */}
      {selectedSpan && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex justify-end animate-in fade-in duration-200">
          <div className="w-full max-w-2xl bg-[#090e1c] border-l border-slate-800 h-full overflow-y-auto p-6 space-y-6 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-sm font-bold text-white">
                    Span: {selectedSpan.span_id}
                  </span>
                  {getVerdictBadge(selectedSpan.verdict)}
                </div>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  Trace ID: {selectedSpan.trace_id} &bull; {selectedSpan.timestamp}
                </p>
              </div>
              <button
                onClick={() => setSelectedSpan(null)}
                className="p-1.5 rounded-lg bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Waterfall Breakdown */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
              <h4 className="text-xs font-bold text-slate-300 flex items-center space-x-2 font-mono">
                <Clock className="h-4 w-4 text-cyan-400" />
                <span>RUNTIME INTERCEPTION WATERFALL</span>
              </h4>
              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                <div className="p-2 rounded bg-[#0b1020] border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-mono">Deterministic</div>
                  <div className="font-mono font-bold text-cyan-400">{selectedSpan.latency_deterministic_ms}ms</div>
                </div>
                <div className="p-2 rounded bg-[#0b1020] border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-mono">SLM Jury</div>
                  <div className="font-mono font-bold text-indigo-400">{selectedSpan.latency_jury_ms}ms</div>
                </div>
                <div className="p-2 rounded bg-[#0b1020] border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-mono">Upstream LLM</div>
                  <div className="font-mono font-bold text-emerald-400">{selectedSpan.latency_upstream_ms}ms</div>
                </div>
                <div className="p-2 rounded bg-[#0b1020] border border-slate-800">
                  <div className="text-[10px] text-slate-400 font-mono">Total Latency</div>
                  <div className="font-mono font-bold text-white">{selectedSpan.latency_total_ms}ms</div>
                </div>
              </div>
            </div>

            {/* Prompts & Redactions */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-300 font-mono">PAYLOAD INSPECTOR</h4>
              
              <div className="space-y-1.5">
                <div className="text-[11px] text-slate-400 font-mono">Raw Prompt:</div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap">
                  {selectedSpan.raw_prompt}
                </div>
              </div>

              {selectedSpan.sanitized_prompt !== selectedSpan.raw_prompt && (
                <div className="space-y-1.5">
                  <div className="text-[11px] text-cyan-400 font-mono">Sanitized In-Flight Payload:</div>
                  <div className="p-3 rounded-lg bg-cyan-950/20 border border-cyan-900/40 font-mono text-xs text-cyan-200 whitespace-pre-wrap">
                    {selectedSpan.sanitized_prompt}
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <div className="text-[11px] text-slate-400 font-mono">Response Payload:</div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 whitespace-pre-wrap">
                  {selectedSpan.response_text}
                </div>
              </div>
            </div>

            {/* Presidio Entities */}
            {selectedSpan.pii_entities.length > 0 && (
              <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-900/40 space-y-2">
                <h4 className="text-xs font-bold text-cyan-300 font-mono flex items-center space-x-1.5">
                  <ShieldCheck className="h-4 w-4 text-cyan-400" />
                  <span>PRESIDIO PII TOKENS REDACTED ({selectedSpan.pii_entities.length})</span>
                </h4>
                <div className="space-y-1.5">
                  {selectedSpan.pii_entities.map((p, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs font-mono bg-slate-950/60 p-2 rounded border border-slate-800">
                      <span className="text-cyan-400 font-bold">{p.entity_type}</span>
                      <span className="text-slate-400">Matched: "{p.text}"</span>
                      <span className="text-emerald-400 text-[10px] uppercase font-bold">{p.action_taken}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Multi-SLM Jury */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between font-mono">
                <h4 className="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
                  <Scale className="h-4 w-4 text-indigo-400" />
                  <span>MULTI-SLM PROFILE-AS-JURY</span>
                </h4>
                <div className="text-xs text-indigo-400 font-semibold">
                  Uncertainty (U): {selectedSpan.jury_evaluation.regulatory_uncertainty_signal.toFixed(2)}
                </div>
              </div>

              <div className="space-y-2">
                {selectedSpan.jury_evaluation.votes.map((vote, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-[#0b1020] border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center justify-between font-semibold">
                      <span className="text-slate-200 font-mono">{vote.judge_name}</span>
                      <span className={vote.compliant ? 'text-emerald-400' : 'text-rose-400'}>
                        {(vote.compliance_score * 100).toFixed(0)}% Score
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-sans">{vote.rationale}</p>
                    {vote.primary_risk && (
                      <div className="text-[10px] text-rose-400 font-mono font-medium">
                        Risk: {vote.primary_risk}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* GAAT Vault */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 font-mono text-[11px]">
              <h4 className="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
                <FileLock className="h-4 w-4 text-emerald-400" />
                <span>GAAT CRYPTOGRAPHIC SIGNATURE</span>
              </h4>
              <div className="text-slate-400 truncate">
                <strong className="text-slate-300">Previous Hash:</strong> {selectedSpan.previous_span_hash}
              </div>
              <div className="text-cyan-400 truncate">
                <strong className="text-slate-300">Current Hash:</strong> {selectedSpan.current_span_hash}
              </div>
              <div className="text-slate-400 truncate">
                <strong className="text-slate-300">Signature:</strong> {selectedSpan.cryptographic_signature}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
