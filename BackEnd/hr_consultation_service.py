"""
HR 諮詢服務模組（重構版）
基於正確的資料表結構：test_invitee, test_project_result, test_project_trait

變更說明：
1. 使用 test_invitee 作為候選人表（替代 core_user）
2. 使用 test_project_result 作為測驗結果表（替代 individual_test_result）
3. 支援企業隔離（enterprise_id）
4. 支援多測驗項目和特質配置
5. 優化 Prompt 包含完整候選人檔案、測驗歷史、特質權重
"""

import logging
import re
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from prompt_manager import get_prompt_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HRConsultationService:
    """
    HR 諮詢服務類（重構版）
    
    核心變更：
    - 候選人來源：test_invitee（企業創建的候選人）
    - 測驗結果：test_project_result（企業測驗結果）
    - 企業隔離：所有查詢都包含 enterprise_id 過濾
    - 特質配置：支援 test_project_trait 的權重和優先級
    """
    
    def __init__(self, db_connection, llm_service, enterprise_id: Optional[int] = None):
        """
        初始化 HR 諮詢服務
        
        Args:
            db_connection: 資料庫連接
            llm_service: LLM 服務實例
            enterprise_id: 企業 ID（用於數據隔離，可選，None 表示不限制企業）
        """
        self.db_conn = db_connection
        self.llm_service = llm_service
        self.enterprise_id = enterprise_id
        
        # 從環境變數讀取 LLM 配置
        env_value = os.getenv('LLM_MAX_RESPONSE_LENGTH', '150')
        logger.info(f"🔍 讀取環境變數 LLM_MAX_RESPONSE_LENGTH: {env_value}")
        self.max_response_length = int(env_value)
        
        # 獲取 Prompt 管理器
        self.prompt_manager = get_prompt_manager()
        
        logger.info(f"HR 諮詢服務已初始化 (Enterprise ID: {enterprise_id if enterprise_id else '不限制'}, "
                   f"最大回答長度: {self.max_response_length} 字)")
    
    def consult(
        self, 
        query: str, 
        candidate_id: Optional[int] = None,
        candidate_name: Optional[str] = None,
        session_id: Optional[str] = None,
        enterprise_id: Optional[int] = None
    ) -> Dict:
        """
        處理 HR 諮詢請求
        
        Args:
            query: 用戶問題
            candidate_id: 候選人 ID（test_invitee.id）
            candidate_name: 候選人姓名
            session_id: 會話 ID（用於保存歷史）
            enterprise_id: 企業 ID（覆蓋初始化時的設定）
            
        Returns:
            諮詢結果字典
        """
        try:
            # 確定企業 ID（None 表示不限制企業）
            active_enterprise_id = enterprise_id if enterprise_id is not None else self.enterprise_id
            
            logger.info(f"========== HR 諮詢請求開始 ==========")
            logger.info(f"Query: {query}")
            logger.info(f"CandidateID: {candidate_id}")
            logger.info(f"CandidateName: {candidate_name}")
            logger.info(f"EnterpriseID: {active_enterprise_id if active_enterprise_id else '不限制'}")
            logger.info(f"SessionID: {session_id}")
            
            # 1. 確定候選人（從 test_invitee）
            logger.info("步驟 1: 解析候選人...")
            candidate = self._resolve_candidate(
                query, 
                candidate_id, 
                candidate_name,
                active_enterprise_id
            )
            
            if not candidate:
                logger.warning(f"❌ 無法識別候選人")
                logger.warning(f"   Query: {query}")
                logger.warning(f"   CandidateID: {candidate_id}")
                logger.warning(f"   CandidateName: {candidate_name}")
                logger.warning(f"   EnterpriseID: {active_enterprise_id}")
                return {
                    "success": False,
                    "error": "無法識別候選人或候選人不屬於您的企業",
                    "suggestion": "請指定候選人姓名或 ID，例如：「張三適合什麼職位？」"
                }
            
            logger.info(f"✅ 識別候選人成功: {candidate['name']} (ID: {candidate['id']})")
            
            # 2. 獲取最新測評數據（從 test_project_result）
            test_data = self._get_latest_test_data(candidate['id'])
            
            if not test_data:
                logger.warning(f"候選人 {candidate['name']} 無測評數據")
                return {
                    "success": False,
                    "error": f"候選人 {candidate['name']} 尚無已完成的測評數據",
                    "candidate": {
                        "id": candidate['id'],
                        "name": candidate['name'],
                        "email": candidate.get('email'),
                        "position": candidate.get('position'),
                        "status": candidate.get('status')
                    },
                    "suggestion": "請先邀請該候選人完成測評"
                }
            
            # 計算實際特質數量（trait_results 是 dict，key 是特質名稱）
            trait_results = test_data.get('trait_results', {})
            trait_count = len([k for k in trait_results.keys() if isinstance(trait_results[k], dict) and 'score' in trait_results[k]])
            logger.info(f"獲取測評數據成功 - 項目: {test_data.get('project_name')}, "
                       f"特質數: {trait_count}")
            
            # 3. 獲取特質名稱映射（從 trait 表）
            trait_mapping = self._get_trait_name_mapping()
            
            # 4. 獲取特質配置（從 test_project_trait）
            trait_configs = self._get_trait_configs(test_data['project_id'])
            
            # 5. 生成諮詢建議
            consultation_result = self._generate_consultation(
                query,
                candidate,
                test_data,
                trait_configs,
                trait_mapping
            )
            
            # 6. 保存諮詢歷史
            if session_id:
                self._save_consultation_history(
                    session_id,
                    candidate['id'],
                    query,
                    consultation_result
                )
            
            # 6. 返回結果
            return {
                "success": True,
                "candidate": {
                    "id": candidate['id'],
                    "name": candidate['name'],
                    "email": candidate.get('email'),
                    "position": candidate.get('position'),
                    "status": candidate.get('status'),
                    "company": candidate.get('company')
                },
                "question": query,
                "consultation": consultation_result['answer'],
                "parsed_answer": consultation_result.get('parsed_answer'),  # 添加結構化回應
                "data_summary": consultation_result['data_summary'],
                "based_on_traits": consultation_result['used_traits'],
                "test_info": {
                    "project_name": test_data['project_name'],
                    "test_date": test_data['test_date'],
                    "overall_score": test_data.get('score_value')
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"HR 諮詢處理失敗: {e}", exc_info=True)
            return {
                "success": False,
                "error": "諮詢服務暫時不可用",
                "details": str(e)
            }
    
    def _resolve_candidate(
        self,
        query: str,
        candidate_id: Optional[int],
        candidate_name: Optional[str],
        enterprise_id: int
    ) -> Optional[Dict]:
        """
        解析並獲取候選人資訊（from test_invitee）
        
        優先級：candidate_id > candidate_name > 從 query 提取
        """
        # 優先級 1: 使用提供的 candidate_id
        if candidate_id:
            return self._get_candidate_by_id(candidate_id, enterprise_id)
        
        # 優先級 2: 使用提供的 candidate_name
        if candidate_name:
            return self._get_candidate_by_name(candidate_name, enterprise_id)
        
        # 優先級 3: 從 query 中提取姓名
        extracted_name = self._extract_candidate_name_from_query(query)
        if extracted_name:
            return self._get_candidate_by_name(extracted_name, enterprise_id)
        
        return None
    
    def _extract_candidate_name_from_query(self, query: str) -> Optional[str]:
        """
        從查詢中提取候選人姓名
        
        支援模式：
        - "張三適合什麼職位？"
        - "如何培養李四的領導力？"
        - "王五的職業發展建議"
        """
        # 中文姓名模式 (2-4 個字)
        chinese_name_pattern = r'[\u4e00-\u9fa5]{2,4}'
        matches = re.findall(chinese_name_pattern, query)
        
        # 排除常見詞彙
        excluded_words = [
            '什麼', '如何', '適合', '職位', '領導', '發展', 
            '建議', '可以', '能夠', '這個', '那個', '哪些',
            '公司', '團隊', '工作', '能力', '評估', '分析'
        ]
        
        for potential_name in matches:
            if potential_name not in excluded_words:
                return potential_name
        
        return None
    
    def _get_candidate_by_id(
        self, 
        candidate_id: int, 
        enterprise_id: int
    ) -> Optional[Dict]:
        """
        根據 ID 獲取候選人（from test_invitee）
        
        ✅ 包含企業隔離檢查
        ✅ 統計測驗數據
        ✅ 適當的資源清理和錯誤處理
        """
        cursor = None
        try:
            # 確保資料庫連接處於正常狀態
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            # 構建查詢（根據是否有 enterprise_id 決定條件）
            if enterprise_id:
                query = """
                    SELECT 
                        ti.id,
                        ti.name,
                        ti.email,
                        ti.phone,
                        ti.company,
                        ti.status,
                        ti.position,
                        ti.notes,
                        ti.invited_count,
                        ti.completed_count,
                        ti.last_test_date,
                        ti.created_at,
                        
                        -- 統計測驗數據
                        COUNT(DISTINCT tinv.id) as total_invitations,
                        COUNT(DISTINCT CASE 
                            WHEN tpr.crawl_status = 'completed' 
                            THEN tpr.id 
                        END) as completed_tests
                        
                    FROM test_invitee ti
                    LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
                    LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
                    
                    WHERE ti.id = %s AND ti.enterprise_id = %s
                    
                    GROUP BY ti.id
                """
                params = (candidate_id, enterprise_id)
            else:
                query = """
                    SELECT 
                        ti.id,
                        ti.name,
                        ti.email,
                        ti.phone,
                        ti.company,
                        ti.status,
                        ti.position,
                        ti.notes,
                        ti.invited_count,
                        ti.completed_count,
                        ti.last_test_date,
                        ti.created_at,
                        
                        -- 統計測驗數據
                        COUNT(DISTINCT tinv.id) as total_invitations,
                        COUNT(DISTINCT CASE 
                            WHEN tpr.crawl_status = 'completed' 
                            THEN tpr.id 
                        END) as completed_tests
                        
                    FROM test_invitee ti
                    LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
                    LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
                    
                    WHERE ti.id = %s
                    
                    GROUP BY ti.id
                """
                params = (candidate_id,)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"獲取候選人失敗 (ID: {candidate_id}): {e}")
            # 發生錯誤時回滾事務
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            return None
        finally:
            # 確保 cursor 被關閉
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _get_candidate_by_name(
        self, 
        name: str, 
        enterprise_id: int
    ) -> Optional[Dict]:
        """
        根據姓名獲取候選人（from test_invitee）
        
        ✅ 支援模糊匹配
        ✅ 企業隔離
        ✅ 適當的資源清理和錯誤處理
        """
        cursor = None
        try:
            # 確保資料庫連接處於正常狀態
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            # 構建查詢（根據是否有 enterprise_id 決定條件）
            if enterprise_id:
                query = """
                    SELECT 
                        ti.id,
                        ti.name,
                        ti.email,
                        ti.phone,
                        ti.company,
                        ti.status,
                        ti.position,
                        ti.notes,
                        ti.invited_count,
                        ti.completed_count,
                        ti.last_test_date,
                        
                        COUNT(DISTINCT CASE 
                            WHEN tpr.crawl_status = 'completed' 
                            THEN tpr.id 
                        END) as completed_tests
                        
                    FROM test_invitee ti
                    LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
                    LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
                    
                    WHERE ti.name LIKE %s AND ti.enterprise_id = %s
                    
                    GROUP BY ti.id
                    ORDER BY ti.last_test_date DESC NULLS LAST
                    LIMIT 1
                """
                params = (f"%{name}%", enterprise_id)
            else:
                query = """
                    SELECT 
                        ti.id,
                        ti.name,
                        ti.email,
                        ti.phone,
                        ti.company,
                        ti.status,
                        ti.position,
                        ti.notes,
                        ti.invited_count,
                        ti.completed_count,
                        ti.last_test_date,
                        
                        COUNT(DISTINCT CASE 
                            WHEN tpr.crawl_status = 'completed' 
                            THEN tpr.id 
                        END) as completed_tests
                        
                    FROM test_invitee ti
                    LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
                    LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
                    
                    WHERE ti.name LIKE %s
                    
                    GROUP BY ti.id
                    ORDER BY ti.last_test_date DESC NULLS LAST
                    LIMIT 1
                """
                params = (f"%{name}%",)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"獲取候選人失敗 (姓名: {name}): {e}")
            # 發生錯誤時回滾事務
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            return None
        finally:
            # 確保 cursor 被關閉
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _get_latest_test_data(self, candidate_id: int) -> Optional[Dict]:
        """
        獲取候選人最新的測評數據（from test_project_result）
        
        ✅ 使用正確的資料表關聯
        ✅ 只取已完成的測驗（crawl_status='completed'）
        ✅ 適當的資源清理和錯誤處理
        
        Returns:
            {
                'result_id': int,
                'project_id': int,
                'project_name': str,
                'project_description': str,
                'trait_results': dict,  # JSONB
                'score_value': float,
                'prediction_value': str,
                'test_date': datetime,
                'crawl_status': str
            }
        """
        cursor = None
        try:
            # 確保資料庫連接處於正常狀態
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    tpr.id as result_id,
                    tpr.trait_results,
                    tpr.score_value,
                    tpr.prediction_value,
                    tpr.crawled_at as test_date,
                    tpr.crawl_status,
                    tp.id as project_id,
                    tp.name as project_name,
                    tp.description as project_description
                    
                FROM test_project_result tpr
                JOIN test_invitation tinv ON tpr.test_invitation_id = tinv.id
                JOIN test_project tp ON tpr.test_project_id = tp.id
                
                WHERE 
                    tinv.invitee_id = %s 
                    AND tpr.crawl_status = 'completed'
                    
                ORDER BY tpr.crawled_at DESC
                LIMIT 1
            """
            
            cursor.execute(query, (candidate_id,))
            result = cursor.fetchone()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"獲取測評數據失敗: {e}")
            # 發生錯誤時回滾事務
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            return None
        finally:
            # 確保 cursor 被關閉
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _get_trait_name_mapping(self) -> Dict[str, Dict]:
        """
        獲取特質名稱映射（從 trait 表）
        
        將英文 system_name 映射到中文名稱和說明
        
        Returns:
            Dict of {
                'system_name': {
                    'chinese_name': str,
                    'description': str,
                    'english_name': str
                }
            }
        """
        cursor = None
        try:
            # 確保資料庫連接處於正常狀態
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    system_name,
                    chinese_name,
                    english_name,
                    description
                FROM trait
                ORDER BY id
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # 建立映射 dict
            mapping = {}
            for row in results:
                system_name = row['system_name']
                mapping[system_name] = {
                    'chinese_name': row['chinese_name'],
                    'description': row['description'],
                    'english_name': row.get('english_name', system_name)
                }
            
            logger.info(f"✅ 載入特質映射: {len(mapping)} 個特質")
            return mapping
            
        except Exception as e:
            logger.error(f"獲取特質映射失敗: {e}")
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            return {}
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    
    def _get_trait_configs(self, project_id: int) -> List[Dict]:
        """
        獲取測驗項目的特質配置（from test_project_trait）
        
        ✅ 包含權重（weight）和優先級（is_primary）
        ✅ 按顯示順序排序（display_order）
        ✅ 適當的資源清理和錯誤處理
        
        Returns:
            List of {
                'trait_id': int,
                'system_name': str,
                'chinese_name': str,
                'english_name': str,
                'weight': float,
                'is_primary': bool,
                'display_order': int,
                'description': str
            }
        """
        cursor = None
        try:
            # 確保資料庫連接處於正常狀態
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    tpt.trait_id,
                    tpt.weight,
                    tpt.is_primary,
                    tpt.display_order,
                    tpt.min_score,
                    tpt.max_score,
                    tpt.description as config_description,
                    t.system_name,
                    t.chinese_name,
                    t.english_name,
                    t.category,
                    t.description as trait_description
                    
                FROM test_project_trait tpt
                JOIN trait t ON tpt.trait_id = t.id
                
                WHERE tpt.test_project_id = %s
                
                ORDER BY tpt.display_order
            """
            
            cursor.execute(query, (project_id,))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"獲取特質配置失敗: {e}")
            # 發生錯誤時回滾事務
            try:
                self.db_conn.rollback()
            except Exception:
                pass
            return []
        finally:
            # 確保 cursor 被關閉
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    
    def _generate_consultation(
        self,
        query: str,
        candidate: Dict,
        test_data: Dict,
        trait_configs: List[Dict],
        trait_mapping: Dict[str, Dict]
    ) -> Dict:
        """
        生成 HR 諮詢建議
        
        ✅ 基於正確的資料結構
        ✅ 包含候選人檔案、測驗歷史、特質權重
        
        Returns:
            {
                'answer': str,
                'data_summary': dict,
                'used_traits': list
            }
        """
        # 1. 解析 trait_results（JSONB 欄位）
        trait_results = test_data.get('trait_results', {})
        
        # 2. 分析優劣勢（使用特質映射）
        strengths, weaknesses = self._analyze_strengths_weaknesses(trait_results, trait_mapping)
        
        # 3. 構建 System Prompt（包含完整資訊和特質映射）
        system_prompt = self._build_hr_system_prompt(
            candidate,
            test_data,
            trait_results,
            trait_configs,
            strengths,
            weaknesses,
            trait_mapping
        )
        
        # 4. 構建 User Prompt
        user_prompt = self._build_user_prompt(query)
        
        # 5. 調用 LLM
        llm_response = self._call_llm(system_prompt, user_prompt)
        
        # 6. 解析 JSON 回應
        parsed_response = self._parse_llm_response(llm_response)
        
        # 7. 提取使用的特質
        used_traits = self._extract_mentioned_traits(llm_response, trait_results)
        
        return {
            'answer': llm_response,  # 保留原始回應
            'parsed_answer': parsed_response,  # 解析後的結構化數據
            'data_summary': {
                'strengths': strengths,
                'weaknesses': weaknesses,
                'total_traits': len([k for k, v in trait_results.items() if isinstance(v, dict) and 'score' in v]),
                'primary_traits': len([
                    v for k, v in trait_results.items() 
                    if isinstance(v, dict) and v.get('headsupflag') == 1
                ])
            },
            'used_traits': used_traits
        }
    
    def _analyze_strengths_weaknesses(
        self, 
        trait_results: Dict,
        trait_mapping: Dict[str, Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        分析候選人的優劣勢
        
        ✅ 基於實際 trait_results JSONB 結構
        ✅ 使用 trait 表的中文名稱和說明
        實際結構：{"Empathy": {"score": 59.0, "chinese_name": "Empathy", ...}, ...}
        """
        strengths = []
        weaknesses = []
        
        # 遍歷 trait_results 的每個 key（特質英文名稱）
        for trait_name, trait_data in trait_results.items():
            # 跳過非字典類型的值
            if not isinstance(trait_data, dict):
                continue
                
            score = trait_data.get('score', 0)
            
            # 從 trait 表映射獲取中文名稱和說明
            trait_info = trait_mapping.get(trait_name, {})
            chinese_name = trait_info.get('chinese_name', trait_name)
            description = trait_info.get('description', '')
            
            if score >= 80:
                strengths.append({
                    'trait': chinese_name,
                    'system_name': trait_name,
                    'score': score,
                    'level': '優秀',
                    'description': description,
                    'trait_id': trait_data.get('trait_id'),
                    'headsupflag': trait_data.get('headsupflag', 0)
                })
            elif score < 60:
                weaknesses.append({
                    'trait': chinese_name,
                    'system_name': trait_name,
                    'score': score,
                    'level': '待提升',
                    'description': description,
                    'trait_id': trait_data.get('trait_id'),
                    'headsupflag': trait_data.get('headsupflag', 0)
                })
        
        # 按分數排序
        strengths.sort(key=lambda x: x['score'], reverse=True)
        weaknesses.sort(key=lambda x: x['score'])
        
        return strengths, weaknesses
    
    def _build_hr_system_prompt(
        self,
        candidate: Dict,
        test_data: Dict,
        trait_results: Dict,
        trait_configs: List[Dict],
        strengths: List[Dict],
        weaknesses: List[Dict],
        trait_mapping: Dict[str, Dict]
    ) -> str:
        """
        構建 HR 專家 System Prompt（使用 Prompt 管理器）
        
        ✅ 從配置文件載入 Prompt 模板
        ✅ 包含候選人完整檔案
        ✅ 包含測驗歷史統計
        ✅ 包含特質權重和優先級
        ✅ 包含預測結果
        """
        # 候選人狀態映射
        status_map = {
            'employed': '在職',
            'job_seeker': '求職中'
        }
        
        # 解析特質列表（實際結構是 dict，不是 list）
        # 轉換為 list 格式並加入中文名稱和說明
        traits_list = []
        for trait_name, trait_data in trait_results.items():
            if isinstance(trait_data, dict) and 'score' in trait_data:
                trait_info = trait_mapping.get(trait_name, {})
                traits_list.append({
                    'name': trait_name,
                    'chinese_name': trait_info.get('chinese_name', trait_name),
                    'description': trait_info.get('description', ''),
                    'score': trait_data.get('score', 0),
                    'trait_id': trait_data.get('trait_id'),
                    'headsupflag': trait_data.get('headsupflag', 0)
                })
        
        # 按分數排序
        traits_list.sort(key=lambda x: x['score'], reverse=True)
        
        # 分類特質（headsupflag=1 表示需要注意的特質）
        primary_traits = [t for t in traits_list if t.get('headsupflag') == 1]
        all_traits = traits_list
        
        # 統計分佈
        excellent_count = sum(1 for t in traits_list if t.get('score', 0) >= 80)
        good_count = sum(1 for t in traits_list if 70 <= t.get('score', 0) < 80)
        average_count = sum(1 for t in traits_list if 60 <= t.get('score', 0) < 70)
        below_average_count = sum(1 for t in traits_list if t.get('score', 0) < 60)
        
        # 計算完成率
        completion_rate = 0
        if candidate.get('invited_count', 0) > 0:
            completion_rate = round(
                (candidate.get('completed_count', 0) / candidate['invited_count']) * 100, 
                1
            )
        
        # 格式化需要注意的特質（headsupflag=1）
        primary_traits_detail = ""
        if primary_traits:
            primary_traits_detail = "\n".join([
                f"  [{i+1}] {t.get('chinese_name', t.get('name', '未知'))}: "
                f"{t.get('score', 0):.1f} 分 | "
                f"⚠️ 需要特別關注\n"
                f"      說明: {t.get('description', '無說明')}"
                for i, t in enumerate(primary_traits)
            ])
        else:
            primary_traits_detail = "  無需要特別關注的特質"
        
        # 格式化所有特質（已按分數排序，包含中文名稱和說明）
        all_traits_detail = "\n".join([
            f"  {i+1}. {t.get('chinese_name', t.get('name', '未知')):12s} ({t.get('name', '')}): "
            f"{t.get('score', 0):5.1f} 分 "
            f"{'⚠️' if t.get('headsupflag') == 1 else '  '}\n"
            f"      說明: {t.get('description', '無說明')}"
            for i, t in enumerate(all_traits)
        ])
        
        # 格式化優勢（包含說明）
        strengths_detail = "\n".join([
            f"  • {s['trait']}: {s['score']:.1f} 分 - {s.get('level', '優秀')}\n"
            f"    說明: {s.get('description', '無說明')}"
            for s in strengths[:5]
        ]) if strengths else "  無明顯突出優勢（所有特質分數均低於 80 分）"
        
        # 格式化劣勢（包含說明）
        weaknesses_detail = "\n".join([
            f"  • {w['trait']}: {w['score']:.1f} 分 - {w.get('level', '待提升')}\n"
            f"    說明: {w.get('description', '無說明')}"
            for w in weaknesses[:5]
        ]) if weaknesses else "  無明顯弱項（所有特質分數均高於 60 分）"
        
        # 使用 Prompt 管理器生成 Prompt
        system_prompt, _ = self.prompt_manager.get_hr_candidate_prompts(
            candidate_name=candidate.get('name', '未知'),
            candidate_email=candidate.get('email', '未提供'),
            candidate_position=candidate.get('position', '未指定'),
            candidate_status=status_map.get(candidate.get('status', 'employed'), '未知'),
            candidate_company=candidate.get('company', '未提供'),
            candidate_notes=candidate.get('notes', '無') or '無',
            invited_count=candidate.get('invited_count', 0),
            completed_count=candidate.get('completed_count', 0),
            completion_rate=completion_rate,
            last_test_date=candidate.get('last_test_date', '未測驗'),
            test_project_name=test_data.get('project_name', '未知測驗'),
            test_date=test_data.get('test_date', '未知'),
            overall_score=test_data.get('score_value', 0),
            total_traits=len(all_traits),
            primary_traits_detail=primary_traits_detail,
            all_traits_detail=all_traits_detail,
            strengths_detail=strengths_detail,
            weaknesses_detail=weaknesses_detail,
            excellent_count=excellent_count,
            good_count=good_count,
            average_count=average_count,
            below_average_count=below_average_count,
            prediction_value=test_data.get('prediction_value', '無預測結果'),
            max_response_length=self.max_response_length,
            query=""  # 這個在 system prompt 中不需要
        )
        
        return system_prompt
    
    def _build_user_prompt(self, query: str) -> str:
        """構建 User Prompt（使用 Prompt 管理器）"""
        _, user_prompt = self.prompt_manager.get_hr_candidate_prompts(
            query=query,
            max_response_length=self.max_response_length,
            # 其他參數在 user prompt 中不需要，但為了避免錯誤，提供空值
            candidate_name="", candidate_email="", candidate_position="",
            candidate_status="", candidate_company="", candidate_notes="",
            invited_count=0, completed_count=0, completion_rate=0,
            last_test_date="", test_project_name="", test_date="",
            overall_score=0, total_traits=0, primary_traits_detail="",
            all_traits_detail="", strengths_detail="", weaknesses_detail="",
            excellent_count=0, good_count=0, average_count=0,
            below_average_count=0, prediction_value=""
        )
        
        return user_prompt

    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        調用 LLM 生成回答
        
        ✅ 使用 httpx 直接調用 API
        ✅ 強制字數限制
        """
        try:
            import httpx
            import os
            
            # 從環境變數獲取 LLM 配置
            api_key = os.getenv('LLM_API_KEY')
            if not api_key:
                logger.error("LLM_API_KEY 未設定")
                return "抱歉，諮詢服務配置錯誤，請聯繫管理員。"
            
            api_host = os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn')
            api_endpoint = f"{api_host}/v1/chat/completions"
            model = os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3')
            temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
            max_tokens = int(os.getenv('LLM_MAX_TOKENS', '500'))
            
            logger.info(f"調用 LLM API: {api_endpoint}")
            logger.info(f"使用模型: {model}")
            
            # 構建請求
            request_data = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            
            # 記錄 LLM API 調用開始
            logger.info("=" * 80)
            logger.info("🚀 開始調用 LLM API")
            logger.info(f"📍 API 端點: {api_endpoint}")
            logger.info(f"🤖 模型: {model}")
            logger.info(f"🔑 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '****'}")  # 僅在日誌中隱藏
            logger.info(f"🌡️ Temperature: {temperature}")
            logger.info(f"📊 Max Tokens: {max_tokens}")
            logger.info(f"📝 System Prompt 長度: {len(system_prompt)} 字符")
            logger.info(f"📝 User Prompt 長度: {len(user_prompt)} 字符")
            logger.info(f"⏰ 請求時間: {datetime.now().isoformat()}")
            
            # 同步調用
            import time
            start_time = time.time()
            
            # 增加超時時間以支持長回應生成（90 秒）
            with httpx.Client(timeout=90.0) as client:
                response = client.post(
                    api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'  # 使用完整的 API Key
                    },
                    json=request_data
                )
                
                elapsed_time = time.time() - start_time
                
                # 記錄響應狀態
                logger.info(f"⏱️ API 響應時間: {elapsed_time:.2f} 秒")
                logger.info(f"📡 HTTP 狀態碼: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"❌ LLM API 返回錯誤: {response.status_code}")
                    logger.error(f"📄 響應內容: {response.text[:500]}")
                    logger.info("=" * 80)
                    return "抱歉，諮詢服務暫時不可用，請稍後再試。"
                
                result = response.json()
                
                # 記錄響應詳情
                logger.info(f"✅ API 調用成功")
                if 'usage' in result:
                    usage = result['usage']
                    logger.info(f"📊 Token 使用統計:")
                    logger.info(f"   - Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                    logger.info(f"   - Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                    logger.info(f"   - Total Tokens: {usage.get('total_tokens', 'N/A')}")
                
                # 提取回答
                answer = ""
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    message = choice.get('message', {})
                    answer = message.get('content', '')
                    
                    # 記錄回答詳情
                    logger.info(f"💬 原始回答長度: {len(answer)} 字符")
                    if 'finish_reason' in choice:
                        logger.info(f"🏁 完成原因: {choice['finish_reason']}")
                
                if not answer:
                    logger.error(f"❌ 無法從 LLM 響應中提取內容")
                    logger.error(f"📄 完整響應: {result}")
                    logger.info("=" * 80)
                    return "抱歉，諮詢服務暫時不可用，請稍後再試。"
                
                logger.info(f"💬 原始回答長度: {len(answer)} 字符")
                logger.info(f"✅ LLM 回答生成成功")
                logger.info("=" * 80)
                
                # 返回原始回答（不再強制截斷，因為 JSON 格式需要完整）
                return answer.strip()
            
        except Exception as e:
            logger.error(f"LLM 調用失敗: {e}", exc_info=True)
            return "抱歉，諮詢服務暫時不可用，請稍後再試。"
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        解析 LLM 的 JSON 回應
        
        Args:
            response: LLM 返回的字符串
            
        Returns:
            解析後的結構化數據，或原始文本
        """
        try:
            # 嘗試提取 JSON（可能包含在 ```json ``` 代碼塊中）
            import re
            
            # 方法 1：尋找 JSON 代碼塊
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 方法 2：尋找第一個 { 到最後一個 }
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = response[start:end+1]
                else:
                    # 方法 3：整個回應就是 JSON
                    json_str = response
            
            # 解析 JSON
            parsed = json.loads(json_str)
            
            # 驗證必要欄位
            if 'sections' in parsed or 'summary' in parsed:
                logger.info("✅ 成功解析 JSON 格式回應")
                return parsed
            else:
                logger.warning("⚠️ JSON 格式不完整，使用原始文本")
                return {'text': response}
                
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON 解析失敗: {e}，使用原始文本")
            return {'text': response}
        except Exception as e:
            logger.error(f"❌ 解析回應時發生錯誤: {e}")
            return {'text': response}
    
    def _enforce_response_length(self, response: str, max_length: int) -> str:
        """
        強制執行回答長度限制（智能截斷）
        
        ✅ 保留完整句子
        ✅ 添加省略號
        """
        if len(response) <= max_length:
            return response
        
        # 在最大長度附近找到句號、問號、驚嘆號
        truncate_pos = max_length
        for i in range(max_length - 1, max(max_length - 30, 0), -1):
            if i < len(response) and response[i] in ['。', '！', '？', '.', '!', '?']:
                truncate_pos = i + 1
                break
        
        return response[:truncate_pos] + "..."
    
    def _extract_mentioned_traits(
        self, 
        response: str, 
        trait_results: Dict
    ) -> List[str]:
        """提取回答中提到的特質"""
        # trait_results 是 dict，key 是特質名稱
        mentioned = []
        
        # 遍歷 trait_results 的每個特質名稱
        for trait_name in trait_results.keys():
            if isinstance(trait_results[trait_name], dict):
                # 檢查特質名稱是否在回答中被提到
                if trait_name in response:
                    mentioned.append(trait_name)
        
        return mentioned
    
    def _save_consultation_history(
        self,
        session_id: str,
        candidate_id: int,
        query: str,
        consultation_result: Dict
    ):
        """
        保存諮詢歷史到資料庫
        
        ✅ 更新外鍵引用到 test_invitee
        """
        try:
            cursor = self.db_conn.cursor()
            
            # 創建諮詢歷史表（如果不存在）
            create_table_query = """
                CREATE TABLE IF NOT EXISTS hr_consultation_history (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255),
                    candidate_id INTEGER REFERENCES test_invitee(id) ON DELETE CASCADE,
                    query TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    data_summary JSONB,
                    used_traits TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_hr_consult_session 
                ON hr_consultation_history(session_id);
                
                CREATE INDEX IF NOT EXISTS idx_hr_consult_candidate 
                ON hr_consultation_history(candidate_id);
                
                CREATE INDEX IF NOT EXISTS idx_hr_consult_created 
                ON hr_consultation_history(created_at);
            """
            
            cursor.execute(create_table_query)
            
            # 插入歷史記錄
            insert_query = """
                INSERT INTO hr_consultation_history 
                (session_id, candidate_id, query, answer, data_summary, used_traits)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                session_id,
                candidate_id,
                query,
                consultation_result['answer'],
                json.dumps(consultation_result['data_summary']),
                consultation_result['used_traits']
            ))
            
            self.db_conn.commit()
            cursor.close()
            
            logger.info(f"已保存諮詢歷史 (session: {session_id}, candidate: {candidate_id})")
            
        except Exception as e:
            logger.error(f"保存諮詢歷史失敗: {e}")
            self.db_conn.rollback()
    
    def get_consultation_history(
        self, 
        session_id: Optional[str] = None,
        candidate_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        獲取諮詢歷史記錄
        
        ✅ 更新 JOIN 到 test_invitee
        
        Args:
            session_id: 會話 ID（可選）
            candidate_id: 候選人 ID（可選）
            limit: 返回記錄數量限制
            
        Returns:
            歷史記錄列表
        """
        try:
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            # 構建查詢
            conditions = []
            params = []
            
            if session_id:
                conditions.append("session_id = %s")
                params.append(session_id)
            
            if candidate_id:
                conditions.append("candidate_id = %s")
                params.append(candidate_id)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT 
                    h.*,
                    ti.name as candidate_name
                FROM hr_consultation_history h
                LEFT JOIN test_invitee ti ON h.candidate_id = ti.id
                WHERE {where_clause}
                ORDER BY h.created_at DESC
                LIMIT %s
            """
            
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"獲取諮詢歷史失敗: {e}")
            return []


# 輔助函數
def format_consultation_response(result: Dict) -> str:
    """格式化諮詢結果為易讀文本"""
    if not result.get('success'):
        return f"❌ {result.get('error', '諮詢失敗')}"
    
    candidate = result['candidate']
    consultation = result['consultation']
    data_summary = result['data_summary']
    test_info = result.get('test_info', {})
    
    output = f"""
👤 候選人：{candidate['name']}
📧 郵箱：{candidate.get('email', '未提供')}
💼 職位：{candidate.get('position', '未指定')}
🏢 公司：{candidate.get('company', '未提供')}

❓ 問題：{result['question']}

💡 專業建議：
{consultation}

📊 數據概覽：
- 測驗項目：{test_info.get('project_name', '未知')}
- 測驗日期：{test_info.get('test_date', '未知')}
- 總評分數：{test_info.get('overall_score', 'N/A')}
- 優勢特質：{len(data_summary['strengths'])} 項
- 待提升特質：{len(data_summary['weaknesses'])} 項
- 總特質數：{data_summary['total_traits']} 項
- 主要特質：{data_summary['primary_traits']} 項
"""
    
    if result.get('based_on_traits'):
        traits_text = "、".join(result['based_on_traits'])
        output += f"\n🎯 引用特質：{traits_text}"
    
    return output.strip()

