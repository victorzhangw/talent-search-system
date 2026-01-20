
import sys
import os
import sqlite3
import psycopg2
from datetime import datetime

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

from backend.api_v2.database.connection import get_db_session, get_db_engine
from backend.api_v2.database.models import (
    Base, AdminUser, ChatSession, ChatMessage, 
    TraitDefinition, TraitBand, TraitInteraction
)
from backend.api_v2.admin.auth import get_password_hash

def migrate_sqlite_to_pg():
    print("🚀 Starting Migration: SQLite -> Local PostgreSQL")
    
    # 1. Setup PG Connection
    pg_session = get_db_session()
    pg_engine = get_db_engine()
    
    # Ensure tables exist
    print("   Creating PG tables...")
    Base.metadata.create_all(bind=pg_engine)
    
    # 2. Seed Admin User
    print("   Seeding Admin User...")
    admin = pg_session.query(AdminUser).filter_by(username='admin').first()
    if not admin:
        hashed_pw = get_password_hash('admin123')
        new_admin = AdminUser(username='admin', password_hash=hashed_pw)
        pg_session.add(new_admin)
        print("   ✅ Created default admin: admin / admin123")
    else:
        print("   ℹ️ Admin user already exists.")
    
    # 3. Connect to SQLite (app.db)
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db')
    if not os.path.exists(sqlite_path):
        print(f"   ⚠️ SQLite DB not found at {sqlite_path}. Skipping data migration.")
        pg_session.commit()
        return

    print(f"   Reading from {sqlite_path}...")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 4. Migrate Traits (Preserve exact IDs)
    # Check if we need to migrate traits. If PG is empty, yes.
    if pg_session.query(TraitDefinition).count() == 0:
        print("   Migrating Trait Definitions...")
        rows = cursor.execute("SELECT * FROM trait_definitions").fetchall()
        for row in rows:
            trait = TraitDefinition(
                trait_id=row['trait_id'],
                name_zh=row['name_zh'],
                name_en=row['name_en'],
                dimension=row['dimension'],
                definition=row['definition']
            )
            pg_session.merge(trait) # Merge handles potential conflicts
            
        print("   Migrating Trait Bands...")
        rows = cursor.execute("SELECT * FROM trait_bands").fetchall()
        for row in rows:
            band = TraitBand(
                trait_id=row['trait_id'],
                band=row['band'],
                min_score=row['min_score'],
                max_score=row['max_score'],
                semantic_label=row['semantic_label'],
                description=row['description'],
                management_focus=row['management_focus'],
                report_wording=row['report_wording'],
                ai_guidance=row['ai_guidance'] # JSON should auto-map if using SqlAlchemy JSON type
            )
            pg_session.add(band)
            
        print("   Migrating Interactions...")
        rows = cursor.execute("SELECT * FROM trait_interactions").fetchall()
        for row in rows:
            inter = TraitInteraction(
                primary_trait_id=row['primary_trait_id'],
                primary_band=row['primary_band'],
                trigger_trait_id=row['trigger_trait_id'],
                trigger_band=row['trigger_band'],
                narrative=row['narrative']
            )
            pg_session.add(inter)
    else:
        print("   ℹ️ Traits already populate in PG. Skipping trait migration.")

    # 5. Migrate Chat Logs (Optional: Map old ChatLog to new Session/Message?)
    # Old ChatLog: id, session_id, meta_info, timestamp
    # It likely stores the WHOLE conversation in JSON or something?
    # Inspecting database.py from history: ChatLog has meta_info(JSON).
    # If messages are inside meta_info, we extract them.
    
    print("   Migrating Chat History...")
    try:
        logs = cursor.execute("SELECT * FROM chat_logs").fetchall()
        # Track session_ids to avoid duplicates
        existing_sids = {s[0] for s in pg_session.query(ChatSession.session_id).all()}
        
        for log in logs:
            sid = log['session_id']
            if sid in existing_sids:
                continue
                
            # Create Session
            sess = ChatSession(
                session_id=sid,
                started_at=datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S.%f') if isinstance(log['timestamp'], str) else log['timestamp'],
                last_active_at=datetime.utcnow(),
                status='ended' # Assume old logs are ended
            )
            pg_session.add(sess)
            existing_sids.add(sid)
            
            # Extract Messages from meta_info if possible
            # meta = json.loads(log['meta_info'])
            # ... Parsing logic depends on raw data format ...
            # For now, simplistic migration of session record.
            
    except Exception as e:
        print(f"   ⚠️ Could not migrate some chat logs: {e}")

    # Commit all changes
    try:
        pg_session.commit()
        print("✅ Migration Complete!")
    except Exception as e:
        pg_session.rollback()
        print(f"❌ Migration Failed: {e}")
    finally:
        pg_session.close()
        conn.close()

if __name__ == "__main__":
    migrate_sqlite_to_pg()
