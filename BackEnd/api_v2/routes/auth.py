from flask import Blueprint, request, jsonify
import jwt
import time
import uuid

import os

bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv('PARTY_A_PLUGIN_SECRET', "traitty_ai_api")

@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # 1. Construct Payload (Spec)
    payload = {
      "email": email,
      "user_id": 1,
      "token_type": "access",
      "jti": str(uuid.uuid4()),
      "iat": int(time.time()),
      "exp": int(time.time()) + 900, # 15 mins
      "aud": "traitty",
      "scope": "traitty_plugin"
    }

    # 2. Sign Token
    token = jwt.encode(
        payload, 
        SECRET_KEY, 
        algorithm="HS256", 
        headers={"alg": "HS256", "typ": "JWT"}
    )

    # 3. Return Token
    return jsonify({
        "status": "success",
        "token": token,
        "user": {
            "email": email,
            "id": 1
        }
    })

# Legacy init for older mock flow (can remove later if strict)
@bp.route('/init', methods=['POST'])
def init_session():
    data = request.json
    user_id = data.get('userId')
    return jsonify({
        "status": "success", 
        "sessionId": f"sess_{user_id}",
        "mock_token": "mock.jwt.token" 
    })
