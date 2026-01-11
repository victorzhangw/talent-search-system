from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .policy_loader import LoadedPolicy


@dataclass(frozen=True)
class ModerationResult:
    ok: bool
    blocked: bool
    action: str  # allow | block_end | block_continue
    categories: List[str]
    reason: str


class RuleBasedModerator:
    """Rule-based moderation.

    This is a minimal first layer:
    - Deterministic
    - No external API dependency

    Later milestones can add optional LLM moderation or third-party services.
    """

    # NOTE: Keep patterns simple; these are heuristics.
    _PATTERNS: Dict[str, List[re.Pattern]] = {
        "sexual": [
            re.compile(r"\b(rape|porn|sex|nude)\b", re.IGNORECASE),
            re.compile(r"(色情|A片|裸照|強姦|性侵|約炮)"),
        ],
        "violence": [
            re.compile(r"\b(kill|murder|bomb)\b", re.IGNORECASE),
            re.compile(r"(殺人|爆炸|炸彈|砍人|槍擊|恐攻)"),
        ],
        "hate": [
            re.compile(r"(種族歧視|仇恨言論|去死吧)"),
        ],
        "self_harm": [
            re.compile(r"(自殺|想死|割腕|輕生)"),
        ],
        "pii": [
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # US SSN-like
            re.compile(r"\b\+?\d{8,15}\b"),
            re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
            re.compile(r"(身分證|護照|信用卡|卡號|住址)"),
        ],
    }

    def moderate(self, text: str, policy: LoadedPolicy) -> ModerationResult:
        text = text or ""
        matched_categories: List[str] = []

        for category, patterns in self._PATTERNS.items():
            if any(p.search(text) for p in patterns):
                matched_categories.append(category)

        # Decide action from policy rules order
        action = "allow"
        reason = "ok"
        if matched_categories:
            # Find first rule that matches
            for rule in policy.rules:
                if rule.get("category") in matched_categories:
                    action = str(rule.get("action") or "allow")
                    break
            reason = f"matched categories: {', '.join(matched_categories)}"

        blocked = action in {"block_end", "block_continue"}
        ok = not blocked
        return ModerationResult(
            ok=ok,
            blocked=blocked,
            action=action,
            categories=matched_categories,
            reason=reason,
        )
