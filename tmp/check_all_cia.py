
import sqlite3

def check_all_cia():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name_en FROM trait_definitions WHERE trait_id LIKE 'CIA_%'")
        names = [r['name_en'] for r in cursor.fetchall()]
        print(f"CIA Names in DB: {names}")
        
        target = "Efficacy"
        if target in names:
            print(f"✅ Found {target}")
        else:
            print(f"❌ {target} not found in CIA list")
            
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_all_cia()
