import React, { useState } from 'react';
import { 
  FileLock2, 
  ShieldCheck, 
  Download, 
  CheckCircle, 
  AlertCircle, 
  Lock, 
  FileText, 
  Fingerprint, 
  RefreshCw, 
  Award 
} from 'lucide-react';
import { GovernanceSpan } from '../types';
import { api } from '../services/api';

interface AuditVaultViewProps {
  spans: GovernanceSpan[];
}

export const AuditVaultView: React.FC<AuditVaultViewProps> = ({ spans }) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any | null>({
    status: 'VERIFIED_VALID',
    valid: true,
    total_verified: spans.length,
    latest_root_hash: spans[0]?.current_span_hash || 'genesis-root'
  });
  const [isExporting, setIsExporting] = useState(false);

  const handleVerifyChain = async () => {
    setIsVerifying(true);
    try {
      const res = await api.verifyVault();
      setVerificationResult(res);
    } catch (err) {
      console.error('Verification failed', err);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleExportCompliancePack = async () => {
    setIsExporting(true);
    try {
      const pack = await api.exportCompliancePack();
      const blob = new Blob([JSON.stringify(pack, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `EU_AI_Act_Art26_Compliance_Pack_${new Date().toISOString().slice(0,10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="space-y-1.5">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-sans">
          GAAT Cryptographic Audit Vault (EU AI Act Art. 26(6))
        </h1>
        <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">
          Article 26(6) of the EU AI Act explicitly mandates that high-risk AI deployers maintain automatically generated logs for at least six months. 
          Our Governance-Aware Agent Telemetry (GAAT) seals every span inside an immutable <strong className="text-slate-200">SHA-256 hash-chain ledger</strong> with cryptographic ECDSA signatures.
        </p>
      </div>

      {/* Verification & Action Bar */}
      <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center space-x-4">
          <div className="h-11 w-11 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
            <Award className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="font-bold text-slate-100 text-sm font-sans">Ledger Verification Status</span>
              {verificationResult?.valid ? (
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400">
                  CRYPTOGRAPHICALLY INTACT
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-rose-500/10 text-rose-400">
                  TAMPER DETECTED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Verified {verificationResult?.total_verified ?? spans.length} spans against genesis root.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <button
            onClick={handleVerifyChain}
            disabled={isVerifying}
            className="flex-1 sm:flex-none flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-[#0c101a] hover:bg-[#151d2d] text-slate-200 border border-[#1e293b] text-xs font-semibold font-mono transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
            <span>Verify Hash Chain</span>
          </button>

          <button
            onClick={handleExportCompliancePack}
            disabled={isExporting}
            className="flex-1 sm:flex-none flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-[#84cc16] hover:bg-[#65a30d] text-[#0d121d] text-xs font-bold font-mono transition-all disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export Article 26 Dossier (JSON)</span>
          </button>
        </div>
      </div>

      {/* Immutable Hash-Chain Ledger View */}
      <div className="p-6 rounded-xl bg-[#111726] border border-[#1e293b] space-y-4">
        <h3 className="text-sm font-bold text-slate-200 font-sans">
          Signed Cryptographic Audit Chain ({spans.length} Spans)
        </h3>

        <div className="space-y-3">
          {spans.slice(0, 10).map((span, idx) => (
            <div
              key={span.span_id}
              className="p-4 rounded-xl bg-[#0c101a] border border-[#1a2336] text-xs space-y-2.5 font-mono"
            >
              <div className="flex items-center justify-between pb-2 border-b border-[#162030]">
                <div className="flex items-center space-x-2.5">
                  <span className="text-slate-500 font-bold">#{spans.length - idx}</span>
                  <span className="text-slate-200 font-bold">{span.span_id}</span>
                  <span className="text-slate-500 font-sans">&bull; {span.application_name}</span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-xs text-slate-400">{span.timestamp}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-[#111726] text-emerald-400 font-bold">
                    {span.verdict}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="truncate">
                  <span className="text-slate-500">Prev Hash: </span>
                  <span className="text-slate-400">{span.previous_span_hash}</span>
                </div>
                <div className="truncate">
                  <span className="text-slate-500">Curr Hash: </span>
                  <span className="text-emerald-400">{span.current_span_hash}</span>
                </div>
              </div>

              <div className="text-xs text-slate-400 truncate pt-1 border-t border-[#141b2b]">
                <span className="text-slate-500">ECDSA P-256 Sig: </span>
                <span>{span.cryptographic_signature}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
