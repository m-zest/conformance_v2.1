from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False
    profile_id: Optional[str] = "default_customer_support"
    enforcement_mode: Optional[Literal["active_block", "audit_passive", "redact_forward"]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"

class UsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: UsageStats
    governance_metadata: Optional[Dict[str, Any]] = None

class PIIEntity(BaseModel):
    entity_type: str
    text: str
    start: int
    end: int
    score: float
    action_taken: str  # "redacted", "tokenized", "flagged"

class InjectionResult(BaseModel):
    is_injection: bool
    risk_score: float  # 0.0 to 1.0
    attack_category: Optional[str] = None  # "direct_override", "jailbreak_dan", "system_prompt_leak", "tool_exfiltration"
    detected_patterns: List[str] = Field(default_factory=list)

class JudgeVote(BaseModel):
    judge_name: str  # e.g. "EU AI Act Art. 26 Judge (phi4-mini)"
    framework: str   # "EU_AI_ACT", "GDPR", "ANSSI"
    compliant: bool
    compliance_score: float  # 0.0 to 1.0
    rationale: str
    primary_risk: Optional[str] = None

class JuryEvaluation(BaseModel):
    overall_verdict: Literal["PASSED", "FLAGGED_FOR_REVIEW", "BLOCKED"]
    overall_compliance_score: float
    regulatory_uncertainty_signal: float  # 0.0 (unanimous) to 1.0 (high disagreement)
    requires_human_oversight: bool
    votes: List[JudgeVote]
    permutation_tested: bool = True
    calibrated_disagreement_index: float

class KnowledgeGraphDiff(BaseModel):
    evaluated: bool = False
    factual_consistency_score: float = 1.0
    detected_hallucinations: List[str] = Field(default_factory=list)
    missing_ground_truth_edges: List[str] = Field(default_factory=list)

class GovernanceSpan(BaseModel):
    span_id: str
    trace_id: str
    timestamp: str
    client_type: str  # "SDK_DECORATOR", "PROXY_GATEWAY", "DIRECT_API"
    profile_id: str
    enforcement_mode: str  # "active_block", "audit_passive", "redact_forward"
    application_name: str
    user_id: Optional[str] = "corp_internal_user"
    
    # GenAI Semantic Conventions (gen_ai.*)
    gen_ai_system: str = "openai-compatible"
    gen_ai_request_model: str
    gen_ai_response_model: str
    gen_ai_operation_name: str = "chat"
    gen_ai_usage_input_tokens: int
    gen_ai_usage_output_tokens: int
    gen_ai_total_cost_usd: float
    
    # Latencies in milliseconds
    latency_deterministic_ms: float
    latency_jury_ms: float
    latency_upstream_ms: float
    latency_total_ms: float
    
    # Payload details
    raw_prompt: str
    sanitized_prompt: str
    response_text: str
    
    # Security & Governance Results
    pii_entities: List[PIIEntity] = Field(default_factory=list)
    injection_result: InjectionResult
    jury_evaluation: JuryEvaluation
    kg_diff: KnowledgeGraphDiff
    
    verdict: Literal["APPROVED", "BLOCKED_PII", "BLOCKED_INJECTION", "QUARANTINED_UNCERTAINTY", "REDACTED_AND_SERVED", "AUDIT_LOGGED_VIOLATION"]
    block_reason: Optional[str] = None
    
    # GAAT Cryptographic Signature & Hash Chain
    previous_span_hash: str
    current_span_hash: str
    cryptographic_signature: str

class GovernanceProfile(BaseModel):
    profile_id: str
    name: str
    description: str
    target_environment: str  # "public_customer_support", "internal_code_assistant", "hr_screening_high_risk", "financial_advisory"
    default_mode: Literal["active_block", "audit_passive", "redact_forward"]
    pii_policy: str  # "strict_redact", "mask_and_block", "tokenize"
    injection_threshold: float  # e.g., 0.70
    uncertainty_escalation_threshold: float  # e.g., 0.35
    context_injection_template: str
    preferred_models: List[str]
    is_active: bool = True

class HumanReviewItem(BaseModel):
    review_id: str
    span_id: str
    timestamp: str
    profile_id: str
    prompt_snippet: str
    response_snippet: str
    uncertainty_score: float
    flags: List[str]
    status: Literal["PENDING", "APPROVED", "REJECTED_QUARANTINED", "REVOKED_CREDENTIALS"]
    arbitrated_by: Optional[str] = None
    arbitrated_at: Optional[str] = None
    notes: Optional[str] = None
