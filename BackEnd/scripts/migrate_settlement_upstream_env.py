"""Apply the 2026-09-09 upstream_env migration to UAT or PRD, with backup and verification.

Usage:
    python scripts/migrate_settlement_upstream_env.py --target uat --dry-run   # read only
    python scripts/migrate_settlement_upstream_env.py --target uat --backup    # dump table, no writes
    python scripts/migrate_settlement_upstream_env.py --target uat --apply     # backup, then migrate
    python scripts/migrate_settlement_upstream_env.py --target uat --verify    # check + ORM insert test

What this exists to fix
-----------------------
Commit ad16a8c added `daily_settlements.upstream_env` (NOT NULL) to the model, and the
deploy around 2026-09-16 shipped that code without the migration. Every settlement INSERT
on UAT/PRD has failed since: `submit_daily_settlement()` catches the error, logs
"[Daily Settlement] DB Insert Failed" and still calls the upstream API. So deductions most
likely went out, but no local record was kept, and nothing failed upstream can be retried.
PRD: last settlement row 2026-09-15, 272 assistant replies since then with none.

This script only adds the column. Back-filling the missed records is a billing decision
and is deliberately not done here.

Safety
------
- Connection from api_v2/.env.uat (same host for UAT and PRD; PRD is ai_chatbot_v2_prd).
  The password is never printed.
- --dry-run / --backup / the read side of --verify use a readonly session.
- --apply writes a backup first, then runs the migration in one transaction and checks the
  result *before* COMMIT; any check failing rolls the whole thing back.
- lock_timeout 5s: ALTER needs a brief exclusive lock; if live traffic holds the table we
  give up rather than queue behind it and stall every request.
- --verify's ORM insert is always rolled back, and the row count is re-checked afterwards.

Rollback of the migration itself:
    ALTER TABLE daily_settlements DROP COLUMN IF EXISTS upstream_env;
"""

import argparse
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(BACKEND_DIR, 'api_v2', '.env.uat')
BACKUP_DIR = os.path.join(SCRIPT_DIR, 'backups')
MIGRATION = os.path.join(SCRIPT_DIR, 'migrations',
                         '2026-09-09_add_upstream_env_to_daily_settlements.sql')
TABLE = 'daily_settlements'
DBNAMES = {'uat': 'ai_chatbot_v2', 'prd': 'ai_chatbot_v2_prd'}

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
    conn.set_session(readonly=readonly, autocommit=readonly)
    return conn


def q(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def column_def(conn):
    """(data_type, max_len, is_nullable, default) of upstream_env, or None if absent."""
    rows = q(conn, """
        SELECT data_type, character_maximum_length, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = 'upstream_env'""",
             (TABLE,))
    return rows[0] if rows else None


def columns(conn):
    return [c for (c,) in q(conn, """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position""", (TABLE,))]


def sql_literal(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # last_error 存過整頁 HTML（含換行）。一律寫成單行：備份檔一列一筆，讀回驗證才不會切錯。
    if any(ch in s for ch in '\n\r\\'):
        s = s.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace("'", "''")
        return "E'" + s + "'"
    return "'" + s.replace("'", "''") + "'"


def cmd_dry_run(conn, target):
    print(f'\n[DRY-RUN] {target.upper()} / {conn.info.dbname} @ {conn.info.host}')
    cd = column_def(conn)
    n = q(conn, f'SELECT count(*) FROM "{TABLE}"')[0][0]
    last = q(conn, f'SELECT max(created_at) FROM "{TABLE}"')[0][0]
    print(f'  upstream_env column : {"present " + str(cd) if cd else "MISSING"}')
    print(f'  rows                : {n}')
    print(f'  last created_at     : {last}')
    print(f'  migration to run    : {os.path.basename(MIGRATION)}' if not cd
          else '  nothing to do (column already present; migration is idempotent anyway)')


def cmd_backup(conn, target):
    """Dump the table as INSERTs, then read the file back and prove it matches the DB."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(BACKUP_DIR, f'{target}_daily_settlements_{stamp}.sql')
    cols = columns(conn)
    names = ', '.join(f'"{c}"' for c in cols)
    rows = q(conn, f'SELECT {names} FROM "{TABLE}" ORDER BY id')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'-- {target.upper()} {conn.info.dbname}.{TABLE}, {datetime.now():%Y-%m-%d %H:%M:%S}, '
                f'{len(rows)} rows\n')
        f.write(f'-- Restore: psql -h <host> -U postgres -d {conn.info.dbname} -f <this file>\n')
        f.write('BEGIN;\n')
        f.write(f'TRUNCATE "{TABLE}" RESTART IDENTITY;\n')
        for r in rows:
            f.write(f'INSERT INTO "{TABLE}" ({names}) VALUES ({", ".join(sql_literal(v) for v in r)});\n')
        f.write(f"SELECT setval(pg_get_serial_sequence('{TABLE}', 'id'), "
                f"COALESCE((SELECT max(id) FROM \"{TABLE}\"), 1));\n")
        f.write('COMMIT;\n')

    # 讀回檔案驗證：把檔案裡的字面值交給 PostgreSQL 自己解析，逐筆逐欄與表比對。
    # 不比字串——Python 與 PG 印 timestamp 的格式不同（.542180 vs .54218），值卻相同；
    # 這裡證明的是「這份檔案還原回去會得到一模一樣的值」。
    prefix = f'INSERT INTO "{TABLE}" ({names}) VALUES ('
    with open(path, encoding='utf-8') as f:
        tuples = [line[len(prefix) - 1:].rstrip('\n')[:-1]   # 留下 "(...)"，去掉結尾的 ';'
                  for line in f if line.startswith(prefix)]
    types = dict(q(conn, """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a
        WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped""", (TABLE,)))
    vcols = ', '.join(f'"{c}"' for c in cols)
    match = ' AND '.join(f't."{c}" IS NOT DISTINCT FROM v."{c}"::{types[c]}' for c in cols if c != 'id')
    matched = q(conn, f"""
        SELECT count(*) FROM "{TABLE}" t
        JOIN (VALUES {', '.join(tuples)}) AS v({vcols}) ON t.id = v.id::int
        WHERE {match}""")[0][0] if tuples else 0
    n_now = q(conn, f'SELECT count(*) FROM "{TABLE}"')[0][0]
    print(f'  backup written: {path}')
    print(f'  {len(rows)} rows, {os.path.getsize(path):,} bytes, columns: {cols}')
    check('backup INSERT lines == rows dumped', len(tuples) == len(rows), f'{len(tuples)} vs {len(rows)}')
    check('table unchanged while dumping', n_now == len(rows), f'{n_now} vs {len(rows)}')
    check('every backup row equals the DB row (parsed by PG)', matched == n_now, f'{matched} / {n_now}')
    return path, len(rows)


def migration_body():
    """The migration file without its own BEGIN/COMMIT: we hold the transaction here."""
    with open(MIGRATION, encoding='utf-8') as f:
        lines = [ln for ln in f.read().splitlines()
                 if ln.strip().upper() not in ('BEGIN;', 'COMMIT;')]
    return '\n'.join(lines)


def check_column(conn, n_expected):
    cd = column_def(conn)
    check('upstream_env exists', cd is not None, cd)
    if cd:
        dtype, maxlen, nullable, default = cd
        check('type varchar(16)', dtype == 'character varying' and maxlen == 16, f'{dtype}({maxlen})')
        check('NOT NULL', nullable == 'NO', nullable)
        check("default 'default'", (default or '').startswith("'default'"), default)
        nulls = q(conn, f'SELECT count(*) FROM "{TABLE}" WHERE upstream_env IS NULL')[0][0]
        check('no NULL upstream_env', nulls == 0, nulls)
    n = q(conn, f'SELECT count(*) FROM "{TABLE}"')[0][0]
    check('row count unchanged', n == n_expected, f'{n} vs {n_expected}')


def cmd_apply(env, target):
    dbname = DBNAMES[target]
    ro = connect(env, dbname, readonly=True)
    print('\n[BACKUP]')
    _, n_before = cmd_backup(ro, target)
    ro.close()
    if failures:
        sys.exit('ERROR: backup checks failed; not migrating.')

    print(f'\n[APPLY] {target.upper()} / {dbname}')
    rw = connect(env, dbname, readonly=False)
    try:
        with rw.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout = '5s'")
            cur.execute(migration_body())
        check_column(rw, n_before)
        if failures:
            rw.rollback()
            sys.exit('ERROR: post-migration checks failed inside the transaction; ROLLED BACK.')
        rw.commit()
        print('  COMMIT done')
    except Exception:
        rw.rollback()
        print('  ROLLED BACK')
        raise
    finally:
        rw.close()


def cmd_verify(env, target):
    dbname = DBNAMES[target]
    ro = connect(env, dbname, readonly=True)
    print(f'\n[VERIFY] {target.upper()} / {dbname}')
    n_before = q(ro, f'SELECT count(*) FROM "{TABLE}"')[0][0]
    check_column(ro, n_before)

    # 用 App 真正的 model 走一次 INSERT（flush 會真的送出 SQL），然後一定 rollback。
    # 證明的是「App 那條寫入路徑現在能過」，而不只是欄位存在。
    sys.path.insert(0, BACKEND_DIR)
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
    from sqlalchemy.orm import sessionmaker
    from api_v2.database.models import DailySettlementRecord
    url = URL.create('postgresql+psycopg2', username=env['UAT_DB_USER'],
                     password=env['UAT_DB_PASSWORD'], host=env['UAT_DB_HOST'],
                     port=int(env.get('UAT_DB_PORT', '5432')), database=dbname)
    engine = create_engine(url)
    s = sessionmaker(bind=engine)()
    try:
        rec = DailySettlementRecord(user_id='migration-verify@local', plan_id=0,
                                    session_id='migration-verify', message_id=None,
                                    upstream_env='default', status='PENDING')
        s.add(rec)
        s.flush()
        check('ORM INSERT (DailySettlementRecord) succeeds', rec.id is not None, f'id={rec.id}')
    except Exception as e:
        check('ORM INSERT (DailySettlementRecord) succeeds', False, str(e).splitlines()[0])
    finally:
        s.rollback()
        s.close()
        engine.dispose()
    n_after = q(ro, f'SELECT count(*) FROM "{TABLE}"')[0][0]
    check('test row rolled back (count unchanged)', n_after == n_before, f'{n_after} vs {n_before}')
    ro.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=sorted(DBNAMES), required=True)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--backup', action='store_true')
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--verify', action='store_true')
    args = ap.parse_args()

    env = load_env()
    if args.apply:
        cmd_apply(env, args.target)
    elif args.verify:
        cmd_verify(env, args.target)
    else:
        conn = connect(env, DBNAMES[args.target], readonly=True)
        cmd_dry_run(conn, args.target) if args.dry_run else cmd_backup(conn, args.target)
        conn.close()

    print(f"\nRESULT: {'PASS' if not failures else 'FAIL (' + str(len(failures)) + ')'}")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
