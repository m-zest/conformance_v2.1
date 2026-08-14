import React, { useState } from 'react';
import { 
  Network, 
  Database, 
  CheckCircle2, 
  AlertTriangle, 
  Layers, 
  ShieldCheck, 
  Info, 
  Play, 
  Building2, 
  DollarSign, 
  MapPin, 
  Scale, 
  FileText, 
  Lock 
} from 'lucide-react';

export const KnowledgeGraphView: React.FC = () => {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('acme_corp');
  const [testQuery, setTestQuery] = useState('What was ACME Corp\'s total 2025 revenue and headquarter location?');
  const [simulatedResponse, setSimulatedResponse] = useState<string | null>(null);
  const [hallucinationResult, setHallucinationResult] = useState<any | null>(null);

  const nodes = [
    { id: 'acme_corp', label: 'ACME Enterprise Corp', type: 'ORGANIZATION', category: 'Enterprise Core', x: 280, y: 190, icon: Building2, color: '#38bdf8' },
    { id: 'rev_2025', label: '$4.2B USD', type: 'METRIC', category: 'Financial Fact', x: 120, y: 80, icon: DollarSign, color: '#34d399' },
    { id: 'hq_zurich', label: 'Zurich, Switzerland', type: 'LOCATION', category: 'Jurisdiction', x: 440, y: 80, icon: MapPin, color: '#34d399' },
    { id: 'eu_ai_act', label: 'EU AI Act (2024/1689)', type: 'REGULATION', category: 'Statutory Body', x: 120, y: 300, icon: Scale, color: '#818cf8' },
    { id: 'art_26', label: 'Article 26 Deployer Mandate', type: 'LEGAL_CLAUSE', category: 'Compliance Obligation', x: 280, y: 350, icon: FileText, color: '#a78bfa' },
    { id: 'gdpr', label: 'GDPR (EU 2016/679)', type: 'REGULATION', category: 'Privacy Regulation', x: 440, y: 300, icon: Lock, color: '#fbbf24' },
  ];

  const edges = [
    { source: 'acme_corp', target: 'rev_2025', relation: 'audited_revenue_2025' },
    { source: 'acme_corp', target: 'hq_zurich', relation: 'headquarters_at' },
    { source: 'acme_corp', target: 'eu_ai_act', relation: 'governed_by' },
    { source: 'eu_ai_act', target: 'art_26', relation: 'enforces_continuous_monitoring' },
    { source: 'acme_corp', target: 'gdpr', relation: 'subject_to_data_sovereignty' }
  ];

  const triples = [
    { subject: 'ACME Enterprise Corp', predicate: 'audited_revenue_2025', object: '$4.2B USD', status: 'VERIFIED_GROUND_TRUTH' },
    { subject: 'ACME Enterprise Corp', predicate: 'headquarters_at', object: 'Zurich, Switzerland', status: 'VERIFIED_GROUND_TRUTH' },
    { subject: 'EU AI Act (2024/1689)', predicate: 'enforces_obligation', object: 'Article 26 Deployer Mandate (Continuous Monitoring)', status: 'VERIFIED_GROUND_TRUTH' },
    { subject: 'Article 26 Deployer Mandate', predicate: 'mandates_log_retention', object: '6 Months Minimum Immutable Cryptographic Chain', status: 'VERIFIED_GROUND_TRUTH' },
    { subject: 'GDPR (EU 2016/679)', predicate: 'prohibits_unredacted_transfer', object: 'Article 44 International PII Transfer Restrictions', status: 'VERIFIED_GROUND_TRUTH' },
    { subject: 'TalentMatch AI', predicate: 'classified_as', object: 'Annex III High-Risk Employment Screening', status: 'VERIFIED_GROUND_TRUTH' }
  ];

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || nodes[0];

  const handleTestSimulation = (type: 'accurate' | 'hallucinated') => {
    if (type === 'accurate') {
      const resp = "ACME Corp reported $4.2B in audited annual revenue for 2025, with global corporate headquarters in Zurich, Switzerland.";
      setSimulatedResponse(resp);
      setHallucinationResult({
        score: 1.0,
        status: 'VERIFIED_CONSISTENT',
        conflicts: []
      });
    } else {
      const resp = "ACME Corp reported $25 Billion in revenue for 2025, and their primary corporate headquarters is located in Tokyo, Japan.";
      setSimulatedResponse(resp);
      setHallucinationResult({
        score: 0.45,
        status: 'FACTUAL_HALLUCINATION_DETECTED',
        conflicts: [
          "Claimed ACME Corp revenue ($25 Billion) conflicts with verified ground truth ($4.2B USD)",
          "Claimed HQ (Tokyo, Japan) conflicts with verified ground truth (Zurich, Switzerland)"
        ]
      });
    }
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-sans">
            Enterprise Knowledge Graph (Ground Truth Verification)
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic semantic entity triples (Subject &rarr; Predicate &rarr; Object) validating LLM factual consistency
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-mono font-semibold border border-emerald-500/20">
            &bull; 6 Active Ground Truth Entities
          </span>
        </div>
      </div>

      {/* Visual Knowledge Graph Canvas + Node Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: SVG Topological Graph Canvas */}
        <div className="lg:col-span-8 p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase font-semibold text-slate-400 tracking-wider flex items-center space-x-2">
              <Network className="h-4 w-4 text-[#84cc16]" />
              <span>SEMANTIC TOPOLOGY MAP</span>
            </span>
            <span className="text-xs text-slate-400 font-mono">Click any node to inspect</span>
          </div>

          {/* SVG Canvas */}
          <div className="relative w-full h-96 bg-[#0a0e17] rounded-xl border border-[#162030] overflow-hidden flex items-center justify-center">
            <svg viewBox="0 0 580 420" className="w-full h-full">
              {/* Connecting Edges */}
              {edges.map((edge, idx) => {
                const s = nodes.find(n => n.id === edge.source)!;
                const t = nodes.find(n => n.id === edge.target)!;
                const midX = (s.x + t.x) / 2;
                const midY = (s.y + t.y) / 2;

                return (
                  <g key={idx}>
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke="#223048"
                      strokeWidth="2"
                      strokeDasharray="4 2"
                    />
                    {/* Relation Label Pill */}
                    <rect
                      x={midX - 45}
                      y={midY - 9}
                      width="90"
                      height="18"
                      rx="4"
                      fill="#0e1524"
                      stroke="#1b263b"
                    />
                    <text
                      x={midX}
                      y={midY + 3}
                      textAnchor="middle"
                      fill="#64748b"
                      fontSize="8"
                      fontFamily="JetBrains Mono, monospace"
                    >
                      {edge.relation}
                    </text>
                  </g>
                );
              })}

              {/* Node Circles */}
              {nodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isConflicted = hallucinationResult?.status === 'FACTUAL_HALLUCINATION_DETECTED' && 
                  (node.id === 'rev_2025' || node.id === 'hq_zurich');

                return (
                  <g
                    key={node.id}
                    onClick={() => setSelectedNodeId(node.id)}
                    className="cursor-pointer transition-transform hover:scale-105"
                  >
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.id === 'acme_corp' ? 36 : 28}
                      fill={isConflicted ? '#450a0a' : isSelected ? '#16233b' : '#0e1624'}
                      stroke={isConflicted ? '#f87171' : isSelected ? '#38bdf8' : '#223048'}
                      strokeWidth={isSelected ? '3' : '1.5'}
                    />
                    <text
                      x={node.x}
                      y={node.y + 45}
                      textAnchor="middle"
                      fill={isSelected ? '#f8fafc' : '#94a3b8'}
                      fontSize="10"
                      fontWeight={isSelected ? 'bold' : 'normal'}
                      fontFamily="Inter, sans-serif"
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Right: Selected Node Properties & Truth Inspector */}
        <div className="lg:col-span-4 space-y-4">
          <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
            <div className="flex items-center space-x-2.5 pb-3 border-b border-[#1a2336]">
              <Database className="h-5 w-5 text-[#84cc16]" />
              <h3 className="font-bold text-slate-100 text-sm font-sans">Entity Truth Card</h3>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">Entity Identifier:</span>
                <p className="text-slate-100 font-bold font-mono text-sm mt-0.5">{selectedNode.label}</p>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">Semantic Category:</span>
                <p className="text-slate-300 font-medium font-sans mt-0.5">{selectedNode.category}</p>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">Verification Status:</span>
                <div className="flex items-center space-x-1.5 mt-1">
                  <CheckCircle2 className="h-4 w-4 text-[#84cc16]" />
                  <span className="text-[#84cc16] font-mono font-semibold">VERIFIED GROUND TRUTH</span>
                </div>
              </div>
            </div>
          </div>

          {/* Test Hallucination Simulator */}
          <div className="p-5 rounded-xl bg-[#111726] border border-[#1e293b] space-y-3">
            <span className="text-[11px] font-mono uppercase font-bold text-slate-400 tracking-wider">
              TEST HALLUCINATION VERIFIER
            </span>
            <p className="text-xs text-slate-400">
              Simulate an LLM response to see the Knowledge Graph contrast the output facts:
            </p>

            <div className="flex flex-col gap-2 pt-1">
              <button
                onClick={() => handleTestSimulation('accurate')}
                className="w-full py-2 px-3 rounded-lg bg-[#0c101a] hover:bg-[#161f33] border border-[#1e293b] text-xs font-semibold text-slate-200 text-left transition-all"
              >
                &#10003; Test Accurate Output ($4.2B / Zurich)
              </button>

              <button
                onClick={() => handleTestSimulation('hallucinated')}
                className="w-full py-2 px-3 rounded-lg bg-[#0c101a] hover:bg-rose-950/30 border border-rose-500/30 text-xs font-semibold text-rose-300 text-left transition-all"
              >
                &times; Test Hallucinated Output ($25B / Tokyo)
              </button>
            </div>

            {simulatedResponse && (
              <div className="p-3 rounded-lg bg-[#0a0e17] border border-[#162030] text-xs space-y-2 mt-2">
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Consistency Score:</span>
                  <span className={hallucinationResult.score === 1.0 ? 'text-[#84cc16] font-bold' : 'text-rose-400 font-bold'}>
                    {(hallucinationResult.score * 100).toFixed(0)}%
                  </span>
                </div>

                <p className="text-slate-300 text-xs font-mono">{simulatedResponse}</p>

                {hallucinationResult.conflicts.length > 0 && (
                  <div className="pt-2 border-t border-[#1a2336] space-y-1 text-rose-400 text-[11px]">
                    {hallucinationResult.conflicts.map((c: string, cIdx: number) => (
                      <div key={cIdx} className="flex items-start space-x-1.5">
                        <span>&bull;</span>
                        <span>{c}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Semantic Triples Table */}
      <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
        <h3 className="text-sm font-bold text-slate-100 font-sans">
          Ground Truth Entity Triples Matrix
        </h3>

        <div className="overflow-x-auto rounded-lg border border-[#1e293b] bg-[#0a0e17]">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0e1422] text-slate-400 border-b border-[#1e293b] text-[10px] uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Subject</th>
                <th className="py-3 px-4">Predicate (Relationship)</th>
                <th className="py-3 px-4">Object (Ground Truth Fact)</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#162030]">
              {triples.map((t, idx) => (
                <tr key={idx} className="hover:bg-[#121929] transition-colors">
                  <td className="py-3 px-4 text-slate-200 font-semibold">{t.subject}</td>
                  <td className="py-3 px-4 text-slate-400">{t.predicate}</td>
                  <td className="py-3 px-4 text-slate-100 font-medium">{t.object}</td>
                  <td className="py-3 px-4 text-right">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                      {t.status}
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
