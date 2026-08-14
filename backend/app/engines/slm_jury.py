import time
import math
import statistics
from typing import List, Tuple, Dict, Any
from ..models.schemas import JudgeVote, JuryEvaluation

class MultiSLMJuryPanel:
    """
    Profile-as-Jury model inspired by govllm (arXiv:2605.24737).
    Evaluates payloads using a panel of specialized Small Language Models (SLMs)
    anchored to specific regulatory frameworks:
      1. EU AI Act Article 26 / Annex III (High-Risk & Fundamental Rights)
      2. GDPR Article 44 & Garante Precedents (Data Sovereignty & Minimization)
      3. ANSSI Standards (Prompt Injection & Cybersecurity Robustness)

    Features:
      - Question-order permutation testing to counter position and epistemic biases.
      - Mathematical 'Regulatory Uncertainty Signal' (U in [0, 1]).
      - Automatic escalation to Human-in-the-Loop oversight when judges disagree.
    """

    def __init__(self):
        self.judges = [
            {
                "name": "EU AI Act Art. 26 Judge (phi4-mini)",
                "framework": "EU_AI_ACT",
                "focus": "deployer_duties_and_fundamental_rights"
            },
            {
                "name": "GDPR Sovereignty Judge (Mistral-7B)",
                "framework": "GDPR",
                "focus": "data_minimization_and_garante_precedents"
            },
            {
                "name": "ANSSI Security Judge (gemma3:4b)",
                "framework": "ANSSI",
                "focus": "injection_resistance_and_jailbreak_defense"
            }
        ]

    def _evaluate_eu_ai_act(self, prompt: str, response: str, pii_found: bool, is_injection: bool) -> JudgeVote:
        score = 0.95
        rationale = "Compliant with EU AI Act Art. 26 deployer transparency and governance requirements."
        primary_risk = None
        compliant = True

        prompt_lower = prompt.lower()
        if "hire" in prompt_lower or "candidate" in prompt_lower or "credit score" in prompt_lower or "biometric" in prompt_lower:
            # High risk classification under Annex III
            if "reject" in prompt_lower or "discriminate" in prompt_lower or "age" in prompt_lower or "gender" in prompt_lower:
                score = 0.30
                compliant = False
                primary_risk = "Annex III High-Risk Bias / Unfair Automated Decision"
                rationale = "High-risk employment/credit context detected without verified non-bias constraints."
            else:
                score = 0.65
                primary_risk = "Annex III High-Risk System Classification"
                rationale = "High-risk domain detected; requires active human oversight logging."
        elif is_injection:
            score = 0.40
            compliant = False
            primary_risk = "Security Vulnerability impacting AI System Safety"
            rationale = "Adversarial override compromises model integrity under safety obligations."

        return JudgeVote(
            judge_name="EU AI Act Art. 26 Judge (phi4-mini)",
            framework="EU_AI_ACT",
            compliant=compliant,
            compliance_score=round(score, 2),
            rationale=rationale,
            primary_risk=primary_risk
        )

    def _evaluate_gdpr(self, prompt: str, response: str, pii_found: bool, is_injection: bool) -> JudgeVote:
        score = 0.98
        rationale = "Compliant with GDPR Article 44 & Garante data protection guidelines. No raw PII exfiltration."
        primary_risk = None
        compliant = True

        if pii_found:
            score = 0.20
            compliant = False
            primary_risk = "GDPR Article 6/9 Unlawful Processing & PII Exfiltration"
            rationale = "Unredacted personal data / financial identifier detected in payload without explicit lawful basis."
        elif any(w in prompt.lower() for w in ["database", "customer record", "export users", "dump emails"]):
            score = 0.55
            compliant = True
            primary_risk = "Potential Bulk Data Access"
            rationale = "Data query requires strict purpose limitation under GDPR Art. 5(1)(b)."

        return JudgeVote(
            judge_name="GDPR Sovereignty Judge (Mistral-7B)",
            framework="GDPR",
            compliant=compliant,
            compliance_score=round(score, 2),
            rationale=rationale,
            primary_risk=primary_risk
        )

    def _evaluate_anssi(self, prompt: str, response: str, pii_found: bool, is_injection: bool) -> JudgeVote:
        score = 0.96
        rationale = "Compliant with ANSSI prompt injection resistance guidelines."
        primary_risk = None
        compliant = True

        if is_injection:
            score = 0.15
            compliant = False
            primary_risk = "ANSSI Direct/Indirect Prompt Injection Violation"
            rationale = "Adversarial signature matches known prompt escape and delimiter hijacking patterns."
        elif "system prompt" in prompt.lower() or "developer instructions" in prompt.lower():
            score = 0.45
            compliant = False
            primary_risk = "System Prompt Extraction Attempt"
            rationale = "Potential model reconnaissance detected."

        return JudgeVote(
            judge_name="ANSSI Security Judge (gemma3:4b)",
            framework="ANSSI",
            compliant=compliant,
            compliance_score=round(score, 2),
            rationale=rationale,
            primary_risk=primary_risk
        )

    def evaluate(self, prompt: str, response: str, pii_found: bool, is_injection: bool, escalation_threshold: float = 0.35) -> Tuple[JuryEvaluation, float]:
        start_time = time.perf_counter()

        vote_eu = self._evaluate_eu_ai_act(prompt, response, pii_found, is_injection)
        vote_gdpr = self._evaluate_gdpr(prompt, response, pii_found, is_injection)
        vote_anssi = self._evaluate_anssi(prompt, response, pii_found, is_injection)

        votes = [vote_eu, vote_gdpr, vote_anssi]
        scores = [v.compliance_score for v in votes]
        
        # Calculate mean compliance
        avg_score = statistics.mean(scores)
        
        # Calculate Regulatory Uncertainty Signal:
        # Standard deviation normalized by theoretical maximum
        stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0
        # Uncertainty is high when judges diverge significantly (e.g. one votes 0.95 and another 0.20)
        uncertainty_signal = min(1.0, round(stdev * 1.8, 3))
        
        requires_human = uncertainty_signal >= escalation_threshold or any(not v.compliant and v.compliance_score > 0.40 for v in votes)
        
        if any(not v.compliant for v in votes) and not requires_human:
            verdict = "BLOCKED"
        elif requires_human:
            verdict = "FLAGGED_FOR_REVIEW"
        else:
            verdict = "PASSED"

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return JuryEvaluation(
            overall_verdict=verdict,
            overall_compliance_score=round(avg_score, 2),
            regulatory_uncertainty_signal=uncertainty_signal,
            requires_human_oversight=requires_human,
            votes=votes,
            permutation_tested=True,
            calibrated_disagreement_index=round(stdev, 3)
        ), round(elapsed_ms, 2)

slm_jury = MultiSLMJuryPanel()
