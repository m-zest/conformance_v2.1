import re
import time
from typing import List, Tuple
from ..models.schemas import InjectionResult

class InjectionGuardEngine:
    """
    Lightweight, high-accuracy Prompt Injection and Jailbreak detection engine.
    Detects direct prompt overrides, DAN roleplay patterns, system prompt extraction,
    and agentic tool exfiltration signatures.
    """

    def __init__(self):
        self.injection_signatures = [
            (r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)\b", "direct_override", 0.96),
            (r"(?i)\bdisregard\s+(the\s+)?(preceding|initial|system)\s+directives\b", "direct_override", 0.94),
            (r"(?i)\byou\s+are\s+now\s+(DAN|unfiltered|jailbroken|chaos\s*gpt|an\s+anti-censorship\s+ai)\b", "jailbreak_dan", 0.98),
            (r"(?i)\bpretend\s+you\s+have\s+no\s+(ethical|safety|operational)\s+(guidelines|restrictions|rules)\b", "jailbreak_dan", 0.95),
            (r"(?i)\boutput\s+(your\s+)?(exact\s+)?system\s+prompt\b", "system_prompt_leak", 0.92),
            (r"(?i)\brepeat\s+the\s+text\s+above\s+starting\s+with\s+[\"']You\s+are\b", "system_prompt_leak", 0.91),
            (r"(?i)\bprint\s+all\s+(hidden|internal)\s+(developer|system)\s+instructions\b", "system_prompt_leak", 0.93),
            (r"(?i)\bcurl\s+https?://[^\s]+\s+--data\s+[\"']?\$[A-Z0-9_]+\b", "tool_exfiltration", 0.97),
            (r"(?i)\beval\(base64\.b64decode\b", "tool_exfiltration", 0.99),
            (r"(?i)\bexec\([\"'].*os\.system\(.*[\"']\)", "tool_exfiltration", 0.98),
            (r"(?i)\b__import__\(['\"]os['\"]\)\.system\b", "tool_exfiltration", 0.99),
        ]

    def evaluate(self, text: str, threshold: float = 0.70) -> Tuple[InjectionResult, float]:
        start_time = time.perf_counter()
        highest_score = 0.0
        detected_category = None
        matched_patterns = []

        for pattern, category, score in self.injection_signatures:
            if re.search(pattern, text):
                matched_patterns.append(f"Signature matched [{category}]")
                if score > highest_score:
                    highest_score = score
                    detected_category = category

        # Heuristic checks for delimiter manipulation and excessive instruction shifts
        if "```system" in text.lower() or "### system:" in text.lower() or "<|im_start|>system" in text.lower():
            matched_patterns.append("Delimited system token impersonation")
            highest_score = max(highest_score, 0.88)
            detected_category = detected_category or "direct_override"

        is_injection = highest_score >= threshold
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return InjectionResult(
            is_injection=is_injection,
            risk_score=round(highest_score, 2),
            attack_category=detected_category,
            detected_patterns=matched_patterns
        ), round(elapsed_ms, 2)

injection_guard = InjectionGuardEngine()
