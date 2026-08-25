"""Read-only diagnosis: why does clicking a history entry show 「（尚無對話紀錄）」 on PRD?

The symptom (client, 2026-08-24) is that the history *list* is populated on PRD but every
entry opens empty, while the same build on UAT opens normally. The list and the detail come
from two different queries, so the question this script answers is which side is empty:

    GET /chat/history       -> chat_sessions      (list; works on PRD)
    GET /chat/<session_id>  -> chat_messages      (detail; empty on PRD)

routes/chat.py:235 keeps only `role in ('user', 'assistant')`, so an entry also renders
empty when the rows exist but carry some other role. Both possibilities are checked, plus
the schema of the two tables, since PRD has already been found drifting from UAT once
(trait_interactions.primary_band, see sync_prd_reference_data.py).

Read-only is enforced at the connection level for BOTH databases -- this script cannot
write to PRD no matter what the SQL says. Credentials come from api_v2/.env.uat, which
holds the shared host; UAT is `ai_chatbot_v2` and PRD is `ai_chatbot_v2_prd`.

Usage:
    python scripts/diagnose_history_detail.py
    python scripts/diagnose_history_detail.py --session <session_id>   # one session, both DBs
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env.uat')
UAT_DB = 'ai_chatbot_v2'
PRD_DB = 'ai_chatbot_v2_prd'
SEP = '=' * 72

# Exactly the filter routes/chat.py:235 applies before returning messages to the widget.
VISIBLE_ROLES = ('user', 'assistant')


def load_env():
    if not os.path.exists(ENV_PATH):
        sys.exit(f"ERROR: {os.path.abspath(ENV_PATH)} not found.")
    env = {}
    with open(ENV_PATH, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def connect(env, dbname, readonly=True):
    import psycopg2
    conn = psycopg2.connect(
        host=env['UAT_DB_HOST'], port=env.get('UAT_DB_PORT', '5432'),
        dbname=dbname, user=env['UAT_DB_USER'], password=env['UAT_DB_PASSWORD'],
        connect_timeout=10)
    conn.set_session(readonly=readonly, autocommit=True)
    return conn


def q(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def scalar(conn, sql, args=None):
    rows = q(conn, sql, args)
    return rows[0][0] if rows else None


def table_exists(conn, table):
    return scalar(conn, "SELECT to_regclass(%s) IS NOT NULL", (f'public.{table}',))


def report(label, conn):
    print(f'\n{SEP}\n{label}\n{SEP}')

    for table in ('chat_sessions', 'chat_messages'):
        if not table_exists(conn, table):
            print(f'  ERROR: table {table} does not exist')
            return

    sessions = scalar(conn, 'SELECT count(*) FROM chat_sessions')
    messages = scalar(conn, 'SELECT count(*) FROM chat_messages')
    print(f'  chat_sessions : {sessions}')
    print(f'  chat_messages : {messages}')

    print('  role 分布（前端只顯示 user / assistant）:')
    for role, n in q(conn, 'SELECT role, count(*) FROM chat_messages '
                           'GROUP BY role ORDER BY count(*) DESC'):
        mark = '' if role in VISIBLE_ROLES else '   <- 會被前端過濾掉'
        print(f'    {str(role):<12} {n}{mark}')

    # The number that decides it: sessions the widget would open empty.
    empty = scalar(conn, """
        SELECT count(*) FROM chat_sessions s
        WHERE NOT EXISTS (
            SELECT 1 FROM chat_messages m
            WHERE m.session_id = s.session_id AND m.role IN %s)
    """, (VISIBLE_ROLES,))
    print(f'  點開會是空的 session：{empty} / {sessions}')

    orphans = scalar(conn, """
        SELECT count(DISTINCT m.session_id) FROM chat_messages m
        WHERE NOT EXISTS (
            SELECT 1 FROM chat_sessions s WHERE s.session_id = m.session_id)
    """)
    print(f'  有訊息但對不到 session 的 session_id：{orphans}')

    print('  最近 5 筆 session：')
    for sid, last, total, visible in q(conn, """
        SELECT s.session_id, s.last_active_at,
               (SELECT count(*) FROM chat_messages m WHERE m.session_id = s.session_id),
               (SELECT count(*) FROM chat_messages m
                 WHERE m.session_id = s.session_id AND m.role IN %s)
        FROM chat_sessions s ORDER BY s.last_active_at DESC NULLS LAST LIMIT 5
    """, (VISIBLE_ROLES,)):
        print(f'    {sid}  {str(last)[:19]}  訊息 {total} 筆（可顯示 {visible} 筆）')


def compare_columns(uat, prd, table):
    def cols(conn):
        return {r[0]: (r[1], r[2]) for r in q(conn, """
            SELECT column_name, data_type, is_nullable FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s""", (table,))}

    a, b = cols(uat), cols(prd)
    only_uat, only_prd = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    differing = sorted(c for c in set(a) & set(b) if a[c] != b[c])
    if not (only_uat or only_prd or differing):
        print(f'  {table}: 兩邊欄位一致（{len(a)} 欄）')
        return
    print(f'  {table}:')
    for c in only_uat:
        print(f'    UAT 有、PRD 沒有: {c} {a[c]}')
    for c in only_prd:
        print(f'    PRD 有、UAT 沒有: {c} {b[c]}')
    for c in differing:
        print(f'    型別不同: {c} UAT={a[c]} PRD={b[c]}')


def one_session(conn, label, session_id):
    print(f'\n{label}:')
    if not q(conn, 'SELECT 1 FROM chat_sessions WHERE session_id=%s', (session_id,)):
        print('  chat_sessions 查無此 session')
        return
    rows = q(conn, 'SELECT id, role, left(content, 40), created_at FROM chat_messages '
                   'WHERE session_id=%s ORDER BY created_at LIMIT 20', (session_id,))
    if not rows:
        print('  session 存在，但 chat_messages 一筆都沒有 -> 前端顯示「（尚無對話紀錄）」')
        return
    for mid, role, head, created in rows:
        mark = '' if role in VISIBLE_ROLES else '  <- 前端過濾'
        print(f'  #{mid} {role:<10} {str(created)[:19]}  {head!r}{mark}')


def timeline(conn, label, days=45):
    """Sessions created per day vs sessions that ended up with visible messages.

    The counts alone cannot distinguish "messages were never written" from "messages were
    written somewhere else"; lining them up by day can, because a write path that broke on
    a deploy shows a clean cutover rather than a gradual thinning.
    """
    print(f'\n{label}（近 {days} 天，每日 session 數 / 其中有可顯示訊息的）:')
    rows = q(conn, """
        SELECT date(s.started_at) AS d, count(*) AS total,
               count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM chat_messages m
                   WHERE m.session_id = s.session_id AND m.role IN %s)) AS with_msg,
               coalesce(sum((SELECT count(*) FROM chat_messages m
                             WHERE m.session_id = s.session_id)), 0) AS msg_rows
        FROM chat_sessions s
        WHERE s.started_at >= now() - make_interval(days => %s)
        GROUP BY 1 ORDER BY 1
    """, (VISIBLE_ROLES, days))
    if not rows:
        print('    （無資料）')
    for d, total, with_msg, msg_rows in rows:
        flag = '   <- 全空' if with_msg == 0 and total else ''
        print(f'    {d}  session {total:>3}  有訊息 {with_msg:>3}  訊息列 {msg_rows:>4}{flag}')


def sequence_states(conn):
    """(table, column, sequence, max_id, next_id, last_value, is_called) per auto-id column.

    Enumerated from each column's DEFAULT rather than from pg_depend. pg_depend only lists
    sequences *owned* by their column, and PRD's trait_endpoints_id_seq is not owned -- the
    column still defaults to nextval() on it, but a dependency-based query cannot see it, so
    a desync there would go unreported. Which is the failure mode this whole script exists
    to catch, so the audit must not have that hole. Identity columns are covered too; they
    have no DEFAULT and are resolved through pg_get_serial_sequence.

    The LIKE pattern is written `nextval(%%` because psycopg2 interpolates parameters over
    the whole statement even when none are passed -- including inside SQL comments, so a
    stray single percent anywhere in this string raises IndexError before Postgres sees it.
    """
    out = []
    for tbl, col, seq in q(conn, r"""
        SELECT table_name, column_name,
               coalesce(
                   substring(column_default from 'nextval\(''([^'']+)'''),
                   pg_get_serial_sequence(quote_ident(table_name), column_name))
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND (column_default LIKE 'nextval(%%' OR is_identity = 'YES')
        ORDER BY table_name, column_name
    """):
        if not seq:
            continue
        mx = scalar(conn, f'SELECT max({col}) FROM {tbl}') or 0
        last, called = q(conn, f'SELECT last_value, is_called FROM {seq}')[0]
        out.append((tbl, col, seq, mx, last + 1 if called else last, last, called))
    return out


def fix_sequences(env, target, apply):
    """Realign identity sequences that have fallen behind max(id).

    Why a sequence below max(id) is not cosmetic: the next INSERT reuses an id that already
    exists and fails on the primary key. add_message swallows that (session_store.py:63),
    so PRD created chat_sessions rows with no chat_messages for a week and nothing
    surfaced. `daily_settlements` is in the same state.

    Rollback note: `setval` is NOT transactional -- PostgreSQL deliberately exempts
    sequences so concurrent sessions never block on them, and a ROLLBACK will not undo one.
    So this does not pretend to wrap the change in a transaction. It records every original
    value to a backup file first and, if the post-change verification fails, restores each
    touched sequence by calling `setval` again with the value it had. That is the only
    mechanism that actually works here.

    Each setval computes max(id) in the same statement rather than reusing the value read
    during the report, so a row inserted in between cannot leave the sequence short again.
    """
    dbname = {'uat': UAT_DB, 'prd': PRD_DB}[target]
    print(f'\n{SEP}\n序列修復：{target.upper()}  {dbname}   '
          f'{"APPLY（會寫入）" if apply else "DRY-RUN（不寫入）"}\n{SEP}')

    conn = connect(env, dbname, readonly=not apply)
    try:
        broken = [s for s in sequence_states(conn) if s[4] <= s[3]]
        if not broken:
            print('  沒有失步的序列，不需要修復。')
            return 0

        for tbl, col, seq, mx, nxt, last, called in broken:
            print(f'  {tbl}.{col}: max={mx} next={nxt} -> setval({seq!r}, {mx}) '
                  f'使下一筆為 {mx + 1}')

        if not apply:
            print('\n  這是 dry-run，沒有任何寫入。確認無誤後加上 --apply 執行。')
            return 0

        backup_dir = os.path.join(SCRIPT_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = os.path.join(backup_dir, f'sequences-{target}-{stamp}.json')
        original = [{'table': t, 'column': c, 'sequence': s, 'max_id': m,
                     'last_value': lv, 'is_called': ic,
                     'restore_sql': f"SELECT setval('{s}', {lv}, {str(ic).lower()});"}
                    for t, c, s, m, n, lv, ic in broken]
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump({'database': dbname, 'taken_at': stamp, 'sequences': original},
                      f, ensure_ascii=False, indent=2)
        print(f'\n  已備份原始序列值：{backup_path}')

        changed = []
        for tbl, col, seq, mx, nxt, last, called in broken:
            new_last = scalar(conn, f"SELECT setval('{seq}', (SELECT max({col}) FROM {tbl}))")
            changed.append((tbl, col, seq, new_last))
            print(f'  已設定 {seq} = {new_last}')

        failed = [s for s in sequence_states(conn) if s[4] <= s[3]]
        if failed:
            print('\n  ERROR: 重驗未通過，還原到備份的序列值：')
            for item in original:
                scalar(conn, f"SELECT setval('{item['sequence']}', {item['last_value']}, "
                             f"{str(item['is_called']).lower()})")
                print(f"    已還原 {item['sequence']} = {item['last_value']}")
            for tbl, col, seq, mx, nxt, _, _ in failed:
                print(f'    仍然失步: {tbl}.{col} max={mx} next={nxt}')
            return 1

        print('\n  重驗通過，所有序列的下一個 id 都大於 max(id)。')
        for tbl, col, seq, mx, nxt, _, _ in sequence_states(conn):
            print(f'    {tbl}.{col:<12} max={mx:<8} next={nxt:<8} OK')
        return 0
    finally:
        conn.close()


def sequences(conn, label):
    """Every identity sequence vs the max id actually present in its table.

    A sequence sitting below max(id) means the next INSERT collides with an existing row
    and fails on the primary key. SqlSessionStore.add_message swallows that exception
    (services/session_store.py:63) and returns None, so the request still succeeds and the
    message is simply never stored -- which is how PRD lost a week of chat_messages
    without anything surfacing to the user.

    Shares sequence_states() with --fix-sequences on purpose: an audit that enumerates
    sequences differently from the repair can report a table the repair will not touch.
    """
    print(f'\n{label} 序列健康度:')
    rows = sequence_states(conn)
    if not rows:
        print('    （查無序列）')
    for tbl, col, seq, mx, nxt, _, _ in rows:
        state = 'OK' if nxt > mx else f'失步 -> 下一筆 INSERT 會撞到既有的 {col}={nxt}'
        print(f'    {tbl}.{col:<12} max={mx:<8} next={nxt:<8} {state}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sequences', action='store_true',
                    help='檢查兩個資料庫所有序列是否落後於 max(id)')
    ap.add_argument('--fix-sequences', choices=('uat', 'prd'), metavar='{uat,prd}',
                    help='修復失步的序列。必須明講是哪個資料庫，沒有預設值。'
                         '預設只做 dry-run，要真的寫入請再加 --apply')
    ap.add_argument('--apply', action='store_true',
                    help='搭配 --fix-sequences：實際寫入。沒有這個旗標就只印出計畫')
    ap.add_argument('--session', help='比對單一 session_id 在兩個資料庫的訊息')
    ap.add_argument('--timeline', action='store_true', help='逐日比對 session 與訊息寫入')
    args = ap.parse_args()

    env = load_env()

    # Handled before the read-only pair is opened: this is the one mode that writes, and it
    # opens its own connection with readonly cleared only when --apply is present.
    if args.fix_sequences:
        return fix_sequences(env, args.fix_sequences, args.apply)
    if args.apply:
        # print, not sys.exit(msg): sys.exit writes to stderr, which is not the stream
        # reconfigured to UTF-8 above, so a Chinese message comes out mojibake on a cp950
        # console -- the same failure mode CLAUDE.md documents for emoji in print().
        print('ERROR: --apply 只能搭配 --fix-sequences 使用。')
        return 2

    uat, prd = connect(env, UAT_DB), connect(env, PRD_DB)
    try:
        if args.session:
            one_session(uat, f'UAT ({UAT_DB})', args.session)
            one_session(prd, f'PRD ({PRD_DB})', args.session)
            return 0

        if args.timeline:
            timeline(uat, f'UAT  {UAT_DB}')
            timeline(prd, f'PRD  {PRD_DB}')
            return 0

        if args.sequences:
            sequences(uat, f'UAT  {UAT_DB}')
            sequences(prd, f'PRD  {PRD_DB}')
            return 0

        report(f'UAT  {UAT_DB}', uat)
        report(f'PRD  {PRD_DB}', prd)
        print(f'\n{SEP}\n欄位比對\n{SEP}')
        compare_columns(uat, prd, 'chat_sessions')
        compare_columns(uat, prd, 'chat_messages')
        return 0
    finally:
        uat.close()
        prd.close()


if __name__ == '__main__':
    sys.exit(main())
