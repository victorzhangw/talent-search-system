from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


class PromptRegistryError(ValueError):
    pass


_DEFAULT_PROMPTS_PATH = Path(__file__).resolve().parent / "prompts" / "prompts_zh_tw.json"


@lru_cache(maxsize=8)
def load_prompts(path: Path = _DEFAULT_PROMPTS_PATH) -> Dict[str, str]:
    if not path.exists():
        raise PromptRegistryError(f"prompts file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PromptRegistryError("prompts JSON must be an object mapping prompt_id -> template")

    prompts: Dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(v, str):
            prompts[str(k)] = v
    return prompts


def get_prompt(prompt_id: str) -> str:
    prompts = load_prompts()
    if prompt_id not in prompts:
        raise PromptRegistryError(f"prompt_id not found: {prompt_id}")
    return prompts[prompt_id]
