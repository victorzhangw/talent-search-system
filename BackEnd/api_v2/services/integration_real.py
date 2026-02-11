import httpx
import time
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

    def get_candidates(self, auth_key: str, limit: int = 20, offset: int = 0) -> dict:
        """
        Fetch candidates from Traitty API using the provided JWT.
        Endpoint: GET /v1/candidates/
        Includes Retry Logic: 3 attempts with backoff.
        """
        import time
        token = auth_key
        if not token:
            print("[RealService] No token provided")
            return {"data": [], "page": {"total": 0}}

        url = f"{self.base_url}/v1/candidates/"
        headers = self._get_headers(token)
        params = {"limit": limit, "offset": offset}
        
        max_retries = 3
        timeout_seconds = 30.0  # Increased from 15.0 to 30.0
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"[RealService] Requesting {url} with params {params} (Attempt {attempt}/{max_retries})...")
                
                response = httpx.get(url, headers=headers, params=params, timeout=timeout_seconds)
                
                print(f"[RealService] Candidates Response Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    # Ensure structure
                    if 'data' not in data:
                        return {'data': [], 'page': {}}
                    return data
                elif response.status_code >= 500:
                    # Server error (500, 502, 503, 504), retry
                    error_msg = f"[RealService] Server Error {response.status_code}: {response.text}"
                    print(error_msg)
                    
                    if response.status_code == 504:
                         print(f"[RealService] Gateway Timeout detected. Ensuring retry...")

                    if attempt < max_retries:
                        time.sleep(2 * attempt)
                        continue
                    else:
                        # Raise exception to be caught by caller (503 Service Unavailable)
                        response.raise_for_status()
                else:
                    # Client error (4xx), do not retry
                    print(f"[RealService] Candidates Error Body: {response.text}")
                    return {"data": [], "page": {"total": 0}}
                    
            except (httpx.RequestError, httpx.TimeoutException) as e:
                print(f"[RealService] Network Exception fetching candidates (Attempt {attempt}): {e}")
                if attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                else:
                    # Final attempt failed
                    print(f"[RealService] All retries failed for candidates fetch.")
                    # Better to return error structure or raise? 
                    # Returning empty list mimics "no results" which is confusing.
                    # Propagating exception allows caller to handle "Service Unavailable".
                    raise e
            except Exception as e:
                print(f"[RealService] Unexpected Exception: {e}")
                raise e
                
        return {"data": [], "page": {"total": 0}}

    def get_candidate_by_id(self, token: str, candidate_id: str) -> dict:
        """
        Fetch Single Candidate by ID
        Endpoint: GET /v1/candidates/{candidate_id}
        """
        try:
            url = f"{self.base_url}/v1/candidates/{candidate_id}"
            headers = self._get_headers(token)
            
            print(f"[RealService] Fetching Single Candidate: {url}...")
            response = httpx.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[RealService] Single Candidate Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"[RealService] Exception fetching single candidate: {e}")
            return None

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

            print(f"[RealService] Enterprise Response Status: {response.status_code}")
            if response.status_code == 200:
                print(f"[RealService] Enterprise Data: {response.text}")
                return response.json() # Returns { enterprise_name, job_desc: [] }
            else:
                print(f"[Enterprise] Error Body: {response.text}")
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

            print(f"[RealService] Batch Fetch Assessments URL: {url}")
            print(f"[RealService] Request Body: {body}")
            
            response = httpx.post(url, headers=headers, json=body, timeout=20.0)

            print(f"[RealService] Assessments Response Status: {response.status_code}")
            print(f"[RealService] Assessments Response Body: {response.text}")

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
