from typing import Dict, List
import json
from database import db_session, TraitBand, TraitInteraction, TraitDefinition

class ContextBuilder:
    def __init__(self, use_case_config: Dict):
        self.config = use_case_config
        self.prompt_config = use_case_config.get('prompt_config', {})
        
    def build(self, enterprise_data: Dict, candidates_data: List[Dict]) -> Dict[str, str]:
        """
        Assembles the comprehensive RAG Context.
        
        Args:
            enterprise_data: { "enterprise_name": "...", "job_desc": [...] }
            candidates_data: List of candidates with merged 'assessment' details.
            
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
                components["enterprise_context"] += f"- [{job.get('title')}]: {job.get('desc')}\n"
        
        # 2. Candidate Analysis
        for cand in candidates_data:
            # Debug: Log raw candidate data
            print(f"[ContextBuilder-DEBUG] Processing candidate: {cand.get('candidate_id')}, name='{cand.get('name')}', position='{cand.get('position')}'", flush=True)
            
            # Robust name extraction with fallback
            name = cand.get('name') or f"Candidate-{cand.get('candidate_id', 'Unknown')}"
            position = cand.get('position', 'NA')
            cand_name = f"{name} ({position})"
            
            if not cand.get('name'):
                print(f"[ContextBuilder-WARNING] Candidate {cand.get('candidate_id')} has no 'name' field. Using fallback.", flush=True)
            
            components["base_analysis"] += f"### 候選人: {cand_name}\n"

            
            # Assessment Data
            # Note: Upstream API format check needed. 
            # Real Service returns `results` list. Merged data should have 'assessment' key or be flat?
            # Integration logic merges it. Let's assume 'assessment' key or flat 'trait_results'.
            # Based on Swagger: { assessment: { trait_results: ... } } inside the result item.
            
            asmt = cand.get('assessment', {})
            # Robust Extraction: Check 'trait_results' inside assessment or directly in assessment or top level
            results = asmt.get('trait_results', {})
            if not results:
                # Try getting from top level if not nested
                results = cand.get('trait_results', {})
            # Sometimes 'trait_results' is the list itself if not dict
            # or 'asmt' itself is the results dict? Let's check keys
            if not results and isinstance(asmt, dict) and 'trait_id' in str(asmt):
                # Heuristic: asmt might be the results dict/list
                results = asmt
            
            if not results:
                components["base_analysis"] += "  (無詳細測評數據)\n"
                continue

            # Band Calculation
            candidate_bands_map = {}
            processed_traits = []
            
            # Trait Results is expected to be a dict keyed by some ID, or a list.
            # Based on latest sample: Dict { "143b": { "trait_id": "143b", "chinese_name": "Empathy", "score": 61 ... } }
            # New Logic: Map 'chinese_name' (which is English) -> DB Trait ID
            
            # Normalize to list of result items
            if isinstance(results, dict):
                results_list = results.values()
            elif isinstance(results, list):
                results_list = results
            else:
                results_list = []

            from sqlalchemy import func

            for res in results_list:
                # 1. Identify Name (PK)
                # "chinese_name" field actually holds the English Name per User Spec
                trait_name_en = res.get('chinese_name') 
                if not trait_name_en:
                    continue

                # 2. Key Mapping (Name -> DB Trait ID)
                # Use case-insensitive match for safety
                trait_def = db_session.query(TraitDefinition).filter(
                    func.lower(TraitDefinition.name_en) == func.lower(trait_name_en)
                ).first()
                
                if not trait_def:
                    # Log or Skip if unknown trait
                    # print(f"Warning: Unknown trait name '{trait_name_en}'")
                    continue
                
                trait_id = trait_def.trait_id # The canonical ID (e.g. ANI_01)

                # 3. Score Extraction
                # Removed: score_value, prediction_value
                # Retained: score
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
                # Fetch Name (Already resolved trait_def earlier, but safer to query or cache)
                # We need name_zh for the prompt display
                trait_def = db_session.query(TraitDefinition).filter_by(trait_id=trait_id).first()
                t_name_zh = trait_def.name_zh if trait_def else trait_id
                
                components["base_analysis"] += f"  * [{trait_id}] {t_name_zh} (Score {score} -> Band {band_row.band}):\n"
                components["base_analysis"] += f"    - 語意: {band_row.semantic_label}\n"
                components["base_analysis"] += f"    - 描述: {band_row.description}\n"
                
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
