from flask import Blueprint, request
import jwt
import time
import uuid
import os
import httpx

from ..utils.response_helpers import ok, err
from ..utils.traitty_api import fetch_init_data

bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv('PARTY_A_PLUGIN_SECRET', "traitty_ai_api")

@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email') if data else None

    if not email:
        return err('MISSING_FIELD', 'Email is required', 400, field='email')

    # Validate email against Traitty API before issuing token
    try:
        init_data = fetch_init_data(email)
        if not init_data.get('status'):
            return err('UNAUTHORIZED', 'Account not found or inactive', 401)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403, 404):
            return err('UNAUTHORIZED', 'Invalid or inactive Traitty account', 401)
        return err('SERVICE_UNAVAILABLE', 'Unable to verify account, please try again later', 503)
    except Exception:
        return err('SERVICE_UNAVAILABLE', 'Unable to verify account, please try again later', 503)

    payload = {
        "email": email,
        "user_id": 1,
        "token_type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 120,  # 2-minute short-lived token
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
