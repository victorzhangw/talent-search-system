
import os
import sys

# Setup environment to load the app correctly
sys.path.append(r"d:\python\AI-Character-Chatbot")

from BackEnd.api_v2.database import init_db
from BackEnd.api_v2.services.context_builder import ContextBuilder
from flask import Flask

def run_test():
    app = Flask(__name__)
    app.config['DATABASE_URI'] = "sqlite:///d:/python/AI-Character-Chatbot/BackEnd/api_v2/app.db"
    
    with app.app_context():
        init_db(app)
        cb = ContextBuilder({})
        
        # Simulate ANI report
        cand = {
            "candidate_id": 36,
            "name": "Julie",
            "position": "NA",
            "assessment": {
                "assessment_id": 36,
                "project_name_abbreviation": "ANI",
                "trait_results": {
                    "Self-Leadership": {
                        "score": 79,
                        "band": "", 
                        "trait_id": "300b",
                        "chinese_name": "Self-Leadership"
                    }
                }
            }
        }
        
        print("Testing ANI extraction:")
        import sqlalchemy as sa
        # Check trace
        results = cand['assessment']['trait_results']
        from BackEnd.api_v2.database import db_session, TraitDefinition, TraitBand
        
        for name, res in results.items():
            display_name = res.get('chinese_name')
            api_tid = res.get('trait_id')
            project_abbrev = "ANI"
            
            # Step 1: ID Match
            trait_def = db_session.query(TraitDefinition).filter(
                TraitDefinition.trait_id == f"{project_abbrev}_{api_tid}"
            ).first()
            if trait_def:
                print(f"ID Match yes: {trait_def.trait_id}")
            else:
                print(f"ID Match failed for {project_abbrev}_{api_tid}")
            
            # Step 2: Fallback Match
            trait_def = db_session.query(TraitDefinition).filter(
                sa.func.trim(sa.func.lower(TraitDefinition.name_en)) == sa.func.trim(sa.func.lower(display_name)),
                TraitDefinition.trait_id.like(f"{project_abbrev}_%")
            ).first()
            
            if trait_def:
                print(f"Fallback Match yes: {trait_def.trait_id}")
                
            # Score
            score = res.get('score')
            print(f"Score: {score}")
            
            band_row = db_session.query(TraitBand).filter(
                TraitBand.trait_id == trait_def.trait_id,
                TraitBand.min_score <= score,
                TraitBand.max_score >= score
            ).first()
            
            if band_row:
                print(f"Band Match yes: {band_row.band} ({band_row.min_score}-{band_row.max_score})")

        print("\nFull pipeline result:")
        res = cb.build({}, [cand])
        print(res['base_analysis'])

if __name__ == "__main__":
    run_test()
