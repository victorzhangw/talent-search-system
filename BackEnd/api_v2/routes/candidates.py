from flask import Blueprint, request, current_app
from ..services.integration_mock import MockIntegrationService
from ..services.rag_engine import RAGService
from ..database import db_session, TraitDefinition
from ..services.integration_real import RealIntegrationService
from ..utils.token_generator import generate_upstream_token
from ..utils.response_helpers import ok, err
from ..utils.request_identity import resolve_user_email
from ..utils.upstream_env import env_from_request

# No url_prefix, handled in app.py
bp = Blueprint('candidates', __name__)

def get_service():
    mode = current_app.config.get('INTEGRATION_MODE', 'MOCK')
    if mode == 'REAL':
        return RealIntegrationService()
    return MockIntegrationService()

@bp.route('/', methods=['GET'])
def list_candidates():
    # In real scenario, enterprise_code comes from resolved session/token
    enterprise_code = request.args.get('enterprise_code', 'ACME-TW')
    
    # 1. Extract Frontend Identity (Email)
    # Note: In a production app, we would verify the signature of the incoming Session Token.
    # Here we assume the frontend sends a valid JWT and we just extract the email to impersonate/forward.
    # 身分只認這次請求帶的 token，而且驗簽、驗期、驗 aud。解不出來就回 401，
    # 不再退回任何預設帳號（0905 文件 E-7 / E-11）。
    user_email, auth_error = resolve_user_email()
    if auth_error:
        return auth_error

    upstream_token = generate_upstream_token(user_email, env_from_request())

    service = get_service()
    
    # Extract Pagination Params
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError):
        limit = 20
        offset = 0

    # Pass token if supported (Real Service) and params
    try:
        if isinstance(service, RealIntegrationService):
            # returns { 'data': [...], 'page': ... }
            result = service.get_candidates(upstream_token, limit=limit, offset=offset)
            candidates = result.get('data', [])
            page_info = result.get('page', {})
        else:
            # returns { 'data': [...], 'page': ... }
            result = service.get_candidates(enterprise_code, limit=limit, offset=offset)
            candidates = result.get('data', [])
            page_info = result.get('page', {})
    except Exception as e:
        print(f"ERROR: Failed to fetch candidates: {e}")
        return err('UPSTREAM_UNAVAILABLE', 'Upstream service unavailable', 503, details=str(e))

    if candidates and len(candidates) > 0:
        print(f"DEBUG: Successfully fetched {len(candidates)} candidates.", flush=True)

    return ok(candidates, meta={'page': page_info})



# 上游 `GET /v1/candidates/` 的 limit 上限。2026-09-19 對 UAT 實測：送 200 或 500，
# 回來的 `page.limit` 都是 100、資料也只有 100 筆——**超限是靜默改寫，不報錯**。
# 所以 `limit=500` 這種寫法讀起來像「一次取回全部」，實際只拿得到前 100 位：超過
# 100 人的企業會安靜地掉人，而且沒有任何錯誤訊息可查。
UPSTREAM_PAGE_MAX = 100

# 跨頁取回的安全上限（100 × 50 = 5000 人）。壞掉的 `page.total` 不該把伺服器
# 留在迴圈裡；真的撞到就停下來並記一筆警告。
MAX_UPSTREAM_PAGES = 50


def _fetch_candidate_page(service, upstream_token, limit, offset):
    """一頁。Real 走 token，Mock 走 enterprise_code，其餘參數相同。"""
    if isinstance(service, RealIntegrationService):
        return service.get_candidates(upstream_token, limit=limit, offset=offset)
    return service.get_candidates("ACME-TW", limit=limit, offset=offset)


def fetch_all_candidates(service, upstream_token, found_enough=None):
    """把上游的人選清單取回，必要時跨頁。回傳 (依序的 list, {str(id): candidate})。

    `found_enough(by_id)` 回傳 True 時提前結束——「找某幾位」的呼叫端不必翻完整份，
    而絕大多數人就落在第一頁，所以常見情況仍然只打一次上游。

    不用 `limit=500` 一次要完：見 `UPSTREAM_PAGE_MAX` 的說明，那是靜默截斷。
    """
    by_id = {}
    ordered = []
    offset = 0
    total = None

    for _ in range(MAX_UPSTREAM_PAGES):
        resp = _fetch_candidate_page(service, upstream_token, UPSTREAM_PAGE_MAX, offset)
        rows = resp.get('data') or []
        if total is None:
            total = (resp.get('page') or {}).get('total')

        for c in rows:
            cid = str(c.get('candidate_id'))
            if cid not in by_id:
                by_id[cid] = c
                ordered.append(c)

        if found_enough and found_enough(by_id):
            break
        offset += len(rows)
        if not rows or (total is not None and offset >= total):
            break
    else:
        print(f"WARNING: fetch_all_candidates stopped at {MAX_UPSTREAM_PAGES} pages "
              f"({len(ordered)} candidates, upstream total={total}); the list may be "
              f"incomplete.", flush=True)

    return ordered, by_id


@bp.route('/by-ids', methods=['GET'])
def list_candidates_by_ids():
    """
    Batch-fetch full candidate objects by ID (used to restore a history session's
    locked candidates, which may no longer be on the first page(s) of list_candidates).
    Request: GET /by-ids?ids=1,2,3
    """
    raw_ids = request.args.get('ids', '')
    requested_ids = [i.strip() for i in raw_ids.split(',') if i.strip()]
    if not requested_ids:
        return err('MISSING_FIELD', 'ids parameter is required', 400, field='ids')

    # 身分只認這次請求帶的 token，而且驗簽、驗期、驗 aud。解不出來就回 401，
    # 不再退回任何預設帳號（0905 文件 E-7 / E-11）。
    user_email, auth_error = resolve_user_email()
    if auth_error:
        return auth_error

    upstream_token = generate_upstream_token(user_email, env_from_request())
    service = get_service()

    # No get-by-id upstream call is exercised in production yet, so reuse the same
    # proven "fetch list, filter in Python" approach as get_candidate_report below.
    #
    # 原本寫的是 `limit=500`，讀起來像「一次取回全部」——實際上上游把超過 100 的
    # limit 靜默改寫成 100（見 UPSTREAM_PAGE_MAX），所以超過 100 人的企業，還原歷史
    # 對話的鎖定名單時會安靜地掉人。改成跨頁取回，並在湊齊要找的人之後就停。
    wanted = {str(i) for i in requested_ids}
    try:
        _, by_id = fetch_all_candidates(
            service, upstream_token,
            found_enough=lambda m: wanted.issubset(m.keys()))
    except Exception as e:
        print(f"ERROR: Failed to fetch candidate list for by-ids: {e}")
        return err('UPSTREAM_UNAVAILABLE', 'Upstream service unavailable', 503, details=str(e))

    found = []
    missing = []
    for cid in requested_ids:
        cand = by_id.get(str(cid))
        if cand:
            found.append(cand)
        else:
            missing.append(cid)

    return ok(found, meta={'missing_candidate_ids': missing})

@bp.route('/<candidate_id>/report', methods=['GET'])
def get_candidate_report(candidate_id):
    # 1. Auth & Token
    # 身分只認這次請求帶的 token，而且驗簽、驗期、驗 aud。解不出來就回 401，
    # 不再退回任何預設帳號（0905 文件 E-7 / E-11）。
    user_email, auth_error = resolve_user_email()
    if auth_error:
        return auth_error

    upstream_token = generate_upstream_token(user_email, env_from_request())
    service = get_service()

    # 2. Find Assessment ID for this Candidate
    # 原本只取第一頁 100 筆，原始碼自己也註明了「This limits us to finding candidates
    # within the first 100 results」——第 101 位以後的人選，報告就查不到。改成跨頁，
    # 並在找到目標之後立刻停：絕大多數人在第一頁，常見情況仍然只打一次上游。
    # TODO: 上游若補上 get-by-id，這整段就可以不用先抓清單。
    try:
        candidates, _ = fetch_all_candidates(
            service, upstream_token,
            found_enough=lambda m: str(candidate_id) in m)
    except Exception as e:
        print(f"ERROR: Failed to fetch candidate list for report: {e}")
        return err('UPSTREAM_UNAVAILABLE', 'Upstream service unavailable', 503, details=str(e))

    # Debug ID types
    print(f"DEBUG: Looking for candidate_id: {candidate_id} (Type: {type(candidate_id)})", flush=True)
    if candidates:
         print(f"DEBUG: First Candidate ID in list: {candidates[0].get('candidate_id')} (Type: {type(candidates[0].get('candidate_id'))})", flush=True)

    # Debug ID types
    print(f"DEBUG: Looking for candidate_id: {candidate_id}", flush=True)

    # Robust matching (String comparison)
    target_cand = None
    for c in candidates:
        if str(c.get('candidate_id')) == str(candidate_id):
            target_cand = c
            break
    
    if not target_cand:
        print(f"DEBUG: Candidate {candidate_id} not found in list.", flush=True)
        return err('NOT_FOUND', 'Candidate not found in list', 404)
        
    # Check assessment ID location
    asmt_id = None
    lat = target_cand.get('latest_assessment')
    if lat and isinstance(lat, dict):
        asmt_id = lat.get('assessment_id')
    else:
        asmt_id = target_cand.get('assessment_id')
        
    if not asmt_id:
        print(f"DEBUG: No assessment_id found for candidate {candidate_id}. Data: {target_cand}", flush=True)
        return ok({
            'candidate_name': target_cand.get('name'),
            'assessment_date': 'N/A',
            'traits': []
        })

    # 3. Fetch Assessment Details
    print(f"DEBUG: Fetching assessment {asmt_id} for candidate {candidate_id}", flush=True)
    if isinstance(service, RealIntegrationService):
        results = service.get_assessments(upstream_token, [asmt_id])
        
        # Result is list of assessments
        # Match by assessment_id (Check both top-level and inner 'assessment' object)
        report_data = None
        for r in results:
            # Check top-level
            if str(r.get('assessment_id')) == str(asmt_id):
                report_data = r
                break
            # Check nested assessment object
            inner = r.get('assessment', {})
            if inner and str(inner.get('assessment_id')) == str(asmt_id):
                report_data = r
                break
                
        if not report_data:
             print(f"DEBUG: Real service returned results but ID {asmt_id} not found. Results: {results}", flush=True)
    else:
        # Mock Service
        assessments = service.get_assessments([asmt_id]) 
        # Mock might return dict or list, assuming consistent list for now or dict
        report_data = assessments if isinstance(assessments, dict) else (assessments[0] if assessments else None)

    if not report_data:
        print(f"DEBUG: Report data is empty after fetch.", flush=True)
        return err('REPORT_FETCH_FAILED', 'Report fetch failed', 500, details=f'Assessment {asmt_id} not retrieved')

    # 4. Simplify/Format for UI (Business Style)
    # Extract trait list
    formatted_traits = []
    
    # Handle different structures (Real vs Mock)
    raw_traits = report_data.get('assessment', {}).get('trait_results', {})
    if not raw_traits and 'trait_results' in report_data:
        raw_traits = report_data['trait_results']
        
    # Normalize to list
    if isinstance(raw_traits, dict):
        iter_traits = raw_traits.values()
    elif isinstance(raw_traits, list):
        iter_traits = raw_traits
    else:
        iter_traits = []
        
    for t in iter_traits:
        tid = t.get('trait_id')
        name = t.get('chinese_name') or t.get('trait_name') or tid or 'Unknown'
        score = t.get('score', 0)
        formatted_traits.append({
            'trait_id': tid,
            'name': name,
            'score': score,
            'band': t.get('band', '') # Optional
        })
        
    # Sort by score desc
    formatted_traits.sort(key=lambda x: x['score'], reverse=True)

    return ok({
        'candidate_name': target_cand.get('name'),
        'assessment_date': target_cand.get('latest_assessment', {}).get('completion_time', 'N/A'),
        'traits': formatted_traits
    })
