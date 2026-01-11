from flask import Blueprint, request, jsonify, current_app
from services.integration_mock import MockIntegrationService
from services.integration_real import RealIntegrationService
from utils.token_generator import generate_upstream_token
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
    # This ensures consistency with RAG flow and prevents expiration issues.
    upstream_token = generate_upstream_token(user_email)

    service = get_service()
    
    # Pass token if supported (Real Service)
    if isinstance(service, RealIntegrationService):
        candidates = service.get_candidates(upstream_token)
    else:
        candidates = service.get_candidates(enterprise_code)
    
    return jsonify({'data': candidates})

@bp.route('/<candidate_id>/report', methods=['GET'])
def get_candidate_report(candidate_id):
    # 1. Auth & Token (Duplicated logic, ideally refactor to decorator)
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
    # We must fetch the list first to link Candidate -> Assessment
    if isinstance(service, RealIntegrationService):
        candidates = service.get_candidates(upstream_token)
    else:
        candidates = service.get_candidates("ACME-TW")
        
    target_cand = next((c for c in candidates if str(c.get('candidate_id')) == str(candidate_id)), None)
    
    if not target_cand:
        return jsonify({'error': 'Candidate not found'}), 404
        
    # Check assessment ID location
    asmt_id = None
    lat = target_cand.get('latest_assessment')
    if lat and isinstance(lat, dict):
        asmt_id = lat.get('assessment_id')
    else:
        asmt_id = target_cand.get('assessment_id')
        
    if not asmt_id:
         return jsonify({'error': 'No assessment found for candidate'}), 404

    # 3. Fetch Assessment Details
    if isinstance(service, RealIntegrationService):
        results = service.get_assessments(upstream_token, [asmt_id])
        # Result is list of assessments
        # Match by assessment_id
        report_data = next((r for r in results if str(r.get('assessment_id')) == str(asmt_id)), None)
    else:
        # Mock Service
        assessments = service.get_assessments([asmt_id]) 
        # Mock might return dict or list, assuming consistent list for now or dict
        report_data = assessments if isinstance(assessments, dict) else (assessments[0] if assessments else None)

    if not report_data:
        return jsonify({'error': 'Report fetch failed'}), 500

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
        # Use English Name (chinese_name field) or fallback
        name = t.get('chinese_name') or t.get('trait_name') or 'Unknown'
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
