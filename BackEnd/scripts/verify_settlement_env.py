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

from datetime import datetime                                         # noqa: E402

import jwt                                                            # noqa: E402
from flask import Flask                                               # noqa: E402
from sqlalchemy import create_engine                                  # noqa: E402
from sqlalchemy.orm import sessionmaker                               # noqa: E402

from api_v2.database.models import Base, DailySettlementRecord        # noqa: E402
from api_v2.utils import traitty_api                                  # noqa: E402
from api_v2.utils import upstream_env as ue                           # noqa: E402
from api_v2 import scheduler                                          # noqa: E402
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


def make_record(status='FAILED', env='default', retry_count=0, days_ago=1):
    """一筆長得像真的扣點紀錄。`days_ago` 用來測 7 天掃描視窗。

    `created_at` 固定為 2026-09-01 的偏移，讓 report_date 的斷言不隨執行日期漂移。
    """
    from datetime import timedelta
    base = datetime(2026, 9, 1, 10, 30, 0)
    return DailySettlementRecord(
        user_id='x@example.com', plan_id=7, session_id='sess-1', message_id='42',
        upstream_env=env, status=status, retry_count=retry_count,
        created_at=base if days_ago == 1 else base - timedelta(days=days_ago))


def run_job(app, session, capture, dry_run=False, limit=None):
    """跑一輪 scheduler.process_pending_and_failed_records()，資料庫換成傳入的 session。

    掃描視窗是相對 `datetime.utcnow()` 算的，而測試資料固定在 2026-09-01，所以這裡把
    scheduler 的 `datetime` 換掉，讓「現在」永遠是 2026-09-02——否則這支腳本會在
    2026-09-08 之後開始無聲地選不到任何紀錄，變成一個永遠通過但什麼都沒驗的測試。
    """
    class FrozenDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return datetime(2026, 9, 2, 12, 0, 0)

    orig = (scheduler.get_db_session, scheduler.httpx.post, scheduler.datetime)
    scheduler.get_db_session = lambda: session
    scheduler.httpx.post = capture
    scheduler.datetime = FrozenDatetime
    try:
        return scheduler.process_pending_and_failed_records(app, dry_run=dry_run,
                                                            limit=limit)
    finally:
        (scheduler.get_db_session, scheduler.httpx.post, scheduler.datetime) = orig


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

    print('\n[7] 補送作業跑一輪：成功的轉 SYNCED')
    session, cap = fresh_db(), Captured(ok=True)
    session.add(make_record(status='FAILED', env='prd', retry_count=1))
    session.commit()
    total, failed = run_job(app_with(True), session, cap)
    rec = session.query(DailySettlementRecord).one()
    check('處理 1 筆、失敗 0 筆', (total, failed) == (1, 0), (total, failed))
    check('status -> SYNCED', rec.status == 'SYNCED', rec.status)
    check('last_error 清空', rec.last_error == '', repr(rec.last_error))
    check('打的是 PRD（紀錄的環境）', cap.calls[0]['url'].startswith(PRD), cap.calls[0]['url'])
    check('report_date 用紀錄當初的日期，不是今天',
          cap.calls[0]['json']['report_date'] == '2026-09-01',
          cap.calls[0]['json']['report_date'])

    print('\n[8] 補送作業跑一輪：失敗的累加 retry_count、截斷 last_error')
    session, cap = fresh_db(), Captured(ok=False)
    session.add(make_record(status='FAILED', env='prd', retry_count=1))
    session.commit()
    total, failed = run_job(app_with(True), session, cap)
    rec = session.query(DailySettlementRecord).one()
    check('處理 1 筆、失敗 1 筆', (total, failed) == (1, 1), (total, failed))
    check('status 仍為 FAILED', rec.status == 'FAILED', rec.status)
    check('retry_count 由 1 加到 2', rec.retry_count == 2, rec.retry_count)
    check('last_error 截斷在 500 字以內（id 83/84 曾整頁 HTML 塞進來）',
          len(rec.last_error or '') <= 500, len(rec.last_error or ''))

    print('\n[9] --dry-run 不打上游也不寫資料庫')
    session, cap = fresh_db(), Captured(ok=True)
    session.add(make_record(status='FAILED', env='prd', retry_count=3))
    session.commit()
    total, failed = run_job(app_with(True), session, cap, dry_run=True)
    rec = session.query(DailySettlementRecord).one()
    check('回報有 1 筆待處理', (total, failed) == (1, 0), (total, failed))
    check('完全沒有打上游', cap.calls == [], cap.calls)
    check('status 沒有被改動', rec.status == 'FAILED', rec.status)
    check('retry_count 沒有被改動', rec.retry_count == 3, rec.retry_count)

    print('\n[10] 篩選條件：視窗外、重試用盡、已 SYNCED 的都不處理')
    session, cap = fresh_db(), Captured(ok=True)
    session.add(make_record(status='FAILED', days_ago=30))              # 視窗外
    session.add(make_record(status='FAILED', retry_count=scheduler.MAX_RETRIES))  # 用盡
    session.add(make_record(status='SYNCED'))                            # 已完成
    session.add(make_record(status='PENDING'))                           # 該處理
    session.commit()
    total, failed = run_job(app_with(True), session, cap, dry_run=True)
    check('4 筆裡只挑出 1 筆（PENDING 且在視窗內、重試未用盡）', total == 1, total)

    print('\n[11] --limit 限制單輪筆數')
    session, cap = fresh_db(), Captured(ok=True)
    for _ in range(3):
        session.add(make_record(status='PENDING'))
    session.commit()
    check('不給 limit -> 3 筆',
          run_job(app_with(True), session, cap, dry_run=True)[0] == 3)
    check('limit=2 -> 2 筆',
          run_job(app_with(True), session, cap, dry_run=True, limit=2)[0] == 2)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
