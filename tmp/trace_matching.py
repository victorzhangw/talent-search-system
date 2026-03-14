
import sqlite3

def full_trace():
    """
    Simulates EXACTLY what context_builder.py does:
    For each trait in the report, try:
    1. ID match:   '{project}_{api_tid}'
    2. Name match: name_en LIKE lower(display_name) AND trait_id LIKE '{project}_%'
    3. Band match: trait_id + score range
    """
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Simulate the data from sessionStorage
    candidates = {
        "36": {
            "project_name_abbreviation": "ANI",
            "traits": [
                {"name": "Self-Leadership", "score": 79, "trait_id": "300b"},
                {"name": "Resilience",       "score": 71, "trait_id": "294b"},
                {"name": "Empathy",          "score": 53, "trait_id": "143b"},
            ]
        },
        "84": {
            "project_name_abbreviation": "CIA",
            "traits": [
                {"name": "Efficacy",          "score": 89, "trait_id": "215f"},
                {"name": "Resilience",        "score": 83, "trait_id": "100f"},
                {"name": "Empathy",           "score": 53, "trait_id": "143b"},
            ]
        }
    }

    for cand_id, report in candidates.items():
        proj = report["project_name_abbreviation"]
        print(f"\n===== Candidate {cand_id} | Project: {proj} =====")
        
        for trait in report["traits"]:
            name = trait["name"]
            score = trait["score"]
            api_tid = trait["trait_id"]
            
            # Step 1: ID match
            cur.execute(
                "SELECT trait_id, name_en, name_zh FROM trait_definitions WHERE trait_id = ?",
                (f"{proj}_{api_tid}",)
            )
            row = cur.fetchone()
            if row:
                print(f"  [OK] ID match '{proj}_{api_tid}' -> {dict(row)}")
                db_tid = row["trait_id"]
            else:
                print(f"  [--] ID match '{proj}_{api_tid}' -> NOT FOUND")
                
                # Step 2: name_en fallback
                cur.execute(
                    "SELECT trait_id, name_en, name_zh FROM trait_definitions WHERE trim(lower(name_en)) = trim(lower(?)) AND trait_id LIKE ?",
                    (name, f"{proj}_%")
                )
                row = cur.fetchone()
                if row:
                    print(f"  [OK] Name fallback '{name}' in {proj} -> {dict(row)}")
                    db_tid = row["trait_id"]
                else:
                    print(f"  [!!] Name fallback '{name}' in {proj} -> NOT FOUND => TRAIT SKIPPED")
                    db_tid = None

            # Step 3: Band match
            if db_tid:
                cur.execute(
                    "SELECT band, min_score, max_score, semantic_label FROM trait_bands WHERE trait_id = ? AND min_score <= ? AND max_score >= ?",
                    (db_tid, score, score)
                )
                band_row = cur.fetchone()
                if band_row:
                    print(f"       Band: {dict(band_row)}")
                else:
                    print(f"       Band: NOT FOUND for score {score}")

    conn.close()

if __name__ == "__main__":
    full_trace()
