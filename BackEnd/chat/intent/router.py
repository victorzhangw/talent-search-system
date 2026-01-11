from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .intent_registry import IntentRegistry
from .llm_classifier import LLMIntentClassifier
from .rule_router import RuleIntentRouter


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    entities: Dict[str, Any]
    source: str  # rule | llm | fallback


class IntentRouter:
    def __init__(self, registry: Optional[IntentRegistry] = None):
        self.registry = registry or IntentRegistry()
        self.rule_router = RuleIntentRouter()
        self.llm = LLMIntentClassifier()

    async def route(self, text: str) -> IntentResult:
        enabled = self.registry.enabled_intents()

        # 1) rule-first (high confidence)
        rr = self.rule_router.route(text)
        if rr and rr.intent in enabled:
            return IntentResult(intent=rr.intent, confidence=rr.confidence, entities={}, source="rule")

        # 2) LLM fallback (optional)
        llm_res = await self.llm.classify(text, enabled_intents=enabled)
        if llm_res:
            return IntentResult(
                intent=llm_res.intent,
                confidence=llm_res.confidence,
                entities=llm_res.entities,
                source="llm",
            )

        # 3) fallback
        return IntentResult(intent="search", confidence=0.4, entities={}, source="fallback")
