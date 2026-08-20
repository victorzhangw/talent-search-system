"""Sync the five trait-spec reference tables from UAT into PRD.

Usage:
    python scripts/sync_prd_reference_data.py --dry-run     # report only, no writes
    python scripts/sync_prd_reference_data.py --backup      # dump PRD's tables, no writes
    python scripts/sync_prd_reference_data.py --apply       # backup, then sync
    python scripts/sync_prd_reference_data.py --verify      # hash-compare the two sides

Scope
-----
Only reference data: trait_definitions, endpoint_blocks, trait_bands, trait_interactions,
trait_endpoints. The transactional tables (chat_sessions, chat_messages,
daily_settlements, admin_users) are never read for writing and never touched.

What this exists to fix
-----------------------
PRD's trait_interactions.primary_band holds 'A (高)' where UAT holds 'A'. The selector
does `split_part(primary_band, '(', 1)` (interaction_selector.py:33), which turns
'A (高)' into 'A ' -- with a trailing space -- and the equality test at line 104 then
rejects every row. So PRD emits no interaction narratives at all, silently. That is the
defect the client reported on 2026-08-10; the fix reached UAT and never reached PRD.

PRD is also missing endpoint_blocks (3 rows) and trait_endpoints (74 rows) entirely, plus
two indexes, and its trait_bands.ai_guidance predates the `do_raw` field.

Safety
------
Every write happens inside one transaction, and the hash comparison runs *before* COMMIT:
if the copied tables do not match UAT byte for byte, the transaction is rolled back and
PRD is left exactly as it was. A backup is written first regardless, because a rollback
cannot help once a COMMIT has happened for the wrong reason.

The read side is opened readonly, so a mistake in this script cannot damage UAT.
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env.uat')
BACKUP_DIR = os.path.join(SCRIPT_DIR, 'backups')

# 父表在前。TRUNCATE 五張表要寫在同一個陳述式裡（外鍵才不會擋），INSERT 則必須依這個
# 順序，子表才有父鍵可指。
TABLES = ['trait_definitions', 'endpoint_blocks',
          'trait_bands', 'trait_interactions', 'trait_endpoints']

# TRUNCATE ... RESTART IDENTITY 之後仍要 setval：下面是帶著 UAT 原本的 id 寫入的，
# 序列若停在 1，下一次 INSERT 會撞主鍵。
SEQUENCE_TABLES = ['trait_bands', 'trait_interactions', 'trait_endpoints']

MISSING_INDEXES = [
    ('ix_trait_endpoints_lookup',
     'CREATE INDEX IF NOT EXISTS ix_trait_endpoints_lookup '
     'ON trait_endpoints USING btree (trait_id, band)'),
    ('ix_trait_endpoints_type',
     'CREATE INDEX IF NOT EXISTS ix_trait_endpoints_type '
     'ON trait_endpoints USING btree (endpoint_type)'),
]

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


def columns(conn, table):
    """(name, data_type) in ordinal order."""
    return [(c, t) for c, t in q(conn, """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position""", (table,))]


def select_list(cols):
    """json/jsonb read as text so the copy is byte-faithful rather than re-serialised."""
    return ', '.join(f'"{c}"::text' if t in ('json', 'jsonb') else f'"{c}"'
                     for c, t in cols)


def placeholders(cols):
    return ', '.join('%s::json' if t in ('json', 'jsonb') else '%s' for _, t in cols)


def fetch(conn, table):
    cols = columns(conn, table)
    return cols, q(conn, f'SELECT {select_list(cols)} FROM "{table}" ORDER BY 1')


def table_hash(conn, table):
    """Order-independent hash of a table's contents, id column excluded.

    `id` is a per-database sequence value; comparing it would report a difference on every
    row of two tables that are in fact identical, which is exactly what happened on the
    first pass of this comparison.
    """
    cols = [(c, t) for c, t in columns(conn, table) if c != 'id']
    rows = q(conn, f'SELECT {select_list(cols)} FROM "{table}"')
    norm = sorted('\x1f'.join('' if v is None else str(v) for v in r) for r in rows)
    return hashlib.sha256('\x1e'.join(norm).encode()).hexdigest()[:16], len(rows)


def cmd_verify(uat, prd):
    print('\n[VERIFY] UAT vs PRD, reference tables')
    for t in TABLES:
        hu, nu = table_hash(uat, t)
        hp, np_ = table_hash(prd, t)
        check(f'{t:20} UAT {nu:>5} / PRD {np_:>5}', hu == hp,
              '' if hu == hp else f'{hu} vs {hp}')


def sql_literal(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def cmd_backup(prd):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(BACKUP_DIR, f'prd_reference_{stamp}.sql')
    total = 0
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'-- PRD reference tables, {datetime.now():%Y-%m-%d %H:%M:%S}\n')
        f.write('-- Restore: psql -h <host> -U postgres -d ai_chatbot_v2_prd -f <this file>\n')
        f.write('BEGIN;\n')
        f.write(f'TRUNCATE {", ".join(reversed(TABLES))} RESTART IDENTITY;\n\n')
        for t in TABLES:
            cols, rows = fetch(prd, t)
            names = ', '.join(f'"{c}"' for c, _ in cols)
            f.write(f'-- {t}: {len(rows)} rows\n')
            for r in rows:
                vals = ', '.join(sql_literal(v) for v in r)
                f.write(f'INSERT INTO "{t}" ({names}) VALUES ({vals});\n')
            f.write('\n')
            total += len(rows)
        for t in SEQUENCE_TABLES:
            f.write(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                    f"COALESCE((SELECT max(id) FROM \"{t}\"), 1));\n")
        f.write('COMMIT;\n')
    size = os.path.getsize(path)
    print(f'  backup written: {path}')
    print(f'  {total:,} rows, {size:,} bytes')
    return path


def cmd_apply(env, uat, prd_ro):
    print('\n[BACKUP]')
    cmd_backup(prd_ro)

    print('\n[READ UAT]')
    payload = {}
    for t in TABLES:
        cols, rows = fetch(uat, t)
        payload[t] = (cols, rows)
        print(f'  {t:20} {len(rows):>5} rows')

    print('\n[APPLY] one transaction; verified before COMMIT')
    from psycopg2.extras import execute_values
    conn = connect(env, 'ai_chatbot_v2_prd', readonly=False)
    try:
        with conn.cursor() as cur:
            cur.execute(f'TRUNCATE {", ".join(TABLES)} RESTART IDENTITY')
            print(f'  truncated {len(TABLES)} tables')
            for t in TABLES:
                cols, rows = payload[t]
                if not rows:
                    continue
                names = ', '.join(f'"{c}"' for c, _ in cols)
                execute_values(
                    cur, f'INSERT INTO "{t}" ({names}) VALUES %s',
                    rows, template=f'({placeholders(cols)})', page_size=500)
                print(f'  inserted {len(rows):>5} into {t}')
            for t in SEQUENCE_TABLES:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                    f"COALESCE((SELECT max(id) FROM \"{t}\"), 1))", (t,))
            print(f'  reset {len(SEQUENCE_TABLES)} sequences')
            for name, ddl in MISSING_INDEXES:
                cur.execute(ddl)
            print(f'  ensured {len(MISSING_INDEXES)} indexes')

        # 在 COMMIT 之前驗證。這個 cursor 看得到尚未提交的資料，比對不過就整批回滾，
        # PRD 維持原狀——事後才發現寫錯的話，回滾已經來不及了。
        print('\n[VERIFY BEFORE COMMIT]')
        for t in TABLES:
            hu, nu = table_hash(uat, t)
            hp, np_ = table_hash(conn, t)
            check(f'{t:20} UAT {nu:>5} / PRD {np_:>5}', hu == hp,
                  '' if hu == hp else f'{hu} vs {hp}')

        if failures:
            conn.rollback()
            print('\n  ROLLED BACK -- PRD is unchanged.')
            return
        conn.commit()
        print('\n  COMMITTED')
    except Exception:
        conn.rollback()
        print('\n  ROLLED BACK on exception -- PRD is unchanged.')
        raise
    finally:
        conn.close()


def cmd_dry_run(uat, prd):
    print('\n[DRY RUN] what --apply would change')
    for t in TABLES:
        hu, nu = table_hash(uat, t)
        hp, np_ = table_hash(prd, t)
        if hu == hp:
            verdict = 'identical, would be rewritten with the same content'
        elif np_ == 0:
            verdict = f'PRD empty, would gain {nu} rows'
        else:
            verdict = f'differs, {np_} rows replaced by {nu}'
        print(f'  {t:20} UAT {nu:>5} / PRD {np_:>5}  {verdict}')
    have = {r[0] for r in q(prd, "SELECT indexname FROM pg_indexes WHERE schemaname='public'")}
    for name, _ in MISSING_INDEXES:
        print(f'  index {name:34} {"present" if name in have else "would be created"}')
    print('\n  untouched: chat_sessions, chat_messages, daily_settlements, admin_users')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--backup', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    if not any([args.dry_run, args.backup, args.apply, args.verify]):
        ap.print_help()
        return 2

    env = load_env()
    uat = connect(env, 'ai_chatbot_v2', readonly=True)
    prd = connect(env, 'ai_chatbot_v2_prd', readonly=True)
    try:
        if args.dry_run:
            cmd_dry_run(uat, prd)
        if args.backup and not args.apply:
            print('\n[BACKUP]')
            cmd_backup(prd)
        if args.apply:
            cmd_apply(env, uat, prd)
        if args.verify:
            cmd_verify(uat, connect(env, 'ai_chatbot_v2_prd', readonly=True))
    finally:
        uat.close()
        prd.close()

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
