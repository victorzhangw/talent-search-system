from __future__ import annotations

from typing import Any, Dict, List

from .client import OpenAICompatibleClient
from .model_policy import ModelPolicy, get_model_policy


class LLMRunner:
    def __init__(self):
        self.client = OpenAICompatibleClient()

    def is_configured(self) -> bool:
        return self.client.is_configured()

    async def run(
        self,
        model_policy_key: str,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        policy = get_model_policy(model_policy_key)
        return await self._run_with_policy(policy, messages)

    async def _run_with_policy(self, policy: ModelPolicy, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        last_err: Exception | None = None
        keys_to_try = [policy.key] + list(policy.fallbacks)

        for key in keys_to_try:
            p = policy if key == policy.key else get_model_policy(key)
            try:
                resp = await self.client.chat_completions(
                    model=p.model_name,
                    messages=messages,
                    temperature=p.temperature,
                    max_tokens=p.max_tokens,
                    timeout_seconds=p.timeout_seconds,
                )
                return {
                    "content": resp.content,
                    "raw": resp.raw,
                    "model_policy": p.key,
                    "model": p.model_name,
                }
            except Exception as e:  # noqa: BLE001
                last_err = e
                continue

        raise RuntimeError(f"LLM call failed after fallbacks: {last_err}")
