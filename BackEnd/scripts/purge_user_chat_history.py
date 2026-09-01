"""Delete one user's chat history (chat_sessions + chat_messages) from PRD.

Usage:
    python scripts/purge_user_chat_history.py --user a080697@gmail.com --dry-run
    python scripts/purge_user_chat_history.py --user a080697@gmail.com --apply
    python scripts/purge_user_chat_history.py --user a080697@gmail.com --db uat --dry-run

Scope
-----
chat_messages first, then chat_sessions -- that order, because chat_messages.session_id
is a FK to chat_sessions.session_id and there is no ON DELETE CASCADE.

daily_settlements is deliberately NOT touched. Those rows are the billing side and the
ones seen so far are all status='SYNCED', i.e. already handed to the external settlement
system; deleting them locally would leave the two sides unable to reconcile. Pass
--include-settlements only if you actually intend to retract billing too.

Safety
------
1. A JSON backup of every row about to be deleted is written to scripts/backups/ first.
   A COMMIT cannot be undone by a rollback, so the backup has to exist before the write.
2. The delete runs inside one transaction. Before COMMIT it verifies both that the user
   has zero rows left and that the *global* row counts fell by exactly the number of rows
   the backup contains. A wider-than-intended DELETE therefore rolls back instead of
   committing.
3. --dry-run opens the connection readonly, so it cannot write regardless of the SQL.
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env.uat')
BACKUP_DIR = os.path.join(SCRIPT_DIR, 'backups')
DBS = {'prd': 'ai_chatbot_v2_prd', 'uat': 'ai_chatbot_v2'}
SEP = '=' * 72

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


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


def connect(env, dbname, readonly):
    import psycopg2
    conn = psycopg2.connect(
        host=env['UAT_DB_HOST'], port=env.get('UAT_DB_PORT', '5432'),
        dbname=dbname, user=env['UAT_DB_USER'], password=env['UAT_DB_PASSWORD'],
        connect_timeout=10)
    # autocommit off for --apply: the whole delete has to be one transaction.
    conn.set_session(readonly=readonly, autocommit=readonly)
    return conn


def rows(cur, sql, args=None):
    cur.execute(sql, args) if args else cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def scalar(cur, sql, args=None):
    cur.execute(sql, args) if args else cur.execute(sql)
    return cur.fetchone()[0]


def json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


def collect(cur, user):
    """Every row that would be deleted, read before anything is written."""
    sessions = rows(cur, 'SELECT * FROM chat_sessions WHERE user_id = %s '
                         'ORDER BY started_at', (user,))
    ids = [s['session_id'] for s in sessions]
    messages = rows(cur, 'SELECT * FROM chat_messages WHERE session_id = ANY(%s) '
                         'ORDER BY session_id, id', (ids,)) if ids else []
    settlements = rows(cur, 'SELECT * FROM daily_settlements WHERE user_id = %s '
                            'ORDER BY id', (user,))
    return sessions, messages, settlements


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', required=True, help='chat_sessions.user_id, e.g. an email')
    ap.add_argument('--db', choices=sorted(DBS), default='prd')
    ap.add_argument('--include-settlements', action='store_true',
                    help='also delete daily_settlements rows (billing side -- see docstring)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run', action='store_true', help='report only, readonly connection')
    g.add_argument('--apply', action='store_true', help='backup, then delete')
    args = ap.parse_args()

    dbname = DBS[args.db]
    env = load_env()
    conn = connect(env, dbname, readonly=args.dry_run)
    mode = 'APPLY (will write)' if args.apply else 'DRY-RUN (no writes)'
    print(f'{SEP}\n{args.db.upper()}  {dbname}  user={args.user!r}   {mode}\n{SEP}')

    try:
        cur = conn.cursor()
        sessions, messages, settlements = collect(cur, args.user)

        print(f'\n  chat_sessions      : {len(sessions)}')
        for s in sessions:
            n = sum(1 for m in messages if m['session_id'] == s['session_id'])
            print(f'    {s["session_id"]}  {s["started_at"]}  messages={n}')
        print(f'  chat_messages      : {len(messages)}')
        print(f'  daily_settlements  : {len(settlements)}'
              f'{"  (WILL DELETE)" if args.include_settlements else "  (kept)"}')

        if not sessions and not messages:
            print('\n  Nothing to delete.')
            return 0

        before_s = scalar(cur, 'SELECT count(*) FROM chat_sessions')
        before_m = scalar(cur, 'SELECT count(*) FROM chat_messages')
        print(f'\n  table totals before: chat_sessions={before_s} chat_messages={before_m}')

        if args.dry_run:
            print('\n  This is a dry-run, nothing was written. '
                  'Re-run with --apply when the list above is right.')
            return 0

        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        safe_user = args.user.replace('@', '_at_').replace('/', '_')
        path = os.path.join(BACKUP_DIR, f'chat-history-{args.db}-{safe_user}-{stamp}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'db': dbname, 'user_id': args.user, 'taken_at': stamp,
                       'chat_sessions': sessions, 'chat_messages': messages,
                       'daily_settlements': settlements,
                       'settlements_deleted': args.include_settlements},
                      f, ensure_ascii=False, indent=2, default=json_default)
        print(f'\n  backup: {path}')

        ids = [s['session_id'] for s in sessions]
        cur.execute('DELETE FROM chat_messages WHERE session_id = ANY(%s)', (ids,))
        del_m = cur.rowcount
        cur.execute('DELETE FROM chat_sessions WHERE user_id = %s', (args.user,))
        del_s = cur.rowcount
        del_d = 0
        if args.include_settlements:
            cur.execute('DELETE FROM daily_settlements WHERE user_id = %s', (args.user,))
            del_d = cur.rowcount

        print('\n  verification (before COMMIT):')
        check('deleted chat_messages matches backup', del_m == len(messages),
              f'{del_m} vs {len(messages)}')
        check('deleted chat_sessions matches backup', del_s == len(sessions),
              f'{del_s} vs {len(sessions)}')
        if args.include_settlements:
            check('deleted daily_settlements matches backup', del_d == len(settlements),
                  f'{del_d} vs {len(settlements)}')
        check('user has no chat_sessions left',
              scalar(cur, 'SELECT count(*) FROM chat_sessions WHERE user_id = %s',
                     (args.user,)) == 0)
        check('user has no chat_messages left',
              scalar(cur, 'SELECT count(*) FROM chat_messages m JOIN chat_sessions s '
                          'ON s.session_id = m.session_id WHERE s.user_id = %s',
                     (args.user,)) == 0)
        # The guard that matters: nobody else's rows moved.
        after_s = scalar(cur, 'SELECT count(*) FROM chat_sessions')
        after_m = scalar(cur, 'SELECT count(*) FROM chat_messages')
        check('chat_sessions total fell by exactly the backed-up count',
              before_s - after_s == len(sessions), f'{before_s} -> {after_s}')
        check('chat_messages total fell by exactly the backed-up count',
              before_m - after_m == len(messages), f'{before_m} -> {after_m}')
        check('no orphaned chat_messages anywhere',
              scalar(cur, 'SELECT count(*) FROM chat_messages m LEFT JOIN chat_sessions s '
                          'ON s.session_id = m.session_id WHERE s.session_id IS NULL') == 0)

        if failures:
            conn.rollback()
            print(f'\n  ROLLED BACK -- {len(failures)} check(s) failed: {failures}')
            print('  The database is exactly as it was.')
            return 1

        conn.commit()
        print(f'\n  COMMITTED. Deleted {del_s} sessions, {del_m} messages'
              + (f', {del_d} settlements' if args.include_settlements else '')
              + f' from {dbname}.')
        return 0
    except Exception:
        if args.apply:
            conn.rollback()
            print('\n  ROLLED BACK on exception.')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
