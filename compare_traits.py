
import re
import os

def extract_traits_from_sql(file_path):
    trait_ids = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for INSERT INTO trait_definitions ("trait_id", ... ) VALUES ('ID', ...
            # Regex to capture the first value in the values tuple
            matches = re.findall(r"INSERT INTO trait_definitions.*VALUES\s*\(\s*'([^']+)'.*", content)
            for match in matches:
                trait_ids.add(match)
    except Exception as e:
        print(f"Error reading SQL file: {e}")
    return trait_ids


def extract_traits_from_md(file_path):
    trait_ids = set()
    in_trait_table = False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "Sheet: 02_特質語意Bands_TraitSemanticBands" in line:
                    in_trait_table = True
                    continue
                
                # Stop if we hit the next sheet
                if in_trait_table and line.startswith("## Sheet"):
                    break

                if in_trait_table and line.startswith("|"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) > 1:
                        tid = parts[1]
                        # Use regex to validate ID format (e.g., ANI_01, CIA_36)
                        if re.match(r"^[A-Z]{3}_\d{2}$", tid):
                             trait_ids.add(tid)

                
    except Exception as e:
        print(f"Error reading MD file: {e}")
    return trait_ids

def main():
    base_dir = r"d:\python\AI-Character-Chatbot"
    sql_path = os.path.join(base_dir, "migration", "02_seed_data.sql")
    md_path = os.path.join(base_dir, "Reference-Docs", "Extracted", "Traitty_RAG_SpeC_v3.xlsx.md")

    print(f"Reading SQL file: {sql_path}")
    sql_traits = extract_traits_from_sql(sql_path)
    print(f"Found {len(sql_traits)} traits in SQL.")

    print(f"Reading MD file: {md_path}")
    md_traits = extract_traits_from_md(md_path)
    print(f"Found {len(md_traits)} traits in MD.")

    only_in_sql = sql_traits - md_traits
    only_in_md = md_traits - sql_traits

    if not only_in_sql and not only_in_md:
        print("SUCCESS: Trait IDs match exactly between SQL and MD.")
    else:
        if only_in_sql:
            print(f"Traits in SQL but not in MD ({len(only_in_sql)}):")
            for t in sorted(only_in_sql):
                print(f"  - {t}")
        
        if only_in_md:
            print(f"Traits in MD but not in SQL ({len(only_in_md)}):")
            for t in sorted(only_in_md):
                print(f"  - {t}")

if __name__ == "__main__":
    main()
