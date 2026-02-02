import os
import re
import json
import argparse

def clean_sql_string(s):
    if not s:
        return ""
    return str(s).replace("'", "''")

def parse_markdown_table(lines):
    """
    Parses a markdown table from a list of lines.
    Returns a list of dictionaries where keys are headers.
    """
    header_line = None
    headers = []
    data = []
    
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
            
        if not header_line:
            header_line = line
            # Extract headers, assuming simpler markdown table structure
            headers = [h.strip() for h in line.split('|')[1:-1]]
            continue
            
        if '---' in line:
            continue
            
        # Data row
        cols = [c.strip() for c in line.split('|')[1:-1]]
        
        # Handle cases where cells might have escaped pipes or are shorter/longer
        # This is a basic split; for robustness with escaped pipes, we might need more complex logic.
        # But for this known spec file, simple split usually suffices or we align with expected len.
        
        if len(cols) != len(headers):
            # Try to handle potential mismatched columns if possible, or just pad/truncate
            # For now, we'll pad with empty strings if short
            if len(cols) < len(headers):
                cols += [''] * (len(headers) - len(cols))
            else:
                cols = cols[:len(headers)]
        
        row_dict = dict(zip(headers, cols))
        data.append(row_dict)
        
    return data

def extract_sheet_content(content, sheet_name_part):
    """
    Extracts the lines belonging to a specific sheet section.
    """
    lines = content.splitlines()
    extraction = []
    in_sheet = False
    
    for line in lines:
        if line.startswith('## Sheet:') and sheet_name_part in line:
            in_sheet = True
            continue
        elif line.startswith('## Sheet:') and in_sheet:
            break
            
        if in_sheet:
            extraction.append(line)
            
    return extraction

def clean_sql_string(s):
    if s is None:
        return ""
    # Escape single quotes for SQL
    return s.replace("'", "''")

def main():
    parser = argparse.ArgumentParser(description="Generate SQL seed data from Markdown spec.")
    parser.add_argument("--input", default=r"d:\python\AI-Character-Chatbot\Reference-Docs\Extracted\Traitty_RAG_SpeC_v3.xlsx.md", help="Path to input Markdown file")
    parser.add_argument("--output", default=r"d:\python\AI-Character-Chatbot\migration\02_seed_data.sql", help="Path to output SQL file")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file definition not found at {args.input}")
        return

    print(f"Reading from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- Sheet 02: Definitions and Bands ---
    print("Parsing Sheet 02 (Definitions & Bands)...")
    sheet02_lines = extract_sheet_content(content, "02")
    sheet02_data = parse_markdown_table(sheet02_lines)
    
    trait_definitions = {} # stored by trait_id to ensure uniqueness
    trait_bands = []

    # Map column headers from Markdown to what we expect
    # Based on verified inspection:
    # 0: trait_id | 1: trait_name_zh | 2: trait_name_en | 3: dimension_group | 4: definition ...
    # 6: band | 8: semantic_label | 9: semantic_description | 10: management_focus
    # 13: report_wording_zh | 14: report_wording_friendly | 15: ai_do | 16: ai_dont
    
    # Since headers might be slightly different in text, we'll try to map by index or known names.
    # The 'parse_markdown_table' returns dict with keys as they appear in the header line.
    # Let's verify header names from the file view:
    # trait_id, trait_name_zh, trait_name_en, dimension_group, definition, band, semantic_label, semantic_description, management_focus, report_wording_zh, report_wording_friendly, ai_do, ai_dont
    
    for row in sheet02_data:
        t_id = row.get('trait_id')
        if not t_id or t_id == '特質編號，向量庫關鍵索引': # Skip description row
            continue
            
        # Collect Definition
        if t_id not in trait_definitions:
            trait_definitions[t_id] = {
                'trait_id': t_id,
                'name_zh': row.get('trait_name_zh', ''),
                'name_en': row.get('trait_name_en', ''),
                'dimension': row.get('dimension_group', 'nan'),
                'definition': row.get('definition', '')
            }
        
        # Collect Band
        band = row.get('band')
        if band:
            # Parse scores from 'band_range' if needed, mostly fixed A(75-100), B(50-74), C(0-49)
            # Spec has 'band_range' column e.g. "高分（約75–100）"
            # We can infer or hardcode based on A/B/C for now as in existing seed, or parse.
            min_s, max_s = 0, 0
            if band.startswith('A'): min_s, max_s = 75, 100
            elif band.startswith('B'): min_s, max_s = 50, 74
            elif band.startswith('C'): min_s, max_s = 0, 49
            
            # Trait Project
            t_project = t_id[:3]
            
            # AI Guidance JSON
            ai_data = {
                "do": row.get('ai_do', ''),
                "dont": row.get('ai_dont', '')
            }
            
            # V4 New Columns
            usage_note = row.get('usage_note', '')
            hidden_anchor = row.get('hidden_anchor', '')
            trait_interaction_guide = row.get('trait_interaction_guide', '')
            
            trait_bands.append({
                'trait_id': t_id,
                'trait_project': t_project,
                'band': band,
                'min': min_s,
                'max': max_s,
                'label': row.get('semantic_label', ''),
                'desc': row.get('semantic_description', ''),
                'mgt_focus': row.get('management_focus', ''),
                'report': row.get('report_wording_zh', ''),
                'report_friendly': row.get('report_wording_friendly', ''),
                'ai_guidance': json.dumps(ai_data, ensure_ascii=False),
                'usage_note': usage_note,
                'hidden_anchor': hidden_anchor,
                'trait_interaction_guide': trait_interaction_guide
            })

    # --- Sheet 08: Interactions ---
    print("Parsing Sheet 08 (Interactions)...")
    sheet08_lines = extract_sheet_content(content, "08")
    sheet08_data = parse_markdown_table(sheet08_lines)
    
    interactions = []
    
    # Sheet 08 Headers: trait_id, trait_name_zh, band, interaction_json, interaction_narrative
    for row in sheet08_data:
        p_id = row.get('trait_id')
        if not p_id or p_id == 'None': continue
        
        p_band_raw = row.get('band', '') # e.g., "A (高)"
        # Extract just "A" or "B" or "C"
        match = re.search(r'([ABC])', p_band_raw)
        p_band = match.group(1) if match else ''
        
        if not p_band: continue

        narrative = row.get('interaction_narrative', '')
        if not narrative:
            narrative = row.get('interaction_narrative (AI 解說語意)', '')

        
        # Parse interaction_json to get trigger
        # e.g., {"trigger":[{"id":"CIA_02","score":"high"}]} OR {"trigger":[{"id":"CIA_01","band":"A"}]}
        int_json_str = row.get('interaction_json (系統判斷)', '')
        if not int_json_str:
            # Fallback check for simple header name
            int_json_str = row.get('interaction_json', '')

        t_id = None
        t_band = None
        
        try:
            if int_json_str:
                data = json.loads(int_json_str)
                triggers = data.get('trigger', [])
                if triggers:
                    t_obj = triggers[0]
                    t_id = t_obj.get('id')
                    # 'score' might be used in v3 spec instead of 'band' sometimes, need to map
                    # v3 spec usually uses 'band': "A". 
                    # If 'score' is present: "high"->A, "low"->C?
                    # Let's look at the sample data viewed earlier:
                    # {"trigger":[{"id":"CIA_02","score":"high"}]} -> Narrative says "CIA_02 ... 高分聯動"
                    # {"trigger":[{"id":"CIA_12","band":"C"}]} -> Narrative says "C聯動"
                    
                    val = t_obj.get('band')
                    score_val = t_obj.get('score')
                    
                    if val:
                        t_band = val
                    elif score_val:
                        if score_val.lower() == 'high': t_band = 'A'
                        elif score_val.lower() == 'low': t_band = 'C'
                        # What about B? usually interactions are A/C extremes.
        except Exception as e:
            print(f"Warning: Failed to parse JSON for {p_id} {p_band}: {e}")
            print(f"Raw string: {repr(int_json_str)}")
            
        if p_id and p_band and t_id and t_band:
            interactions.append({
                'primary_trait_id': p_id,
                'primary_band': p_band,
                'trigger_trait_id': t_id,
                'trigger_band': t_band,
                'narrative': narrative
            })

    # --- Write SQL ---
    print(f"Generating SQL to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(f"-- Generated seed data for Traitty\n")
        f.write(f"-- Source: {os.path.basename(args.input)}\n\n")
        
        # Admin User (Keep existing logic or just comment out if not needed every time, 
        # but seed usually implies init. We used upsert for data, maybe keep admin insert simple or Ignore)
        # Using ON CONFLICT DO NOTHING for admin
        f.write("-- Admin Users\n")
        f.write("INSERT INTO admin_users (username, password_hash) VALUES ('admin', '$argon2id$v=19$m=65536,t=3,p=4$0KRkQK2UpXoQqrTquT/kHw$ZNckKgPc9sipGbEgNQXg83kwblyWvI9S4C2NEOuV0gA') ON CONFLICT (username) DO NOTHING;\n\n")
        
        # Trait Definitions
        f.write("-- Trait Definitions\n")
        for tid, t in trait_definitions.items():
            sql = f"""INSERT INTO trait_definitions (trait_id, name_zh, name_en, dimension, definition) VALUES ('{t['trait_id']}', '{clean_sql_string(t['name_zh'])}', '{clean_sql_string(t['name_en'])}', '{clean_sql_string(t['dimension'])}', '{clean_sql_string(t['definition'])}') ON CONFLICT (trait_id) DO UPDATE SET name_zh = EXCLUDED.name_zh, name_en = EXCLUDED.name_en, dimension = EXCLUDED.dimension, definition = EXCLUDED.definition;\n"""
            f.write(sql)
        f.write("\n")
            
        # Trait Bands
        f.write("-- Trait Bands\n")
        for b in trait_bands:
            sql = f"""INSERT INTO trait_bands (trait_id, trait_project, band, min_score, max_score, semantic_label, description, management_focus, report_wording, report_wording_friendly, ai_guidance, usage_note, hidden_anchor, trait_interaction_guide) VALUES ('{b['trait_id']}', '{b['trait_project']}', '{b['band']}', {b['min']}, {b['max']}, '{clean_sql_string(b['label'])}', '{clean_sql_string(b['desc'])}', '{clean_sql_string(b['mgt_focus'])}', '{clean_sql_string(b['report'])}', '{clean_sql_string(b['report_friendly'])}', '{clean_sql_string(b['ai_guidance'])}', '{clean_sql_string(b['usage_note'])}', '{clean_sql_string(b['hidden_anchor'])}', '{clean_sql_string(b['trait_interaction_guide'])}') ON CONFLICT (trait_id, band) DO UPDATE SET trait_project = EXCLUDED.trait_project, min_score = EXCLUDED.min_score, max_score = EXCLUDED.max_score, semantic_label = EXCLUDED.semantic_label, description = EXCLUDED.description, management_focus = EXCLUDED.management_focus, report_wording = EXCLUDED.report_wording, report_wording_friendly = EXCLUDED.report_wording_friendly, ai_guidance = EXCLUDED.ai_guidance, usage_note = EXCLUDED.usage_note, hidden_anchor = EXCLUDED.hidden_anchor, trait_interaction_guide = EXCLUDED.trait_interaction_guide;\n"""
            f.write(sql)
        f.write("\n")

        # Trait Interactions
        f.write("-- Trait Interactions\n")
        for i in interactions:
            sql = f"""INSERT INTO trait_interactions (primary_trait_id, primary_band, trigger_trait_id, trigger_band, narrative) VALUES ('{i['primary_trait_id']}', '{i['primary_band']}', '{i['trigger_trait_id']}', '{i['trigger_band']}', '{clean_sql_string(i['narrative'])}') ON CONFLICT (primary_trait_id, primary_band, trigger_trait_id, trigger_band) DO UPDATE SET narrative = EXCLUDED.narrative;\n"""
            f.write(sql)
            
    print("Done.")

if __name__ == "__main__":
    main()
