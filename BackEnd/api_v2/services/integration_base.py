from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IntegrationServiceInterface(ABC):
    """
    Abstract Base Class for Integration Service.
    Defines methods to interact with the external Candidate/Assessment system (Party A).
    """

    @abstractmethod
    def resolve_enterprise(self, plugin_token: str) -> Dict[str, Any]:
        """
        Exchange plugin token for enterprise_code and details.
        Expected return: {'enterprise_code': 'ACME', 'enterprise_name': '...', ...}
        """
        pass

    @abstractmethod
    def get_candidates(self, auth_key: str, limit: int = 20, offset: int = 0,
                       q: str = None) -> Dict[str, Any]:
        """
        Get list of candidates for the enterprise.

        `q` 是上游支援的模糊搜尋（swagger:「搜尋姓名/email/職務（模糊）」）。帶了 `q`
        之後 `page.total` 回的是**篩選後**的總數，所以呼叫端可以拿它決定要翻幾頁。
        （2026-09-19 對 UAT 實測：q='吳' -> total=4；q='zzz' -> total=0；空字串等同沒帶。）

        Returns: { 'data': [...], 'page': {'total': N, ...} }
        """
        pass

    @abstractmethod
    def get_assessments(self, enterprise_code: str, candidate_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Batch retrieve latest assessments for candidates.
        Must return 'trait_results' and 'trait_metadata' (with semantic bands).
        """
        pass
