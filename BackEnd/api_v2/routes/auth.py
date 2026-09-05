from flask import Blueprint, request
import jwt
import time
import uuid
import os
import httpx

from ..utils.response_helpers import ok, err
from ..utils.traitty_api import fetch_init_data
from ..utils.upstream_env import (ENV_CLAIM, ENV_DEFAULT, KNOWN_ENVS, describe,
                                  normalize_env, switching_allowed)

bp = Blueprint('auth', __name__)

SECRET_KEY = os.getenv('PARTY_A_PLUGIN_SECRET', "traitty_ai_api")

@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email') if data else None

    if not email:
        return err('MISSING_FIELD', 'Email is required', 400, field='email')

    # 開發端切換上游（UAT / PRD）。`normalize_env` 會把不認得的名字、以及功能未開啟時的
    # 任何值，一律收斂回 default，所以這裡不必再擋一次。帳號是對「該環境」驗的——同一個
    # email 在 UAT 有效不代表在 PRD 也有效，驗錯環境等於發出一張用不了的 token。
    env = normalize_env(data.get('env') if data else None)

    # Validate email against Traitty API before issuing token
    try:
        init_data = fetch_init_data(email, env)
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
        "scope": "traitty_plugin",
        # 環境跟著身分走。後續每個要打上游的路由本來就會解這個 token 取 email，多讀一個
        # 欄位就好，不必在 12 個前端呼叫點各加一次 header。
        ENV_CLAIM: env,
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT"}
    )

    return ok({
        "token": token,
        "user": {"email": email, "id": 1},
        # 前端拿這個顯示「現在連的是哪一個環境」，並在切換功能沒開時把選項收起來。
        "upstream": describe(env),
    })


@bp.route('/environments', methods=['GET'])
def list_environments():
    """開發端 widget 用來決定要不要顯示環境切換器，以及有哪些選項。

    功能沒開就回一份空清單——前端因此不需要自己判斷是不是開發環境，看後端說了算。
    不回傳任何 secret。
    """
    if not switching_allowed():
        return ok({'enabled': False, 'environments': [], 'current': ENV_DEFAULT})
    from ..utils.upstream_env import upstream_base
    return ok({
        'enabled': True,
        'current': ENV_DEFAULT,
        'environments': [{'env': name, 'base_url': upstream_base(name)}
                         for name in KNOWN_ENVS],
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
