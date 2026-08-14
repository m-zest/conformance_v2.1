import React, { useState } from 'react';
import { 
  UserCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  KeyRound, 
  ShieldAlert, 
  Clock, 
  FileText,
  Radio,
  Fingerprint
} from 'lucide-react';
import { HumanReviewItem } from '../types';
import { api } from '../services/api';

interface HumanReviewViewProps {
  reviews: HumanReviewItem[];
  onReviewUpdated: () => void;
}

export const HumanReviewView: React.FC<HumanReviewViewProps> = ({
  reviews,
  onReviewUpdated
}) => {
  const [selectedReview, setSelectedReview] = useState<HumanReviewItem | null>(null);
  const [arbitrationNotes, setArbitrationNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleArbitrate = async (decision: string) => {
    if (!selectedReview) return;
    setIsSubmitting(true);
    try {
      await api.arbitrateReview(
        selectedReview.review_id,
        decision,
        'Senior Compliance Officer (EU AI Act Lead)',
        arbitrationNotes
      );
      setSelectedReview(null);
      setArbitrationNotes('');
      onReviewUpdated();
    } catch (err) {
      console.error('Arbitration failed', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const pendingReviews = reviews.filter(r => r.status === 'PENDING');
  const resolvedReviews = reviews.filter(r => r.status !== 'PENDING');

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-[#080d1a] border border-slate-800 space-y-2">
        <div className="flex items-center space-x-3">
          <UserCheck className="h-6 w-6 text-amber-400" />
          <h2 className="text-xl font-bold text-white tracking-tight font-sans">
            EU AI Act Article 26(2) Human Oversight & Arbitration
          </h2>
        </div>
        <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
          The EU AI Act mandates that high-risk AI deployers assign continuous human oversight to natural persons with authority to intervene. 
          Interactions with high <strong className="text-amber-300">Regulatory Uncertainty ($U \ge 0.35$)</strong> or Annex III bias signals are quarantined here for manual compliance arbitration.
        </p>
      </div>

      {/* Review Queue Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Pending List */}
        <div className="lg:col-span-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider font-mono flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4" />
              <span>Pending Escalations ({pendingReviews.length})</span>
            </h3>
          </div>

          <div className="space-y-3">
            {pendingReviews.length === 0 ? (
              <div className="p-8 rounded-2xl bg-[#080d1a] border border-slate-800 text-center text-slate-500 font-mono text-xs">
                No pending items in human oversight queue. All operational signals nominal.
              </div>
            ) : (
              pendingReviews.map((rev) => (
                <div
                  key={rev.review_id}
                  onClick={() => setSelectedReview(rev)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    selectedReview?.review_id === rev.review_id
                      ? 'bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-500/10'
                      : 'bg-[#080d1a] border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-amber-400">{rev.review_id}</span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Uncertainty: <strong className="text-amber-300">{rev.uncertainty_score.toFixed(2)}</strong>
                    </span>
                  </div>

                  <div className="text-xs text-slate-200 font-mono mb-2 line-clamp-2">
                    "{rev.prompt_snippet}"
                  </div>

                  <div className="flex flex-wrap gap-1 mt-2">
                    {rev.flags.map((flag, fIdx) => (
                      <span key={fIdx} className="px-2 py-0.5 rounded text-[9px] font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20">
                        {flag}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Resolved History */}
          {resolvedReviews.length > 0 && (
            <div className="pt-6 space-y-3">
              <h3 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider">
                Recent Arbitrations ({resolvedReviews.length})
              </h3>
              <div className="space-y-2">
                {resolvedReviews.map((rev) => (
                  <div key={rev.review_id} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono flex items-center justify-between">
                    <div>
                      <span className="text-slate-300 font-bold mr-2">{rev.review_id}</span>
                      <span className="text-slate-400 font-sans truncate max-w-xs inline-block">{rev.prompt_snippet}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                      rev.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      {rev.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Arbitration Action Box */}
        <div className="lg:col-span-6">
          {selectedReview ? (
            <div className="p-6 rounded-2xl bg-[#080d1a] border border-slate-800 space-y-5 sticky top-24 shadow-2xl animate-in fade-in">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h3 className="font-bold text-slate-100 text-sm font-sans">
                    Arbitration Case: {selectedReview.review_id}
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">
                    Span Ref: {selectedReview.span_id} &bull; Profile: {selectedReview.profile_id}
                  </span>
                </div>
                <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  Awaiting Decision
                </span>
              </div>

              {/* Snippets */}
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 font-medium font-sans">Intercepted Prompt:</span>
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-200 mt-1 whitespace-pre-wrap">
                    {selectedReview.prompt_snippet}
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 font-medium font-sans">Model Output:</span>
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-200 mt-1 whitespace-pre-wrap">
                    {selectedReview.response_snippet}
                  </div>
                </div>
              </div>

              {/* Compliance Notes Input */}
              <div className="space-y-1.5">
                <label className="text-xs text-slate-400 font-medium font-sans">
                  Compliance Officer Rationale & Notes:
                </label>
                <textarea
                  rows={3}
                  value={arbitrationNotes}
                  onChange={(e) => setArbitrationNotes(e.target.value)}
                  placeholder="Enter audit justification (recorded into cryptographic vault)..."
                  className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-3 gap-2 pt-2">
                <button
                  onClick={() => handleArbitrate('APPROVED')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center space-x-1.5 py-2 px-3 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 text-xs font-semibold transition-all disabled:opacity-50"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Approve & Release</span>
                </button>

                <button
                  onClick={() => handleArbitrate('REJECTED_QUARANTINED')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center space-x-1.5 py-2 px-3 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-all disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" />
                  <span>Quarantine Session</span>
                </button>

                <button
                  onClick={() => handleArbitrate('REVOKED_CREDENTIALS')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center space-x-1.5 py-2 px-3 rounded-lg bg-slate-800 hover:bg-rose-950/80 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-800 text-xs font-semibold transition-all disabled:opacity-50"
                >
                  <KeyRound className="h-4 w-4" />
                  <span>Revoke API Keys</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-2xl bg-[#080d1a] border border-slate-800 text-center space-y-3">
              <div className="h-12 w-12 rounded-full bg-slate-900 text-slate-400 flex items-center justify-center mx-auto border border-slate-800">
                <FileText className="h-6 w-6 text-cyan-400" />
              </div>
              <h4 className="font-semibold text-slate-300 text-sm">Select an Escalation Case</h4>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Click on any flagged item on the left to review the full interaction and execute regulatory arbitration.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
