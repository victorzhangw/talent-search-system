
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
        
        # Candidate 1: Julie (ANI)
        cand_ani = {
            "candidate_id": 36,
            "name": "Julie",
            "assessment": {
                "assessment_id": 36,
                "project_name_abbreviation": "ANI",
                "trait_results": {
                    "Self-Leadership": {"score": 79, "trait_id": "300b", "chinese_name": "Self-Leadership"}
                }
            }
        }
        
        # Candidate 2: Teacher Liu (CIA)
        cand_cia = {
            "candidate_id": 84,
            "name": "Teacher Liu",
            "assessment": {
                "assessment_id": 88,
                "project_name_abbreviation": "CIA",
                "trait_results": {
                    "Efficacy": {"score": 89, "trait_id": "215f", "chinese_name": "Efficacy"}
                }
            }
        }
        
        print("\n--- Running build with BOTH ---")
        final_data = [cand_ani, cand_cia]
        res = cb.build({}, final_data)
        
        print("BASE ANALYSIS CONTENT:")
        print(res['base_analysis'])

if __name__ == "__main__":
    run_test()
