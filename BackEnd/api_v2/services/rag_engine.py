import json
import os
import openai
import logging
from typing import List, Dict, Any, Optional
from flask import current_app
from .integration_base import IntegrationServiceInterface
from .integration_mock import MockIntegrationService
from .integration_real import RealIntegrationService
from .context_builder import ContextBuilder 
from ..utils.token_generator import generate_upstream_token
from ..utils.logger import get_daily_logger

def get_rag_logger():
    return get_daily_logger("RAG_Logger", "rag_service.log", level=logging.DEBUG)

def get_prompt_logger():
    formatter_str = "\n============================================================\nTIME: %(asctime)s\n%(message)s\n============================================================"
    return get_daily_logger("RAG_Prompt_Logger", "prompts.log", level=logging.INFO, formatter_str=formatter_str)

rag_logger = get_rag_logger()

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
             rag_logger.warning("mode_rules.json not found.")
             self.mode_rules = {}

        # 2. Setup Integration Service
        mode = current_app.config.get('INTEGRATION_MODE', 'MOCK')
        if mode == 'REAL':
            self.integration_service = RealIntegrationService()
        else:
            self.integration_service = MockIntegrationService()
            
        # 3. Setup LLM Client (DeepSeek / MockConfig)
        api_key = current_app.config.get('DEEPSEEK_API_KEY')
        api_base = current_app.config.get('DEEPSEEK_API_BASE')
        self.model_name = current_app.config.get('DEEPSEEK_MODEL', 'deepseek-chat')
        
        # Fallback: Retry loading .env if key is missing (Hotfix for loading issue)
        if not api_key:
             rag_logger.warning("DEEPSEEK_API_KEY is None. Attempting to reload .env manually...")
             try:
                 from dotenv import load_dotenv
                 env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
                 load_dotenv(env_path, override=True)
                 api_key = os.getenv('DEEPSEEK_API_KEY')
             except Exception as e:
                 rag_logger.error(f".env reload failed: {e}", exc_info=True)

        # Final Safety Check: Use dummy key to prevent crash, let call_llm handle authentication error
        if not api_key:
             rag_logger.error("CRITICAL: Still no API KEY. Using dummy key to prevent startup crash.", exc_info=False)
             api_key = "sk-dummy-key-for-init"

        rag_logger.info(f"Init LLM - Base: {api_base}, Key: {api_key[:5]}...")
        
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
        """
        
        # Cache Key Strategy: Session ID + Candidate IDs hash
        # This ensures isolation per session, while supporting re-fetch if candidates change
        # For MVP: Simple string key
        cand_key = "-".join(sorted(map(str, candidate_ids)))
        cache_key = f"{session_id}::{cand_key}"
        
        # 0. Check Cache
        cached_context_data = self._get_cached_data(cache_key)
        
        if cached_context_data:
            rag_logger.info(f"Cache HIT for key: {cache_key}")
            enterprise_data = cached_context_data['enterprise_data']
            final_candidates_data = cached_context_data['final_candidates_data']
        else:
            rag_logger.info(f"Cache MISS for key: {cache_key}. Fetching upstream...")
            # 1. Generate Fresh Token for Upstream
            user_email = "eva@wepredict.io" 
            upstream_token = generate_upstream_token(user_email)
            
            # 2. Fetch Data (Parallelizable, but sync for now)
            rag_logger.info(f"Orchestrating Data Fetch for {len(candidate_ids)} candidates...")
            
            # A. Enterprise Context
            enterprise_data = {}
            if isinstance(self.integration_service, RealIntegrationService):
                enterprise_data = self.integration_service.resolve_enterprise(upstream_token) or {}
                rag_logger.info(f"Enterprise: {enterprise_data.get('enterprise_name')}")
            
            # B. Candidates Basic Info
            # NEW: Prioritize frontend-provided candidate info
            target_candidates_basic = []
            
            if candidates_info:
                # Use frontend-provided data (preferred)
                rag_logger.info(f"Using {len(candidates_info)} candidates from frontend")
                target_candidates_basic = candidates_info
                for c in target_candidates_basic:
                    rag_logger.debug(f"Frontend candidate: id={c.get('candidate_id')}, name='{c.get('name')}', position='{c.get('position')}'")
            else:
                # Fallback: Fetch from API
                rag_logger.info(f"No frontend candidate info. Fetching from API...")
                try:
                    cand_resp = self.integration_service.get_candidates(upstream_token, limit=100)
                    
                    if isinstance(cand_resp, dict):
                        all_candidates = cand_resp.get('data', [])
                    else:
                        all_candidates = cand_resp
                except Exception as e:
                    rag_logger.error(f"Critical Error fetching candidates from upstream: {e}", exc_info=True)
                    # Decide: crashes here (stopping flow) or continue with empty candidates?
                    all_candidates = []
                    
                def to_str(v): return str(v) if v is not None else ""
                target_ids_str = set(map(to_str, candidate_ids))
                
                for c in all_candidates:
                    cid = to_str(c.get('candidate_id'))
                    if cid in target_ids_str:
                        target_candidates_basic.append(c)
                        rag_logger.debug(f"Found candidate {cid}: name='{c.get('name')}', position='{c.get('position')}'")

            # C. Detailed Assessments (Batch)
            # NEW: Check if trait_reports are provided from frontend
            if trait_reports:
                rag_logger.info(f"✅ Using trait reports from frontend for {len(trait_reports)} candidates")
                
                # Merge trait reports with candidate basic info
                final_candidates_data = []
                for cand in target_candidates_basic:
                    cand_id = str(cand.get('candidate_id'))
                    merged = cand.copy()
                    
                    # Get trait report from frontend data
                    if cand_id in trait_reports:
                        report = trait_reports[cand_id]
                        rag_logger.info(f"Found trait report for candidate {cand_id}: {len(report.get('traits', []))} traits")
                        
                        # Convert frontend report format to expected format
                        trait_results = {}
                        for trait in report.get('traits', []):
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
                        rag_logger.warning(f"No trait report found for candidate {cand_id}")
                    
                    final_candidates_data.append(merged)
                
                rag_logger.info(f"Merged {len(final_candidates_data)} candidates with trait reports")
                
            else:
                # Fallback: Fetch assessments from upstream API (original logic)
                rag_logger.info(f"No trait reports from frontend. Fetching from upstream API...")
                
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
                        rag_logger.warning(f"Skipped candidate {cand.get('name')} - No Assessment ID. Data: {lat}")
                
                assessment_ids = list(set([aid for aid in assessment_ids if aid]))
                rag_logger.info(f"Prepared Assessment IDs: {assessment_ids} for candidates: {list(cand_map.values())}")

                assessments_list = []
                if assessment_ids and isinstance(self.integration_service, RealIntegrationService):
                    try:
                        assessments_list = self.integration_service.get_assessments(upstream_token, assessment_ids)
                        rag_logger.info(f"Fetched {len(assessments_list)} assessments.")
                    except Exception as e:
                        rag_logger.error(f"Assessments Fetch Failed: {e}", exc_info=True)
                
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
                    rag_logger.debug(f"Final merged candidate: id={merged.get('candidate_id')}, name='{merged.get('name')}', has_assessment={bool(my_asmt_data)}")

            
            # Save to Cache
            self._cache_data(cache_key, {
                'enterprise_data': enterprise_data,
                'final_candidates_data': final_candidates_data
            })
 
        # 3. Intent Routing & Mode Handling (NEW LOGIC)
        # We now use a unified prompt and delegate intention detection to the LLM itself
        determined_mode = 'expert' # Fetch high-resolution data from ContextBuilder for LLM
        rag_logger.info(f"Input Mode: {mode}, Using Unified Intent Prompt")

        # Inject Special Prompt Content based on Unified AI Mode
        prompt_content_file = 'unified_rag_prompt.txt'
        prompt_content_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', prompt_content_file)
        
        custom_role_prompt = "(Role Definition Missing)"
        if os.path.exists(prompt_content_path):
            with open(prompt_content_path, 'r', encoding='utf-8') as f:
                custom_role_prompt = f.read()

        # Decide on Base Use Case Configuration
        uc_id, uc_config = self._get_use_case(query)
        
        # 不可修改全域 config，永遠建立 shallow copy
        uc_config = uc_config.copy()

        if uc_id == "UC-INT-01":
            # 面試提問指南：有專屬 template_file，維持原本完整 guidance，不注入角色定義
            rag_logger.info(f"UC-INT-01 detected: preserving specialized interview template.")
        else:
            # 所有其他 UC（包含 UC-GENERAL、UC-SEL-01、UC-DEV-01、UC-CMP-01 等）
            original_guidance = uc_config.get('answer_guidence', '').strip()
            if original_guidance:
                uc_config['answer_guidence'] = (
                    custom_role_prompt.strip()
                    + "\n\n【本次問題補充限制】\n"
                    + original_guidance
                )
            else:
                uc_config['answer_guidence'] = custom_role_prompt

        rag_logger.info(f"Final Use Case: {uc_id}")
 
        # 4. Build Context
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
        template_filename = 'rag_system_prompt.txt'
        
        # Override if specified in prompt_config
        if 'prompt_config' in uc_config and 'template_file' in uc_config['prompt_config']:
            template_filename = uc_config['prompt_config']['template_file']
            rag_logger.info(f"Using specialized prompt template: {template_filename}")
            
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', template_filename)
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            rag_logger.error(f"Error loading prompt template: {e}", exc_info=True)
            # Fallback (Emergency simple prompt to avoid crash)
            return f"System Error: Prompt template missing. Context: {rag_context['base_analysis']}"

        # Format variables
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
            rag_logger.error(f"Prompt formatting error: Missing key {e}", exc_info=True)
            return f"System Error: Prompt key error {e}"

    def _log_prompt(self, session_id, uc_id, sys_prompt, user_query):
        """ Log the prompt using standard logging """
        try:
            prompt_logger = get_prompt_logger()
            log_message = (
                f"SESSION: {session_id} | USE_CASE: {uc_id}\n"
                f"============================================================\n"
                f"[SYSTEM PROMPT]\n{sys_prompt}\n\n"
                f"[USER QUERY]\n{user_query}"
            )
            prompt_logger.info(log_message)
        except Exception as e:
            rag_logger.error(f"Failed to write prompt log using logger: {e}", exc_info=True)
            print(f"[Log] Failed to write prompt log using logger: {e}")

    def _call_llm(self, sys_prompt, query, uc_id, session_id="unknown"):
        # Log the prompt before calling
        self._log_prompt(session_id, uc_id, sys_prompt, query)
        
        rag_logger.debug(f"--- DEBUG RAG SYSTEM PROMPT ---\n{sys_prompt}\n-------------------------")
        
        messages = [
            {"role": "system", "content": sys_prompt.strip()},
            {"role": "user", "content": query}
        ]

        try:
            rag_logger.info(f"Calling DeepSeek API with model '{self.model_name}'...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            return response, uc_id
        except Exception as e:
            rag_logger.error(f"LLM Call Failed: {e}", exc_info=True)
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
