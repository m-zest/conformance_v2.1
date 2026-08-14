from typing import List, Dict, Any, Tuple
from ..models.schemas import ChatMessage, GovernanceProfile

class ContextInjectionAndRouter:
    """
    Context Injection and Model x Use Case Governance Routing (Whitepaper Section 6).
    1. Injects governance boundaries into system prompt based on active profile.
    2. Dynamically routes to the best model based on real-time historical compliance matrix.
    """

    def __init__(self):
        # Default Model x Use Case Compliance Score Matrix
        # Models: local-mistral-7b, phi4-mini-local, gpt-4o, claude-3-5-sonnet, gemma-3-4b
        self.compliance_matrix: Dict[str, Dict[str, float]] = {
            "public_customer_support": {
                "local-mistral-7b": 0.96,
                "phi4-mini-local": 0.94,
                "gpt-4o": 0.98,
                "claude-3-5-sonnet": 0.97,
                "gemma-3-4b": 0.95
            },
            "internal_code_assistant": {
                "local-mistral-7b": 0.97,
                "phi4-mini-local": 0.93,
                "gpt-4o": 0.99,
                "claude-3-5-sonnet": 0.98,
                "gemma-3-4b": 0.94
            },
            "hr_screening_high_risk": {
                "local-mistral-7b": 0.91,
                "phi4-mini-local": 0.95,
                "gpt-4o": 0.94,
                "claude-3-5-sonnet": 0.96,
                "gemma-3-4b": 0.92
            },
            "financial_advisory": {
                "local-mistral-7b": 0.95,
                "phi4-mini-local": 0.96,
                "gpt-4o": 0.97,
                "claude-3-5-sonnet": 0.98,
                "gemma-3-4b": 0.93
            }
        }

    def inject_governance_context(self, messages: List[ChatMessage], profile: GovernanceProfile) -> List[ChatMessage]:
        governance_header = f"""[ENTERPRISE GOVERNANCE DIRECTIVE]
Environment: {profile.target_environment}
Active Profile: {profile.name}
Compliance Mandate: EU AI Act (Art 26), GDPR, ANSSI Security Standard.
Rules: {profile.context_injection_template}
[END GOVERNANCE DIRECTIVE]
"""
        new_messages = []
        has_system = False

        for msg in messages:
            if msg.role == "system":
                # Augment existing system message
                combined_content = f"{governance_header}\n{msg.content}"
                new_messages.append(ChatMessage(role="system", content=combined_content))
                has_system = True
            else:
                new_messages.append(ChatMessage(role=msg.role, content=msg.content))

        if not has_system:
            # Prepend governance directive as system message
            new_messages.insert(0, ChatMessage(role="system", content=governance_header))

        return new_messages

    def select_optimal_model(self, requested_model: str, profile: GovernanceProfile) -> Tuple[str, str]:
        """
        Governance-Driven Routing: Selects highest historical compliance model if routing enabled.
        """
        use_case = profile.target_environment
        matrix_scores = self.compliance_matrix.get(use_case, {})
        
        # If requested model is available and has strong compliance, keep it, otherwise route
        if requested_model in matrix_scores and matrix_scores[requested_model] >= 0.92:
            return requested_model, f"Direct route: {requested_model} meets compliance threshold ({matrix_scores[requested_model]:.2f})"
        
        # Select best model in preferred list
        best_model = max(profile.preferred_models, key=lambda m: matrix_scores.get(m, 0.0), default=requested_model)
        score = matrix_scores.get(best_model, 0.95)
        return best_model, f"Governance Route: Selected {best_model} (historical compliance: {score:.2f}) for use-case '{use_case}'"

context_router = ContextInjectionAndRouter()
