import httpx
from flask import current_app
from .integration_base import IntegrationServiceInterface

class RealIntegrationService(IntegrationServiceInterface):
    def __init__(self):
        # Base URL handled via property
        pass

    @property
    def base_url(self):
        return current_app.config.get('TRAITTY_API_BASE', 'https://uat.traitty.com')

    def _get_headers(self, token: str):
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    def get_candidates(self, token: str):
        """
        Fetch candidates from Traitty API using the provided JWT.
        Endpoint: GET /v1/candidates/
        """
        if not token:
            print("[RealService] No token provided")
            return []

        try:
            url = f"{self.base_url}/v1/candidates/"
            headers = self._get_headers(token)
            
            print(f"[RealService] Requesting {url}...")
            response = httpx.get(url, headers=headers, timeout=15.0)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                print(f"[RealService] Candidates Error {response.status_code}: {response.text}")
                return []
        except Exception as e:
            print(f"[RealService] Exception fetching candidates: {e}")
            return []

    def resolve_enterprise(self, token: str):
        """
        Resolve Enterprise Context (Company Name, Jobs)
        Endpoint: GET /v1/enterprise/resolve/
        """
        try:
            url = f"{self.base_url}/v1/enterprise/resolve/"
            headers = self._get_headers(token)

            print(f"[RealService] Resolving Enterprise: {url}...")
            response = httpx.get(url, headers=headers, timeout=10.0)

            if response.status_code == 200:
                return response.json() # Returns { enterprise_name, job_desc: [] }
            else:
                print(f"[Enterprise] Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"[Enterprise] Exception: {e}")
            return None

    def get_assessments(self, token: str, assessment_ids: list):
        """
        Batch Fetch Assessment Details
        Endpoint: POST /v1/assessments/latest:batch
        """
        if not assessment_ids:
            return []

        try:
            url = f"{self.base_url}/v1/assessments/latest:batch"
            headers = self._get_headers(token)
            body = { "assessment_ids": assessment_ids }

            print(f"[RealService] Batch Fetch Assessments: {len(assessment_ids)} IDs...")
            response = httpx.post(url, headers=headers, json=body, timeout=20.0)

            if response.status_code == 200:
                # Response model: { enterprise_code, results: [{...}] }
                data = response.json()
                return data.get('results', [])
            else:
                print(f"[Assessments] Error {response.status_code}: {response.text}")
                return []
        except Exception as e:
            print(f"[Assessments] Exception: {e}")
            return []

    # Legacy/Interface Stub (Single)
    def get_assessment(self, candidate_id: str):
        return {}
