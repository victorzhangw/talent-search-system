import json
import os
import openai
from typing import List, Dict, Any, Optional
from flask import current_app
from .integration_base import IntegrationServiceInterface
from .integration_mock import MockIntegrationService
from .integration_real import RealIntegrationService
from .context_builder import ContextBuilder 
from utils.token_generator import generate_upstream_token

class RAGService:
    def __init__(self):
        # 1. Load Use Cases Config
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'use_cases.json')
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.use_cases = json.load(f)
        
        # 2. Setup Integration Service
        mode = current_app.config.get('INTEGRATION_MODE', 'MOCK')
        if mode == 'REAL':
            self.integration_service = RealIntegrationService()
        else:
            self.integration_service = MockIntegrationService()
            
        # 3. Setup LLM Client (DeepSeek / MockConfig)
        # HARDCODED FOR VERIFICATION
        key = "sk-8377e508025f417eaa201aa714eabb0f"
        base = "https://api.deepseek.com"
        print(f"[RAG] HARDCODED INIT - Base: {base}, Key: {key[:5]}...")
        
        self.client = openai.OpenAI(
            api_key=key,
            base_url=base
        )

        # 4. In-Memory Cache (Simple Dict for MVP)
        # Structure: { key: { 'data': context_data, 'timestamp': time } }
        self._context_cache = {}
        self.CACHE_TTL = 300 # 5 minutes

    def _get_use_case(self, query: str) -> Dict[str, Any]:
        """ Hybrid Intent Router """
        for uc_id, uc_data in self.use_cases.items():
            for keyword in uc_data.get('keywords', []):
                if keyword in query:
                    return uc_id, uc_data
        return "UC-GENERAL", self.use_cases["UC-GENERAL"]

    def _get_cached_data(self, key):
        import time
        if key in self._context_cache:
            entry = self._context_cache[key]
            if time.time() - entry['timestamp'] < self.CACHE_TTL:
                return entry['data']
            else:
                del self._context_cache[key] # Expired
        return None

    def _cache_data(self, key, data):
        import time
        self._context_cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

    def generate_response(self, query: str, candidate_ids: List[str], session_id: str):
        """
        Orchestrates the Full RAG Flow:
        Token -> Data Fetch (Cache/API) -> Context -> LLM
        """
        
        # Cache Key Strategy: Session ID + Candidate IDs hash
        # This ensures isolation per session, while supporting re-fetch if candidates change
        # For MVP: Simple string key
        cand_key = "-".join(sorted(map(str, candidate_ids)))
        cache_key = f"{session_id}::{cand_key}"
        
        # 0. Check Cache
        cached_context_data = self._get_cached_data(cache_key)
        
        if cached_context_data:
            print(f"[RAG] Cache HIT for key: {cache_key}")
            enterprise_data = cached_context_data['enterprise_data']
            final_candidates_data = cached_context_data['final_candidates_data']
        else:
            print(f"[RAG] Cache MISS for key: {cache_key}. Fetching upstream...")
            # 1. Generate Fresh Token for Upstream
            user_email = "eva@wepredict.io" 
            upstream_token = generate_upstream_token(user_email)
            
            # 2. Fetch Data (Parallelizable, but sync for now)
            print(f"[RAG] Orchestrating Data Fetch for {len(candidate_ids)} candidates...")
            
            # A. Enterprise Context
            enterprise_data = {}
            if isinstance(self.integration_service, RealIntegrationService):
                enterprise_data = self.integration_service.resolve_enterprise(upstream_token) or {}
                print(f"[RAG] Enterprise: {enterprise_data.get('enterprise_name')}")
            
            # B. Candidates Basic Info
            all_candidates = self.integration_service.get_candidates(upstream_token)
            target_candidates_basic = [c for c in all_candidates if c['candidate_id'] in candidate_ids]
            
            # C. Detailed Assessments (Batch)
            assessment_ids = []
            for cand in target_candidates_basic:
                # Check various locations for assessment_id
                lat = cand.get('latest_assessment')
                if lat and isinstance(lat, dict) and 'assessment_id' in lat:
                    assessment_ids.append(lat['assessment_id'])
                elif cand.get('assessment_id'):
                    assessment_ids.append(cand.get('assessment_id'))
            
            assessments_list = []
            if assessment_ids and isinstance(self.integration_service, RealIntegrationService):
                try:
                    assessments_list = self.integration_service.get_assessments(upstream_token, assessment_ids)
                    print(f"[RAG] Fetched {len(assessments_list)} assessments.")
                except Exception as e:
                    print(f"[RAG] Assessments Fetch Failed: {e}")
            
            # D. Merge Data
            final_candidates_data = []
            for cand in target_candidates_basic:
                my_asmt_id = cand.get('latest_assessment', {}).get('assessment_id')
                
                # Fix: Cast to string for comparison to avoid Int vs Str mismatch
                my_asmt_data = next((a for a in assessments_list if str(a.get('assessment_id')) == str(my_asmt_id)), None)
                
                merged = cand.copy()
                if my_asmt_data:
                    merged['assessment'] = my_asmt_data.get('assessment', {}) 
                
                final_candidates_data.append(merged)
            
            # Save to Cache
            self._cache_data(cache_key, {
                'enterprise_data': enterprise_data,
                'final_candidates_data': final_candidates_data
            })

        # 3. Intent Routing
        uc_id, uc_config = self._get_use_case(query)
        print(f"[RAG] Use Case: {uc_id}")

        # 4. Build Context
        builder = ContextBuilder(uc_config)
        rag_context = builder.build(enterprise_data, final_candidates_data)

        # 5. Assemble System Prompt
        sys_prompt = self._assemble_prompt(uc_config, rag_context)
        
        # 6. Call LLM
        return self._call_llm(sys_prompt, query, uc_id, session_id)

    def _assemble_prompt(self, uc_config, rag_context):
        # Retrieve answer guidance safely, default to empty string if missing
        ans_guide = uc_config.get('answer_guidence', '')
        
        return f"""
你是一個專業的人才測評顧問助手。
{rag_context['enterprise_context']}

【Strict Context Constraint】
1. 回答必須完全基於上方提供的【基礎特質分析資料】。
2. 禁止捏造報告中不存在的特質分數。
3. 若使用者詢問職位適配性，請引用具體的特質分數作為證據。即使使用者切換話題，此規則依然適用。
4. 請務必使用候選人的「真實姓名」進行稱呼（例如 "Evagelion", "Devin"），嚴禁使用 "候選人A"、"候選人B" 等代稱。

【核心指導原則】
{ans_guide}

【回答風格與模式】
模式: {uc_config['prompt_config']['style_ref']}
風險提示:
{chr(10).join(['- '+n for n in uc_config['prompt_config']['risk_notes']])}

【基礎特質分析資料】 (Sheet 02 - Base Semantics)
{rag_context['base_analysis']}

【特質交互作用加強分析】 (Sheet 08 - Enhanced Context)
{rag_context['interactions'] if rag_context['interactions'] else "(無顯著交互作用)"}

【AI 回答約束條件】 (Do/Dont)
{rag_context['constraints']}
"""

    def _log_prompt(self, session_id, uc_id, sys_prompt, user_query):
        """ Log the prompt to a file for audit/debugging """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, 'prompts.log')
        
        entry = f"""
{'='*60}
TIME: {timestamp}
SESSION: {session_id} | USE_CASE: {uc_id}
{'='*60}
[SYSTEM PROMPT]
{sys_prompt}

[USER QUERY]
{user_query}
{'='*60}
"""
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            print(f"[Log] Failed to write prompt log: {e}")

    def _call_llm(self, sys_prompt, query, uc_id, session_id="unknown"):
        # Log the prompt before calling
        self._log_prompt(session_id, uc_id, sys_prompt, query)
        
        print(f"--- DEBUG RAG SYSTEM PROMPT ---\n{sys_prompt}\n-------------------------")
        
        messages = [
            {"role": "system", "content": sys_prompt.strip()},
            {"role": "user", "content": query}
        ]

        try:
            print(f"[LLM] Calling DeepSeek API with model 'deepseek-chat'...")
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True
            )
            return response, uc_id
        except Exception as e:
            print(f"LLM Call Failed: {e}")
            return self._mock_stream_fallback(), uc_id

    def _mock_stream_fallback(self):
        class MockChunk: 
            def __init__(self, content):
                self.choices = [type('obj', (object,), {'delta': type('obj', (object,), {'content': content})})]
        
        def generator():
            yield MockChunk("注意：由於 LLM 連線失敗 (或 Key 設定為 Mock)，以下為模擬回應。\n\n")
            yield MockChunk("根據系統檢索到的企業與候選人資料，我已準備好回答您的問題。\n")
            yield MockChunk("請檢查後端 Console Log 以確認 RAG Context 是否組裝正確。")
        return generator()
