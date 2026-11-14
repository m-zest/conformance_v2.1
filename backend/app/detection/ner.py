"""Named entity detection (people, locations) through Microsoft Presidio and spaCy.

This detector is optional. When the libraries or the language model are not
installed it reports itself as unavailable and the rest of the pipeline keeps
working. It is only applied to a bounded amount of text because statistical
NER is far slower than the pattern detectors.
"""
from __future__ import annotations

import logging
import threading

from ..config import settings
from .model import SEVERITY, Finding

log = logging.getLogger("conformance.detection.ner")


class NerDetector:
    name = "ner"

    def __init__(self) -> None:
        self.enabled = settings.ner_enabled
        self.available = False
        self.error = ""
        self._analyzer = None
        self._lock = threading.Lock()
        if self.enabled:
            self._load()

    def _load(self) -> None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            provider = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": settings.ner_language, "model_name": settings.ner_model}],
            })
            self._analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(),
                                            supported_languages=[settings.ner_language])
            self.available = True
        except Exception as exc:  # library or model missing
            self.error = f"{type(exc).__name__}: {exc}"[:300]
            log.warning("NER detector unavailable: %s", self.error)

    def scan(self, text: str) -> list[Finding]:
        if not self.available or not text.strip():
            return []
        text = text[: settings.ner_max_chars]
        with self._lock:
            results = self._analyzer.analyze(text=text, entities=settings.ner_entities,
                                             language=settings.ner_language, score_threshold=0.6)
        findings = []
        for r in results:
            value = text[r.start:r.end]
            if len(value) < 3 or (r.entity_type == "PERSON" and " " not in value.strip()):
                continue  # single tokens are too noisy to be useful
            findings.append(Finding("ner", "pii.person", r.entity_type, r.start, r.end, round(float(r.score), 2),
                                    SEVERITY["low"], text=value))
        return findings

    def status(self) -> dict:
        state = "disabled" if not self.enabled else ("ready" if self.available else "unavailable")
        return {"id": "ner", "name": "Named entities (Presidio and spaCy)", "state": state,
                "detail": self.error or f"model {settings.ner_model}, entities {', '.join(settings.ner_entities)}"}
