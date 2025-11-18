#!/usr/bin/env python3
"""
對話上下文管理器
支援多輪對話、上下文記憶、智能推理
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class ConversationContext:
    """對話上下文"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, Any]] = []
        self.current_candidate: Optional[Dict] = None
        self.current_candidates: List[Dict] = []
        self.last_intent: Optional[str] = None
        self.last_query: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加訊息到對話歷史"""
        message = {
            'role': role,  # 'user' or 'assistant'
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def set_current_candidate(self, candidate: Dict):
        """設定當前關注的候選人"""
        self.current_candidate = candidate
        self.updated_at = datetime.now()
    
    def set_current_candidates(self, candidates: List[Dict]):
        """設定當前候選人列表"""
        self.current_candidates = candidates
        self.updated_at = datetime.now()
    
    def set_last_intent(self, intent: str):
        """設定最後的意圖"""
        self.last_intent = intent
        self.updated_at = datetime.now()
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """獲取對話歷史（最近 N 條）"""
        return self.messages[-limit:]
    
    def get_context_summary(self) -> str:
        """生成上下文摘要"""
        summary_parts = []
        
        if self.current_candidate:
            summary_parts.append(f"當前關注候選人: {self.current_candidate.get('name')}")
        
        if self.current_candidates:
            names = [c.get('name') for c in self.current_candidates[:3]]
            summary_parts.append(f"當前候選人列表: {', '.join(names)}")
        
        if self.last_intent:
            summary_parts.append(f"上一個意圖: {self.last_intent}")
        
        return " | ".join(summary_parts) if summary_parts else "無上下文"
    
    def clear(self):
        """清空上下文"""
        self.messages = []
        self.current_candidate = None
        self.current_candidates = []
        self.last_intent = None
        self.last_query = None


class ConversationManager:
    """對話管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationContext] = {}
    
    def get_or_create_session(self, session_id: str) -> ConversationContext:
        """獲取或創建會話"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationContext(session_id)
        return self.sessions[session_id]
    
    def analyze_context_intent(self, context: ConversationContext, current_query: str) -> Dict[str, Any]:
        """
        基於上下文分析意圖
        
        這個函數會考慮：
        1. 當前查詢
        2. 對話歷史
        3. 當前關注的候選人
        4. 上一個意圖
        
        返回增強的意圖分析結果
        """
        
        # 檢查是否是後續問題
        follow_up_patterns = {
            'describe': ['描述', '介紹', '說明', '特質', '能力', '優勢', '怎麼樣', '如何', '告訴我'],
            'interview': ['面試', '問題', '綱要', '準備'],
            'compare': ['比較', '對比', '差異', '哪個好'],
            'detail': ['詳細', '更多', '具體', '深入'],
            'filter_from_current': ['從裡面', '從這些', '從中', '其中', '再篩選', '進一步篩選', '縮小範圍', '過濾'],
            'filter_new': ['再找', '還要', '另外', '類似', '相似', '加上'],
            'exclude': ['排除', '不要', '去掉', '移除', '刪除', '除了'],
            'new_search': ['重新找', '換一批', '不要這些', '清空', '重新搜索'],
        }
        
        # 如果有當前候選人，檢查是否是針對該候選人的後續問題
        if context.current_candidate:
            candidate_name = context.current_candidate.get('name')
            
            # 檢查查詢中是否提到候選人
            mentions_candidate = candidate_name.lower() in current_query.lower()
            
            # 檢查是否是後續問題（沒有明確提到候選人名字）
            is_follow_up = not mentions_candidate and any(
                any(pattern in current_query for pattern in patterns)
                for patterns in follow_up_patterns.values()
            )
            
            if is_follow_up or mentions_candidate:
                # 判斷具體的後續意圖
                for intent_type, patterns in follow_up_patterns.items():
                    if any(pattern in current_query for pattern in patterns):
                        return {
                            'is_follow_up': True,
                            'follow_up_intent': intent_type,
                            'target_candidate': context.current_candidate,
                            'original_query': current_query,
                            'enhanced_query': f"{current_query} (針對 {candidate_name})"
                        }
                
                # 默認為描述意圖
                return {
                    'is_follow_up': True,
                    'follow_up_intent': 'describe',
                    'target_candidate': context.current_candidate,
                    'original_query': current_query,
                    'enhanced_query': f"描述 {candidate_name} 的特質"
                }
        
        # 檢查是否是從當前結果中篩選
        if context.current_candidates and len(context.current_candidates) > 0:
            # 檢測篩選關鍵詞
            filter_from_current_keywords = follow_up_patterns.get('filter_from_current', [])
            is_filter_from_current = any(kw in current_query for kw in filter_from_current_keywords)
            
            if is_filter_from_current:
                return {
                    'is_follow_up': True,
                    'follow_up_intent': 'filter_from_current',
                    'target_candidates': context.current_candidates,
                    'original_query': current_query,
                    'enhanced_query': f"從 {len(context.current_candidates)} 位候選人中篩選: {current_query}",
                    'scope': 'current',
                    'previous_count': len(context.current_candidates)
                }
            
            # 檢測比較意圖
            if any(word in current_query for word in ['比較', '對比', '哪個', '選擇']):
                return {
                    'is_follow_up': True,
                    'follow_up_intent': 'compare',
                    'target_candidates': context.current_candidates,
                    'original_query': current_query,
                    'enhanced_query': f"比較這些候選人: {', '.join([c.get('name') for c in context.current_candidates[:3]])}"
                }
            
            # 檢測排除意圖
            exclude_keywords = follow_up_patterns.get('exclude', [])
            if any(kw in current_query for kw in exclude_keywords):
                return {
                    'is_follow_up': True,
                    'follow_up_intent': 'exclude',
                    'target_candidates': context.current_candidates,
                    'original_query': current_query,
                    'enhanced_query': f"從 {len(context.current_candidates)} 位候選人中排除某些人",
                    'scope': 'current'
                }
        
        # 檢測新搜索意圖
        new_search_keywords = follow_up_patterns.get('new_search', [])
        if any(kw in current_query for kw in new_search_keywords):
            return {
                'is_follow_up': True,
                'follow_up_intent': 'new_search',
                'original_query': current_query,
                'enhanced_query': current_query,
                'scope': 'all'
            }
        
        # 不是後續問題
        return {
            'is_follow_up': False,
            'original_query': current_query,
            'scope': 'all'
        }
    
    def generate_context_aware_prompt(self, context: ConversationContext, current_query: str) -> str:
        """生成包含上下文的 Prompt"""
        
        prompt_parts = ["# 對話上下文\n"]
        
        # 添加對話歷史
        if context.messages:
            prompt_parts.append("## 對話歷史（最近 3 輪）:")
            for msg in context.get_conversation_history(limit=6):  # 3 輪 = 6 條訊息
                role = "用戶" if msg['role'] == 'user' else "助手"
                prompt_parts.append(f"- {role}: {msg['content'][:100]}")
        
        # 添加當前關注的候選人
        if context.current_candidate:
            candidate = context.current_candidate
            prompt_parts.append(f"\n## 當前關注的候選人:")
            prompt_parts.append(f"- 姓名: {candidate.get('name')}")
            prompt_parts.append(f"- Email: {candidate.get('email')}")
            
            if candidate.get('trait_results'):
                prompt_parts.append(f"- 特質數量: {len(candidate.get('trait_results', {}))}")
        
        # 添加當前查詢
        prompt_parts.append(f"\n## 當前查詢:")
        prompt_parts.append(f"{current_query}")
        
        prompt_parts.append("\n請基於以上上下文，理解用戶的真實意圖。")
        
        return "\n".join(prompt_parts)
    
    def should_auto_describe(self, context: ConversationContext, search_result: Dict) -> bool:
        """
        判斷是否應該自動描述候選人
        
        條件：
        1. 搜索到了單一候選人
        2. 是通過姓名搜索的
        3. 沒有其他明確的意圖
        """
        
        # 只找到一個候選人
        if search_result.get('total') != 1:
            return False
        
        # 檢查查詢是否是簡單的姓名搜索
        query = context.last_query or ""
        simple_search_patterns = ['找', '找到', '搜索', '查找', '有沒有']
        
        is_simple_search = any(pattern in query for pattern in simple_search_patterns)
        
        # 沒有其他複雜意圖
        no_complex_intent = not any(word in query for word in [
            '面試', '比較', '統計', '列出', '特質', '能力'
        ])
        
        return is_simple_search and no_complex_intent


# 全域對話管理器實例
conversation_manager = ConversationManager()
