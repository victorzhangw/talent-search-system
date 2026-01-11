from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional



@dataclass(frozen=True)
class LLMIntentResult:
    intent: str
    confidence: float
    entities: Dict[str, Any]


class LLMIntentClassifier:
    """Optional LLM-based intent classifier.

    Uses the shared `LLMRunner` + model policy (`classifier_model`).
    If env vars are not configured, this classifier returns None.
    """

    def __init__(self):
        from chat.llm.runner import LLMRunner

        self._runner = LLMRunner()

    def is_configured(self) -> bool:
        return self._runner.is_configured()

    async def classify(self, text: str, enabled_intents: list[str]) -> Optional[LLMIntentResult]:
        if not self.is_configured():
            return None

        schema_hint = {
            "intent": "one_of:" + ",".join(enabled_intents),
            "confidence": "0.0-1.0",
            "entities": {},
        }

        system = (
            "你是一個意圖分類器。\n"
            "請只輸出 JSON（不要任何額外文字），格式："
            "{\"intent\": str, \"confidence\": number, \"entities\": object}.\n"
            "intent 必須是允許清單之一。"
        )
        user = (
            f"允許 intent：{enabled_intents}\n"
            f"使用者輸入：{text}\n"
            f"輸出 JSON schema 參考：{json.dumps(schema_hint, ensure_ascii=False)}"
        )

        llm_out = await self._runner.run(
            model_policy_key="classifier_model",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        content = str(llm_out.get("content") or "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # try to extract first json object
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                parsed = json.loads(content[start : end + 1])
            else:
                return None

        intent = str(parsed.get("intent") or "")
        confidence = float(parsed.get("confidence") or 0.0)
        entities = parsed.get("entities") or {}
        if intent not in enabled_intents:
            return None

        return LLMIntentResult(intent=intent, confidence=confidence, entities=dict(entities))
