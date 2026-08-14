import React from 'react';
import { 
  Scale, 
  Cpu, 
  ShieldCheck, 
  AlertCircle, 
  Layers, 
  HelpCircle, 
  UserCheck, 
  CheckCircle, 
  TrendingUp, 
  Activity 
} from 'lucide-react';
import { GovernanceSpan } from '../types';

interface JuryPanelViewProps {
  spans: GovernanceSpan[];
}

export const JuryPanelView: React.FC<JuryPanelViewProps> = ({ spans }) => {
  const judges = [
    {
      name: "EU AI Act Art. 26 Judge (phi4-mini)",
      framework: "EU AI Act (Regulation 2024/1689)",
      focus: "Deployer continuous monitoring, Annex III high-risk classification, fundamental rights impact.",
      model: "Microsoft phi4-mini (3.8B On-Prem)",
      iconColor: "text-[#38bdf8]",
      avgScore: 94.2
    },
    {
      name: "GDPR Sovereignty Judge (Mistral-7B)",
      framework: "GDPR Article 44 & Garante Precedents",
      focus: "Data minimization, cross-border transfer prevention, Italian Garante ChatGPT/GEDI rules.",
      model: "Mistral 7B Instruct (On-Prem)",
      iconColor: "text-[#818cf8]",
      avgScore: 96.8
    },
    {
      name: "ANSSI Security Judge (gemma3:4b)",
      framework: "ANSSI AI Security Standard",
      focus: "Direct/indirect prompt injection defense, recursive jailbreak mitigation, delimiter sanitization.",
      model: "Google gemma3:4b (On-Prem)",
      iconColor: "text-[#a78bfa]",
      avgScore: 98.1
    }
  ];

  const recentJurySpans = spans.filter(s => s.jury_evaluation && s.jury_evaluation.votes?.length > 0).slice(0, 5);

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="space-y-1.5">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-sans">
          Multi-SLM Profile-as-Jury Panel
        </h1>
        <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">
          Rather than relying on a single general-purpose model, our architecture evaluates every payload across a panel of specialized on-premise Small Language Models (SLMs) anchored to EU AI Act, GDPR, and ANSSI frameworks.
        </p>
      </div>

      {/* The Three Specialized On-Premise Judges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {judges.map((judge, idx) => (
          <div key={idx} className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Cpu className={`h-5 w-5 ${judge.iconColor}`} />
                <span className="font-bold text-slate-100 text-xs font-mono">{judge.name}</span>
              </div>
              <span className="text-xs font-mono font-bold text-[#84cc16]">{judge.avgScore}% Pass</span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">Regulatory Anchor:</span>
                <p className="text-slate-200 font-medium font-sans mt-0.5">{judge.framework}</p>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">Evaluation Scope:</span>
                <p className="text-slate-400 text-xs leading-relaxed font-sans mt-0.5">{judge.focus}</p>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">Local Inference Model:</span>
                <p className="text-slate-300 font-mono text-xs mt-0.5">{judge.model}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Epistemic Bias & Uncertainty Signal Explanation */}
      <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-2.5">
          <div className="flex items-center space-x-2 text-slate-200 font-bold text-sm font-sans">
            <TrendingUp className="h-4 w-4 text-[#84cc16]" />
            <span>Position Bias & Permutation Testing</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Empirical validation of SLMs reveals severe question-order bias (up to 25% variance across original, reversed, and permuted questions). 
            Our jury engine automatically applies question-order permutation compensation before calculating the aggregate compliance score.
          </p>
        </div>

        <div className="space-y-2.5">
          <div className="flex items-center space-x-2 text-slate-200 font-bold text-sm font-sans">
            <UserCheck className="h-4 w-4 text-[#f59e0b]" />
            <span>Automated Escalation Threshold (U ≥ 0.35)</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            When inter-judge disagreement exceeds the regulatory threshold ($U \ge 0.35$), the system operationalizes EU AI Act Article 26(2) by automatically quarantining the request and routing the full execution trace to the Human Compliance Officer queue.
          </p>
        </div>
      </div>

      {/* Recent Jury Decisions */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-slate-200 font-sans">
          Recent Multi-SLM Jury Decisions
        </h3>

        <div className="space-y-3">
          {recentJurySpans.map((span) => (
            <div key={span.span_id} className="p-5 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
              <div className="flex items-center justify-between font-mono">
                <div className="flex items-center space-x-2.5 text-xs">
                  <span className="font-bold text-slate-200">{span.span_id}</span>
                  <span className="text-slate-500">&bull;</span>
                  <span className="text-slate-400 font-sans">{span.application_name}</span>
                </div>
                <div className="flex items-center space-x-4 text-xs">
                  <span className="text-slate-400">
                    Uncertainty: <strong className="text-slate-200">{span.jury_evaluation.regulatory_uncertainty_signal.toFixed(2)}</strong>
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    span.verdict.includes('BLOCKED') ? 'bg-rose-500/10 text-rose-400' :
                    span.verdict.includes('QUARANTINED') ? 'bg-amber-500/10 text-amber-400' :
                    'bg-emerald-500/10 text-emerald-400'
                  }`}>
                    {span.verdict}
                  </span>
                </div>
              </div>

              {/* Individual Judge Scorecards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {span.jury_evaluation.votes.map((vote, vIdx) => (
                  <div key={vIdx} className="p-3.5 rounded-lg bg-[#0c101a] border border-[#1a2336] text-xs">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-slate-300 text-[11px] truncate font-mono">{vote.judge_name}</span>
                      <span className={vote.compliant ? 'text-[#84cc16] font-bold font-mono' : 'text-rose-400 font-bold font-mono'}>
                        {(vote.compliance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed font-sans">{vote.rationale}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
