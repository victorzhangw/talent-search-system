from flask import Blueprint, request, jsonify, current_app
from services.integration_mock import MockIntegrationService
from services.integration_real import RealIntegrationService
from utils.token_generator import generate_upstream_token
import jwt

# No url_prefix, handled in app.py
bp = Blueprint('reports', __name__, url_prefix='/reports')

def get_service():
    mode = current_app.config.get('INTEGRATION_MODE', 'MOCK')
    if mode == 'REAL':
        return RealIntegrationService()
    return MockIntegrationService()

# Trait Name Translation Map (Shared)
TRAIT_TRANSLATIONS = {
    '143b': '同理心', '266f': '洞察力', '82b': '好奇心', '294b': '韌性',
    '302b': 'AI 素養', '306b': '可靠性', '268f': '自我批判', '299b': '變革敏捷性',
    '119b': '自我覺察', '311b': '決策力', '300b': '自我領導', '269f': '自我反思',
    '303b': '積極傾聽', '265f': '尋求反饋', '297b': '社會影響力', '305b': '系統思考',
    '301b': '創意思考', '309b': '批判性思考', '121b': '終身學習', '308b': '談判技巧',
    '298b': '分析思考', '145b': '關注細節', '68b': '社會讚許性', '310b': '社交智慧',
    '293b': '認知彈性', '195b': '成就動機', '267f': '績效冷漠', '307b': '人際溝通'
}

@bp.route('/batch', methods=['POST'])
def get_batch_reports():
    """
    Batch fetch trait reports for multiple candidates
    Request Body: { "assessment_ids": [62, 63, 64, 61] }
    Response: { "reports": [ { "assessment_id": 62, "traits": [...], "assessment_date": "..." }, ... ] }
    """
    import sys
    
    # 強制輸出到 stderr 確保一定會顯示
    print("\n" + "=" * 80, file=sys.stderr, flush=True)
    print("🔥🔥🔥 BATCH REPORTS API CALLED! 🔥🔥🔥", file=sys.stderr, flush=True)
    print("=" * 80, file=sys.stderr, flush=True)
    
    # 同時輸出到 stdout
    print("=" * 60, flush=True)
    print("[Batch Reports] ========== Request Received ==========", flush=True)
    
    # 1. Auth & Token
    user_email = "eva@wepredict.io"
    auth_header = request.headers.get('Authorization')
    print(f"[Batch Reports] Authorization header: {auth_header[:50] if auth_header else 'None'}...", flush=True)
    print(f"[Batch Reports] Authorization header: {auth_header[:50] if auth_header else 'None'}...", file=sys.stderr, flush=True)
    
    if auth_header and auth_header.startswith('Bearer '):
        incoming_token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(incoming_token, options={"verify_signature": False})
            user_email = decoded.get('email', user_email)
            print(f"[Batch Reports] Decoded email: {user_email}", flush=True)
        except Exception as e:
            print(f"[Batch Reports] Token decode error: {e}", flush=True)
    
    upstream_token = generate_upstream_token(user_email)
    print(f"[Batch Reports] Generated upstream token: {upstream_token[:50]}...", flush=True)
    
    service = get_service()
    print(f"[Batch Reports] Using service: {type(service).__name__}", flush=True)
    
    # 2. Get assessment IDs from request
    data = request.json
    print(f"\n🔥 REQUEST BODY: {data}", file=sys.stderr, flush=True)
    print(f"🔥 REQUEST BODY TYPE: {type(data)}", file=sys.stderr, flush=True)
    print(f"[Batch Reports] Request body: {data}", flush=True)
    
    assessment_ids = data.get('assessment_ids', []) if data else []
    print(f"🔥 ASSESSMENT IDS: {assessment_ids}", file=sys.stderr, flush=True)
    print(f"[Batch Reports] Assessment IDs: {assessment_ids}", flush=True)
    
    if not assessment_ids:
        print("❌ ERROR: No assessment_ids provided", file=sys.stderr, flush=True)
        print("[Batch Reports] ERROR: No assessment_ids provided", flush=True)
        return jsonify({'error': 'assessment_ids is required'}), 400
    
    print(f"[Batch Reports] Fetching {len(assessment_ids)} reports for IDs: {assessment_ids}", flush=True)
    
    # 3. Fetch assessments from upstream API
    try:
        if isinstance(service, RealIntegrationService):
            print("[Batch Reports] Calling RealIntegrationService.get_assessments()", flush=True)
            results = service.get_assessments(upstream_token, assessment_ids)
        else:
            print("[Batch Reports] Calling MockIntegrationService.get_assessments()", flush=True)
            results = service.get_assessments(assessment_ids)
        
        print(f"[Batch Reports] Received {len(results) if results else 0} results from service", flush=True)
        if results:
            print(f"[Batch Reports] First result structure: {list(results[0].keys()) if results else 'N/A'}", flush=True)
    except Exception as e:
        print(f"[Batch Reports] ERROR fetching from service: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch assessments: {str(e)}'}), 500
    
    if not results:
        print(f"[Batch Reports] WARNING: No results returned from service", flush=True)
        return jsonify({'reports': []}), 200
    
    # 4. Format each report
    formatted_reports = []
    
    for idx, report_data in enumerate(results):
        print(f"[Batch Reports] Processing report {idx + 1}/{len(results)}", flush=True)
        
        # Extract assessment_id
        # IMPORTANT: The top-level 'assessment_id' is actually the candidate_id
        # The real assessment_id is inside the 'assessment' object
        inner = report_data.get('assessment', {})
        asmt_id = inner.get('assessment_id')
        
        # Fallback: if not in nested structure, try top-level (for compatibility)
        if not asmt_id:
            asmt_id = report_data.get('assessment_id')
        
        print(f"[Batch Reports] Report {idx + 1} assessment_id: {asmt_id}", flush=True)
        print(f"🔥 DEBUG: Top-level assessment_id: {report_data.get('assessment_id')}, Nested assessment_id: {inner.get('assessment_id')}", file=sys.stderr, flush=True)
        
        if not asmt_id:
            print(f"[Batch Reports] WARNING: Skipping report without assessment_id", flush=True)
            continue
        
        # Extract trait results
        raw_traits = report_data.get('assessment', {}).get('trait_results', {})
        if not raw_traits and 'trait_results' in report_data:
            raw_traits = report_data['trait_results']
        
        print(f"[Batch Reports] Report {idx + 1} has {len(raw_traits) if raw_traits else 0} traits", flush=True)
        
        # Normalize to list
        if isinstance(raw_traits, dict):
            iter_traits = raw_traits.values()
        elif isinstance(raw_traits, list):
            iter_traits = raw_traits
        else:
            iter_traits = []
        
        # Format traits
        formatted_traits = []
        for t in iter_traits:
            tid = t.get('trait_id')
            name = TRAIT_TRANSLATIONS.get(tid) or t.get('chinese_name') or t.get('trait_name') or 'Unknown'
            score = t.get('score', 0)
            formatted_traits.append({
                'name': name,
                'score': score,
                'band': t.get('band', '')
            })
        
        # Sort by score desc
        formatted_traits.sort(key=lambda x: x['score'], reverse=True)
        
        # Get assessment date
        assessment_date = report_data.get('assessment', {}).get('completion_time', 'N/A')
        if assessment_date == 'N/A' and 'completion_time' in report_data:
            assessment_date = report_data['completion_time']
        
        formatted_report = {
            'assessment_id': asmt_id,
            'traits': formatted_traits,
            'assessment_date': assessment_date
        }
        
        formatted_reports.append(formatted_report)
        print(f"[Batch Reports] Report {idx + 1} formatted with {len(formatted_traits)} traits", flush=True)
    
    print(f"[Batch Reports] ✅ Returning {len(formatted_reports)} formatted reports", flush=True)
    print("[Batch Reports] ========== End Processing ==========", flush=True)
    print("=" * 60, flush=True)
    
    return jsonify({
        'reports': formatted_reports
    })
