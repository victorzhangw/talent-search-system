from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RuleRoute:
    intent: str
    confidence: float


class RuleIntentRouter:
    """High-confidence keyword rules.

    Keep this conservative; only return when confident.
    """

    def route(self, text: str) -> Optional[RuleRoute]:
        t = (text or "").lower()

        # compare
        if any(k in t for k in ["比較", "對比", "差異", "哪個好", "compare"]):
            return RuleRoute(intent="compare", confidence=0.9)

        # interview
        if any(k in t for k in ["面試", "interview", "提問", "問題", "綱要"]):
            return RuleRoute(intent="interview", confidence=0.85)

        # statistics
        if any(k in t for k in ["統計", "分佈", "有多少", "數量", "比例"]):
            return RuleRoute(intent="statistics", confidence=0.8)

        # list all
        if any(k in t for k in ["列出所有", "全部候選人", "所有候選人", "list all"]):
            return RuleRoute(intent="list_all", confidence=0.85)

        # list traits
        if any(k in t for k in ["有哪些特質", "列出特質", "特質列表", "list traits"]):
            return RuleRoute(intent="list_traits", confidence=0.85)

        # advice / hr consultation
        if any(k in t for k in ["建議", "怎麼做", "該如何", "顧問", "advice"]):
            return RuleRoute(intent="advice", confidence=0.75)

        # search (fallback-ish but still a rule)
        if any(k in t for k in ["找", "搜尋", "推薦", "尋找", "search"]):
            return RuleRoute(intent="search", confidence=0.65)

        return None
