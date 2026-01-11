import sys
import os
import json
from flask import Flask

# Setup Environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from BackEnd.api_v2.database import init_db, db_session, TraitDefinition
from BackEnd.api_v2.services.context_builder import ContextBuilder

app = Flask(__name__)
app.config['DATABASE_URI'] = f"sqlite:///{os.path.abspath('BackEnd/api_v2/instance/app.db')}"
init_db(app)

def verify_logic():
    with app.app_context():
        # 1. Mock Data matching User Sample
        mock_results = {
            "143b": {
                "trait_id": "143b", # This ID implies it might differ from DB if DB uses ANI_xx
                "score": 61,
                "headsupflag": 0,
                "chinese_name": "Empathy" # English Name
            },
            "298b": {
                "trait_id": "298b",
                "score": 84,
                "headsupflag": 0,
                "chinese_name": "Analytical Thinking"
            }
        }
        
        mock_candidate = {
            "name": "Test Candidate",
            "position": "Tester",
            "assessment": {
                "trait_results": mock_results
            }
        }
        
        # 2. Run Context Builder
        # We need a dummy Use Case config
        uc_config = {"prompt_config": {"style_ref": "TEST"}}
        builder = ContextBuilder(uc_config)
        
        print("--- Running Context Builder Build ---")
        try:
            # We pass empty enterprise data, just testing candidate parsing
            context = builder.build({}, [mock_candidate])
            print("--- Build Success ---")
            print("Base Analysis Output:")
            print(context['base_analysis'])
            
            # 3. Verification
            # Check if "Analytical Thinking" mapped to "ANI_01" (or whatever is in DB)
            # We expect to see the Trait Name and ID in the output
            if "Analytical Thinking" in context['base_analysis']:
                 print("PASS: Analytical Thinking found.")
            else:
                 print("FAIL: Analytical Thinking NOT found.")
                 
            # Check if Empathy found
            if "Empathy" in context['base_analysis']:
                print("PASS: Empathy found.")
            
        except Exception as e:
            print(f"FAIL: Exception during build: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_logic()
