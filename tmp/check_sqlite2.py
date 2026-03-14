
import sqlite3

def check_sqlite():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        display_name = 'Self-Leadership'
        project_abbrev = 'ANI'
        
        # Test exact query logic used by ContextBuilder
        cursor.execute("""
            SELECT trait_id, name_en, name_zh 
            FROM trait_definitions 
            WHERE trim(lower(name_en)) = trim(lower(?))
            AND trait_id LIKE ?
        """, (display_name, f"{project_abbrev}_%"))
        
        rows = cursor.fetchall()
        print("SQLAlchemy Fallback Match:")
        for r in rows:
            print(dict(r))
            
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    check_sqlite()
