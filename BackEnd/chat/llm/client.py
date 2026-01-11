from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


class LLMClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    content: str
    raw: Dict[str, Any]


class OpenAICompatibleClient:
    def __init__(self):
        self.host = os.getenv("LLM_API_HOST", "https://api.siliconflow.cn").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0,
        max_tokens: int = 512,
        timeout_seconds: float = 30,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMClientError("LLM_API_KEY is not configured")
        if not model:
            raise LLMClientError("model is empty")

        url = f"{self.host}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()

        content = raw["choices"][0]["message"]["content"]
        return LLMResponse(content=content, raw=raw)
