"""歷史清單 v2：天數設定、台北時間分組、游標分頁、舊介面不變、索引。

Usage:
    python scripts/verify_history_pagination.py

  [1] bucket_for 的邊界：台北午夜前後、7／30 天、跨年月份。
  [2] HISTORY_DAYS 的解析：缺值、合法、超出範圍、非數字、前後空白。
  [3] 游標與 limit 的解析。
  [4] /chat/history?v=2 實打：翻完所有頁不重複不遺漏、嚴格新到舊、窗外的不出現、別人的
      不出現、最後一頁沒有 next_cursor、時間帶 +00:00、每筆有 bucket。
  [5] 翻頁途中有對話被聊到而跳到最上面：後面的頁不會重複也不會擠掉別筆。
  [6] HISTORY_DAYS 改成 270 天，同一批資料多出 180–270 天那段。
  [7] 舊介面（不帶 v=2）：格式不變、固定 30 天，不跟 HISTORY_DAYS。
  [8] 查詢計畫用得到 ix_chat_sessions_user_lower_active。

在本機資料庫建測試資料（一個測試帳號 80 筆、另一個帳號 1 筆），跑完一定刪除。
"""

import os
import sys
import time
import uuid
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

import jwt  # noqa: E402
from sqlalchemy import text  # noqa: E402
from api_v2.app import create_app  # noqa: E402
from api_v2.config import settings  # noqa: E402
from api_v2.database.connection import get_db_session  # noqa: E402
from api_v2.database.models import ChatSession  # noqa: E402
from api_v2.services import history_list as hl  # noqa: E402
from api_v2.utils.request_identity import AUDIENCE, _secret  # noqa: E402

failures = []
USER = 'verify-history-page@example.test'
OTHER = 'verify-history-other@example.test'
TAG = uuid.uuid4().hex[:8]


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          + (f' -- {detail}' if detail != '' and not condition else ''))
    if not condition:
        failures.append(label)


def auth(email):
    now = int(time.time())
    tok = jwt.encode({'email': email, 'aud': AUDIENCE, 'iat': now, 'exp': now + 120},
                     _secret(), algorithm='HS256')
    return {'Authorization': f'Bearer {tok}'}


def part1_buckets():
    print('\n[1] 台北時間分組')
    now = datetime(2026, 10, 3, 3, 0)               # 台北 10/03 11:00
    cases = [
        (datetime(2026, 10, 2, 16, 0), 'today', '台北 10/03 00:00'),
        (datetime(2026, 10, 2, 15, 59), 'yesterday', '台北 10/02 23:59（UTC 仍是 10/02，但差 8 小時才對）'),
        (now - timedelta(days=2), 'last_7_days', '2 天前'),
        (now - timedelta(days=6), 'last_7_days', '6 天前'),
        (now - timedelta(days=7), 'last_30_days', '7 天前'),
        (now - timedelta(days=29), 'last_30_days', '29 天前'),
        (now - timedelta(days=30), '2026-09', '30 天前 -> 月份'),
        (datetime(2025, 12, 31, 17, 0), '2026-01', 'UTC 12/31 17:00 = 台北 1/01，月份歸 2026-01'),
    ]
    for active, want, why in cases:
        got = hl.bucket_for(active, now)[0]
        check(f'{why} -> {want}', got == want, got)
    check('月份標籤帶年份', hl.bucket_for(datetime(2026, 4, 10), now) == ('2026-04', '2026 年 4 月'),
          hl.bucket_for(datetime(2026, 4, 10), now))


def part2_env():
    print('\n[2] HISTORY_DAYS 解析')
    key = 'VERIFY_HISTORY_DAYS_TMP'
    cases = [(None, 180, '缺值 -> 預設'), ('270', 270, '合法值'), (' 90 ', 90, '前後空白'),
             ('1800', 180, '超出上限 -> 預設'), ('0', 180, '低於下限 -> 預設'),
             ('abc', 180, '非數字 -> 預設'), ('', 180, '空字串 -> 預設')]
    for raw, want, why in cases:
        if raw is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = raw
        got = settings._int_env(key, 180, 1, 730)
        check(f'{why}（{raw!r} -> {want}）', got == want, got)
    os.environ.pop(key, None)
    check('Config.HISTORY_DAYS 是 1..730 的整數',
          isinstance(settings.Config.HISTORY_DAYS, int) and 1 <= settings.Config.HISTORY_DAYS <= 730,
          settings.Config.HISTORY_DAYS)


def part3_cursor():
    print('\n[3] 游標與 limit')
    t = datetime(2026, 9, 1, 12, 34, 56, 789000)
    check('游標來回不失真', hl.decode_cursor(hl.encode_cursor(t, 'abc-1')) == (t, 'abc-1'))
    for bad in ('not-base64!!', hl.encode_cursor(t, 'x')[:-3] + '###', 'e30',
                'eyJ0IjoiMjAyNi0wOS0wMVQwMDowMDowMCswMDowMCIsInMiOiJ4In0'):
        try:
            hl.decode_cursor(bad)
            check(f'壞游標被拒：{bad[:20]}', False)
        except hl.InvalidCursor:
            check(f'壞游標被拒：{bad[:20]}', True)
    check('limit 解析', [hl.parse_limit(x) for x in (None, '0', '20', '999', 'x')]
          == [30, 1, 20, 50, 30], [hl.parse_limit(x) for x in (None, '0', '20', '999', 'x')])


def seed(now):
    """USER：80 筆，每 61 小時一筆（約 203 天），其中 3 筆同一時間；另加 180 天邊界兩側各一筆。
    OTHER：1 筆（今天），不該出現在 USER 的清單。"""
    db = get_db_session()
    rows = {}
    try:
        for i in range(80):
            t = now - timedelta(hours=61 * i, minutes=1)
            rows[f'vhp-{TAG}-{i:03d}'] = t
        tie = now - timedelta(days=3, minutes=1)
        for k in range(3):
            rows[f'vhp-{TAG}-tie{k}'] = tie
        rows[f'vhp-{TAG}-edge-in'] = now - timedelta(days=180) + timedelta(hours=1)
        rows[f'vhp-{TAG}-edge-out'] = now - timedelta(days=180) - timedelta(hours=1)
        for sid, t in rows.items():
            db.add(ChatSession(session_id=sid, user_id=USER, started_at=t, last_active_at=t,
                               metadata_={'title': sid}))
        db.add(ChatSession(session_id=f'vhp-{TAG}-other', user_id=OTHER, started_at=now,
                           last_active_at=now, metadata_={'title': 'other'}))
        db.commit()
    finally:
        db.close()
    return rows


def cleanup():
    db = get_db_session()
    try:
        db.query(ChatSession).filter(ChatSession.session_id.like(f'vhp-{TAG}-%')).delete(
            synchronize_session=False)
        db.commit()
        return db.query(ChatSession).filter(ChatSession.session_id.like(f'vhp-{TAG}-%')).count()
    finally:
        db.close()


def touch(session_id):
    db = get_db_session()
    try:
        db.query(ChatSession).filter_by(session_id=session_id).update(
            {'last_active_at': datetime.utcnow()}, synchronize_session=False)
        db.commit()
    finally:
        db.close()


def walk(client, limit=30, first=None):
    """翻完所有頁，回 (所有 item, 每頁筆數, 最後一頁的 body)。"""
    items, sizes, cursor, body = [], [], None, None
    for _ in range(50):
        url = f'/chat/history?v=2&limit={limit}' + (f'&cursor={cursor}' if cursor else '')
        r = client.get(url, headers=auth(USER))
        body = (r.get_json() or {}).get('data') or {}
        page = body.get('items', [])
        if first is not None and not items:
            first(page)
        items += page
        sizes.append(len(page))
        cursor = body.get('next_cursor')
        if not body.get('has_more'):
            break
    return items, sizes, body


def part4_to_7():
    app = create_app()
    app.config['HISTORY_DAYS'] = 180
    client = app.test_client()
    now = datetime.utcnow()
    rows = seed(now)
    try:
        print('\n[4] v2 實打，180 天')
        r = client.get('/chat/history?v=2')
        check('沒有 token -> 401', r.status_code == 401, r.status_code)
        r = client.get('/chat/history?v=2&cursor=garbage', headers=auth(USER))
        check('壞游標 -> 400 INVALID_CURSOR', r.status_code == 400
              and (r.get_json() or {}).get('error', {}).get('code') == 'INVALID_CURSOR', r.status_code)
        r = client.get('/chat/history?v=2', headers=auth(USER))
        check('不帶 limit 第一頁 30 筆', len((r.get_json() or {}).get('data', {}).get('items', [])) == 30)

        items, sizes, last = walk(client)
        ids = [i['session_id'] for i in items]
        window = {s for s, t in rows.items() if t >= now - timedelta(days=180)}
        check('翻完沒有重複', len(ids) == len(set(ids)), len(ids) - len(set(ids)))
        check('窗內的全部拿到、窗外的一筆都沒有', set(ids) == window,
              (sorted(window - set(ids))[:3], sorted(set(ids) - window)[:3]))
        check('180 天邊界：內側那筆在、外側那筆不在',
              f'vhp-{TAG}-edge-in' in ids and f'vhp-{TAG}-edge-out' not in ids)
        check('別人的對話不出現', f'vhp-{TAG}-other' not in ids)
        keys = [(rows[i['session_id']], i['session_id']) for i in items]
        check('嚴格新到舊（同時間依 session_id）', keys == sorted(keys, reverse=True))
        check('同一時間的 3 筆都在、各一次',
              sum(1 for s in ids if '-tie' in s) == 3)
        check('最後一頁 has_more=false、next_cursor=null',
              last.get('has_more') is False and last.get('next_cursor') is None, last.get('next_cursor'))
        check('回應帶 history_days=180', last.get('history_days') == 180, last.get('history_days'))
        check('每頁不超過 limit', all(n <= 30 for n in sizes), sizes)
        check('時間帶 +00:00、每筆有 bucket 與標籤',
              all(i['last_active_at'].endswith('+00:00') and i['bucket'] and i['bucket_label']
                  for i in items))
        buckets = []
        for i in items:
            if not buckets or buckets[-1] != i['bucket']:
                buckets.append(i['bucket'])
        check('分組依序出現、同一組不會被拆成兩段', len(buckets) == len(set(buckets)), buckets)
        _, sizes20, _ = walk(client, limit=20)
        check('limit=20 時頁數相應增加、總數相同', sum(sizes20) == len(ids) and max(sizes20) <= 20,
              sizes20)
        # 同時間的 3 筆排在第 3–5 位。limit=3 時頁界正好切在它們中間：第一頁最後一筆是
        # tie 之一，游標若只比時間，另外兩筆會被當成「已經給過」而永遠消失。上面 limit=30
        # 的翻頁抓不到這種錯——3 筆剛好落在同一頁（2026-10-03 變異測試實際漏過一次）。
        items3, _, _ = walk(client, limit=3)
        ids3 = [i['session_id'] for i in items3]
        check('頁界切在同時間的幾筆中間時，一筆都不少也不重複',
              set(ids3) == window and len(ids3) == len(set(ids3)),
              (len(window - set(ids3)), len(ids3) - len(set(ids3))))

        print('\n[5] 翻頁途中有對話跳到最上面')
        state = {}

        def after_first_page(page):
            state['first'] = [p['session_id'] for p in page]
            mover = sorted(window - set(state['first']))[0]       # 一筆還在後面頁的
            state['mover'] = mover
            touch(mover)

        items2, _, _ = walk(client, first=after_first_page)
        ids2 = [i['session_id'] for i in items2]
        check('不重複', len(ids2) == len(set(ids2)), len(ids2) - len(set(ids2)))
        check('跳走的那筆不會在後面的頁再出現（前端會把它放到最上面）', state['mover'] not in ids2[30:])
        check('其他筆一筆都沒少', set(ids2) | {state['mover']} == window,
              sorted(window - set(ids2) - {state['mover']})[:3])
        # 被聊到的那筆現在是「剛剛」，後面各段的預期值要跟著它的新時間算。
        rows[state['mover']] = datetime.utcnow()

        print('\n[6] HISTORY_DAYS=270')
        app.config['HISTORY_DAYS'] = 270
        items270, _, last270 = walk(client)
        ids270 = {i['session_id'] for i in items270}
        window270 = {s for s, t in rows.items() if t >= now - timedelta(days=270)}
        check('270 天窗內全部拿到', ids270 == window270, len(window270 - ids270))
        check('比 180 天多出 180–270 天那段', len(ids270) > len(window), (len(ids270), len(window)))
        check('history_days=270', last270.get('history_days') == 270, last270.get('history_days'))

        print('\n[7] 舊介面不變')
        r = client.get(f'/chat/history?user_id={USER}', headers=auth(USER))
        d = (r.get_json() or {}).get('data') or {}
        check('格式仍是 today / past_30_days / has_more',
              set(d) == {'today', 'past_30_days', 'has_more'} and d.get('has_more') is False, sorted(d))
        legacy = [s['session_id'] for g in ('today', 'past_30_days') for s in d.get(g, [])]
        within30 = {s for s, t in rows.items() if t >= now - timedelta(days=30)}
        check('固定 30 天，不跟 HISTORY_DAYS=270', set(legacy) == within30,
              (len(legacy), len(within30)))
    finally:
        left = cleanup()
        check('測試資料已清除', left == 0, left)


def part8_index():
    print('\n[8] 查詢計畫')
    db = get_db_session()
    try:
        db.execute(text('SET LOCAL enable_seqscan = off'))
        plan = '\n'.join(r[0] for r in db.execute(text(
            "EXPLAIN SELECT * FROM chat_sessions WHERE lower(user_id) = :u "
            "AND last_active_at >= now() - interval '180 days' "
            "AND (last_active_at, session_id) < (now(), 'zzz') "
            "ORDER BY last_active_at DESC, session_id DESC LIMIT 31"), {'u': USER}))
        db.rollback()
    finally:
        db.close()
    check('用到 ix_chat_sessions_user_lower_active', 'ix_chat_sessions_user_lower_active' in plan, plan)
    check('不需要另外排序（索引本身就是這個順序）', 'Sort' not in plan.split('Limit')[-1], plan)


def main():
    part1_buckets()
    part2_env()
    part3_cursor()
    part4_to_7()
    part8_index()
    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
