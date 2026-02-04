import json
import os
import openai
from typing import List, Dict, Any, Optional
from flask import current_app
from .integration_base import IntegrationServiceInterface
from .integration_mock import MockIntegrationService
from .integration_real import RealIntegrationService
from .context_builder import ContextBuilder 
from ..utils.token_generator import generate_upstream_token

class RAGService:
    def __init__(self):
        # 1. Load Use Cases Config
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'use_cases.json')
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.use_cases = json.load(f)
        
        # 1.5 Load Mode Rules
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'mode_rules.json')
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.mode_rules = json.load(f)
        else:
             print("[RAG] Warning: mode_rules.json not found.")
             self.mode_rules = {}

        # 2. Setup Integration Service
        mode = current_app.config.get('INTEGRATION_MODE', 'MOCK')
        if mode == 'REAL':
            self.integration_service = RealIntegrationService()
        else:
            self.integration_service = MockIntegrationService()
            
        # 3. Setup LLM Client (DeepSeek / MockConfig)
        # 3. Setup LLM Client
        api_key = current_app.config.get('DEEPSEEK_API_KEY')
        api_base = current_app.config.get('DEEPSEEK_API_BASE')
        
        # Fallback: Retry loading .env if key is missing (Hotfix for loading issue)
        if not api_key:
             print("[RAG] WARNING: DEEPSEEK_API_KEY is None. Attempting to reload .env manually...")
             try:
                 from dotenv import load_dotenv
                 env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
                 load_dotenv(env_path, override=True)
                 api_key = os.getenv('DEEPSEEK_API_KEY')
             except Exception as e:
                 print(f"[RAG] .env reload failed: {e}")

        # Final Safety Check: Use dummy key to prevent crash, let call_llm handle authentication error
        if not api_key:
             print("[RAG] CRITICAL: Still no API KEY. Using dummy key to prevent startup crash.")
             api_key = "sk-dummy-key-for-init"

        print(f"[RAG] Init LLM - Base: {api_base}, Key: {api_key[:5]}...")
        
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=api_base
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

    def _determine_mode(self, query: str, input_mode: str) -> str:
        """
        Determines the routing mode based on input signal and semantic rules.
        """
        # 1. Force override from frontend (e.g. Quick Buttons)
        if input_mode == 'expert':
            return 'expert'
            
        # 2. Rule-Based Semantic Routing
        rules = self.mode_rules.get('expert_mode_rules', {})
        
        # Combine all keyword lists for checking
        all_expert_keywords = (
            rules.get('intent_keywords', []) + 
            rules.get('phrase_patterns', []) + 
            rules.get('context_keywords', [])
        )
        
        for kw in all_expert_keywords:
            if kw in query:
                print(f"[RAG] Router: Hit Expert Keyword '{kw}' -> Expert Mode")
                return 'expert'
                
        # 3. Default Fallback
        print(f"[RAG] Router: No Expert keywords found -> Explanation Mode")
        return 'explanation'
 
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

    def generate_response(self, query: str, candidate_ids: List[str], session_id: str, 
                         candidates_info: List[Dict] = None, trait_reports: Dict = None, mode: str = 'explanation'):
        """
        Orchestrates the Full RAG Flow:
        Token -> Data Fetch (Cache/API) -> Context -> LLM
        
        Args:
            query: User's question
            candidate_ids: List of candidate IDs
            session_id: Session identifier for caching
            candidates_info: Optional. Full candidate info from frontend (includes name, position, etc.)
            trait_reports: Optional. Trait reports from frontend Session Storage (keyed by candidate_id)
            mode: 'expert', 'explanation' (legacy), or 'auto' (new).
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
            # NEW: Prioritize frontend-provided candidate info
            target_candidates_basic = []
            
            if candidates_info:
                # Use frontend-provided data (preferred)
                print(f"[RAG] Using {len(candidates_info)} candidates from frontend")
                target_candidates_basic = candidates_info
                for c in target_candidates_basic:
                    print(f"[RAG-DEBUG] Frontend candidate: id={c.get('candidate_id')}, name='{c.get('name')}', position='{c.get('position')}'", flush=True)
            else:
                # Fallback: Fetch from API
                print(f"[RAG] No frontend candidate info. Fetching from API...")
                cand_resp = self.integration_service.get_candidates(upstream_token, limit=100)
                
                if isinstance(cand_resp, dict):
                    all_candidates = cand_resp.get('data', [])
                else:
                    all_candidates = cand_resp
                    
                def to_str(v): return str(v) if v is not None else ""
                target_ids_str = set(map(to_str, candidate_ids))
                
                for c in all_candidates:
                    cid = to_str(c.get('candidate_id'))
                    if cid in target_ids_str:
                        target_candidates_basic.append(c)
                        print(f"[RAG-DEBUG] Found candidate {cid}: name='{c.get('name')}', position='{c.get('position')}'", flush=True)

            # C. Detailed Assessments (Batch)
            # NEW: Check if trait_reports are provided from frontend
            if trait_reports:
                print(f"[RAG] ✅ Using trait reports from frontend for {len(trait_reports)} candidates")
                
                # Merge trait reports with candidate basic info
                final_candidates_data = []
                for cand in target_candidates_basic:
                    cand_id = str(cand.get('candidate_id'))
                    merged = cand.copy()
                    
                    # Get trait report from frontend data
                    if cand_id in trait_reports:
                        report = trait_reports[cand_id]
                        print(f"[RAG] Found trait report for candidate {cand_id}: {len(report.get('traits', []))} traits")
                        
                        # Convert frontend report format to expected format
                        # Frontend format: { assessment_id, traits: [...], assessment_date }
                        # Expected format: { assessment: { trait_results: {...} } }
                        
                        # Convert traits array to trait_results dict
                        trait_results = {}
                        for trait in report.get('traits', []):
                            # Use trait name as key (not ideal, but works for now)
                            # Better would be to use trait_id, but frontend doesn't have it
                            trait_name = trait.get('name', 'Unknown')
                            trait_results[trait_name] = {
                                'score': trait.get('score', 0),
                                'band': trait.get('band', ''),
                                'chinese_name': trait_name  # Already translated
                            }
                        
                        merged['assessment'] = {
                            'assessment_id': report.get('assessment_id'),
                            'trait_results': trait_results,
                            'completion_time': report.get('assessment_date', 'N/A')
                        }
                    else:
                        print(f"[RAG] WARNING: No trait report found for candidate {cand_id}")
                    
                    final_candidates_data.append(merged)
                
                print(f"[RAG] Merged {len(final_candidates_data)} candidates with trait reports")
                
            else:
                # Fallback: Fetch assessments from upstream API (original logic)
                print(f"[RAG] No trait reports from frontend. Fetching from upstream API...")
                
                assessment_ids = []
                cand_map = {}
                
                for cand in target_candidates_basic:
                    lat = cand.get('latest_assessment')
                    aid = None
                    
                    if lat and isinstance(lat, dict) and 'assessment_id' in lat:
                        aid = lat['assessment_id']
                    elif cand.get('assessment_id'):
                        aid = cand.get('assessment_id')
                        
                    if aid:
                        assessment_ids.append(aid)
                        cand_map[str(aid)] = cand.get('name', 'Unknown')
                    else:
                        print(f"[RAG] Skipped candidate {cand.get('name')} - No Assessment ID. Data: {lat}")
                
                assessment_ids = list(set([aid for aid in assessment_ids if aid]))
                print(f"[RAG] Prepared Assessment IDs: {assessment_ids} for candidates: {list(cand_map.values())}")

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
                    
                    my_asmt_data = None
                    for a in assessments_list:
                        if str(a.get('assessment_id')) == str(my_asmt_id):
                            my_asmt_data = a
                            break
                        inner = a.get('assessment', {})
                        if inner and str(inner.get('assessment_id')) == str(my_asmt_id):
                            my_asmt_data = a
                            break
                    
                    merged = cand.copy()
                    if my_asmt_data:
                        merged['assessment'] = my_asmt_data.get('assessment', {}) 
                    
                    final_candidates_data.append(merged)
                    print(f"[RAG-DEBUG] Final merged candidate: id={merged.get('candidate_id')}, name='{merged.get('name')}', has_assessment={bool(my_asmt_data)}", flush=True)

            
            # Save to Cache
            self._cache_data(cache_key, {
                'enterprise_data': enterprise_data,
                'final_candidates_data': final_candidates_data
            })
 
        # 3. Intent Routing & Mode Handling (NEW LOGIC)
        # Determine actual mode (expert vs explanation)
        determined_mode = self._determine_mode(query, mode)
        print(f"[RAG] Input Mode: {mode}, Determined Mode: {determined_mode}")

        # Inject Special Prompt Content based on Determined Mode
        prompt_content_file = 'prompt_explanation_mode.txt' if determined_mode == 'explanation' else 'prompt_expert_mode.txt'
        prompt_content_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', prompt_content_file)
        
        custom_role_prompt = "(Role Definition Missing)"
        if os.path.exists(prompt_content_path):
            with open(prompt_content_path, 'r', encoding='utf-8') as f:
                custom_role_prompt = f.read()

        # Decide on Base Use Case Configuration
        # If the query matches a specific use case (e.g., Interview Guide), use it.
        # Otherwise, use a Generic Use Case and override its guidance.
        
        # Check specific use cases first (like UC-INT-01 which has its own template)
        uc_id, uc_config = self._get_use_case(query)
        
        # Logic: 
        # If it's a "generic" match (UC-GENERAL) or "explanation forced" (UC-EXPLAIN was logic before),
        # we now override the 'answer_guidence' with our custom role prompt.
        # If it's a specific UC (e.g. UC-INT-01), we might want to respect its specialized template, 
        # BUT we still need to apply the Expert Mode style if applicable?
        # Actually, UC-INT-01 (Interview Guide) is highly specialized.
        
        if uc_id == "UC-GENERAL":
            # Override Generic Guidance with our Role Definition
            # Create a shallow copy to avoid mutating global config
            uc_config = uc_config.copy() 
            uc_config['answer_guidence'] = custom_role_prompt
        else:
            # It's a specific use case (e.g. Interview Guide or specific Competency Check)
            # We might still want to prepend the Role Definition or keep specific one?
            # User requirement: "If query matches specific use case (e.g. Interview Guide), prioritize it"
            # BUT if it's just general chat, we switch between Expert/Explanation.
            pass

        print(f"[RAG] Final Use Case: {uc_id}")
 
        # 4. Build Context
        # Pass Mode to ContextBuilder to select correct wording (Friendly vs Standard)
        builder = ContextBuilder(uc_config)
        rag_context = builder.build(enterprise_data, final_candidates_data, mode=determined_mode)
 
        # 5. Assemble System Prompt
        candidate_count = len(final_candidates_data)
        sys_prompt = self._assemble_prompt(uc_config, rag_context, candidate_count)
        
        # 6. Call LLM
        return self._call_llm(sys_prompt, query, uc_id, session_id)

    def _assemble_prompt(self, uc_config, rag_context, candidate_count=1):
        # Retrieve answer guidance safely, default to empty string if missing
        ans_guide = uc_config.get('answer_guidence', '')
        
        # Inject Multi-Candidate Constraint if needed
        if candidate_count > 1:
            ans_guide += "\n\n【多候選人回答規範】\n"
            ans_guide += "1. 必須「逐一解讀」每一位候選人，不可混在一起講。\n"
            ans_guide += "2. 在每一段解讀開始前，必須明確提及「候選人姓名」作為標題。\n"
            ans_guide += "3. 在逐一解讀完畢後，必須在文末加入「綜合點評」作為總結，比較這些候選人的異同或適用情境。"
            
        style_ref = uc_config['prompt_config'].get('style_ref', '')
        risk_notes = chr(10).join([f'- {n}' for n in uc_config['prompt_config'].get('risk_notes', [])])
        
        # Load prompt template from file
        import os
        
        # Determine which template file to load
        # Default: rag_system_prompt.txt
        template_filename = 'rag_system_prompt.txt'
        
        # Override if specified in prompt_config
        if 'prompt_config' in uc_config and 'template_file' in uc_config['prompt_config']:
            template_filename = uc_config['prompt_config']['template_file']
            print(f"[RAG] Using specialized prompt template: {template_filename}")
            
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', template_filename)
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            print(f"[RAG] Error loading prompt template: {e}")
            # Fallback (Emergency simple prompt to avoid crash)
            return f"System Error: Prompt template missing. Context: {rag_context['base_analysis']}"

        # Format variables
        # Note: We use .format(**dict) style but ensure keys match template placeholders
        try:
            sys_prompt = template.format(
                enterprise_context=rag_context.get('enterprise_context', ''),
                ans_guide=ans_guide,
                style_ref=style_ref,
                risk_notes=risk_notes,
                base_analysis=rag_context.get('base_analysis', ''),
                interactions=rag_context.get('interactions') if rag_context.get('interactions') else "(無顯著交互作用)",
                constraints=rag_context.get('constraints', '')
            )
            return sys_prompt
        except KeyError as e:
            print(f"[RAG] Prompt formatting error: Missing key {e}")
            return f"System Error: Prompt key error {e}"

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
                stream=True,
                stream_options={"include_usage": True}
            )
            return response, uc_id
        except Exception as e:
            print(f"LLM Call Failed: {e}")
            # Use 'yield from' if this was a generator, but here we return the generator object
            return self._mock_stream_fallback(error_msg=str(e)), uc_id


    def _mock_stream_fallback(self, error_msg=None):
        class MockChunk: 
            def __init__(self, content):
                self.choices = [type('obj', (object,), {'delta': type('obj', (object,), {'content': content})})]
        
        def generator():
            if error_msg:
                 yield MockChunk(f"⚠️ 系統提示：AI 服務暫時無法連線 ({error_msg})。\n\n")
            else:
                 yield MockChunk("注意：由於 LLM 連線失敗 (或 Key 設定為 Mock)，以下為模擬回應。\n\n")
            
            yield MockChunk("很抱歉，因為後端服務暫時沒有回應，無法為您分析這幾位候選人。\n")
            yield MockChunk("請稍後再試，或聯繫管理員檢查 API 設定。")
        return generator()
