from typing import Dict, List
import json
import re
from ..database import db_session, TraitBand, TraitInteraction, TraitDefinition
from ..utils.logger import get_daily_logger

trait_match_audit_logger = get_daily_logger('TraitMatchAudit', 'trait_match_audit.log')

_NON_ALNUM_RE = re.compile(r'[^a-zA-Z0-9]')


def _normalize_band(value):
    """'A (高)' -> 'A'; plain 'A' stays 'A'. trait_interactions.primary_band is stored
    with a Chinese descriptor suffix while trait_bands.band and trigger_band are not."""
    if not value:
        return value
    return value.split('(')[0].strip()


def _normalize_en_name(value):
    """Format-tolerant normalization for English trait names: lowercase and strip
    everything that isn't a letter/digit, so vendor formatting variance (extra/missing
    spaces, hyphens, underscores -- e.g. 'Self-Discipline' vs 'Self Discipline') doesn't
    cause an exact-match miss. Does not resolve genuine wording differences (different
    words), only formatting differences."""
    if not value:
        return value
    return _NON_ALNUM_RE.sub('', value).lower()


# trait_interactions.narrative is authored as "與 {trait_id} ({name_zh}) {band}聯動：{actual text}"
# (sometimes chaining a second trait, e.g. "與 CIA_06 (條理性) C 與 CIA_07 (完美主義) A：...").
# That lead-in exposes exactly the trait_id/name_zh/band the rest of this module is designed to
# hide from the LLM (see the "安全輸出" comments below). Confirmed against all 2,389 rows: every
# narrative starts with '與' and has its first full-width/half-width colon right after the leak,
# so stripping up to (and including) the first colon removes the leak with zero collateral loss.
_INTERACTION_LEAK_PREFIX_RE = re.compile(r'^與\s*[A-Za-z]+_\d+.*?[：:]\s*')


def _strip_interaction_leak(narrative):
    if not narrative:
        return narrative
    return _INTERACTION_LEAK_PREFIX_RE.sub('', narrative, count=1)


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
                # 1. Identify Identifiers
                # 注意：API 的 chinese_name 欄位實際存放的是英文名稱（如 'Hope'、'Gratitude'）
                # API 的 trait_id（如 '99f'）與 DB 的 trait_id（如 'CIA_16'）格式不同，不使用
                display_name = res.get('chinese_name') or res.get('trait_name')

                if not display_name:
                    trait_match_audit_logger.warning(
                        f"reason=no_name | candidate={cand_name} | raw_res={res}"
                    )
                    continue

                # 2. Key Mapping (ID/Name -> DB Trait ID)
                # [方案 B] 不使用硬編碼預設值 'CIA'，缺失時直接跳過此特質
                project_abbrev = asmt.get('project_name_abbreviation')
                if not project_abbrev:
                    # 無法識別報告類型，跳過整個候選人的此特質（不能亂猜）
                    trait_match_audit_logger.warning(
                        f"reason=no_project_abbrev | candidate={cand_name} | display_name={display_name!r}"
                    )
                    continue
                
                # --- DB 查詢策略 ---
                # 甲方 API 的 trait_id（如 '99f'、'147b'）與 DB 的 trait_id（如 'CIA_16'）
                # 格式完全不同，無法直接比對。
                # 正確做法：用 API 的 chinese_name（實為英文名，如 'Hope'）
                # 比對 DB 的 name_en，再以 project_abbrev 前綴過濾。
                trait_def = None
                
                if display_name:
                    # 策略 A：用英文名比對 name_en（主要路徑）
                    # 格式容錯：比對前雙方都去除空白/連字號等非英數字元並轉小寫，
                    # 避免廠商端格式差異（如 'Self-Discipline' vs 'Self Discipline'）
                    # 造成明明是同一個特質卻比對失敗。不處理真正用詞不同的情況。
                    normalized_input = _normalize_en_name(display_name)
                    normalized_name_en = func.lower(func.regexp_replace(TraitDefinition.name_en, r'[^a-zA-Z0-9]', '', 'g'))
                    trait_def = db_session.query(TraitDefinition).filter(
                        normalized_name_en == normalized_input,
                        TraitDefinition.trait_id.like(f"{project_abbrev}_%")
                    ).first()
                
                if not trait_def and display_name:
                    # 策略 B：Fallback 用中文名比對 name_zh（以防規格書 name_en 為中文的情況）
                    trait_def = db_session.query(TraitDefinition).filter(
                        func.trim(func.lower(TraitDefinition.name_zh)) == func.trim(func.lower(display_name)),
                        TraitDefinition.trait_id.like(f"{project_abbrev}_%")
                    ).first()
                
                if not trait_def:
                    trait_match_audit_logger.warning(
                        f"reason=no_trait_def_match | candidate={cand_name} | "
                        f"project_abbrev={project_abbrev} | display_name={display_name!r}"
                    )
                    continue

                trait_id = trait_def.trait_id
                score = res.get('score')
                if score is None:
                    trait_match_audit_logger.warning(
                        f"reason=no_score | candidate={cand_name} | trait_id={trait_id} | "
                        f"display_name={display_name!r}"
                    )
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
                else:
                    trait_match_audit_logger.warning(
                        f"reason=no_band_range | candidate={cand_name} | trait_id={trait_id} | "
                        f"score={score} | display_name={display_name!r}"
                    )
            
            # A. Base Traits Semantics + Constraints (merged into one block per trait)
            for trait_id, score, band_row in processed_traits:
                # --- 安全輸出：不向 LLM 暴露 trait_id / name_zh / score / band ---
                # 統一使用 semantic_label + description，讓 LLM 無法引用原始特質名稱
                semantic = band_row.semantic_label or '行為傾向'
                if mode == 'explanation':
                    wording = band_row.report_wording_friendly or band_row.description or '無描述'
                else:
                    wording = band_row.description or '無描述'

                components["base_analysis"] += f"  [{cand_name} - {semantic}]:\n"
                components["base_analysis"] += f"   * 行為面向 — {semantic}:\n"
                components["base_analysis"] += f"    - {wording}\n"
                if band_row.management_focus:
                    components["base_analysis"] += f"    - 管理重點: {band_row.management_focus}\n"

                # Constraints (Do/Dont), nested under the same trait block
                if band_row.ai_guidance:
                    guidance = self._parse_json(band_row.ai_guidance)
                    # Use the verbatim cell text. Interpolating the split list rendered
                    # its Python repr into the prompt ("MUST DO: ['可用於：…']"), which is
                    # the `['` that b §6 unit check 3 forbids -- and the reason the client's
                    # regex_pack carries a strip_python_list_wrapper rule as a workaround.
                    # `*_raw` is written by both importers; fall back for rows imported
                    # before that change.
                    do = guidance.get('do_raw') or '；'.join(guidance.get('do') or [])
                    dont = guidance.get('dont_raw') or '；'.join(guidance.get('dont') or [])
                    if do:
                        components["base_analysis"] += f"    - MUST DO: {do}\n"
                    if dont:
                        components["base_analysis"] += f"    - DONT: {dont}\n"

            # C. Interactions
            # Check interaction database for pairs present in this candidate
            for trait_id, score, band_row in processed_traits:
                # Check for interactions where this trait is PRIMARY
                # NOTE: primary_band is compared in Python (not via filter_by) because
                # trait_interactions.primary_band is stored as 'A (高)' while
                # trait_bands.band is plain 'A' -- see _normalize_band().
                interactions = db_session.query(TraitInteraction).filter_by(
                    primary_trait_id=trait_id
                ).all()

                for comm in interactions:
                    if _normalize_band(comm.primary_band) != band_row.band:
                        continue
                    # Check if the TRIGGER trait exists and matches the required band
                    trigger_band = candidate_bands_map.get(comm.trigger_trait_id)
                    if trigger_band and trigger_band == _normalize_band(comm.trigger_band):
                        # 安全輸出：不向 LLM 暴露特質名稱，僅提供行為交互敘述
                        # narrative 原文開頭寫死了 trait_id/中文名/band（見 _strip_interaction_leak
                        # 說明），這裡先清除該前綴，只保留實際敘述內容。
                        safe_narrative = _strip_interaction_leak(comm.narrative)
                        components["interactions"] += f"  > [{cand_name}] 行為交互作用:\n"
                        components["interactions"] += f"    {safe_narrative}\n"

        return components

    def _parse_json(self, content):
        if isinstance(content, dict): return content
        try:
            return json.loads(content)
        except:
            return {}
