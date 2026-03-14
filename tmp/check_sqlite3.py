
import sqlite3

def check_sqlite():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM trait_bands 
            WHERE trait_id = 'ANI_05'
        """)
        
        rows = cursor.fetchall()
        print("Bands for ANI_05:")
        for r in rows:
            print(dict(r))
            
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_sqlite()
