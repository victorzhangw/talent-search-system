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
    def get_candidates(self, auth_key: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get list of candidates for the enterprise.
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
