import sys
import os

# Setup Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.rag_engine import RAGService
from services.integration_mock import MockIntegrationService

# Mock Config
mock_config = {
    'DEEPSEEK_API_KEY': 'test',
    'DEEPSEEK_API_BASE': 'test'
}

# Override integration to prevent real API calls needed
class DirectVerifiedRAG(RAGService):
    def __init__(self):
        self.integration_service = MockIntegrationService()
        self.client = None # Don't need real LLM client for this test

    def _call_llm(self, sys_prompt, query, uc_id, session_id):
        # Just print the prompt directly for verification
        print("Verified Prompt Content:")
        print(sys_prompt)
        return None, uc_id

def main():
    rag = DirectVerifiedRAG()
    
    # Simulate a query that triggers UC-CMP-01
    query = "比較這兩位候選人A和B"
    mock_candidates = ["cand_1", "cand_2"]
    
    # Force the logic (simulate engine flow mostly)
    # We just want to test _assemble_prompt logic really
    # But let's user _assemble_prompt directly if we can access logic
    
    # 1. Get Use Case Config
    uc_id, uc_config = rag._get_use_case(query)
    print(f"Detected Use Case: {uc_id}")
    
    # 2. Mock Context
    rag_context = {
        'enterprise_context': "Enterprise Info...",
        'base_analysis': "Base Analysis Data...",
        'interactions': "",
        'constraints': "- Do X\n- Dont Y"
    }
    
    # 3. Assemble
    prompt = rag._assemble_prompt(uc_config, rag_context)
    print("\n" + "="*20 + " GENERATED PROMPT " + "="*20)
    print(prompt)
    print("="*60)

if __name__ == "__main__":
    main()
