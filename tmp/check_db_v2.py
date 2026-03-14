
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from BackEnd.api_v2.database import db_session, TraitDefinition
from sqlalchemy import func

def check_traits():
    print("Checking database traits...")
    count = db_session.query(TraitDefinition).count()
    print(f"Total traits in DB: {count}")
    
    prefixes = ["ANI", "CIA"]
    for p in prefixes:
        found = db_session.query(TraitDefinition).filter(TraitDefinition.trait_id.like(f"{p}_%")).count()
        print(f"Traits with prefix {p}_: {found}")
        
    # Check specific ID
    target = "ANI_300b"
    t = db_session.query(TraitDefinition).filter_by(trait_id=target).first()
    if t:
        print(f"✅ Found {target}: {t.name_en} / {t.name_zh}")
    else:
        # Check if it exists without prefix
        t2 = db_session.query(TraitDefinition).filter_by(trait_id="300b").first()
        if t2:
            print(f"❓ Found '300b' WITHOUT prefix: {t2.name_en}")
        else:
            print(f"❌ '{target}' and '300b' not found.")

if __name__ == "__main__":
    check_traits()
