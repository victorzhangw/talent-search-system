
import sqlite3
import sys

def full_trace():
    db_path = r"d:\python\AI-Character-Chatbot\BackEnd\api_v2\app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    candidates = {
        "36": {
            "project_name_abbreviation": "ANI",
            "traits": [
                {"name": "Self-Leadership",  "score": 79, "trait_id": "300b"},
                {"name": "Resilience",       "score": 71, "trait_id": "294b"},
                {"name": "Empathy",          "score": 53, "trait_id": "143b"},
            ]
        },
        "84": {
            "project_name_abbreviation": "CIA",
            "traits": [
                {"name": "Efficacy",   "score": 89, "trait_id": "215f"},
                {"name": "Resilience", "score": 83, "trait_id": "100f"},
                {"name": "Empathy",    "score": 53, "trait_id": "143b"},
            ]
        }
    }

    results = []

    for cand_id, report in candidates.items():
        proj = report["project_name_abbreviation"]
        results.append(f"\n=== Candidate {cand_id} | Project: {proj} ===")
        
        for trait in report["traits"]:
            name   = trait["name"]
            score  = trait["score"]
            api_tid = trait["trait_id"]
            
            # Step 1: Exact ID match
            cur.execute("SELECT trait_id, name_en FROM trait_definitions WHERE trait_id=?", (f"{proj}_{api_tid}",))
            row = cur.fetchone()
            db_tid = None

            if row:
                db_tid = row["trait_id"]
                results.append(f"  [ID-OK]   '{proj}_{api_tid}' -> {row['trait_id']}")
            else:
                results.append(f"  [ID-MISS] '{proj}_{api_tid}' not found")
                
                # Step 2: Name fallback
                cur.execute(
                    "SELECT trait_id, name_en FROM trait_definitions WHERE trim(lower(name_en))=trim(lower(?)) AND trait_id LIKE ?",
                    (name, f"{proj}_%")
                )
                row2 = cur.fetchone()
                if row2:
                    db_tid = row2["trait_id"]
                    results.append(f"  [NM-OK]   '{name}' in {proj} -> {row2['trait_id']}")
                else:
                    results.append(f"  [NM-MISS] '{name}' in {proj} -> NOT FOUND, TRAIT SKIPPED!")

            # Step 3: Band
            if db_tid:
                cur.execute(
                    "SELECT band, min_score, max_score FROM trait_bands WHERE trait_id=? AND min_score<=? AND max_score>=?",
                    (db_tid, score, score)
                )
                band = cur.fetchone()
                if band:
                    results.append(f"  [BAND]    score={score} -> band={band['band']} ({band['min_score']}-{band['max_score']})")
                else:
                    results.append(f"  [BAND-X]  score={score} -> NO BAND FOUND for {db_tid}")

    conn.close()

    with open("tmp/trace_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    print("Done. See tmp/trace_result.txt")

if __name__ == "__main__":
    full_trace()
