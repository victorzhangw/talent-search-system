import json
import os
from typing import List, Dict, Any
from .integration_base import IntegrationServiceInterface

class MockIntegrationService(IntegrationServiceInterface):
    def __init__(self):
        # Load mock data
        self.data_path = os.path.join(os.path.dirname(__file__), 'mock_data.json')
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def resolve_enterprise(self, plugin_token: str) -> Dict[str, Any]:
        # Return mock enterprise data regardless of token
        return {
            'account_id': 'mock_acc_001',
            'enterprise_id': 'mock_ent_001',
            'enterprise_code': self.data['enterprise_code'],
            'enterprise_name': self.data['enterprise_name']
        }

    def get_candidates(self, auth_key: str, limit: int = 20, offset: int = 0,
                       q: str = None) -> Dict[str, Any]:
        all_candidates = self.data['candidates']

        # 比對欄位刻意與上游一致（swagger:「搜尋姓名/email/職務（模糊）」），否則 MOCK
        # 與 REAL 的搜尋結果會不一樣，而測試幾乎都跑在 MOCK 上。
        needle = (q or '').strip().lower()
        if needle:
            def hit(c):
                return any(needle in str(c.get(f) or '').lower()
                           for f in ('name', 'email', 'position'))
            all_candidates = [c for c in all_candidates if hit(c)]

        sliced = all_candidates[offset: offset + limit]

        return {
            "data": sliced,
            "page": {
                # 帶 q 時回篩選後的總數，與上游一致。
                "total": len(all_candidates),
                "limit": limit,
                "offset": offset
            }
        }

    def get_candidate_by_id(self, candidate_id: str) -> Dict[str, Any]:
        return next(
            (c for c in self.data['candidates'] if str(c.get('candidate_id')) == str(candidate_id)),
            None
        )

    def get_assessments(self, enterprise_code: str, candidate_ids: List[str]) -> List[Dict[str, Any]]:
        results = []
        for cid in candidate_ids:
            if cid in self.data['assessments']:
                results.append({
                    'candidate_id': cid,
                    'ok': True,
                    'assessment': self.data['assessments'][cid]
                })
            else:
                results.append({
                    'candidate_id': cid,
                    'ok': False,
                    'error': {'code': 'NOT_FOUND'}
                })
        return results
