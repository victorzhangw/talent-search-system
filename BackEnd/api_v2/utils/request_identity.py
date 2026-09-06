"""這次請求的使用者身分——驗證 Authorization 的 JWT 並取出 email。

為什麼要有這個檔：`candidates.py`／`reports.py`／`init_proxy.py` 原本各自寫著同一段
「解不開 token 就退回寫死的帳號」。2026-09-05 對 PRD 實測時，
`Authorization: Bearer null` 得到的是：

    POST /api/v2/reports/batch  -> HTTP 200 success:true，2 份報告，每份 traits=0
    GET  /api/v2/candidates/    -> HTTP 200 success:true，另一個企業的 2 位候選人
                                   （該使用者實際有 497 位）

前端因此判定成功、`traitReportsState` 變成 ready、`chat.py` 的守門因為 key 都在也放行，
接著 `from_trait_reports` 因為 scores 是空的把每個人都丟掉，整個請求悄悄退回舊路徑。
使用者看到的是「資料好像少了」而畫面上一切正常。（0905 文件 E-7）

現在一律回 401，不再有預設身分；而且**驗簽章、驗效期、驗 aud**（E-11）——只解不驗的
話，任何人偽造一張 `{"email": "別人"}` 都讀得到別人的資料。

驗效期以前做不到，因為 `/auth/login` 的 token 只有 2 分鐘而 widget 登入時取一次就一路
用到底，一驗就會把正常使用者在兩分鐘後全部擋掉。前端改成每次呼叫前先換一張新 token
之後（`useChatLogic.js` 的 `authFetch`），這裡才收得緊。

`env_from_request()`（`upstream_env.py`）仍然是不驗簽只取欄位——那是刻意的，它的安全性
靠白名單與預設關閉的開關，不靠解碼；詳見該檔的說明。
"""

import os
from typing import Optional, Tuple

import jwt
from flask import request

from .response_helpers import err

# 簽發端是 `routes/auth.py`，用同一把 secret、同一個 aud。
AUDIENCE = 'traitty'

# 允許的時鐘誤差。token 本身只有 2 分鐘，這個值只是讓前後端差幾秒不會誤擋。
LEEWAY_SECONDS = 10


def _secret() -> str:
    # 在呼叫當下讀，不在 import 當下讀——測試會在載入模組之後才設環境變數。
    return os.getenv('PARTY_A_PLUGIN_SECRET', 'traitty_ai_api')


def resolve_user_email() -> Tuple[Optional[str], object]:
    """回 `(email, error_response)`。

    解得出身分就是 `(email, None)`；否則 `(None, <flask 回應>)`，呼叫端直接 return 它。
    沒有預設值，也沒有「解不開就算了」這條路。
    """
    auth_header = request.headers.get('Authorization') or ''
    if not auth_header.startswith('Bearer '):
        return None, _reject('missing or malformed Authorization header')

    token = auth_header[7:].strip()
    if not token or token.lower() in ('null', 'undefined'):
        return None, _reject('empty token')

    try:
        claims = jwt.decode(token, _secret(), algorithms=['HS256'],
                            audience=AUDIENCE, leeway=LEEWAY_SECONDS)
    except jwt.ExpiredSignatureError:
        # 與 `/chat/` 用同一個碼：前端據此決定是「重新整理」還是「請重新登入」。
        _log('token expired')
        return None, err('TOKEN_EXPIRED', '登入已過期，請重新整理頁面', 401)
    except jwt.InvalidTokenError as e:
        return None, _reject(f'invalid token: {e}')

    email = claims.get('email')
    if not isinstance(email, str) or not email.strip():
        return None, _reject('token carries no email claim')

    return email.strip(), None


def unauthorized():
    """身分解不出來時的統一回應。用字與 `chat.py` 的 401 一致。"""
    return err('UNAUTHORIZED', '請先登入後再試', 401)


def _reject(reason: str):
    _log(reason)
    return unauthorized()


def _log(reason: str) -> None:
    try:
        path = request.path
    except Exception:
        path = '?'
    print(f"[Auth] 401 on {path}: {reason}", flush=True)
