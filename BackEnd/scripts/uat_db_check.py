"""Read-only queries against the UAT database, for closing the loop on the history work.

Usage:
    python scripts/uat_db_check.py --ping
    python scripts/uat_db_check.py --sessions [--days 3]
    python scripts/uat_db_check.py --session <session_id>
    python scripts/uat_db_check.py --verify-log <path/to/prompts.log>

Connection comes from `BackEnd/api_v2/.env.uat` (gitignored), never from the command line:
a password in argv shows up in shell history and in the process list. The file is read for
UAT_DB_HOST / UAT_DB_PORT / UAT_DB_NAME / UAT_DB_USER / UAT_DB_PASSWORD; see
.env.uat.example for the template. The password is never printed, not even masked back.

Read-only is enforced at the session level (`readonly=True`), so a mistake here cannot
write to UAT no matter what the SQL says. Every statement below is a SELECT regardless.

--verify-log is the one that matters. It takes a prompts.log written by the packer and,
for every record in it, rebuilds what `load_history()` would have returned from the
database at that turn, then compares it against the `[CONVERSATION HISTORY]` block the
record actually carries. The log proves what was sent to the model; this proves the log
matches the stored conversation. Together they cover the whole path.
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env.uat')
LOCAL_ENV_PATH = os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env')
SEP = '=' * 60

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


def read_env_file(path):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def load_env():
    if not os.path.exists(ENV_PATH):
        sys.exit(f"ERROR: {os.path.abspath(ENV_PATH)} not found.\n"
                 f"Copy api_v2/.env.uat.example to api_v2/.env.uat and fill it in.")
    env = read_env_file(ENV_PATH)
    missing = [k for k in ('UAT_DB_HOST', 'UAT_DB_NAME', 'UAT_DB_USER', 'UAT_DB_PASSWORD')
               if not env.get(k)]
    if missing:
        sys.exit(f"ERROR: {ENV_PATH} is missing: {', '.join(missing)}")
    return env


def load_local_env():
    """The DB the backend on this machine talks to.

    Reads the same DB_* keys `database/connection.py:get_db_url()` reads -- deliberately
    not DATABASE_URI, which .env.example advertises but that function ignores.
    """
    env = read_env_file(LOCAL_ENV_PATH)
    return {'UAT_DB_HOST': env.get('DB_HOST', 'localhost'),
            'UAT_DB_PORT': env.get('DB_PORT', '5432'),
            'UAT_DB_NAME': env.get('DB_NAME', 'ai_chatbot_v2'),
            'UAT_DB_USER': env.get('DB_USER', 'postgres'),
            'UAT_DB_PASSWORD': env.get('DB_PASSWORD', '')}


def connect(env):
    import psycopg2
    conn = psycopg2.connect(
        host=env['UAT_DB_HOST'], port=env.get('UAT_DB_PORT', '5432'),
        dbname=env['UAT_DB_NAME'], user=env['UAT_DB_USER'],
        password=env['UAT_DB_PASSWORD'], connect_timeout=10)
    # Belt and braces: this script must not be able to modify either database.
    conn.set_session(readonly=True, autocommit=True)
    return conn


def q(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def cmd_ping(conn, env):
    ver, db, usr = q(conn, "SELECT version(), current_database(), current_user")[0]
    print(f"  host      {env['UAT_DB_HOST']}:{env.get('UAT_DB_PORT', '5432')}")
    print(f"  database  {db}")
    print(f"  user      {usr}")
    print(f"  server    {ver.split(',')[0]}")
    ro = q(conn, "SHOW transaction_read_only")[0][0]
    check('session is read-only', ro == 'on', ro)
    n = q(conn, "SELECT count(*) FROM chat_sessions")[0][0]
    m = q(conn, "SELECT count(*) FROM chat_messages")[0][0]
    print(f"  chat_sessions={n:,}  chat_messages={m:,}")


def cmd_sessions(conn, days):
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = q(conn, """
        SELECT s.session_id, s.user_id, s.last_active_at,
               count(*) FILTER (WHERE m.role = 'user')      AS users,
               count(*) FILTER (WHERE m.role = 'assistant') AS ais
        FROM chat_sessions s LEFT JOIN chat_messages m ON m.session_id = s.session_id
        WHERE s.last_active_at >= %s
        GROUP BY s.session_id, s.user_id, s.last_active_at
        ORDER BY s.last_active_at DESC
    """, (cutoff,))
    print(f"  {len(rows)} sessions active in the last {days} day(s)\n")
    print(f"  {'session_id':38} {'user':10} {'last active':20} {'user':>5} {'ai':>4}")
    for sid, uid, act, u, a in rows:
        print(f"  {sid:38} {str(uid or '-')[:10]:10} "
              f"{act.strftime('%Y-%m-%d %H:%M:%S') if act else '-':20} {u:>5} {a:>4}")


def schema_snapshot(conn):
    """Columns, indexes and constraints for the public schema, as comparable dicts.

    Only public: extensions and pg_catalog differ between installs for reasons that have
    nothing to do with the application. Defaults are captured as text because that is how
    a drifting default actually shows up -- `now()` on one side and a literal on the other.
    """
    cols = {}
    for tbl, col, typ, nullable, default, maxlen in q(conn, """
        SELECT table_name, column_name, data_type, is_nullable,
               column_default, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """):
        typ = f'{typ}({maxlen})' if maxlen else typ
        cols[(tbl, col)] = (typ, nullable, (default or '').split('::')[0])

    idx = {}
    for tbl, name, definition in q(conn, """
        SELECT tablename, indexname, indexdef FROM pg_indexes
        WHERE schemaname = 'public' ORDER BY tablename, indexname
    """):
        # 索引定義裡帶了 schema 前綴與資料庫無關的空白差異，正規化後再比。
        idx[(tbl, name)] = re.sub(r'\s+', ' ', definition.replace('public.', ''))

    cons = {}
    for tbl, name, ctype in q(conn, """
        SELECT tc.table_name, tc.constraint_name, tc.constraint_type
        FROM information_schema.table_constraints tc
        WHERE tc.table_schema = 'public' AND tc.constraint_type IN
              ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
        ORDER BY tc.table_name, tc.constraint_name
    """):
        cons[(tbl, name)] = ctype

    return {'columns': cols, 'indexes': idx, 'constraints': cons}


def diff_section(title, left, right, lname, rname):
    """Report keys only on one side, and keys whose values differ. Returns a problem count."""
    lk, rk = set(left), set(right)
    only_l, only_r = sorted(lk - rk), sorted(rk - lk)
    changed = sorted(k for k in lk & rk if left[k] != right[k])
    if not (only_l or only_r or changed):
        print(f"  [OK] {title}: identical ({len(lk)} entries)")
        return 0
    print(f"  [DIFF] {title}")
    for k in only_l:
        print(f"      only in {lname:5}  {'.'.join(k)}  {left[k]}")
    for k in only_r:
        print(f"      only in {rname:5}  {'.'.join(k)}  {right[k]}")
    for k in changed:
        print(f"      differs        {'.'.join(k)}")
        print(f"        {lname:5} {left[k]}")
        print(f"        {rname:5} {right[k]}")
    return len(only_l) + len(only_r) + len(changed)


def cmd_diff_schema(uat_conn, local_conn):
    uat, local = schema_snapshot(uat_conn), schema_snapshot(local_conn)
    tables_u = {t for t, _ in uat['columns']}
    tables_l = {t for t, _ in local['columns']}
    print(f"  tables: UAT={len(tables_u)}  LOCAL={len(tables_l)}")
    if tables_u ^ tables_l:
        print(f"  [DIFF] table set")
        for t in sorted(tables_u - tables_l):
            print(f"      only in UAT    {t}")
        for t in sorted(tables_l - tables_u):
            print(f"      only in LOCAL  {t}")
    else:
        print(f"  [OK] table set: identical")
    n = sum(diff_section(s, uat[s], local[s], 'UAT', 'LOCAL')
            for s in ('columns', 'indexes', 'constraints'))
    n += len(tables_u ^ tables_l)
    check('UAT and LOCAL schemas match', n == 0, f'{n} difference(s)' if n else '')


def conversation(conn, session_id):
    """user/assistant messages for a session, oldest first -- what load_history reads."""
    return q(conn, """
        SELECT role, content, created_at FROM chat_messages
        WHERE session_id = %s AND role IN ('user', 'assistant')
        ORDER BY created_at, id
    """, (session_id,))


def cmd_session(conn, session_id):
    rows = conversation(conn, session_id)
    print(f"  {len(rows)} user/assistant messages\n")
    for i, (role, content, at) in enumerate(rows, 1):
        head = content.replace('\n', ' ')[:60]
        print(f"  #{i:<3} {role:10} {at.strftime('%H:%M:%S')} {len(content):>6,} chars  {head}")


def log_records(path):
    """prompts.log records: header fields plus the history block, in file order."""
    text = open(path, encoding='utf-8').read()
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith('REQ: '):
            cur = {'header': line, 'lines': []}
            out.append(cur)
        elif cur is not None:
            cur['lines'].append(line)
    for r in out:
        body = '\n'.join(r['lines'])
        start, end = body.find('[CONVERSATION HISTORY]'), body.find(SEP)
        r['block'] = body[start:end] if 0 <= start < end else ''
        r['req'] = re.search(r'REQ: (\w+)', r['header']).group(1)
        r['session_id'] = re.search(r'SESSION: ([\w-]+)', r['header']).group(1)
        r['msgs'] = int(re.search(r'HISTORY_MSGS: (\d+)', r['header']).group(1))
        r['cap_turns'] = int(re.search(r'cap=(\d+) turns', r['header']).group(1))
    return out


def render_block(history):
    """The same text packed_chat writes, rebuilt from database rows."""
    if not history:
        return '[CONVERSATION HISTORY]\n(none -- first turn of this session)\n'
    lines = [f'[CONVERSATION HISTORY] oldest first, verbatim, {len(history)} messages']
    for i, (role, content) in enumerate(history, 1):
        lines.append(f'--- #{i} {role.upper()} ---')
        lines.append(content)
    return '\n'.join(lines) + '\n'


def cmd_verify_log(conn, path):
    recs = log_records(path)
    if not recs:
        sys.exit(f"ERROR: no `REQ:` records found in {path}")
    by_session = {}
    for r in recs:
        by_session.setdefault(r['session_id'], []).append(r)
    print(f"  {len(recs)} records across {len(by_session)} session(s)\n")

    for sid, srecs in by_session.items():
        print(f"  session {sid}")
        rows = conversation(conn, sid)
        if not rows:
            check(f'{sid[:8]}: session found in the database', False,
                  'no user/assistant messages -- wrong database, or the rows were purged')
            continue
        convo = [(role, content) for role, content, _ in rows]
        # 每一則 user 訊息開啟一輪；load_history 看到的是它之前的所有訊息，
        # 因為 chat.py 是先寫入當輪 query 再呼叫 load_history、然後把最後那則剔掉。
        turns = [i for i, (role, _) in enumerate(convo) if role == 'user']
        if len(turns) < len(srecs):
            check(f'{sid[:8]}: database has at least as many turns as the log', False,
                  f'db={len(turns)} log={len(srecs)}')
            continue
        # 對齊：log 記的是最後 N 輪（檔案可能只保留一天），所以從尾端對齊。
        turns = turns[len(turns) - len(srecs):]
        for rec, start in zip(srecs, turns):
            cap = rec['cap_turns'] * 2
            expected = convo[max(0, start - cap):start]
            rebuilt = render_block(expected)
            same = rebuilt == rec['block']
            check(f"{rec['req']}: history block matches the database "
                  f"({len(expected)} msgs)", same,
                  '' if same else f"log={rec['msgs']} msgs / db={len(expected)} msgs")
            if not same and expected:
                for i, ((role, content), _) in enumerate(zip(expected, expected), 1):
                    if f'--- #{i} {role.upper()} ---\n{content}' not in rec['block']:
                        print(f"        first divergence at #{i} {role}: "
                              f"{content[:50]!r}")
                        break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ping', action='store_true', help='connection and row counts')
    ap.add_argument('--sessions', action='store_true', help='recently active sessions')
    ap.add_argument('--days', type=int, default=3)
    ap.add_argument('--session', help='dump one session\'s messages')
    ap.add_argument('--verify-log', help='compare a prompts.log against the database')
    ap.add_argument('--diff-schema', action='store_true',
                    help='compare the UAT schema against this machine\'s database')
    ap.add_argument('--schema', action='store_true',
                    help='print one database\'s schema summary (use --local for this machine)')
    ap.add_argument('--local', action='store_true',
                    help='run against api_v2/.env\'s DB_* instead of .env.uat')
    args = ap.parse_args()

    if not any([args.ping, args.sessions, args.session, args.verify_log,
                args.diff_schema, args.schema]):
        ap.print_help()
        return 2

    if args.diff_schema:
        # 兩邊都要，所以這條路徑不吃 --local。
        uat_conn, local_conn = connect(load_env()), connect(load_local_env())
        try:
            print('\n[DIFF SCHEMA] UAT vs LOCAL')
            cmd_diff_schema(uat_conn, local_conn)
        finally:
            uat_conn.close()
            local_conn.close()
        if not any([args.ping, args.sessions, args.session, args.verify_log, args.schema]):
            print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
            return 1 if failures else 0

    env = load_local_env() if args.local else load_env()
    conn = connect(env)
    try:
        if args.schema:
            label = 'LOCAL' if args.local else 'UAT'
            snap = schema_snapshot(conn)
            print(f'\n[SCHEMA {label}] {env["UAT_DB_HOST"]}:{env.get("UAT_DB_PORT")}'
                  f'/{env["UAT_DB_NAME"]}')
            tables = sorted({t for t, _ in snap['columns']})
            print(f'  {len(tables)} tables, {len(snap["columns"])} columns, '
                  f'{len(snap["indexes"])} indexes, {len(snap["constraints"])} constraints\n')
            for t in tables:
                cs = [(c, v) for (tt, c), v in snap['columns'].items() if tt == t]
                print(f'  {t}  ({len(cs)} cols)')
                for c, (typ, nullable, default) in cs:
                    print(f'      {c:24} {typ:28} '
                          f'{"NULL" if nullable == "YES" else "NOT NULL":9}'
                          f'{("DEFAULT " + default) if default else ""}')
        if args.ping:
            print('\n[PING]')
            cmd_ping(conn, env)
        if args.sessions:
            print('\n[SESSIONS]')
            cmd_sessions(conn, args.days)
        if args.session:
            print(f'\n[SESSION {args.session}]')
            cmd_session(conn, args.session)
        if args.verify_log:
            print(f'\n[VERIFY {args.verify_log}]')
            cmd_verify_log(conn, args.verify_log)
    finally:
        conn.close()

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
