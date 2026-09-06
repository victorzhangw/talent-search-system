"""無效或缺少 token 一律回 401，不再退回寫死的帳號。

為什麼要有這支：`candidates.py`／`reports.py`／`init_proxy.py` 原本解不開 token 就用
`eva@wepredict.io` 去打上游。2026-09-05 對 PRD 實測時，`Authorization: Bearer null`
拿到的是 HTTP 200 + 另一個企業的資料（該使用者實際有 497 位候選人，回來 2 位），
前端判定成功，使用者只看到「資料好像少了」。（0905 待驗證文件 E-7）

這支釘住的是「沒有預設身分」這件事。四種壞 token（沒 header／Bearer null／不是 JWT／
沒有 email 欄位）對五個端點都必須是 401；合法 token 則必須通得過這一關。

E-11 之後再加一層：簽章、效期、aud 都要驗（第 [8] 節）。偽造的簽章、過期的 token、
別人家的 aud，一律進不來。

用法：
    python scripts/verify_request_identity.py

不打網路：上游走 MOCK，init proxy 的 httpx.get 換成 stub。
"""

import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

import jwt as pyjwt                                    # noqa: E402
from api_v2.app import create_app                      # noqa: E402
from api_v2.routes import candidates as cand_route     # noqa: E402
from api_v2.routes import init_proxy as init_route     # noqa: E402
from api_v2.routes import reports as reports_route     # noqa: E402
from api_v2.routes import chat as chat_route           # noqa: E402
from api_v2.services.rag_engine import RAGService      # noqa: E402
from api_v2.utils.upstream_env import ENV_CLAIM        # noqa: E402

failures = []

# 五個端點：(標籤, method, path, body)。by-ids 要帶 ids，否則 400 會先擋在身分檢查前面。
ENDPOINTS = [
    ('GET  /api/v2/candidates/',          'GET',  '/api/v2/candidates/?limit=1', None),
    ('GET  /api/v2/candidates/by-ids',    'GET',  '/api/v2/candidates/by-ids?ids=1', None),
    ('GET  /api/v2/candidates/1/report',  'GET',  '/api/v2/candidates/1/report', None),
    ('POST /api/v2/reports/batch',        'POST', '/api/v2/reports/batch', {'assessment_ids': [1]}),
    ('GET  /api/v2/init/',                'GET',  '/api/v2/init/', None),
]

# 四種進不去的身分。None 代表整個 header 都不送。
BAD_TOKENS = [
    ('沒有 Authorization header', None),
    ('Bearer null（前端 userToken 是 null 時實際送出的字串）', 'null'),
    ('不是 JWT', 'not-a-jwt'),
    ('JWT 但沒有 email 欄位', None),  # 下面填
]


class _StubRag:
    """/chat/ 的模型替身：只記下傳進來的身分，不呼叫模型。

    路由的 before_request 會在 rag_service 是 None 時自己建一個真的 RAGService，
    在 MOCK 模式下那會去讀不存在的 mock_data.json 而 500——所以凡是要打 /chat/ 的
    段落都要先把它換掉。
    """

    seen = {}
    model_name = 'stub'

    def load_history(self, session_id):
        return []

    def generate_response(self, *args, **kwargs):
        _StubRag.seen.update(kwargs)
        return iter([]), 'stub'


class _FakeService:
    """上游的替身：回空清單，讓路由跑完但不打網路。"""

    def get_candidates(self, *a, **k):
        return {'data': [], 'page': {'total': 0}}

    def get_assessments(self, *a, **k):
        return []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def sign(payload):
    secret = os.getenv('PARTY_A_PLUGIN_SECRET', 'traitty_ai_api')
    return pyjwt.encode(payload, secret, algorithm='HS256')


def call(app, method, path, body, token):
    headers = {} if token is None else {'Authorization': f'Bearer {token}'}
    client = app.test_client()
    if method == 'POST':
        return client.post(path, json=body, headers=headers)
    return client.get(path, headers=headers)


def is_401(resp):
    if resp.status_code != 401:
        return False, f'HTTP {resp.status_code}'
    try:
        payload = json.loads(resp.get_data(as_text=True))
    except Exception:
        return False, 'body 不是 JSON'
    if payload.get('success') is not False:
        return False, f"success={payload.get('success')}"
    if payload.get('data') is not None:
        return False, '401 竟然還帶 data'
    code = (payload.get('error') or {}).get('code')
    return code == 'UNAUTHORIZED', f'code={code}'


def main():
    app = create_app()
    # 上游走 MOCK：這支驗的是身分這一關，不是上游整合。
    app.config['INTEGRATION_MODE'] = 'MOCK'

    BAD_TOKENS[3] = ('JWT 但沒有 email 欄位', sign({'user_id': 1, 'aud': 'traitty'}))

    print('\n[1] 壞身分：五個端點 x 四種壞 token，全部要是 401 UNAUTHORIZED')
    for label, method, path, body in ENDPOINTS:
        for token_label, token in BAD_TOKENS:
            resp = call(app, method, path, body, token)
            good, detail = is_401(resp)
            check(f'{label} <- {token_label}', good, detail)

    print('\n[2] 沒有預設身分：原始碼裡不能再有那個寫死的 email')
    routes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                              'api_v2', 'routes')
    hits = []
    for name in sorted(os.listdir(routes_dir)):
        if not name.endswith('.py'):
            continue
        text = open(os.path.join(routes_dir, name), encoding='utf-8').read()
        if 'eva@wepredict.io' in text:
            hits.append(name)
    check('routes/ 裡沒有 eva@wepredict.io', not hits, hits)

    print('\n[3] 合法 token 通得過這一關（不能把正常使用者一起擋掉）')
    good_token = sign({'email': 'someone@example.com', 'user_id': 1, 'aud': 'traitty'})

    # 上游全部換成 stub（`_FakeService`，模組層級）：這一節要問的是「身分這一關有沒有
    # 把人放過去」，不是上游整合。回空清單就夠——路由邏輯本來就有各自的測試。
    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {'status': True, 'quota_summary': {}}

    saved = (cand_route.get_service, reports_route.get_service, init_route.httpx.get)
    cand_route.get_service = lambda: _FakeService()
    reports_route.get_service = lambda: _FakeService()
    init_route.httpx.get = lambda *a, **k: _Resp()
    try:
        for label, method, path, body in ENDPOINTS:
            resp = call(app, method, path, body, good_token)
            # `/candidates/1/report` 在空清單下回 404 NOT_FOUND——那是「通過身分之後」
            # 才做得到的判斷，正是這裡要看的。
            check(f'{label} <- 合法 token 不是 401', resp.status_code != 401,
                  f'HTTP {resp.status_code}')
    finally:
        cand_route.get_service, reports_route.get_service, init_route.httpx.get = saved

    print('\n[4] 解出來的 email 真的被拿去簽上游 token（不是被換成別人）')
    from api_v2.utils.request_identity import resolve_user_email
    with app.test_request_context(headers={'Authorization': f'Bearer {good_token}'}):
        email, error = resolve_user_email()
        check('resolve_user_email() 回 token 裡的 email', email == 'someone@example.com', email)
        check('合法 token 沒有 error', error is None, error)
    with app.test_request_context(headers={'Authorization': 'Bearer null'}):
        email, error = resolve_user_email()
        check('壞 token 回 None（不是回預設值）', email is None, email)
        check('壞 token 一定帶著 error 回應', error is not None)

    print()
    print('[5] /chat/ 把「這次是誰在問」傳給 RAG（E-9）')
    # /chat/ 本來就驗簽、驗期、驗 aud，所以這裡的 token 要簽得對。
    chat_ok = sign({'email': 'asker@example.com', 'aud': 'traitty', 'exp': 4102444800})
    chat_no_email = sign({'sub': 'tester', 'aud': 'traitty', 'exp': 4102444800})

    seen = _StubRag.seen
    seen.clear()

    body = {'query': '你好', 'session_id': 'IDENTITY_TEST', 'user_id': 'asker@example.com',
            'mode': 'expert', 'candidate_ids': [], 'candidates_info': [], 'trait_reports': {}}

    saved_rag = chat_route.rag_service
    chat_route.rag_service = _StubRag()
    try:
        resp = app.test_client().post('/chat/', json=body,
                                      headers={'Authorization': 'Bearer ' + chat_no_email})
        good, detail = is_401(resp)
        check('POST /chat/ <- 簽章正確但沒有 email 欄位 -> 401', good, detail)

        app.test_client().post('/chat/', json=body,
                               headers={'Authorization': 'Bearer ' + chat_ok})
        check('generate_response() 收到的 user_email 是發問者',
              seen.get('user_email') == 'asker@example.com', seen.get('user_email'))
    finally:
        chat_route.rag_service = saved_rag

    print()
    print('[6] RAG 沒有身分就不做事，也沒有寫死的預設身分')
    engine_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                   'api_v2', 'services', 'rag_engine.py'),
                      encoding='utf-8').read()
    check('rag_engine.py 裡沒有 eva@wepredict.io', 'eva@wepredict.io' not in engine_src)

    raised = None
    try:
        RAGService.generate_response(object(), 'q', [], 's')
    except ValueError as e:
        raised = str(e)
    except Exception as e:
        raised = type(e).__name__ + ': ' + str(e)
    check('少了 user_email 就 raise ValueError（不是靜默用預設值）',
          isinstance(raised, str) and 'user_email' in raised, raised)

    print()
    print('[7] 簽上游 token 的鑰匙跟著環境走（E-10）')
    # 網址早就跟著 env 走了（integration_real.base_url），但 candidates / reports 以前
    # 是 generate_upstream_token(user_email) 沒帶 env——鑰匙固定是預設那把。今天沒事只是
    # 因為 PRD 剛好接受同一把（C-1）；哪天不是，症狀會是「init 正常、清單與報告 401」。
    app.config['ALLOW_UPSTREAM_ENV_SWITCH'] = True
    app.config['PARTY_A_PLUGIN_SECRET_PRD'] = 'prd-only-secret'
    app.config['TRAITTY_API_BASE_PRD'] = 'https://prd.example.test'

    prd_token = sign({'email': 'someone@example.com', 'aud': 'traitty',
                      ENV_CLAIM: 'prd', 'exp': 4102444800})

    for module, label in ((cand_route, 'candidates'), (reports_route, 'reports')):
        recorded = {}
        real = module.generate_upstream_token

        def spy(email, env=None, _real=real, _rec=recorded):
            _rec['env'] = env
            _rec['token'] = _real(email, env)
            return _rec['token']

        module.generate_upstream_token = spy
        saved_service = module.get_service
        module.get_service = lambda: _FakeService()
        try:
            path = ('/api/v2/candidates/?limit=1' if label == 'candidates'
                    else '/api/v2/reports/batch')
            if label == 'candidates':
                app.test_client().get(path, headers={'Authorization': 'Bearer ' + prd_token})
            else:
                app.test_client().post(path, json={'assessment_ids': [1]},
                                       headers={'Authorization': 'Bearer ' + prd_token})
        finally:
            module.generate_upstream_token = real
            module.get_service = saved_service

        check(f'{label}: 帶著 env=prd 去簽', recorded.get('env') == 'prd', recorded.get('env'))
        verified = None
        try:
            pyjwt.decode(recorded.get('token', ''), 'prd-only-secret',
                         algorithms=['HS256'], audience='traitty')
            verified = True
        except Exception as e:
            verified = f'{type(e).__name__}: {e}'
        check(f'{label}: 簽出來的 token 用 PRD 的 secret 驗得過', verified is True, verified)

    app.config['ALLOW_UPSTREAM_ENV_SWITCH'] = False

    print()
    print('[8] 驗簽 + 驗期 + 驗 aud（E-11）')
    # 前端改成每次呼叫前先換一張新 token（useChatLogic.js 的 authFetch）之後，這裡才
    # 收得緊：以前驗 exp 會把正常使用者在兩分鐘後全部擋掉。
    now = int(time.time())
    forged = pyjwt.encode({'email': 'someone@example.com', 'aud': 'traitty',
                           'exp': now + 600}, 'not-the-real-secret', algorithm='HS256')
    expired = sign({'email': 'someone@example.com', 'aud': 'traitty',
                    'iat': now - 600, 'exp': now - 300})
    wrong_aud = sign({'email': 'someone@example.com', 'aud': 'someone-else',
                      'exp': now + 600})
    valid = sign({'email': 'someone@example.com', 'aud': 'traitty', 'exp': now + 600})

    chat_endpoint = ('POST /chat/', 'POST', '/chat/',
                     {'query': '你好', 'session_id': 'IDENTITY_TEST',
                      'user_id': 'someone@example.com', 'mode': 'expert',
                      'candidate_ids': [], 'candidates_info': [], 'trait_reports': {}})

    chat_saved = chat_route.rag_service
    chat_route.rag_service = _StubRag()
    for label, method, path, body in ENDPOINTS + [chat_endpoint]:
        resp = call(app, method, path, body, forged)
        good, detail = is_401(resp)
        check(f'{label} <- 偽造簽章', good, detail)

        resp = call(app, method, path, body, wrong_aud)
        good, detail = is_401(resp)
        check(f'{label} <- aud 不是 traitty', good, detail)

        resp = call(app, method, path, body, expired)
        code = ''
        try:
            code = (json.loads(resp.get_data(as_text=True)).get('error') or {}).get('code')
        except Exception:
            pass
        check(f'{label} <- 過期 -> 401 TOKEN_EXPIRED',
              resp.status_code == 401 and code == 'TOKEN_EXPIRED',
              f'HTTP {resp.status_code} code={code}')

    chat_route.rag_service = chat_saved

    # 收緊之後，正常的（沒過期、簽章對的）token 還是要過得去。
    saved = (cand_route.get_service, reports_route.get_service, init_route.httpx.get)
    cand_route.get_service = lambda: _FakeService()
    reports_route.get_service = lambda: _FakeService()

    class _Resp2:
        status_code = 200

        @staticmethod
        def json():
            return {'status': True, 'quota_summary': {}}

    init_route.httpx.get = lambda *a, **k: _Resp2()
    try:
        for label, method, path, body in ENDPOINTS:
            resp = call(app, method, path, body, valid)
            check(f'{label} <- 沒過期的合法 token 不是 401', resp.status_code != 401,
                  f'HTTP {resp.status_code}')
    finally:
        cand_route.get_service, reports_route.get_service, init_route.httpx.get = saved

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
