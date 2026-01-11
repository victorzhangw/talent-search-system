from __future__ import annotations

from typing import Any, Dict, List, Optional


class TalentSearchTool:
    """Wrapper around existing talent search engine.

    Design goal: do NOT rewrite existing logic; just adapt it into a tool interface.

    Important:
    - We intentionally avoid importing `talent_search_api.py` to prevent FastAPI side effects.
    - We use a direct DB connection from env (no SSH tunnel in Milestone 6 v1).

    If DB is not configured, raise an error so workflow can fall back.
    """

    def __init__(self):
        # Lazy import to avoid importing heavy modules at import time
        from talent_search_engine_fixed import TalentSearchEngineFixed

        self._engine_cls = TalentSearchEngineFixed

    def search(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        from .db import get_pg_connection_from_env

        conn = get_pg_connection_from_env()
        try:
            engine = self._engine_cls(conn)
            candidates = engine.search_candidates(parsed_query)
            return {
                "success": True,
                "total": len(candidates),
                "candidates": candidates,
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass
