#!/usr/bin/env python3
"""
對話增強搜索模塊
整合對話上下文管理，實現智能多輪對話
"""

from typing import Dict, Any, List, Optional
from conversation_manager import conversation_manager, ConversationContext
import httpx
import json


class ConversationEnhancedSearch:
    """對話增強搜索引擎"""
    
    def __init__(self, llm_service, talent_search_engine):
        self.llm_service = llm_service
        self.engine = talent_search_engine
    
    async def process_query_with_context(
        self, 
        query: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        處理帶上下文的查詢
        
        流程：
        1. 獲取會話上下文
        2. 分析是否為後續問題
        3. 如果是後續問題，自動補充上下文
        4. 執行搜索或其他操作
        5. 更新上下文
        """
        
        # 獲取會話上下文
        context = conversation_manager.get_or_create_session(session_id)
        context.last_query = query
        context.add_message('user', query)
        
        # 分析上下文意圖
        context_analysis = conversation_manager.analyze_context_intent(context, query)
        
        print(f"\n🔍 上下文分析:")
        print(f"   是否為後續問題: {context_analysis.get('is_follow_up')}")
        if context_analysis.get('is_follow_up'):
            print(f"   後續意圖: {context_analysis.get('follow_up_intent')}")
            print(f"   增強查詢: {context_analysis.get('enhanced_query')}")
        
        # 如果是後續問題，直接處理
        if context_analysis.get('is_follow_up'):
            result = await self._handle_follow_up_query(context, context_analysis, query)
            
            # 更新上下文
            if result.get('response'):
                context.add_message('assistant', result['response'][:200])
            
            return result
        
        # 否則，正常處理查詢
        result = await self._handle_new_query(context, query)
        
        # 更新上下文
        if result.get('response'):
            context.add_message('assistant', result['response'][:200])
        
        return result
    
    async def _handle_follow_up_query(
        self, 
        context: ConversationContext,
        context_analysis: Dict,
        query: str
    ) -> Dict[str, Any]:
        """處理後續問題"""
        
        follow_up_intent = context_analysis.get('follow_up_intent')
        target_candidate = context_analysis.get('target_candidate')
        
        if follow_up_intent == 'describe':
            # 描述候選人特質
            return await self._describe_candidate(target_candidate, query)
        
        elif follow_up_intent == 'interview':
            # 生成面試綱要
            return await self._generate_interview_guide(target_candidate, query)
        
        elif follow_up_intent == 'compare':
            # 比較候選人
            target_candidates = context_analysis.get('target_candidates', [])
            return await self._compare_candidates(target_candidates, query)
        
        elif follow_up_intent == 'detail':
            # 提供更多細節
            return await self._provide_details(target_candidate, query)
        
        else:
            # 默認：描述候選人
            return await self._describe_candidate(target_candidate, query)
    
    async def _handle_new_query(
        self, 
        context: ConversationContext,
        query: str
    ) -> Dict[str, Any]:
        """處理新查詢"""
        
        # 使用 LLM 解析查詢
        parsed_query = await self.engine.parse_query(query)
        intent = parsed_query.get('intent', 'search')
        entities = parsed_query.get('entities', {})
        
        context.set_last_intent(intent)
        
        # 根據意圖處理
        if intent == 'search':
            # 搜索候選人
            candidate_name = entities.get('candidate_name')
            
            if candidate_name:
                # 搜索特定候選人
                candidate = self.engine.find_candidate_by_name(candidate_name)
                
                if candidate:
                    # 找到候選人，設定為當前候選人
                    context.set_current_candidate(candidate)
                    
                    # 自動描述候選人
                    return await self._describe_candidate(candidate, query, auto=True)
                else:
                    return {
                        'success': False,
                        'response': f"找不到候選人：{candidate_name}",
                        'suggestions': ['列出所有候選人', '檢查姓名拼寫']
                    }
            else:
                # 按特質搜索
                candidates = self.engine.search_candidates(parsed_query)
                
                if candidates:
                    context.set_current_candidates(candidates)
                    
                    return {
                        'success': True,
                        'response': f"找到 {len(candidates)} 位符合條件的候選人",
                        'candidates': candidates,
                        'suggestions': [
                            '查看第一位候選人的詳細資料',
                            '比較這些候選人',
                            '為候選人準備面試'
                        ]
                    }
                else:
                    return {
                        'success': False,
                        'response': '沒有找到符合條件的候選人',
                        'suggestions': ['調整搜索條件', '列出所有候選人']
                    }
        
        # 其他意圖...
        return {
            'success': True,
            'response': f"處理意圖: {intent}",
            'intent': intent
        }
    
    async def _describe_candidate(
        self, 
        candidate: Dict, 
        query: str,
        auto: bool = False
    ) -> Dict[str, Any]:
        """描述候選人特質"""
        
        trait_results = candidate.get('trait_results', {})
        
        if not trait_results:
            return {
                'success': False,
                'response': f"{candidate.get('name')} 尚未完成測評",
                'candidate': candidate
            }
        
        # 使用 LLM 生成描述
        description = await self._generate_candidate_description(candidate, query, auto)
        
        return {
            'success': True,
            'response': description,
            'candidate': candidate,
            'suggestions': [
                f"為 {candidate.get('name')} 設計面試綱要",
                "搜索類似特質的人才",
                "查看其他候選人"
            ]
        }
    
    async def _generate_candidate_description(
        self, 
        candidate: Dict, 
        query: str,
        auto: bool = False
    ) -> str:
        """使用 LLM 生成候選人描述"""
        
        trait_results = candidate.get('trait_results', {})
        
        # 分類特質
        strengths = []
        moderate = []
        weaknesses = []
        
        for trait_name, trait_data in trait_results.items():
            if isinstance(trait_data, dict):
                score = trait_data.get('score', 0)
                if score >= 80:
                    strengths.append(f"{trait_name} ({score}分)")
                elif score >= 60:
                    moderate.append(f"{trait_name} ({score}分)")
                else:
                    weaknesses.append(f"{trait_name} ({score}分)")
        
        prompt = f"""
請為候選人 {candidate.get('name')} 生成一段簡潔的特質描述。

**優勢特質** (≥80分):
{chr(10).join(f'• {s}' for s in strengths[:5]) if strengths else '• 無明顯優勢'}

**中等特質** (60-80分):
{chr(10).join(f'• {m}' for m in moderate[:3]) if moderate else '• 無'}

**待發展特質** (<60分):
{chr(10).join(f'• {w}' for w in weaknesses[:2]) if weaknesses else '• 無明顯劣勢'}

請生成：

## 📋 {candidate.get('name')} 的特質概況

### 整體印象
用 2-3 句話概括這位候選人的整體特質。

### 核心優勢
列出 3-5 個最突出的優勢，每個用一句話說明。

### 適合職位
基於特質分析，這位候選人適合什麼類型的職位？

### 注意事項
有哪些方面需要在面試時特別關注？

請用繁體中文，簡潔專業。
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.llm_service.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.llm_service.api_key}'
                    },
                    json={
                        'model': self.llm_service.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': '你是一位專業的人力資源顧問，擅長分析候選人特質。'
                            },
                            {
                                'role': 'user',
                                'content': prompt
                            }
                        ],
                        'temperature': 0.7,
                        'max_tokens': 1000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    if auto:
                        prefix = f"✅ 找到候選人：{candidate.get('name')}\n\n"
                        return prefix + content
                    else:
                        return content
                else:
                    return self._generate_simple_description(candidate, strengths, moderate)
        
        except Exception as e:
            print(f"生成描述錯誤: {str(e)}")
            return self._generate_simple_description(candidate, strengths, moderate)
    
    def _generate_simple_description(
        self, 
        candidate: Dict, 
        strengths: List[str],
        moderate: List[str]
    ) -> str:
        """簡單的描述生成（降級方案）"""
        
        parts = [f"## {candidate.get('name')} 的特質概況\n"]
        
        if strengths:
            parts.append("### 核心優勢")
            parts.extend([f"• {s}" for s in strengths[:5]])
            parts.append("")
        
        if moderate:
            parts.append("### 中等特質")
            parts.extend([f"• {m}" for m in moderate[:3]])
            parts.append("")
        
        parts.append(f"Email: {candidate.get('email')}")
        
        return "\n".join(parts)
    
    async def _generate_interview_guide(
        self, 
        candidate: Dict, 
        query: str
    ) -> Dict[str, Any]:
        """生成面試綱要"""
        
        guide = await self.engine.generate_interview_guide(candidate, query)
        
        return {
            'success': True,
            'response': guide,
            'candidate': candidate,
            'suggestions': [
                f"查看 {candidate.get('name')} 的詳細測評",
                "搜索類似的候選人",
                "比較其他候選人"
            ]
        }
    
    async def _compare_candidates(
        self, 
        candidates: List[Dict], 
        query: str
    ) -> Dict[str, Any]:
        """比較候選人"""
        
        comparison = await self.engine.generate_comparison(candidates, query)
        
        return {
            'success': True,
            'response': comparison,
            'candidates': candidates,
            'suggestions': [
                "查看候選人詳細資料",
                "為候選人準備面試",
                "搜索更多候選人"
            ]
        }
    
    async def _provide_details(
        self, 
        candidate: Dict, 
        query: str
    ) -> Dict[str, Any]:
        """提供更多細節"""
        
        trait_results = candidate.get('trait_results', {})
        
        # 生成詳細的特質分析
        details = []
        details.append(f"## {candidate.get('name')} 的詳細特質分析\n")
        
        for trait_name, trait_data in trait_results.items():
            if isinstance(trait_data, dict):
                score = trait_data.get('score', 0)
                percentile = trait_data.get('percentile', 0)
                description = trait_data.get('description', '')
                
                details.append(f"### {trait_name}")
                details.append(f"- 分數: {score}/100")
                details.append(f"- 百分位: {percentile}%")
                details.append(f"- 說明: {description}")
                details.append("")
        
        return {
            'success': True,
            'response': "\n".join(details),
            'candidate': candidate,
            'suggestions': [
                f"為 {candidate.get('name')} 設計面試綱要",
                "比較其他候選人",
                "搜索類似特質的人才"
            ]
        }
