
import os
import sys

# Setup environment
sys.path.append(r"d:\python\AI-Character-Chatbot")

import BackEnd.api_v2.database.connection as conn_mod
# Mock get_db_url before anything else
conn_mod.get_db_url = lambda: "sqlite:///d:/python/AI-Character-Chatbot/BackEnd/api_v2/app.db"

from BackEnd.api_v2.database import init_db, db_session, TraitDefinition, TraitBand
from BackEnd.api_v2.services.context_builder import ContextBuilder
from flask import Flask

def run_test():
    app = Flask(__name__)
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
