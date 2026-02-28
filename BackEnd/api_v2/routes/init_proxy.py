from flask import Blueprint, request, jsonify, current_app
from ..utils.token_generator import generate_upstream_token
import jwt
import httpx

bp = Blueprint('init_proxy', __name__)

@bp.route('/', methods=['GET'])
def get_init_status():
    user_email = "eva@wepredict.io" # Default fallback
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        incoming_token = auth_header.split(" ")[1]
        try:
            # Decode without verification just to get email (for now)
            decoded = jwt.decode(incoming_token, options={"verify_signature": False})
            user_email = decoded.get('email', user_email)
        except Exception as e:
            print(f"Warning: Failed to decode incoming token: {e}")

    # Generate FRESH Upstream Token
    upstream_token = generate_upstream_token(user_email)
    
    base_url = current_app.config.get('TRAITTY_API_BASE', 'https://uat.traitty.com')
    url = f"{base_url}/v1/init/"
    
    headers = {
        "Authorization": f"Bearer {upstream_token}",
        "Accept": "application/json"
    }

    try:
        print(f"[Init Proxy] Forwarding request to {url}...", flush=True)
        # Verify=False might be needed if there are local SSL issues, but usually okay
        response = httpx.get(url, headers=headers, timeout=15.0)
        
        # Check if response is valid JSON
        try:
            data = response.json()
        except Exception:
            print(f"[Init Proxy] Upstream did not return valid JSON. Status: {response.status_code}")
            return jsonify({'error': 'Invalid JSON from upstream', 'status': False}), 502
            
        print(f"[Init Proxy] Response Status: {response.status_code}, data: {data}")    
        return jsonify(data), response.status_code
        
    except httpx.RequestError as e:
        print(f"[Init Proxy] Network Error: {e}")
        return jsonify({'error': 'Upstream network error', 'details': str(e), 'status': False}), 503
    except Exception as e:
        print(f"[Init Proxy] Unexpected Error: {e}")
        return jsonify({'error': 'Internal proxy error', 'details': str(e), 'status': False}), 500
