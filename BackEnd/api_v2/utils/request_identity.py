"""這次請求的使用者身分——從 Authorization 的 JWT 取 email。

為什麼要有這個檔：`candidates.py`／`reports.py`／`init_proxy.py` 原本各自寫著同一段
「解不開 token 就退回寫死的 eva@wepredict.io」。2026-09-05 對 PRD 實測時，
`Authorization: Bearer null` 得到的是：

    POST /api/v2/reports/batch  -> HTTP 200 success:true，2 份報告，每份 traits=0
    GET  /api/v2/candidates/    -> HTTP 200 success:true，另一個企業的 2 位候選人
                                   （該使用者實際有 497 位）

前端因此判定成功、`traitReportsState` 變成 ready、`chat.py` 的守門因為 key 都在也放行，
接著 `from_trait_reports` 因為 scores 是空的把每個人都丟掉，整個請求悄悄退回舊路徑。
使用者看到的是「資料好像少了」而畫面上一切正常。現在一律回 401，不再有預設身分。

**這裡不驗簽章、也不驗 exp**，維持本專案既有作法。`/auth/login` 簽出來的 token 只有
2 分鐘，而 widget 登入時取一次就一路用到底（`useChatLogic.js` 的 `userToken.value`），
驗 exp 會讓正常使用者在 2 分鐘後全部被擋。要收緊到「驗簽 + 驗期」得先讓前端會換 token，
那是另一個單元。這一單元只拿掉「預設身分」這條退路。

`/chat/` 不走這裡——它本來就驗簽、驗期、驗 aud（`chat.py`），不需要放寬。
"""

from typing import Optional

import jwt
from flask import request

from .response_helpers import err


def user_email_from_request() -> Optional[str]:
    """回這次請求的使用者 email。

    缺 header、不是 Bearer、JWT 解不開、或 payload 裡沒有 email —— 一律回 None，
    由呼叫端回 401。不提供任何預設值。
    """
    auth_header = request.headers.get('Authorization') or ''
    if not auth_header.startswith('Bearer '):
        _log('missing or malformed Authorization header')
        return None

    incoming_token = auth_header[7:].strip()
    if not incoming_token or incoming_token.lower() in ('null', 'undefined'):
        _log('empty token')
        return None

    try:
        decoded = jwt.decode(incoming_token, options={"verify_signature": False})
    except Exception as e:
        _log(f'failed to decode token: {e}')
        return None

    email = decoded.get('email')
    if not isinstance(email, str) or not email.strip():
        _log('token carries no email claim')
        return None

    return email.strip()


def unauthorized():
    """身分解不出來時的統一回應。用字與 `chat.py` 的 401 一致。"""
    return err('UNAUTHORIZED', '請先登入後再試', 401)


def _log(reason: str) -> None:
    try:
        path = request.path
    except Exception:
        path = '?'
    print(f"[Auth] 401 on {path}: {reason}", flush=True)
