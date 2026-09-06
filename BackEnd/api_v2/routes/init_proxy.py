from flask import Blueprint, request, current_app
from ..utils.token_generator import generate_upstream_token
from ..utils.upstream_env import env_from_request, upstream_base, describe
from ..utils.response_helpers import ok, err
from ..utils.request_identity import resolve_user_email
import httpx

bp = Blueprint('init_proxy', __name__)

@bp.route('/', methods=['GET'])
def get_init_status():
    # 身分只認這次請求帶的 token，而且驗簽、驗期、驗 aud。解不出來就回 401，
    # 不再退回任何預設帳號（0905 文件 E-7 / E-11）。
    user_email, auth_error = resolve_user_email()
    if auth_error:
        return auth_error

    env = env_from_request()
    upstream_token = generate_upstream_token(user_email, env)

    base_url = upstream_base(env)
    url = f"{base_url}/v1/init/"
    
    headers = {
        "Authorization": f"Bearer {upstream_token}",
        "Accept": "application/json"
    }

    try:
        print(f"[Init Proxy] Forwarding request to {url}...", flush=True)
        response = httpx.get(url, headers=headers, timeout=15.0)

        try:
            data = response.json()
        except Exception:
            print(f"[Init Proxy] Upstream did not return valid JSON. Status: {response.status_code}")
            return err('UPSTREAM_INVALID_RESPONSE', 'Upstream returned invalid JSON', 502)

        print(f"[Init Proxy] Response Status: {response.status_code}, data: {data}")

        if response.status_code >= 400:
            return err('UPSTREAM_ERROR', 'Upstream service returned an error', response.status_code, details=data)

        return ok(data)

    except httpx.RequestError as e:
        print(f"[Init Proxy] Network Error: {e}")
        return err('UPSTREAM_NETWORK_ERROR', 'Upstream network error', 503, details=str(e))
    except Exception as e:
        print(f"[Init Proxy] Unexpected Error: {e}")
        return err('PROXY_ERROR', 'Internal proxy error', 500, details=str(e))
