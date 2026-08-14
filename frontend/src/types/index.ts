export interface PIIEntity {
  entity_type: string;
  text: string;
  start: number;
  end: number;
  score: number;
  action_taken: string;
}

export interface InjectionResult {
  is_injection: boolean;
  risk_score: number;
  attack_category?: string;
  detected_patterns: string[];
}

export interface JudgeVote {
  judge_name: string;
  framework: string;
  compliant: boolean;
  compliance_score: number;
  rationale: string;
  primary_risk?: string;
}

export interface JuryEvaluation {
  overall_verdict: "PASSED" | "FLAGGED_FOR_REVIEW" | "BLOCKED";
  overall_compliance_score: number;
  regulatory_uncertainty_signal: number;
  requires_human_oversight: boolean;
  votes: JudgeVote[];
  permutation_tested: boolean;
  calibrated_disagreement_index: number;
}

export interface KnowledgeGraphDiff {
  evaluated: boolean;
  factual_consistency_score: number;
  detected_hallucinations: string[];
  missing_ground_truth_edges: string[];
}

export interface GovernanceSpan {
  span_id: string;
  trace_id: string;
  timestamp: string;
  client_type: "SDK_DECORATOR" | "PROXY_GATEWAY" | "DIRECT_API";
  profile_id: string;
  enforcement_mode: "active_block" | "audit_passive" | "redact_forward";
  application_name: string;
  user_id?: string;
  
  gen_ai_system: string;
  gen_ai_request_model: string;
  gen_ai_response_model: string;
  gen_ai_operation_name: string;
  gen_ai_usage_input_tokens: number;
  gen_ai_usage_output_tokens: number;
  gen_ai_total_cost_usd: number;
  
  latency_deterministic_ms: number;
  latency_jury_ms: number;
  latency_upstream_ms: number;
  latency_total_ms: number;
  
  raw_prompt: string;
  sanitized_prompt: string;
  response_text: string;
  
  pii_entities: PIIEntity[];
  injection_result: InjectionResult;
  jury_evaluation: JuryEvaluation;
  kg_diff: KnowledgeGraphDiff;
  
  verdict: "APPROVED" | "BLOCKED_PII" | "BLOCKED_INJECTION" | "QUARANTINED_UNCERTAINTY" | "REDACTED_AND_SERVED" | "AUDIT_LOGGED_VIOLATION";
  block_reason?: string;
  
  previous_span_hash: string;
  current_span_hash: string;
  cryptographic_signature: string;
}

export interface GovernanceProfile {
  profile_id: string;
  name: string;
  description: string;
  target_environment: string;
  default_mode: "active_block" | "audit_passive" | "redact_forward";
  pii_policy: string;
  injection_threshold: number;
  uncertainty_escalation_threshold: number;
  context_injection_template: string;
  preferred_models: string[];
  is_active: boolean;
}

export interface HumanReviewItem {
  review_id: string;
  span_id: string;
  timestamp: string;
  profile_id: string;
  prompt_snippet: string;
  response_snippet: string;
  uncertainty_score: number;
  flags: string[];
  status: "PENDING" | "APPROVED" | "REJECTED_QUARANTINED" | "REVOKED_CREDENTIALS";
  arbitrated_by?: string;
  arbitrated_at?: string;
  notes?: string;
}

export interface MetricsSummary {
  total_governed_spans: number;
  violation_prevention_rate_vpr: number;
  total_blocked_attacks: number;
  total_pii_redactions: number;
  total_quarantined_uncertain: number;
  mean_deterministic_latency_ms: number;
  total_processed_tokens: number;
  cost_saved_usd: number;
  pending_human_reviews: number;
  eu_ai_act_compliance_level: string;
}
