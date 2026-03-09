from typing import Dict, List
import json
from ..database import db_session, TraitBand, TraitInteraction, TraitDefinition

class ContextBuilder:
    def __init__(self, use_case_config: Dict):
        self.config = use_case_config
        self.prompt_config = use_case_config.get('prompt_config', {})
        
    def build(self, enterprise_data: Dict, candidates_data: List[Dict], mode: str = 'explanation') -> Dict[str, str]:
        """
        Assembles the comprehensive RAG Context.
        
        Args:
            enterprise_data: { "enterprise_name": "...", "job_desc": [...] }
            candidates_data: List of candidates with merged 'assessment' details.
            mode: 'expert' or 'explanation'. Used to toggle wording friendliness.
            
        Returns:
            Dict containing formatted string blocks for System Prompt.
        """
        components = {
            "enterprise_context": "",
            "base_analysis": "",
            "constraints": "",
            "interactions": ""
        }
        
        # 1. Enterprise Context (New)
        ent_name = enterprise_data.get('enterprise_name', 'Unknown Company')
        jobs = enterprise_data.get('job_desc', [])
        
        components["enterprise_context"] += f"雇主: {ent_name}\n"
        if jobs:
            components["enterprise_context"] += "相關職缺:\n"
            for job in jobs:
                if isinstance(job, dict):
                    components["enterprise_context"] += f"- [{job.get('title')}]: {job.get('desc')}\n"
                else:
                    components["enterprise_context"] += f"- {str(job)}\n"
        
        # 2. Candidate Analysis
        for i, cand in enumerate(candidates_data):
            cand_id = cand.get('candidate_id', 'Unknown')
            # Robust name extraction with fallback
            name = cand.get('name') or f"Candidate-{cand_id}"
            position = cand.get('position', 'NA')
            cand_name = f"{name} ({position})"
            
            components["base_analysis"] += f"### 候選人: {cand_name}\n"

            
            # Assessment Data (Robust Extraction Logic matches previous tool output)
            asmt = cand.get('assessment', {})
            results = asmt.get('trait_results', {})
            if not results:
                results = cand.get('trait_results', {})
            if not results and isinstance(asmt, (dict, str)) and 'trait_id' in str(asmt):
                results = asmt
            
            if not results:
                components["base_analysis"] += "  (無詳細測評數據)\n"
                continue

            # Band Calculation
            candidate_bands_map = {}
            processed_traits = []
            
            if isinstance(results, dict):
                results_list = results.values()
            elif isinstance(results, list):
                results_list = results
            else:
                results_list = []

            from sqlalchemy import func

            for res in results_list:
                # 1. Identify Name (PK)
                trait_name_en = res.get('chinese_name') 
                if not trait_name_en:
                    continue

                # 2. Key Mapping (Name -> DB Trait ID)
                project_abbrev = asmt.get('project_name_abbreviation', 'CIA')
                
                # First try with project-specific prefix to avoid mixing e.g., ANI_02 and CIA_18 (both 'Resilience')
                # Also trim whitespace because excel imports might contain trailing spaces causing missing traits
                trait_def = db_session.query(TraitDefinition).filter(
                    func.trim(func.lower(TraitDefinition.name_en)) == func.trim(func.lower(trait_name_en)),
                    TraitDefinition.trait_id.like(f"{project_abbrev}_%")
                ).first()
                
                # Fallback: if not found with project prefix, try without it just in case
                if not trait_def:
                    trait_def = db_session.query(TraitDefinition).filter(
                        func.trim(func.lower(TraitDefinition.name_en)) == func.trim(func.lower(trait_name_en))
                    ).first()
                
                if not trait_def:
                    continue
                
                trait_id = trait_def.trait_id
                score = res.get('score')
                if score is None: 
                    continue

                # 4. DB Query for Band
                band_row = db_session.query(TraitBand).filter(
                    TraitBand.trait_id == trait_id,
                    TraitBand.min_score <= score,
                    TraitBand.max_score >= score
                ).first()
                
                if band_row:
                    candidate_bands_map[trait_id] = band_row.band
                    processed_traits.append((trait_id, score, band_row))
            
            # A. Base Traits Semantics
            for trait_id, score, band_row in processed_traits:
                # Fetch Name
                trait_def = db_session.query(TraitDefinition).filter_by(trait_id=trait_id).first()
                t_name_zh = trait_def.name_zh if trait_def else trait_id
                
                # WORDING SELECTION BASED ON MODE
                if mode == 'explanation':
                    # Use Friendly Wording if available, else fallback to standard
                    wording = band_row.report_wording_friendly or band_row.description or '無描述'
                    # Explanation Mode: Hide specific scores and bands in the output string if possible, 
                    # but context needs to provide the semantic meaning.
                    # User constraint: "cannot mention trait names/scores".
                    # We provide the semantic analysis to LLM but instruct LLM not to output raw names.
                    components["base_analysis"] += f"  * [特質洞察]: {wording}\n"
                    # Using generic label to help LLM avoid leaking names? 
                    # But LLM needs to connect interactions. 
                    # Let's provide the name for internal logic but trust the system prompt to hide it.
                    # Or better: "  * [{t_name_zh}]: {wording}" 
                    # The prompt instruction says "Don't mention trait names".
                else: 
                    # Expert Mode
                    wording = band_row.description or '無描述'
                    components["base_analysis"] += f"  * [{trait_id}] {t_name_zh} (Score {score} -> Band {band_row.band}):\n"
                    components["base_analysis"] += f"    - 語意: {band_row.semantic_label}\n"
                    components["base_analysis"] += f"    - 描述: {wording}\n"
                
                # B. Constraints (Do/Dont)
                if band_row.ai_guidance:
                    guidance = self._parse_json(band_row.ai_guidance)
                    if guidance.get('do') or guidance.get('dont'):
                        components["constraints"] += f"  [{cand_name} - {t_name_zh} ({band_row.band})]:\n"
                        if guidance.get('do'):
                            components["constraints"] += f"    - MUST DO: {guidance['do']}\n"
                        if guidance.get('dont'):
                            components["constraints"] += f"    - DONT: {guidance['dont']}\n"

            # C. Interactions
            # Check interaction database for pairs present in this candidate
            for trait_id, score, band_row in processed_traits:
                # Check for interactions where this trait is PRIMARY
                interactions = db_session.query(TraitInteraction).filter_by(
                    primary_trait_id=trait_id, 
                    primary_band=band_row.band
                ).all()
                
                for comm in interactions:
                    # Check if the TRIGGER trait exists and matches the required band
                    trigger_band = candidate_bands_map.get(comm.trigger_trait_id)
                    if trigger_band and trigger_band == comm.trigger_band:
                        # Get names for clarity
                        t1_def = db_session.query(TraitDefinition).filter_by(trait_id=trait_id).first()
                        t2_def = db_session.query(TraitDefinition).filter_by(trait_id=comm.trigger_trait_id).first()
                        t1_name = t1_def.name_zh if t1_def else trait_id
                        t2_name = t2_def.name_zh if t2_def else comm.trigger_trait_id
                        
                        components["interactions"] += f"  > [{cand_name}] [主: {t1_name}] + [引: {t2_name}]:\n"
                        components["interactions"] += f"    {comm.narrative}\n"

        return components

    def _parse_json(self, content):
        if isinstance(content, dict): return content
        try:
            return json.loads(content)
        except:
            return {}
