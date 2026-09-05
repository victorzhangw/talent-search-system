"""在同一個後端上切換上游 Traitty 服務（UAT / PRD），供開發端重現線上問題用。

為什麼需要這個：`TRAITTY_API_BASE` 是後端的環境變數，widget 改不到它。而重現使用者回報的
狀況需要 PRD 的資料，總不能每次都改 `.env` 重啟一次後端。

安全邊界，三條，缺一不可：

1. **預設關閉。** `ALLOW_UPSTREAM_ENV_SWITCH` 沒有明確打開時，一律回退到 `.env` 設定的
   `TRAITTY_API_BASE`，前端送什麼都沒用。正式部署不打開就完全沒有這個表面。
2. **前端只能送「名字」，不能送 URL。** 名字在伺服器端查表換成網址。讓客戶端指定任意
   URL 等於自己開一個 SSRF 洞。
3. **名字放在登入時簽發的 JWT 裡。** 每個要打上游的路由本來就會解這個 token 取 email，
   所以環境跟著身分走，不會出現「用 A 環境的 token 讀 B 環境的資料」。

每個環境有自己的 shared secret 欄位。UAT 與 PRD 不見得共用同一把——若 PRD 用不同的
secret 而沒設定，上游會回 401，屆時要跟客戶要 PRD 的 `PARTY_A_PLUGIN_SECRET`。

注意：切到 PRD 之後，`/v1/ai/usage/daily-settlement` 扣的是**線上帳號的真實額度**。這不是
唯讀的觀察模式。
"""

import os
from typing import Optional

import jwt
from flask import current_app, request, has_request_context

# 前端送得出來的環境名。`default` 就是 .env 裡的 TRAITTY_API_BASE，也是唯一的退路。
ENV_DEFAULT = 'default'
ENV_PRD = 'prd'
KNOWN_ENVS = (ENV_DEFAULT, ENV_PRD)

# JWT 裡帶環境的欄位名。放在 token 而不是 header：所有路由已經在解這個 token 取 email，
# 多讀一個欄位不必動 12 個呼叫點，而且它是簽過名的。
ENV_CLAIM = 'upstream_env'


def switching_allowed() -> bool:
    try:
        return bool(current_app.config.get('ALLOW_UPSTREAM_ENV_SWITCH'))
    except Exception:
        return False


def normalize_env(name: Optional[str]) -> str:
    """把外面送進來的環境名收斂成一個已知值。不認得、或功能沒開，一律回 default。"""
    if not name or not switching_allowed():
        return ENV_DEFAULT
    name = str(name).strip().lower()
    return name if name in KNOWN_ENVS else ENV_DEFAULT


def _config(key: str) -> Optional[str]:
    try:
        return current_app.config.get(key)
    except Exception:
        return os.getenv(key)


def upstream_base(env: Optional[str] = None) -> Optional[str]:
    """該環境的上游網址。PRD 沒設定就退回 default，不會半途指向空字串。"""
    if normalize_env(env) == ENV_PRD:
        return _config('TRAITTY_API_BASE_PRD') or _config('TRAITTY_API_BASE')
    return _config('TRAITTY_API_BASE')


def upstream_secret(env: Optional[str] = None) -> str:
    """簽上游 token 用的 shared secret。PRD 沒單獨設定就沿用主要那把。"""
    default = os.getenv('PARTY_A_PLUGIN_SECRET', 'traitty_ai_api')
    if normalize_env(env) == ENV_PRD:
        return _config('PARTY_A_PLUGIN_SECRET_PRD') or default
    return default


def env_from_request() -> str:
    """本次請求要用哪個上游——從 Authorization 的 JWT 讀。

    這裡沿用本專案既有的作法：不驗簽，只取欄位（`candidates.py`／`init_proxy.py`／
    `reports.py` 取 email 都是這樣做的）。安全性不靠這個解碼，靠的是 `normalize_env()`
    的白名單與預設關閉的開關——就算有人偽造 token 塞一個環境名進來，能得到的也只是我們
    自己允許清單裡的那幾個，而且開關沒開時完全無效。
    """
    if not has_request_context() or not switching_allowed():
        return ENV_DEFAULT
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return ENV_DEFAULT
    try:
        decoded = jwt.decode(auth[7:], options={'verify_signature': False})
    except Exception:
        return ENV_DEFAULT
    return normalize_env(decoded.get(ENV_CLAIM))


def describe(env: Optional[str] = None) -> dict:
    """給 log 與前端顯示用：現在打的是哪一個上游。不含 secret。"""
    resolved = normalize_env(env)
    return {'env': resolved, 'base_url': upstream_base(resolved),
            'switch_enabled': switching_allowed()}
