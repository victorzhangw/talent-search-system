"""歷史對話三條路由必須驗身分，而且只看得到自己的對話。

Usage:
    python scripts/verify_history_auth.py

2026-10-03 本機實測：不帶任何 token，
    GET /chat/history?user_id=<email>  -> 200，列出那個人的對話（標題含受測者姓名）
    GET /chat/<session_id>             -> 200，回傳 716 則訊息全文
同一個檔案裡的 POST /chat/ 與 /api/v2/* 早就走 resolve_user_email，只有這三條漏掉。

這支在本機資料庫建兩個測試帳號各一筆對話（外加一筆 anonymous），跑完一定刪除。

已知限制（不在本支範圍）：/auth/login 只確認 email 在 Traitty 上游存在，不驗密碼，
所以知道別人 email 的人仍可換到 token。這裡驗的是「沒有 token 不行、拿 A 的 token
看不到 B」，也就是與其他路由同等的保護。
"""

import os
import sys
import time
import uuid

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

import jwt  # noqa: E402
from api_v2.app import create_app  # noqa: E402
from api_v2.database.connection import get_db_session  # noqa: E402
from api_v2.database.models import ChatSession, ChatMessage  # noqa: E402
from api_v2.utils.request_identity import AUDIENCE, _secret  # noqa: E402

failures = []

USER_A = 'verify-history-a@example.test'
USER_B = 'verify-history-b@example.test'
TAG = uuid.uuid4().hex[:8]
SID_A = f'verify-hist-a-{TAG}'
SID_B = f'verify-hist-b-{TAG}'
SID_ANON = f'verify-hist-anon-{TAG}'


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          + (f' -- {detail}' if detail != '' and not condition else ''))
    if not condition:
        failures.append(label)


def token(email, expires_in=120):
    now = int(time.time())
    return jwt.encode({'email': email, 'aud': AUDIENCE, 'iat': now, 'exp': now + expires_in},
                      _secret(), algorithm='HS256')


def auth(email, **kw):
    return {'Authorization': f'Bearer {token(email, **kw)}'}


def seed():
    db = get_db_session()
    try:
        ids = {}
        for sid, uid in ((SID_A, USER_A), (SID_B, USER_B), (SID_ANON, 'anonymous')):
            db.add(ChatSession(session_id=sid, user_id=uid, metadata_={'title': f'verify {sid}'}))
            db.flush()
            m = ChatMessage(session_id=sid, role='assistant', content='verify', rating=0)
            db.add(m)
            db.flush()
            ids[sid] = m.id
        db.commit()
        return ids
    finally:
        db.close()


def cleanup():
    db = get_db_session()
    try:
        for sid in (SID_A, SID_B, SID_ANON):
            db.query(ChatMessage).filter_by(session_id=sid).delete()
            db.query(ChatSession).filter_by(session_id=sid).delete()
        db.commit()
    finally:
        db.close()


def rating_of(message_id):
    db = get_db_session()
    try:
        return db.query(ChatMessage.rating).filter_by(id=message_id).scalar()
    finally:
        db.close()


def listed(resp):
    d = (resp.get_json() or {}).get('data') or {}
    return {s['session_id'] for group in ('today', 'past_30_days') for s in d.get(group, [])}


def main():
    msg = seed()
    try:
        c = create_app().test_client()

        print('\n[1] GET /chat/history')
        r = c.get(f'/chat/history?user_id={USER_A}')
        check('沒有 token -> 401', r.status_code == 401, r.status_code)
        r = c.get('/chat/history', headers=auth(USER_A, expires_in=-60))
        check('過期 token -> 401 TOKEN_EXPIRED', r.status_code == 401
              and (r.get_json() or {}).get('error', {}).get('code') == 'TOKEN_EXPIRED',
              r.get_json())
        r = c.get(f'/chat/history?user_id={USER_A}', headers=auth(USER_A))
        got = listed(r)
        check('A 的 token 看得到 A 的對話', r.status_code == 200 and SID_A in got, (r.status_code, got))
        check('A 的 token 看不到 B 與 anonymous 的對話',
              SID_B not in got and SID_ANON not in got, got)
        r = c.get(f'/chat/history?user_id={USER_B}', headers=auth(USER_A))
        got = listed(r)
        check('拿 A 的 token 帶 ?user_id=B -> 參數被忽略，仍只有 A',
              SID_A in got and SID_B not in got, got)
        r = c.get('/chat/history', headers=auth(USER_A.upper()))
        check('email 大小寫不同仍視為同一人（不會看不到自己的對話）', SID_A in listed(r), listed(r))
        r = c.get('/chat/history', headers=auth(USER_A))
        check('新版前端不帶 user_id 也能用', r.status_code == 200 and SID_A in listed(r), r.status_code)

        print('\n[2] GET /chat/<session_id>')
        r = c.get(f'/chat/{SID_A}')
        check('沒有 token -> 401', r.status_code == 401, r.status_code)
        r = c.get(f'/chat/{SID_A}', headers=auth(USER_A))
        check('本人 -> 200 且有訊息', r.status_code == 200
              and len((r.get_json() or {}).get('data', {}).get('messages', [])) == 1, r.status_code)
        r = c.get(f'/chat/{SID_B}', headers=auth(USER_A))
        check('別人的對話 -> 404', r.status_code == 404, r.status_code)
        r = c.get(f'/chat/{SID_ANON}', headers=auth(USER_A))
        check('anonymous 的對話不屬於任何人 -> 404', r.status_code == 404, r.status_code)
        r = c.get(f'/chat/no-such-session-{TAG}', headers=auth(USER_A))
        check('不存在的對話 -> 404（與「不是你的」同一個回應）', r.status_code == 404, r.status_code)

        print('\n[3] PUT /chat/message/<id>/rating')
        r = c.put(f'/chat/message/{msg[SID_A]}/rating', json={'rating': 1})
        check('沒有 token -> 401', r.status_code == 401, r.status_code)
        check('  而且沒有寫入', rating_of(msg[SID_A]) == 0, rating_of(msg[SID_A]))
        r = c.put(f'/chat/message/{msg[SID_A]}/rating', json={'rating': 1}, headers=auth(USER_A))
        check('本人 -> 200 並寫入', r.status_code == 200 and rating_of(msg[SID_A]) == 1,
              (r.status_code, rating_of(msg[SID_A])))
        r = c.put(f'/chat/message/{msg[SID_B]}/rating', json={'rating': -1}, headers=auth(USER_A))
        check('評別人的訊息 -> 404', r.status_code == 404, r.status_code)
        check('  而且 B 的評分沒有被改', rating_of(msg[SID_B]) == 0, rating_of(msg[SID_B]))
        r = c.put('/chat/message/2147483646/rating', json={'rating': 1}, headers=auth(USER_A))
        check('不存在的訊息 -> 404', r.status_code == 404, r.status_code)
    finally:
        cleanup()
        db = get_db_session()
        try:
            left = db.query(ChatSession).filter(ChatSession.session_id.in_(
                [SID_A, SID_B, SID_ANON])).count()
        finally:
            db.close()
        check('測試資料已清除', left == 0, left)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
