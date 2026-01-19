
import sys
import os
import sqlite3
import json
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

# Adjust path to find backend module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api_v2.database.connection import get_db_connection
from api_v2.database.models import Base, TraitDefinition, TraitBand, TraitInteraction

# SQLite Path
SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../api_v2/app.db'))

def migrate():
    print(f"🚀 Starting Migration from {SQLITE_DB_PATH} to PostgreSQL...")
    
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ SQLite DB not found at: {SQLITE_DB_PATH}")
        return

    # 1. Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    # 2. Connect to PostgreSQL (using SQLAlchemy for ORM models)
    # We use raw psycopg2 connection to create engine for SQLAlchemy
    pg_raw_conn = get_db_connection()
    # Construct a URL for SQLAlchemy from the raw connection params? 
    # Or just reuse the logic. Let's create an engine similarly.
    from api_v2.database.connection import get_db_config, get_ssh_tunnel
    
    config = get_db_config()
    tunnel = get_ssh_tunnel()
    
    port = config['db_port']
    host = config['db_host']
    
    if tunnel:
        port = tunnel.local_bind_port
        host = 'localhost'
        
    db_url = f"postgresql://{config['db_user']}:{config['db_password']}@{host}:{port}/{config['db_name']}"
    engine = create_engine(db_url)
    
    # Create Tables if they don't exist
    print("🔄 creating tables in PostgreSQL...")
    Base.metadata.create_all(engine)
    
    session = Session(engine)

    try:
        # --- Migrate TraitDefinition ---
        print("\n📦 Migrating TraitDefinition...")
        cursor.execute("SELECT * FROM trait_definitions")
        rows = cursor.fetchall()
        for row in rows:
            # Check if exists
            existing = session.query(TraitDefinition).filter_by(trait_id=row['trait_id']).first()
            if not existing:
                new_trait = TraitDefinition(
                    trait_id=row['trait_id'],
                    name_zh=row['name_zh'],
                    name_en=row['name_en'],
                    dimension=row['dimension'],
                    definition=row['definition']
                )
                session.add(new_trait)
        session.commit()
        print(f"✅ Processed {len(rows)} TraitDefinitions")

        # --- Migrate TraitBand ---
        print("\n📦 Migrating TraitBand...")
        cursor.execute("SELECT * FROM trait_bands")
        rows = cursor.fetchall()
        count = 0
        for row in rows:
            # For bands, we might just clear and reload or check carefully.
            # Let's assume ID might change (autoincrement), so we match by business key (trait_id + band)
            existing = session.query(TraitBand).filter_by(trait_id=row['trait_id'], band=row['band']).first()
            if not existing:
                # Handle ai_guidance JSON
                ai_guidance = row['ai_guidance']
                if isinstance(ai_guidance, str):
                    try:
                        ai_guidance = json.loads(ai_guidance)
                    except:
                        ai_guidance = {}
                
                new_band = TraitBand(
                    trait_id=row['trait_id'],
                    band=row['band'],
                    min_score=row['min_score'],
                    max_score=row['max_score'],
                    semantic_label=row['semantic_label'],
                    description=row['description'],
                    management_focus=row['management_focus'],
                    report_wording=row['report_wording'],
                    ai_guidance=ai_guidance
                )
                session.add(new_band)
                count += 1
        session.commit()
        print(f"✅ Added {count} new TraitBands")

        # --- Migrate TraitInteraction ---
        print("\n📦 Migrating TraitInteraction...")
        cursor.execute("SELECT * FROM trait_interactions")
        rows = cursor.fetchall()
        count = 0
        for row in rows:
            # Match by unique combination
            existing = session.query(TraitInteraction).filter_by(
                primary_trait_id=row['primary_trait_id'],
                primary_band=row['primary_band'],
                trigger_trait_id=row['trigger_trait_id'],
                trigger_band=row['trigger_band']
            ).first()
            
            if not existing:
                new_interaction = TraitInteraction(
                    primary_trait_id=row['primary_trait_id'],
                    primary_band=row['primary_band'],
                    trigger_trait_id=row['trigger_trait_id'],
                    trigger_band=row['trigger_band'],
                    narrative=row['narrative']
                )
                session.add(new_interaction)
                count += 1
        session.commit()
        print(f"✅ Added {count} new TraitInteractions")
        
        print("\n🎉 Migration Complete!")
        
    except Exception as e:
        print(f"\n❌ Migration Failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        sqlite_conn.close()

if __name__ == "__main__":
    migrate()
