import React, { useState } from 'react';
import { 
  ShieldAlert, 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  Lock, 
  FileText, 
  Activity, 
  Scale, 
  AlertTriangle, 
  Cpu, 
  Layers, 
  Play, 
  Database,
  Fingerprint,
  Zap,
  Terminal,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { GovernanceSpan } from '../types';

interface PitchDeckViewProps {
  spans?: GovernanceSpan[];
  onSelectScenario: (scenarioId: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const PitchDeckView: React.FC<PitchDeckViewProps> = ({
  spans = [],
  onSelectScenario,
  onNavigateTab
}) => {
  const [triggeringScenario, setTriggeringScenario] = useState<string | null>(null);

  const handleRunScenario = async (scenarioId: string, targetTab: string = 'signal_feed') => {
    try {
      setTriggeringScenario(scenarioId);
      await api.triggerScenario(scenarioId);
      setTimeout(() => {
        setTriggeringScenario(null);
        onNavigateTab(targetTab);
      }, 800);
    } catch (err) {
      console.error('Failed to run scenario', err);
      setTriggeringScenario(null);
    }
  };

  return (
    <div className="space-y-10 pb-16">
      {/* Hero Problem Statement */}
      <section className="rounded-xl bg-[#111726] border border-[#1e293b] p-8 sm:p-10 space-y-5">
        <div className="max-w-4xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#182234] border border-[#23314a] text-slate-300 text-xs font-mono font-medium">
            <Sparkles className="h-3.5 w-3.5 text-[#84cc16]" />
            <span>Research-Backed Enterprise Blueprint (arXiv:2605.24737 & arXiv:2604.05119)</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-slate-100 leading-tight">
            Continuous Enterprise AI Governance: <br />
            <span className="text-[#84cc16]">
              The Sovereign Runtime Control Plane
            </span>
          </h1>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-3xl">
            Static point-in-time audits create the <strong className="text-rose-400 font-semibold">"Compliance Fiction"</strong>—the dangerous illusion that an AI model evaluated once remains compliant throughout its operational lifecycle. 
            Our platform turns compliance into an <strong className="text-[#84cc16] font-semibold">automated continuous runtime signal</strong> with sub-15ms deterministic guardrails, local Multi-SLM jury panels, and cryptographic GAAT audit chains.
          </p>

          <div className="pt-2 flex flex-wrap gap-4">
            <button
              onClick={() => onNavigateTab('inspector')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-[#84cc16] hover:bg-[#65a30d] text-[#0d121d] font-bold text-xs shadow-sm transition-all"
            >
              <span>Open Inspector Sandbox</span>
              <ArrowRight className="h-4 w-4" />
            </button>

            <button
              onClick={() => onNavigateTab('signal_feed')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-[#0c101a] hover:bg-[#151d2d] border border-[#1e293b] text-slate-200 font-semibold text-xs transition-all"
            >
              <Activity className="h-4 w-4 text-slate-400" />
              <span>Inspect Signal Feed</span>
            </button>
          </div>
        </div>
      </section>

      {/* Interactive Live Attack Scenarios (1-Click Pitch Demonstrations) */}
      <section className="space-y-5">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2 font-sans">
            <Play className="h-4 w-4 text-[#84cc16]" />
            <span>Interactive 1-Click Attack & Compliance Scenarios</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Click any scenario to inject real adversarial traffic through the proxy and watch the live guardrails react.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Scenario 1 */}
          <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  GDPR & GARANTE PRECEDENT
                </span>
                <span className="text-xs text-slate-400 font-mono">0.18ms Det.</span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm mb-1.5 font-sans">
                Shadow AI Customer PII Leakage
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Employee pastes customer SSN & Credit Card into an unvetted model. Intercepted by Presidio layer and sanitized before upstream network boundary.
              </p>
            </div>
            <button
              onClick={() => handleRunScenario('scenario_pii_leakage', 'signal_feed')}
              disabled={triggeringScenario !== null}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-lg bg-[#0c101a] hover:bg-[#151d2d] text-slate-200 border border-[#1e293b] text-xs font-semibold transition-all disabled:opacity-50"
            >
              {triggeringScenario === 'scenario_pii_leakage' ? (
                <span>Executing Stream...</span>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current text-[#84cc16]" />
                  <span>Simulate PII Interception</span>
                </>
              )}
            </button>
          </div>

          {/* Scenario 2 */}
          <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  ANSSI AI SECURITY
                </span>
                <span className="text-xs text-slate-400 font-mono">98.3% VPR</span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm mb-1.5 font-sans">
                Recursive DAN Jailbreak Attack
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Adversary attempts system prompt escape and credential dumping. Zero-Trust classifier drops request with 403 refusal in &lt;15ms.
              </p>
            </div>
            <button
              onClick={() => handleRunScenario('scenario_jailbreak_attack', 'signal_feed')}
              disabled={triggeringScenario !== null}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-lg bg-[#0c101a] hover:bg-[#151d2d] text-slate-200 border border-[#1e293b] text-xs font-semibold transition-all disabled:opacity-50"
            >
              {triggeringScenario === 'scenario_jailbreak_attack' ? (
                <span>Executing Stream...</span>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current text-[#84cc16]" />
                  <span>Simulate Jailbreak Block</span>
                </>
              )}
            </button>
          </div>

          {/* Scenario 3 */}
          <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  EU AI ACT ART. 26(2)
                </span>
                <span className="text-xs text-slate-400 font-mono">U = 0.48 Disagreement</span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm mb-1.5 font-sans">
                High-Risk HR Bias Escalation
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Annex III employment screening prompt triggers divergent SLM jury votes. Quarantined and routed to human compliance officer queue.
              </p>
            </div>
            <button
              onClick={() => handleRunScenario('scenario_high_risk_hr_uncertainty', 'signal_feed')}
              disabled={triggeringScenario !== null}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-lg bg-[#0c101a] hover:bg-[#151d2d] text-slate-200 border border-[#1e293b] text-xs font-semibold transition-all disabled:opacity-50"
            >
              {triggeringScenario === 'scenario_high_risk_hr_uncertainty' ? (
                <span>Executing Stream...</span>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current text-[#84cc16]" />
                  <span>Trigger Human Review Flow</span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Comparative Architecture: Legacy vs Runtime Control Plane */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center border border-rose-500/20">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-sm">Static Point-in-Time Audits</h3>
              <p className="text-[11px] text-rose-400/90 font-mono font-medium">THE "COMPLIANCE FICTION"</p>
            </div>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-400 font-sans">
            <li className="flex items-start space-x-2">
              <span className="text-rose-400 font-bold">&times;</span>
              <span>Point-in-time penetration tests and annual static PDF checklists.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-rose-400 font-bold">&times;</span>
              <span>Blind to non-deterministic model drift, prompt injection, and tool misuse.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-rose-400 font-bold">&times;</span>
              <span>Direct non-compliance with EU AI Act Art. 26 continuous monitoring obligation.</span>
            </li>
          </ul>
        </div>

        <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-lg bg-[#84cc16]/10 text-[#84cc16] flex items-center justify-center border border-[#84cc16]/20">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-sm">Our Continuous Runtime Control Plane</h3>
              <p className="text-[11px] text-[#84cc16] font-mono font-medium">CLOSED-LOOP GOVERNANCE (GAAT)</p>
            </div>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-300 font-sans">
            <li className="flex items-start space-x-2">
              <span className="text-[#84cc16] font-bold">&#10003;</span>
              <span>Tripartite Architecture: Python SDK Decorator + ASGI Proxy + Dashboard.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#84cc16] font-bold">&#10003;</span>
              <span>Multi-SLM Profile-as-Jury with quantifiable Regulatory Uncertainty Signal ($U$).</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#84cc16] font-bold">&#10003;</span>
              <span>Signed SHA-256 hash chains satisfying EU AI Act Art. 26(6) 6-month log retention.</span>
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
};
