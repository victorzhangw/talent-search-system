
import sys
import os
import re

# Add the project root to sys.path
sys.path.append(os.getcwd())

from BackEnd.api_v2.database.session import db_session, engine
from sqlalchemy import text

def run_migration():
    migration_file = r"d:\python\AI-Character-Chatbot\migration\02_seed_data.sql"
    if not os.path.exists(migration_file):
        print(f"File not found: {migration_file}")
        return

    print(f"Reading {migration_file}...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by semicolon but be careful with quotes
    # Simple split might work for bulk inserts
    statements = content.split(';')
    
    print(f"Executing {len(statements)} statements...")
    
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            for i, stmt in enumerate(statements):
                stmt = stmt.strip()
                if not stmt or stmt.startswith('--'):
                    continue
                
                # Progress every 100
                if i % 100 == 0:
                    print(f"Progress: {i}/{len(statements)}")
                
                conn.execute(text(stmt))
            
            transaction.commit()
            print("✅ Migration completed successfully!")
        except Exception as e:
            transaction.rollback()
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_migration()
