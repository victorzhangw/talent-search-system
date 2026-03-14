
import sqlite3

def check_sqlite():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check trait_definitions
    try:
        cursor.execute("SELECT trait_id, name_en, name_zh FROM trait_definitions LIMIT 10")
        rows = cursor.fetchall()
        print("First 10 traits:")
        for r in rows:
            print(dict(r))
        
        # Count ANI vs CIA
        cursor.execute("SELECT COUNT(*) as c FROM trait_definitions WHERE trait_id LIKE 'ANI_%'")
        ani_count = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM trait_definitions WHERE trait_id LIKE 'CIA_%'")
        cia_count = cursor.fetchone()['c']
        print(f"ANI count: {ani_count}, CIA count: {cia_count}")

        cursor.execute("SELECT * FROM trait_definitions WHERE trait_id = 'ANI_300b'")
        q1 = cursor.fetchall()
        print("\nSearching ANI_300b:")
        for r in q1: print(dict(r))
        
        cursor.execute("SELECT * FROM trait_definitions WHERE trait_id = '300b'")
        q2 = cursor.fetchall()
        print("\nSearching 300b:")
        for r in q2: print(dict(r))
        
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_sqlite()
