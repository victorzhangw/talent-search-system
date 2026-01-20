
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Adjust path to import backend modules if needed, or just use raw sql
# DB_URL = "postgresql://postgres:postgres@localhost:5432/ai_chatbot_v2"
# Using the values known: user=postgres, pass=postgres, db=ai_chatbot_v2

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_chatbot_v2"

def inspect_and_fix():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Connected to DB.")
        
        # 1. Inspect
        print("\n--- Inspecting first 5 rows of trait_bands ---")
        result = conn.execute(text("SELECT trait_id, band, ai_guidance FROM trait_bands LIMIT 5"))
        
        needs_fix = False
        
        for row in result:
            trait_id, band, guidance = row
            print(f"ID: {trait_id}, Band: {band}")
            print(f"Raw Guidance Type: {type(guidance)}")
            print(f"Raw Guidance Value: {guidance}")
            
            # Check if it looks like a double-encoded string
            # Example: '"{\"do\": ...}"' -> This is a string containing a JSON string
            # We want: '{"do": ...}' -> This is a JSON string (which SQLAlchemy/PG might assume is string, or JSONB if mapped)
            
            # Note: In the ContextBuilder error, it was 'str' object has no attribute 'get'.
            # This implies guidance is a STR, not a DICT.
            # If the column type is JSONB, SQLAlchemy usually returns a Dict.
            # If the column type is TEXT, SQLAlchemy returns a Str.
            
            # Let's check if the string content is itself a JSON string that evaluates to the real dict,
            # OR if it's a double-quoted string.
            
            if isinstance(guidance, str):
                # Try parsing
                try:
                    parsed = json.loads(guidance)
                    print(f"Parsed 1 level: type={type(parsed)}")
                    if isinstance(parsed, str):
                        print(f"  -> It was double encoded! Inner value: {parsed}")
                        needs_fix = True
                    elif isinstance(parsed, dict):
                         print("  -> Parsed into dict. This is correct for a String column containing JSON.")
                         # But wait, if ContextBuilder crashed with "str object has no attribute get",
                         # it means `_parse_json` returned a string.
                         # ContextBuilder._parse_json logic:
                         # if isinstance(content, dict): return content
                         # try: return json.loads(content) ...
                         
                         # If `guidance` (the content) is '"{\"a\":1}"', json.loads returns a string '{"a":1}'.
                         # Then '{"a":1}'.get('do') fails.
                         pass
                except Exception as e:
                    print(f"Parse error: {e}")
                    
        if needs_fix:
            print("\n--- ATTEMPTING FIX ---")
            # We want to unwrap the double encoding.
            # Update query: set ai_guidance = ai_guidance # But we need to parse it.
            # It's easier to do via python update.
            pass

def simple_fix():
    # If we confirmed it's double encoded, we can run a mass update.
    # Logic: Fetch all, if double encoded, update.
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        rows = session.execute(text("SELECT trait_id, band, ai_guidance FROM trait_bands")).fetchall()
        count = 0
        for row in rows:
            trait_id, band, guidance = row
            if not guidance: continue
            
            is_modified = False
            new_guidance = guidance
            
            # Check 1: Is it a string that looks like a JSON string?
            if isinstance(new_guidance, str):
                try:
                    # Parse once
                    first_pass = json.loads(new_guidance)
                    # Use case: guidance is '"{\"do\":...}"' -> first_pass is '{"do":...}' (str)
                    
                    if isinstance(first_pass, str):
                         # If parsing once results in a string that looks like json (starts with {), 
                         # then the original was double encoded.
                         if first_pass.strip().startswith('{'):
                             print(f"Fixing double encoding for {trait_id}-{band}")
                             new_guidance = first_pass
                             is_modified = True
                except:
                    pass
            
            if is_modified:
                # Update DB
                # Escaping single quotes in params is handled by bind params
                session.execute(
                    text("UPDATE trait_bands SET ai_guidance = :g WHERE trait_id = :t AND band = :b"),
                    {"g": new_guidance, "t": trait_id, "b": band}
                )
                count += 1
                
        session.commit()
        print(f"Fixed {count} rows.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    inspect_and_fix()
    simple_fix()
