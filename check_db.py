import sqlite3
import os

db_path = r'd:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables index: {tables}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"Table '{table_name}' has {count} rows.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
