from __future__ import annotations

from typing import Any, Dict, List


def naive_parse_query_to_engine_format(text: str) -> Dict[str, Any]:
    """Very small parser to produce parsed_query shape expected by TalentSearchEngineFixed.

    NOTE: This is a stopgap for Milestone 6.
    The proper solution is to reuse/centralize the existing parsing logic (likely in talent_search_api).
    """

    # Minimal shape used by TalentSearchEngineFixed.search_candidates:
    # It appears to accept keys like: intent, traits, ...
    return {
        "intent": "search",
        "raw_query": text,
        # Engine uses this to add extra WHERE clauses.
        "sql_conditions": [],
        # Reserved for later structured parsing.
        "traits": [],
        "keywords": [text],
    }
