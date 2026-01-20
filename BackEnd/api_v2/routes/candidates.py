from flask import Blueprint, request, jsonify, current_app
from ..services.integration_mock import MockIntegrationService
from ..services.rag_engine import RAGService
from ..database import db_session, TraitDefinition
from ..services.integration_real import RealIntegrationService
from ..utils.token_generator import generate_upstream_token
import jwt

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
    user_email = "eva@wepredict.io" # Default fallback
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        incoming_token = auth_header.split(" ")[1]
        try:
            # Decode without verification just to get email (for now)
            # OR if we share the secret, we can verify.
            # Assuming same secret key as Auth Route.
            decoded = jwt.decode(incoming_token, options={"verify_signature": False})
            user_email = decoded.get('email', user_email)
        except Exception as e:
            print(f"Warning: Failed to decode incoming token: {e}")

    # 2. Key Step: Generate FRESH Upstream Token
    upstream_token = generate_upstream_token(user_email)

    service = get_service()
    
    # Extract Pagination Params
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError):
        limit = 20
        offset = 0

    # Pass token if supported (Real Service) and params
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
    
    if candidates and len(candidates) > 0:
        print(f"DEBUG: Successfully fetched {len(candidates)} candidates.", flush=True)

    # Return structure matching Upstream
    return jsonify({
        'data': candidates,
        'page': page_info
    })

@bp.route('/<candidate_id>/report', methods=['GET'])
def get_candidate_report(candidate_id):
    # 1. Auth & Token
    user_email = "eva@wepredict.io"
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        incoming_token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(incoming_token, options={"verify_signature": False})
            user_email = decoded.get('email', user_email)
        except: pass
    
    upstream_token = generate_upstream_token(user_email)
    service = get_service()

    # 2. Find Assessment ID for this Candidate
    # Note: This limits us to finding candidates within the first 100 results.
    # TODO: Implement Get-By-ID in Upstream or Service to avoid fetching list.
    if isinstance(service, RealIntegrationService):
        resp = service.get_candidates(upstream_token, limit=100)
        candidates = resp.get('data', [])
    else:
        resp = service.get_candidates("ACME-TW", limit=100)
        candidates = resp.get('data', [])

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
        return jsonify({'error': 'Candidate not found in list'}), 404
        
    # Check assessment ID location
    asmt_id = None
    lat = target_cand.get('latest_assessment')
    if lat and isinstance(lat, dict):
        asmt_id = lat.get('assessment_id')
    else:
        asmt_id = target_cand.get('assessment_id')
        
    if not asmt_id:
         print(f"DEBUG: No assessment_id found for candidate {candidate_id}. Data: {target_cand}", flush=True)
         # Graceful UI handling: Return basic info but no traits
         return jsonify({
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
        return jsonify({'error': 'Report fetch failed', 'details': f'Assessment {asmt_id} not retrieved'}), 500

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
        
    # Trait Name Translation Map (Fallback for UAT returning English)
    TRAIT_TRANSLATIONS = {
        '143b': '同理心', '266f': '洞察力', '82b': '好奇心', '294b': '韌性',
        '302b': 'AI 素養', '306b': '可靠性', '268f': '自我批判', '299b': '變革敏捷性',
        '119b': '自我覺察', '311b': '決策力', '300b': '自我領導', '269f': '自我反思',
        '303b': '積極傾聽', '265f': '尋求反饋', '297b': '社會影響力', '305b': '系統思考',
        '301b': '創意思考', '309b': '批判性思考', '121b': '終身學習', '308b': '談判技巧',
        '298b': '分析思考', '145b': '關注細節', '68b': '社會讚許性', '310b': '社交智慧',
        '293b': '認知彈性', '195b': '成就動機', '267f': '績效冷漠', '307b': '人際溝通'
    }

    for t in iter_traits:
        # Priority: Hardcoded Map > API Chinese Name > API Trait Name
        tid = t.get('trait_id')
        name = TRAIT_TRANSLATIONS.get(tid) or t.get('chinese_name') or t.get('trait_name') or 'Unknown'
        score = t.get('score', 0)
        formatted_traits.append({
            'name': name,
            'score': score,
            'band': t.get('band', '') # Optional
        })
        
    # Sort by score desc
    formatted_traits.sort(key=lambda x: x['score'], reverse=True)

    return jsonify({
        'candidate_name': target_cand.get('name'),
        'assessment_date': target_cand.get('latest_assessment', {}).get('completion_time', 'N/A'),
        'traits': formatted_traits
    })
