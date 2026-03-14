
import sqlite3

def check_schema():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(trait_bands)")
        cols = [r[1] for r in cursor.fetchall()]
        print(f"Columns in trait_bands: {cols}")
        
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()
