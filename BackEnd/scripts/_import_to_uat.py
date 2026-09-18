# -*- coding: utf-8 -*-
"""Run the 0915 trait migration against UAT, using the project's .env.uat.

UAT and PRD share a host and differ only by database name, so the target is asserted
before anything is written. Ad-hoc driver for the 0915 rollout.
"""
import os, sys, io, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

EXPECT_DB = 'ai_chatbot_v2'          # UAT. PRD is ai_chatbot_v2_prd on the same host.

def load_uat_env():
    path = os.path.join(HERE, '..', 'api_v2', '.env.uat')
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if k.startswith('UAT_DB_'):
                    os.environ[k[4:]] = v        # UAT_DB_HOST -> DB_HOST
    # load_dotenv(override=False) below must not clobber these
    return {k: os.environ.get(k) for k in ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER')}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--excel', required=True)
    ap.add_argument('--apply', action='store_true', help='without this, stops after backup')
    args = ap.parse_args()

    shown = load_uat_env()
    print(f"[Env] from .env.uat -> {shown}")

    import migrate_traits_from_excel as mig
    from sqlalchemy import text

    engine = mig.get_db_engine()
    with engine.connect() as c:
        db, usr, addr = c.execute(text(
            "SELECT current_database(), current_user, inet_server_addr()")).fetchone()
    print(f"[Target] database={db} user={usr} server={addr}")
    if db != EXPECT_DB:
        sys.exit(f"[ABORT] expected {EXPECT_DB}, got {db}")
    if str(addr) in ('127.0.0.1', '::1'):
        sys.exit(f"[ABORT] resolved to localhost; .env.uat did not take effect")
    print(f"[Target] confirmed UAT\n")

    definitions, bands, interactions, endpoints, blocks = mig.parse_excel(
        os.path.abspath(args.excel), require_endpoints=False)

    backup_dir = os.path.join(HERE, 'backups', 'uat')
    print("\n[Step 1] Backup (UAT)...")
    path = mig.create_backup(engine, backup_dir)

    if not args.apply:
        print("\n[STOP] backup only. Re-run with --apply to write.")
        return 0

    print("\n[Step 2] Schema migration...")
    mig.apply_schema_migration(engine)
    mig.apply_endpoint_schema(engine)

    print("\n[Step 3] Writing...")
    mig.write_to_db(engine, definitions, bands, interactions,
                    preserve_endpoints=(endpoints is None))
    print(f"\n[DONE] UAT migration complete. Backup: {path}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
