"""扣點紀錄要記住它打過哪一個上游，補送要回到同一個上游（單元 U3a）。

用法：
    python scripts/verify_settlement_env.py

問題長什麼樣：`submit_daily_settlement()` 打上游時走 `env_from_request()`，
`ALLOW_UPSTREAM_ENV_SWITCH` 打開時解得出 `prd`，於是用 `TRAITTY_API_BASE_PRD` +
`PARTY_A_PLUGIN_SECRET_PRD` 送出。但 `daily_settlements` 以前沒有欄位記下這件事，
`scheduler.py` 補送時只能用預設上游與預設 secret——一筆 PRD 的扣點會被重送到 UAT，
或用錯的 shared secret 拿到 401。`upstream_env.py` 自己的 docstring 就寫了「切到 PRD
之後扣的是線上帳號的真實額度，這不是唯讀的觀察模式」。

不打網路、不碰 PostgreSQL：資料庫是 in-memory SQLite（`models.py` 的欄位型別都是
SQLite 也支援的），`httpx.post` 換成攔截器，只記下它被叫去打哪一個網址。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

import jwt                                                            # noqa: E402
from flask import Flask                                               # noqa: E402
from sqlalchemy import create_engine                                  # noqa: E402
from sqlalchemy.orm import sessionmaker                               # noqa: E402

from api_v2.database.models import Base, DailySettlementRecord        # noqa: E402
from api_v2.utils import traitty_api                                  # noqa: E402
from api_v2.utils import upstream_env as ue                           # noqa: E402
from api_v2.scheduler import upstream_for_record                      # noqa: E402

UAT = 'https://uat.example.test'
PRD = 'https://prd.example.test'

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def app_with(switch_on):
    app = Flask(__name__)
    app.config.update(TRAITTY_API_BASE=UAT,
                      TRAITTY_API_BASE_PRD=PRD,
                      PARTY_A_PLUGIN_SECRET_PRD='prd-secret',
                      ALLOW_UPSTREAM_ENV_SWITCH=switch_on)
    return app


def fresh_db():
    """每個情境一個乾淨的 in-memory SQLite，互不影響。"""
    engine = create_engine('sqlite://')
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class Captured:
    """攔下 httpx.post，記錄它被叫去打哪裡，並依 `ok` 決定成功或失敗。"""

    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def __call__(self, url, headers=None, json=None, timeout=None):
        self.calls.append({'url': url, 'headers': headers or {}, 'json': json})
        outer = self

        class Resp:
            status_code = 200 if outer.ok else 500
            text = '' if outer.ok else 'upstream exploded'

            def raise_for_status(self):
                if not outer.ok:
                    raise RuntimeError('upstream exploded')

            def json(self):
                return {'status': True, 'summary': {'accepted': 1}}

        return Resp()


def token_claiming(env_value):
    return jwt.encode({'email': 'x@example.com', ue.ENV_CLAIM: env_value},
                      'irrelevant', algorithm='HS256')


def submit(app, session, capture, env_claim):
    """在帶著某個 upstream_env 宣告的請求裡跑一次 submit_daily_settlement()。"""
    orig_session, orig_post = traitty_api.get_db_session, traitty_api.httpx.post
    traitty_api.get_db_session = lambda: session
    traitty_api.httpx.post = capture
    try:
        with app.test_request_context(
                headers={'Authorization': f'Bearer {token_claiming(env_claim)}'}):
            try:
                traitty_api.submit_daily_settlement('x@example.com', 7, 'sess-1',
                                                    message_id='42')
            except Exception:
                pass  # 失敗情境是刻意的：要驗的是失敗之後那筆紀錄長什麼樣
    finally:
        traitty_api.get_db_session, traitty_api.httpx.post = orig_session, orig_post
    return session.query(DailySettlementRecord).one()


def main():
    os.environ['PARTY_A_PLUGIN_SECRET'] = 'main-secret'

    print('\n[1] 開關打開 + token 宣告 prd：紀錄要寫下 prd，且真的打 PRD')
    session, cap = fresh_db(), Captured(ok=True)
    rec = submit(app_with(True), session, cap, 'prd')
    check('upstream_env 存成 prd', rec.upstream_env == 'prd', rec.upstream_env)
    check('status 成功後為 SYNCED', rec.status == 'SYNCED', rec.status)
    check('POST 打的是 PRD 網址', cap.calls[0]['url'].startswith(PRD), cap.calls[0]['url'])
    tok = cap.calls[0]['headers']['Authorization'][7:]
    jwt.decode(tok, 'prd-secret', algorithms=['HS256'], audience='traitty')
    check('token 是用 PRD secret 簽的', True)

    print('\n[2] 開關關閉：解不出 prd，紀錄與實際打的都是 default（既有安全邊界不變）')
    session, cap = fresh_db(), Captured(ok=True)
    rec = submit(app_with(False), session, cap, 'prd')
    check('upstream_env 存成 default', rec.upstream_env == 'default', rec.upstream_env)
    check('POST 打的是預設上游', cap.calls[0]['url'].startswith(UAT), cap.calls[0]['url'])

    print('\n[3] 上游失敗時，FAILED 紀錄仍保有正確的 upstream_env（補送才有依據）')
    session, cap = fresh_db(), Captured(ok=False)
    rec = submit(app_with(True), session, cap, 'prd')
    check('status 為 FAILED', rec.status == 'FAILED', rec.status)
    check('upstream_env 仍是 prd', rec.upstream_env == 'prd', rec.upstream_env)
    check('last_error 有記錄', bool(rec.last_error), (rec.last_error or '')[:40])

    print('\n[4] 補送解析：即使開關已被關掉，PRD 的紀錄仍回到 PRD')
    #     這就是這個單元存在的理由。以前 scheduler 用
    #     os.getenv('TRAITTY_API_BASE') 一律送預設上游。
    with app_with(False).app_context():
        env, base = upstream_for_record(rec)
        check('upstream_for_record 回 prd', env == 'prd', env)
        check('base_url 是 PRD', base == PRD, base)
        check('對照組：normalize_env 會被閘門改寫成 default（所以不能用它）',
              ue.normalize_env('prd') == 'default')

    print('\n[5] 補送解析：default 的紀錄還是走預設上游')
    with app_with(True).app_context():
        rec.upstream_env = 'default'
        env, base = upstream_for_record(rec)
        check('回 default', env == 'default', env)
        check('base_url 是預設上游', base == UAT, base)

    print('\n[6] 欄位被寫髒或是舊資料（NULL）也不會變成任意上游')
    with app_with(True).app_context():
        for bad in (None, '', 'http://evil.example.com', 'staging', '../prd'):
            rec.upstream_env = bad
            env, base = upstream_for_record(rec)
            check(f'{bad!r} -> env={env}, base={base}',
                  env in ue.KNOWN_ENVS and env != 'prd' and base == UAT, (env, base))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
