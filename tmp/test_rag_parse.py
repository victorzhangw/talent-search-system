
import json
import sys
import os

sys.path.append(r"d:\python\AI-Character-Chatbot")

def simulate():
    candidates_info = [
        {"candidate_id": 84, "name": "Teacher Liu"},
        {"candidate_id": 36, "name": "Julie"}
    ]
    candidate_ids = [36, 84]
    
    # user provided dict
    trait_reports = {
        "36": {
            "assessment_date": "N/A", "assessment_id": 36, "project_name_abbreviation": "ANI",
            "traits": [{"band": "", "name": "Self-Leadership", "score": 79.0, "trait_id": "300b"}]
        },
        "84": {
            "assessment_date": "N/A", "assessment_id": 88, "project_name_abbreviation": "CIA",
            "traits": [{"band": "", "name": "Efficacy", "score": 89.0, "trait_id": "215f"}]
        }
    }
    
    target_candidates_basic = []
    def to_str(v): return str(v) if v is not None else ""
    target_ids_str = set(map(to_str, candidate_ids))
    
    for c in candidates_info:
        cid = to_str(c.get('candidate_id'))
        if cid in target_ids_str:
            target_candidates_basic.append(c)
            
    final_candidates_data = []
    for cand in target_candidates_basic:
        cand_id = str(cand.get('candidate_id'))
        merged = cand.copy()
        print(f"Checking {cand_id}...")
        
        if cand_id in trait_reports:
            report = trait_reports[cand_id]
            print(f"Found trait report for {cand_id}: type abbreviation = {report.get('project_name_abbreviation')}")
            
            trait_results = {}
            for trait in report.get('traits', []):
                trait_name = trait.get('name', 'Unknown')
                trait_results[trait_name] = {
                    'score': trait.get('score', 0),
                    'band': trait.get('band', ''),
                    'trait_id': trait.get('trait_id'),
                    'chinese_name': trait_name
                }
            
            merged['assessment'] = {
                'assessment_id': report.get('assessment_id'),
                'trait_results': trait_results,
                'project_name_abbreviation': report.get('project_name_abbreviation', 'CIA'),
                'completion_time': report.get('assessment_date', 'N/A')
            }
        else:
            print(f"Missing {cand_id} in trait_reports")
            
        final_candidates_data.append(merged)
        
    print(json.dumps(final_candidates_data, indent=2))

simulate()
