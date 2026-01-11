
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'BackEnd', 'api_v2'))

from app import create_app
import database
from database import TraitBand, TraitDefinition

app = create_app()
with app.app_context():
    # Database is initialized in create_app
    print("Checking TraitDefinition count...")
    # Access via module to get updated reference
    session = database.db_session 
    
    count = session.query(TraitDefinition).count()
    print(f"Total Definitions: {count}")
    
    print("\nChecking TraitBand count...")
    b_count = session.query(TraitBand).count()
    print(f"Total Bands: {b_count}")
    
    print("\nChecking CIA_01...")
    defs = session.query(TraitDefinition).filter(TraitDefinition.trait_id.like("CIA%")).all()
    print(f"Found CIA traits: {[d.trait_id for d in defs]}")
    
    bands = session.query(TraitBand).filter_by(trait_id="CIA_01").all()
    for b in bands:
        print(f"  Band {b.band}: {b.min_score}-{b.max_score}")
