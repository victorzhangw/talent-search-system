#!/usr/bin/env python3
"""
修正後的人才搜索引擎
使用正確的數據庫結構（core_user + individual_test_result）
"""

import psycopg2
from typing import List, Dict, Optional, Any
from decimal import Decimal


class TalentSearchEngineFixed:

    """修正後的人才搜索引擎 - 使用正確的數據庫結構"""
    
    def __init__(self, db_conn):
        self.conn = db_conn
    
    def search_candidates(self, parsed_query: Dict, filters: Optional[Dict] = None) -> List[Dict]:
        """
        使用正確的數據庫結構搜索候選人
        
        數據庫結構:
        - core_user: 用戶主表
        - individual_profile: 個人資料（一對一）
        - individual_test_result: 測驗結果
        """
        cursor = self.conn.cursor()
        
        # 使用正確的表名和欄位
        base_sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results,
                itr.category_results,
                itr.score_value,
                itr.test_completion_date
            FROM core_user cu
            JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
              AND itr.trait_results IS NOT NULL
              AND itr.result_status = 'completed'
        """
        
        # 添加 LLM 生成的 SQL 條件
        sql_conditions = parsed_query.get('sql_conditions', [])
        has_conditions = sql_conditions and len(sql_conditions) > 0
        
        if has_conditions:
            where_clause = " AND (" + " OR ".join(sql_conditions) + ")"
            base_sql += where_clause
        
        base_sql += """
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT 50;
        """
        
        # 降級查詢（如果主查詢失敗）
        fallback_sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results,
                itr.category_results,
                itr.score_value,
                itr.test_completion_date
            FROM core_user cu
            JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
              AND itr.trait_results IS NOT NULL
              AND itr.result_status = 'completed'
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT 50;
        """
        
        print(f"\n執行 SQL:\n{base_sql}\n")
        
        try:
            cursor.execute(base_sql)
            results = cursor.fetchall()
            
            # 如果有條件但返回空結果，嘗試降級查詢
            if len(results) == 0 and has_conditions:
                print("⚠️ 主查詢返回空結果，使用降級查詢...")
                cursor.execute(fallback_sql)
                results = cursor.fetchall()
                print(f"降級查詢找到 {len(results)} 筆結果")
            
            candidates = []
            for row in results:
                candidate = {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'trait_results': row[5] if row[5] else {},
                    'category_results': row[6] if row[6] else {},
                    'score_value': float(row[7]) if row[7] else None,
                    'test_completion_date': row[8].isoformat() if row[8] else None,
                    'test_results': []  # 簡化版
                }
                candidates.append(candidate)
            
            cursor.close()
            return candidates
        
        except Exception as e:
            print(f"❌ SQL 執行錯誤: {str(e)}")
            print("使用降級查詢...")
            try:
                cursor.execute(fallback_sql)
                results = cursor.fetchall()
                print(f"✅ 降級查詢找到 {len(results)} 筆結果")
                
                candidates = []
                for row in results:
                    candidate = {
                        'id': row[0],
                        'name': row[1],
                        'email': row[2],
                        'phone': row[3],
                        'created_at': row[4].isoformat() if row[4] else None,
                        'trait_results': row[5] if row[5] else {},
                        'category_results': row[6] if row[6] else {},
                        'score_value': float(row[7]) if row[7] else None,
                        'test_completion_date': row[8].isoformat() if row[8] else None,
                        'test_results': []
                    }
                    candidates.append(candidate)
                
                cursor.close()
                return candidates
            except Exception as e2:
                print(f"❌ 降級查詢也失敗: {str(e2)}")
                cursor.close()
                return []
    
    def get_all_candidates(self, limit: int = 50) -> List[Dict]:
        """獲取所有候選人 - 使用正確的數據庫結構"""
        cursor = self.conn.cursor()
        
        sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results,
                itr.category_results,
                itr.score_value
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username IS NOT NULL
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT %s;
        """
        
        cursor.execute(sql, (limit,))
        results = cursor.fetchall()
        
        candidates = []
        for row in results:
            candidate = {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'trait_results': row[5] if row[5] else {},
                'category_results': row[6] if row[6] else {},
                'score_value': float(row[7]) if row[7] else None,
                'test_results': []
            }
            candidates.append(candidate)
        
        cursor.close()
        return candidates
    
    def find_candidate_by_name(self, name: str) -> Optional[Dict]:
        """根據姓名查找候選人 - 使用正確的數據庫結構"""
        cursor = self.conn.cursor()
        
        sql = """
            SELECT DISTINCT ON (cu.id)
                cu.id,
                cu.username as name,
                cu.email,
                (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
                cu.date_joined as created_at,
                itr.trait_results,
                itr.category_results,
                itr.score_value
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username = %s
            ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
            LIMIT 1;
        """
        
        cursor.execute(sql, (name,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'phone': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
            'trait_results': row[5] if row[5] else {},
            'category_results': row[6] if row[6] else {},
            'score_value': float(row[7]) if row[7] else None,
            'test_results': []
        }
    
    def _find_trait_score(self, trait_name: str, trait_results: Dict) -> Optional[float]:
        """
        在 trait_results 中查找特質分數
        
        trait_results 結構:
        {
            "communication": {
                "chinese_name": "溝通能力",
                "score": 82.5,
                "percentile": 75
            }
        }
        """
        if not trait_results:
            return None
        
        # 嘗試直接匹配 system_name
        if trait_name in trait_results:
            trait_data = trait_results[trait_name]
            if isinstance(trait_data, dict):
                return float(trait_data.get('score', 0))
            return float(trait_data)
        
        # 嘗試通過 chinese_name 匹配
        for key, value in trait_results.items():
            if isinstance(value, dict):
                if value.get('chinese_name') == trait_name:
                    return float(value.get('score', 0))
        
        # 嘗試部分匹配（模糊搜索）
        for key in trait_results.keys():
            if trait_name in key or key in trait_name:
                trait_data = trait_results[key]
                if isinstance(trait_data, dict):
                    return float(trait_data.get('score', 0))
                return float(trait_data)
        
        return None
    
    def calculate_match_score(self, candidate: Dict, parsed_query: Dict) -> float:
        """
        計算匹配分數 - 混合搜索策略
        
        評分邏輯:
        1. 如果沒有測評結果: 0.1
        2. 如果沒有特定要求: 0.5
        3. 根據特質匹配度計算: 0.0-1.0
        """
        matched_traits = parsed_query.get('matched_traits', [])
        trait_results = candidate.get('trait_results', {})
        
        # 沒有測評結果
        if not trait_results:
            return 0.1
        
        # 沒有特定要求，給予基礎分數
        if not matched_traits:
            return 0.5
        
        total_score = 0
        total_weight = 0
        matched_count = 0
        
        for trait in matched_traits:
            # 獲取特質名稱
            possible_names = [
                trait.get('system_name'),
                trait.get('chinese_name')
            ]
            
            weight = trait.get('weight', 1.0)
            min_score = trait.get('min_score', 0)
            
            # 嘗試找到特質分數
            actual_score = None
            for name in possible_names:
                if name:
                    actual_score = self._find_trait_score(name, trait_results)
                    if actual_score is not None:
                        break
            
            if actual_score is not None:
                # 計算加權分數
                if actual_score >= min_score:
                    # 達標：全分
                    total_score += actual_score * weight
                else:
                    # 未達標：給予部分分數（50%）
                    total_score += actual_score * weight * 0.5
                
                total_weight += 100 * weight
                matched_count += 1
        
        # 計算基礎分數
        if total_weight > 0:
            base_score = total_score / total_weight
            
            # 覆蓋率獎勵：匹配的特質越多，分數越高
            coverage_ratio = matched_count / len(matched_traits)
            coverage_bonus = coverage_ratio * 0.1
            
            final_score = min(base_score + coverage_bonus, 1.0)
            return final_score
        
        # 沒有匹配任何特質，但有測評結果
        return 0.3
    
    def generate_trait_sql_condition(self, trait_name: str, min_score: int) -> str:
        """
        生成特質查詢的 SQL 條件
        
        支持兩種查詢方式:
        1. 直接查詢 system_name
        2. 查詢 chinese_name
        """
        conditions = [
            # 方式1: 直接查詢 trait_results
            f"((trait_results->>'{trait_name}')::jsonb->>'score')::float >= {min_score}",
            
            # 方式2: 查詢中文名稱
            f"EXISTS (SELECT 1 FROM jsonb_each(trait_results) WHERE (value->>'chinese_name' = '{trait_name}' AND (value->>'score')::float >= {min_score}))"
        ]
        
        return f"({' OR '.join(conditions)})"
