from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class IntentDefinition:
    intent: str
    name: str
    description: str
    examples: List[str]
    enabled: bool = True


class IntentRegistryError(ValueError):
    pass


_DEFAULT_INTENTS_PATH = Path(__file__).resolve().parent.parent.parent / "intent_definitions.json"


class IntentRegistry:
    def __init__(self, intents_path: Optional[Path] = None):
        self._path = intents_path or _DEFAULT_INTENTS_PATH
        self._raw: Dict[str, Any] = {}
        self._intents: Dict[str, IntentDefinition] = {}

    def load(self) -> None:
        if not self._path.exists():
            raise IntentRegistryError(f"intent definitions not found: {self._path}")

        self._raw = json.loads(self._path.read_text(encoding="utf-8"))
        intents = self._raw.get("intents")
        if not isinstance(intents, dict):
            raise IntentRegistryError("intent_definitions.json must contain 'intents' mapping")

        parsed: Dict[str, IntentDefinition] = {}
        for key, val in intents.items():
            if not isinstance(val, dict):
                continue
            parsed[key] = IntentDefinition(
                intent=key,
                name=str(val.get("name") or key),
                description=str(val.get("description") or ""),
                examples=list(val.get("examples") or []),
                enabled=bool(val.get("enabled", True)),
            )

        self._intents = parsed

    @property
    def intents(self) -> Dict[str, IntentDefinition]:
        if not self._intents:
            self.load()
        return self._intents

    def enabled_intents(self) -> List[str]:
        return [k for k, v in self.intents.items() if v.enabled]
