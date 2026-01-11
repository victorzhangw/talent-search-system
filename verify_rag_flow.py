
import sys
import os
import traceback
import json

# Add local path to sys.path 
sys.path.append(os.path.join(os.getcwd(), 'BackEnd', 'api_v2'))

try:
    from app import create_app
    from services.rag_engine import RAGService
    from services.integration_mock import MockIntegrationService
    
    def test_rag_structure():
        print("Creating Flask App Context...")
        app = create_app()
        
        with app.app_context():
            print("Initializing RAG Service (Structure Test)...")
            rag = RAGService() 
            rag.integration_service = MockIntegrationService()
            
            query = "我想確認這位候選人，能勝任我們現在缺的BD業務嗎？"
            candidate_ids = ["cand_001"] 
            
            # 1. Fetch Data
            print("1. Fetching Candidate Data...")
            assessments = rag.integration_service.get_assessments("ACME-TW", candidate_ids)
            candidates = rag.integration_service.get_candidates("ACME-TW")
            target_candidates = []
            for res in assessments:
                cid = res['candidate_id']
                basic = next((c for c in candidates if c['candidate_id'] == cid), {})
                target_candidates.append({**basic, **res})
                
            # 2. Intent
            print("2. Identifying Intent...")
            uc_id, uc_config = rag._get_use_case(query)
            print(f"   > Matched: {uc_id} ({uc_config['description']})")
            print(f"   > Style Ref: {uc_config['prompt_config']['style_ref']}")
            
            # 3. Build Structured Context
            print("3. Building Structured Context...")
            rag_data = rag._build_context_structured(uc_config, target_candidates)
            
            print("\n" + "="*50)
            print("VERIFICATION OF PROMPT COMPONENTS")
            print("="*50)
            
            print("\n[PART A: Base Analysis & Semantics]")
            print(rag_data['base_analysis'][:500] + "..." if len(rag_data['base_analysis']) > 500 else rag_data['base_analysis'])
            
            print("\n[PART B: AI Constraints (Do/Dont)]")
            print(rag_data['constraints'][:500] + "..." if len(rag_data['constraints']) > 500 else rag_data['constraints'])
            
            print("\n[PART C: Interaction Narratives]")
            print(rag_data['interactions'][:500] + "..." if len(rag_data['interactions']) > 500 else rag_data['interactions'])
            
            print("\n" + "="*50)

    if __name__ == "__main__":
        test_rag_structure()

except Exception:
    traceback.print_exc()
