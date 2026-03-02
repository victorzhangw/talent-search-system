import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from BackEnd.api_v2.database.connection import get_db_engine

def apply_migration():
    engine = get_db_engine()
    with engine.begin() as conn:
        print("Checking/Adding rating column to chat_messages...")
        try:
            conn.execute(
                "ALTER TABLE chat_messages ADD COLUMN rating INTEGER DEFAULT 0;"
            )
            print("Successfully added rating column.")
        except Exception as e:
            if "already exists" in str(e).lower() or '42701' in str(e): # Duplicate column
                print("Column 'rating' already exists.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    apply_migration()
