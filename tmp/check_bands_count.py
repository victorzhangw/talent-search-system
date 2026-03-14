
import sqlite3

def check_bands():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Count bands for ANI vs CIA
        cursor.execute("SELECT COUNT(*) as c FROM trait_bands WHERE trait_id LIKE 'ANI_%'")
        ani_c = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM trait_bands WHERE trait_id LIKE 'CIA_%'")
        cia_c = cursor.fetchone()['c']
        print(f"Bands in DB -> ANI: {ani_c}, CIA: {cia_c}")
        
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_bands()
