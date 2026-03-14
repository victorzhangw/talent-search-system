
import sqlite3

def check_interactions():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM trait_interactions LIMIT 5")
        rows = cursor.fetchall()
        print("Interactions in DB:")
        for r in rows:
            print(dict(r))
            
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_interactions()
