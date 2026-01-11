from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedPolicy:
    raw: Dict[str, Any]
    policy_id: str
    version: int
    rules: list[dict[str, Any]]


_DEFAULT_POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"


def load_policy(policy_id: str, policies_dir: Optional[Path] = None) -> LoadedPolicy:
    policies_dir = policies_dir or _DEFAULT_POLICIES_DIR
    path_yaml = policies_dir / f"{policy_id}.yaml"
    path_yml = policies_dir / f"{policy_id}.yml"

    if path_yaml.exists():
        path = path_yaml
    elif path_yml.exists():
        path = path_yml
    else:
        raise PolicyError(f"policy not found: {policy_id}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PolicyError("policy file must be a mapping")

    pid = str(raw.get("id") or policy_id)
    version = int(raw.get("version") or 1)
    rules = raw.get("rules")
    if not isinstance(rules, list):
        raise PolicyError("policy must define 'rules' list")

    return LoadedPolicy(raw=raw, policy_id=pid, version=version, rules=rules)
