from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ModelPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ModelPolicy:
    key: str
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    fallbacks: list[str]


_DEFAULT_MODELS_PATH = Path(__file__).resolve().parent.parent / "policies" / "models.yaml"


def _resolve_model_name(m: Dict[str, Any]) -> str:
    name_env = m.get("name_env")
    name_default_env = m.get("name_default_env")
    if name_env and os.getenv(str(name_env)):
        return os.getenv(str(name_env)) or ""
    if name_default_env and os.getenv(str(name_default_env)):
        return os.getenv(str(name_default_env)) or ""
    # last resort
    return str(m.get("name") or "")


def load_model_policies(path: Path = _DEFAULT_MODELS_PATH) -> Dict[str, ModelPolicy]:
    if not path.exists():
        raise ModelPolicyError(f"models policy not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ModelPolicyError("models.yaml must be a mapping")

    models = raw.get("models")
    if not isinstance(models, dict):
        raise ModelPolicyError("models.yaml must contain 'models' mapping")

    out: Dict[str, ModelPolicy] = {}
    for key, m in models.items():
        if not isinstance(m, dict):
            continue
        model_name = _resolve_model_name(m)
        if not model_name:
            # allow missing model name: caller can handle configured=false
            model_name = ""

        out[str(key)] = ModelPolicy(
            key=str(key),
            provider=str(m.get("provider") or "openai_compatible"),
            model_name=model_name,
            temperature=float(m.get("temperature") or 0),
            max_tokens=int(m.get("max_tokens") or 512),
            timeout_seconds=float(m.get("timeout_seconds") or 30),
            fallbacks=list(m.get("fallbacks") or []),
        )

    return out


def get_model_policy(policy_key: str) -> ModelPolicy:
    policies = load_model_policies()
    if policy_key not in policies:
        raise ModelPolicyError(f"model policy not found: {policy_key}")
    return policies[policy_key]
