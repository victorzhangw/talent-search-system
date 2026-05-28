from flask import Blueprint, request
import jwt
import time
import uuid
import os

from ..utils.response_helpers import ok, err

bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv('PARTY_A_PLUGIN_SECRET', "traitty_ai_api")

@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email') if data else None

    if not email:
        return err('MISSING_FIELD', 'Email is required', 400, field='email')

    payload = {
        "email": email,
        "user_id": 1,
        "token_type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
        "aud": "traitty",
        "scope": "traitty_plugin"
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT"}
    )

    return ok({
        "token": token,
        "user": {"email": email, "id": 1}
    })

# Legacy init for older mock flow
@bp.route('/init', methods=['POST'])
def init_session():
    data = request.json
    user_id = data.get('userId') if data else None
    return ok({
        "sessionId": f"sess_{user_id}",
        "mock_token": "mock.jwt.token"
    })
