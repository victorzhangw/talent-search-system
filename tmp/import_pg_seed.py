
import os
import sys
from sqlalchemy import create_engine, text

def run_migration():
    # Hardcoded connection based on .env
    db_url = "postgresql://projectuser:projectpass@127.0.0.1:5432/ai_chatbot_v2"
    
    migration_file = r"d:\python\AI-Character-Chatbot\migration\02_seed_data.sql"
    if not os.path.exists(migration_file):
        print(f"File not found: {migration_file}")
        return

    print(f"Connecting to {db_url}...")
    engine = create_engine(db_url)
    
    print(f"Reading {migration_file}...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into clean statements
    # We'll use a more robust split for large SQL files
    statements = []
    current_stmt = []
    for line in content.splitlines():
        if not line.strip() or line.startswith('--'):
            continue
        current_stmt.append(line)
        if line.strip().endswith(';'):
            statements.append("\n".join(current_stmt))
            current_stmt = []
    
    print(f"Executing {len(statements)} statements...")
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        try:
            for i, stmt in enumerate(statements):
                if i % 100 == 0:
                    print(f"Progress: {i}/{len(statements)}")
                conn.execute(text(stmt))
            trans.commit()
            print("✅ Migration completed successfully!")
        except Exception as e:
            trans.rollback()
            print(f"❌ Error during migration: {e}")

if __name__ == "__main__":
    run_migration()
