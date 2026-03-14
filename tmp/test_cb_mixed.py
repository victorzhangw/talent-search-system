
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
        cb = ContextBuilder({"prompt_config": {}})
        
        # Test 1: ANI only
        cand_ani = {
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
        
        # Test 2: CIA only
        cand_cia = {
            "candidate_id": 84,
            "name": "Teacher Liu",
            "position": "NA",
            "assessment": {
                "assessment_id": 88,
                "project_name_abbreviation": "CIA",
                "trait_results": {
                    "Efficacy": {
                        "score": 89,
                        "band": "", 
                        "trait_id": "215f",
                        "chinese_name": "Efficacy"
                    }
                }
            }
        }
        
        print("\n--- Test ANI only ---")
        res1 = cb.build({}, [cand_ani])
        print(res1['base_analysis'])
        
        print("\n--- Test CIA only ---")
        res2 = cb.build({}, [cand_cia])
        print(res2['base_analysis'])

        print("\n--- Test BOTH ---")
        res3 = cb.build({}, [cand_ani, cand_cia])
        print(res3['base_analysis'])

if __name__ == "__main__":
    run_test()
