import re
import json
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import Base, TraitDefinition, TraitBand, TraitInteraction

# Markdown file path
MARKDOWN_FILE = r"d:\python\AI-Character-Chatbot\Reference-Docs\Extracted\Traitty_RAG_SpeC_v3.xlsx.md"
DB_PATH = "sqlite:///d:/python/AI-Character-Chatbot/BackEnd/api_v2/app.db"

engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def parse_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by sheets
    sheets = content.split('## Sheet: ')
    
    trait_definitions = {} # id -> dict
    trait_bands = []
    trait_interactions = []

    for sheet in sheets:
        if sheet.startswith('02_特質語意Bands_TraitSemanticBands'):
            print("Parsing Sheet 02...")
            lines = sheet.strip().split('\n')
            # Skip header lines (usually first few lines till separators)
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('|:---'):
                    start_idx = i + 1
                    break
            
            for line in lines[start_idx:]:
                if not line.strip().startswith('|'): continue
                cols = [c.strip() for c in line.split('|')]
                if len(cols) < 5: continue
                
                # cols[0] is empty because split('|') on "| col1 |" gives ['', 'col1', '']
                # Index mapping based on table header
                # | trait_id | trait_name_zh | trait_name_en | dimension_group | definition | hidden_anchor | band | band_range | semantic_label | semantic_description | ...
                
                # Adjusting index because first elem is empty string
                trait_id = cols[1]
                if not trait_id or trait_id == '特質編號，向量庫關鍵索引': continue
                
                name_zh = cols[2]
                name_en = cols[3]
                dimension = cols[4]
                definition = cols[5]
                band = cols[7] # A/B/C
                # band_range = cols[8]
                semantic_label = cols[9]
                description = cols[10]
                management_focus = cols[11]
                # usage_note = cols[12]
                # interaction = cols[13]
                report = cols[14]
                # friendly = cols[15]
                ai_do = cols[16]
                ai_dont = cols[17]

                # Store Definition
                if trait_id not in trait_definitions:
                    trait_definitions[trait_id] = {
                        'trait_id': trait_id,
                        'name_zh': name_zh,
                        'name_en': name_en,
                        'dimension': dimension,
                        'definition': definition
                    }
                
                # Define Band Ranges
                min_s, max_s = 0, 100
                normalized_band = 'B'
                
                if 'A' in band or '高' in band:
                    normalized_band = 'A'
                    min_s, max_s = 75, 100
                elif 'B' in band or '中' in band:
                    normalized_band = 'B'
                    min_s, max_s = 50, 74
                elif 'C' in band or '低' in band:
                    normalized_band = 'C'
                    min_s, max_s = 0, 49

                # Store Band
                trait_bands.append({
                    'trait_id': trait_id,
                    'band': normalized_band,
                    'min_score': min_s,
                    'max_score': max_s,
                    'semantic_label': semantic_label,
                    'description': description,
                    'management_focus': management_focus,
                    'report_wording': report,
                    'ai_guidance': json.dumps({'do': ai_do, 'dont': ai_dont}, ensure_ascii=False)
                })

        elif sheet.startswith('08 interaction_narrative'):
            print("Parsing Sheet 08...")
            lines = sheet.strip().split('\n')
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('|:---'):
                    start_idx = i + 1
                    break
            
            for line in lines[start_idx:]:
                if not line.strip().startswith('|'): continue
                cols = [c.strip() for c in line.split('|')]
                if len(cols) < 5: continue
                
                # | trait_id | trait_name_zh | band | interaction_json | interaction_narrative |
                trait_id = cols[1]
                if not trait_id: continue
                
                primary_band = cols[3].split('(')[0].strip() # 'A (高)' -> 'A'
                
                interaction_json_str = cols[4]
                narrative = cols[5]
                
                try:
                    interaction_data = json.loads(interaction_json_str)
                    target_trigger = interaction_data['trigger'][0] # Assume list
                    trigger_id = target_trigger['id']
                    
                    # Normalized trigger band
                    trigger_val = target_trigger.get('score', target_trigger.get('band'))
                    trigger_band = 'A'
                    if trigger_val in ['high', 'A']:
                        trigger_band = 'A'
                    elif trigger_val in ['low', 'C']:
                        trigger_band = 'C'
                    elif trigger_val in ['mid', 'B']:
                        trigger_band = 'B'
                        
                    trait_interactions.append({
                        'primary_trait_id': trait_id,
                        'primary_band': primary_band,
                        'trigger_trait_id': trigger_id,
                        'trigger_band': trigger_band,
                        'narrative': narrative
                    })
                    
                except Exception as e:
                    print(f"Error parsing JSON in line: {line[:50]}... Error: {e}")

    return trait_definitions, trait_bands, trait_interactions

def seed_db():
    print("Starting DB Seed...")
    trait_defs, bands, interactions = parse_markdown(MARKDOWN_FILE)
    
    session = SessionLocal()
    try:
        # Clear existing
        session.query(TraitInteraction).delete()
        session.query(TraitBand).delete()
        session.query(TraitDefinition).delete()
        
        # Insert Defs
        print(f"Inserting {len(trait_defs)} definitions...")
        for t in trait_defs.values():
            session.add(TraitDefinition(**t))
            
        # Insert Bands
        print(f"Inserting {len(bands)} bands...")
        for b in bands:
            # Simple min/max mapping if needed, skipping for now
            session.add(TraitBand(**b))
            
        # Insert Interactions
        print(f"Inserting {len(interactions)} interactions...")
        for i in interactions:
            session.add(TraitInteraction(**i))
            
        session.commit()
        print("Seeding Complete.")
    except Exception as e:
        session.rollback()
        print(f"Seeding Failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    seed_db()
