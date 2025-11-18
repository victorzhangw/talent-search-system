#!/usr/bin/env python3
"""
人才聊天搜索 API v2.0
修正版：使用正確的 test_project_result 表
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
from datetime import datetime
import os
import uvicorn
import httpx
import asyncio
from interview_api import router as interview_router
from talent_analysis_service import TalentAnalysisService
from conversation_manager import conversation_manager

# 資料庫連接配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PATH = os.path.join(SCRIPT_DIR, 'private-key-openssh.pem')

DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': PRIVATE_KEY_PATH,
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'projectdb',
    'db_user': 'projectuser',
    'db_password': 'projectpass'
}

# LLM API 配置
LLM_CONFIG = {
    'api_key': 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff',
    'api_host': 'https://api.siliconflow.cn',
    'model': 'deepseek-ai/DeepSeek-V3',
    'endpoint': 'https://api.siliconflow.cn/v1/chat/completions'
}

# FastAPI 應用
app = FastAPI(title="人才聊天搜索 API v2.0", version="2.0.0")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含面試問題路由
app.include_router(interview_router)

# 全域變數
tunnel = None
db_conn = None
trait_cache = {}  # 緩存特質定義

# 資料模型
class SearchQuery(BaseModel):
    query: str
    session_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    previous_candidate_ids: Optional[List[int]] = None  # 上一輪的候選人 ID 列表

class Candidate(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    test_results: List[Dict[str, Any]] = []
    trait_results: Optional[Dict[str, Any]] = {}
    match_score: float
    match_reason: str
    ai_analysis: Optional[Dict[str, Any]] = None  # 新增 AI 分析結果

class SearchResponse(BaseModel):
    candidates: List[Candidate]
    total: int
    query_understanding: str
    suggestions: List[str]

# 資料庫連接管理
def get_db_connection():
    """取得資料庫連接"""
    global tunnel, db_conn
    
    if db_conn is None or db_conn.closed:
        if tunnel is None or not tunnel.is_active:
            tunnel = SSHTunnelForwarder(
                (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
                ssh_username=DB_CONFIG['ssh_username'],
                ssh_pkey=DB_CONFIG['ssh_private_key'],
                remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
            )
            tunnel.start()
        
        db_conn = psycopg2.connect(
            host='localhost',
            port=tunnel.local_bind_port,
            database=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_password']
        )
    
    return db_conn

def load_trait_definitions():
    """載入特質定義到緩存"""
    global trait_cache
    
    if trait_cache:
        return trait_cache
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, chinese_name, system_name, description
        FROM trait
        ORDER BY id;
    """)
    
    for row in cursor.fetchall():
        trait_id, chinese_name, system_name, description = row
        trait_cache[system_name] = {
            'id': trait_id,
            'chinese_name': chinese_name,
            'system_name': system_name,
            'description': description
        }
    
    cursor.close()
    print(f"✓ 載入 {len(trait_cache)} 個特質定義")
    return trait_cache

def enrich_trait_results(trait_results: Dict) -> Dict:
    """豐富特質結果，添加中文名稱和描述"""
    if not trait_results:
        return {}
    
    traits = load_trait_definitions()
    enriched = {}
    
    for trait_key, trait_data in trait_results.items():
        # trait_key 是 trait_results 中的 key (如 "Hope", "Creative Thinking")
        # 需要從 trait 表中查找對應的中文名稱
        
        if trait_key in traits:
            # 找到對應的特質定義
            trait_def = traits[trait_key]
            
            if isinstance(trait_data, dict):
                enriched[trait_key] = {
                    **trait_data,
                    'chinese_name': trait_def['chinese_name'],
                    'description': trait_def['description']
                }
            else:
                enriched[trait_key] = {
                    'score': trait_data,
                    'chinese_name': trait_def['chinese_name'],
                    'description': trait_def['description']
                }
        else:
            # 如果找不到對應的特質定義，保留原始數據
            if isinstance(trait_data, dict):
                enriched[trait_key] = trait_data
            else:
                enriched[trait_key] = {'score': trait_data, 'chinese_name': trait_key}
    
    return enriched

# LLM 服務
class LLMService:
    """LLM 服務 - 智能查詢分析"""
    
    def __init__(self):
        self.api_key = LLM_CONFIG['api_key']
        self.api_endpoint = LLM_CONFIG['endpoint']
        self.model = LLM_CONFIG['model']
        self.available_traits = list(trait_cache.values())
    
    def get_trait_analysis_prompt(self) -> str:
        """生成特質分析 Prompt"""
        traits_list = []
        for trait in self.available_traits[:50]:  # 所有 50 個特質
            traits_list.append(
                f"- {trait['chinese_name']} ({trait['system_name']}): {trait['description']}"
            )
        
        traits_text = '\n'.join(traits_list)
        
        return f"""你是一個專業的人才搜索助手。

用戶會用自然語言描述他們需要的人才，你需要：
1. 理解用戶的需求
2. 從以下特質列表中，選擇最匹配的 1-3 個特質
3. 為每個特質設定最低分數要求（0-100）

**可用的特質列表**：
{traits_text}

請以 JSON 格式輸出：
{{
  "matched_traits": [
    {{
      "system_name": "特質系統名稱",
      "chinese_name": "特質中文名稱",
      "min_score": 70,
      "reason": "為什麼選擇這個特質"
    }}
  ],
  "summary": "需求摘要",
  "understanding": "對用戶需求的理解"
}}

**重要規則**：
1. 只選擇 1-3 個最相關的特質
2. min_score 通常設定為 70-80 分
3. 如果用戶需求模糊，選擇最可能的特質
4. 只輸出 JSON，不要有其他文字"""
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """使用 LLM 分析查詢"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}'
                    },
                    json={
                        'model': self.model,
                        'messages': [
                            {
                                'role': 'system',
                                'content': self.get_trait_analysis_prompt()
                            },
                            {
                                'role': 'user',
                                'content': f'請分析以下人才需求：\n\n{query}'
                            }
                        ],
                        'temperature': 0.3,
                        'max_tokens': 1000,
                        'response_format': {'type': 'json_object'}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    analysis = json.loads(content)
                    
                    print(f"\n🤖 LLM 分析結果:")
                    print(f"   理解: {analysis.get('understanding', '')}")
                    print(f"   匹配特質: {len(analysis.get('matched_traits', []))} 個")
                    for trait in analysis.get('matched_traits', []):
                        print(f"     • {trait['chinese_name']} ({trait['system_name']}) >= {trait['min_score']}")
                    
                    return {
                        'success': True,
                        'analysis': analysis
                    }
                else:
                    print(f"❌ LLM API 錯誤: {response.status_code}")
                    return {'success': False, 'error': 'LLM API 錯誤'}
        
        except Exception as e:
            print(f"❌ LLM 分析錯誤: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def generate_match_reason(self, candidate: Dict, query: str, matched_traits: List[Dict]) -> str:
        """生成匹配理由"""
        trait_results = candidate.get('trait_results', {})
        
        # 提取匹配的特質分數
        matched_scores = []
        for trait in matched_traits:
            system_name = trait['system_name']
            if system_name in trait_results:
                trait_data = trait_results[system_name]
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 0)
                    chinese_name = trait_data.get('chinese_name', trait['chinese_name'])
                    matched_scores.append(f"{chinese_name}({score:.0f}分)")
        
        if matched_scores:
            return f"匹配特質：{', '.join(matched_scores)}"
        else:
            return f"已完成 {len(trait_results)} 項特質測評"

# 人才搜索引擎
class TalentSearchEngine:
    """人才搜索引擎 - 使用 test_project_result + LLM 智能搜索"""
    
    def __init__(self):
        self.conn = get_db_connection()
        load_trait_definitions()
        self.llm_service = LLMService()
    
    def filter_candidates_by_traits(self, candidates: List[Dict], matched_traits: List[Dict]) -> List[Dict]:
        """
        從指定的候選人列表中，根據特質篩選
        
        Args:
            candidates: 候選人列表
            matched_traits: 匹配的特質條件
            
        Returns:
            篩選後的候選人列表
        """
        filtered = []
        
        print(f"\n🔍 從 {len(candidates)} 位候選人中篩選...")
        print(f"   篩選條件: {len(matched_traits)} 個特質")
        
        for candidate in candidates:
            trait_results = candidate.get('trait_results', {})
            
            # 檢查是否符合任一特質條件
            matches_any = False
            for trait in matched_traits:
                system_name = trait['system_name']
                min_score = trait['min_score']
                
                if system_name in trait_results:
                    trait_data = trait_results[system_name]
                    if isinstance(trait_data, dict):
                        score = trait_data.get('score', 0)
                        if score >= min_score:
                            matches_any = True
                            break
            
            if matches_any:
                filtered.append(candidate)
        
        print(f"✓ 篩選後剩餘 {len(filtered)} 位候選人")
        return filtered
    
    def get_all_candidates(self, limit: int = 50) -> List[Dict]:
        """獲取所有候選人 - 使用 test_project_result"""
        cursor = self.conn.cursor()
        
        sql = """
            SELECT 
                tiv.id,
                tiv.name,
                tiv.email,
                tiv.phone,
                tiv.company,
                tiv.position,
                tp.name as project_name,
                tpr.trait_results,
                tpr.category_results,
                tpr.score_value,
                tpr.prediction_value,
                tpr.crawled_at
            FROM test_project_result tpr
            INNER JOIN test_invitation ti ON tpr.test_invitation_id = ti.id
            INNER JOIN test_invitee tiv ON ti.invitee_id = tiv.id
            INNER JOIN test_project tp ON tpr.test_project_id = tp.id
            WHERE tpr.trait_results IS NOT NULL
              AND tpr.trait_results != '{}'::jsonb
            ORDER BY tpr.crawled_at DESC
            LIMIT %s;
        """
        
        print(f"\n🔍 執行查詢: get_all_candidates (limit={limit})")
        cursor.execute(sql, (limit,))
        results = cursor.fetchall()
        print(f"✓ 查詢返回 {len(results)} 筆記錄")
        
        candidates = []
        for row in results:
            # 豐富特質結果，添加中文名稱
            trait_results = enrich_trait_results(row[7] if row[7] else {})
            
            candidate = {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'company': row[4],
                'position': row[5],
                'project_name': row[6],
                'trait_results': trait_results,
                'category_results': row[8] if row[8] else {},
                'score_value': row[9],
                'prediction_value': row[10],
                'test_date': row[11].isoformat() if row[11] else None
            }
            candidates.append(candidate)
            
            print(f"  候選人 {row[1]}: {len(trait_results)} 個特質")
        
        cursor.close()
        return candidates
    
    def search_by_multiple_traits(self, matched_traits: List[Dict], limit: int = 50, previous_candidate_ids: Optional[List[int]] = None) -> List[Dict]:
        """根據多個特質搜索候選人"""
        cursor = self.conn.cursor()
        
        # 構建 WHERE 條件
        where_conditions = []
        params = []
        
        for trait in matched_traits:
            system_name = trait['system_name']
            min_score = trait['min_score']
            where_conditions.append(
                f"(tpr.trait_results->%s->>'score')::float >= %s"
            )
            params.extend([system_name, min_score])
        
        where_clause = ' OR '.join(where_conditions)
        
        # 如果有上一輪的候選人 ID，只在這些候選人中搜索
        if previous_candidate_ids:
            where_clause = f"({where_clause}) AND tiv.id = ANY(%s)"
            params.append(previous_candidate_ids)
        
        sql = f"""
            SELECT 
                tiv.id,
                tiv.name,
                tiv.email,
                tiv.phone,
                tiv.company,
                tiv.position,
                tp.name as project_name,
                tpr.trait_results,
                tpr.category_results,
                tpr.score_value,
                tpr.prediction_value,
                tpr.crawled_at
            FROM test_project_result tpr
            INNER JOIN test_invitation ti ON tpr.test_invitation_id = ti.id
            INNER JOIN test_invitee tiv ON ti.invitee_id = tiv.id
            INNER JOIN test_project tp ON tpr.test_project_id = tp.id
            WHERE tpr.trait_results IS NOT NULL
              AND tpr.trait_results != '{{}}'::jsonb
              AND ({where_clause})
            ORDER BY tpr.crawled_at DESC
            LIMIT %s;
        """
        
        params.append(limit)
        
        print(f"\n📊 執行特質搜索:")
        for trait in matched_traits:
            print(f"   • {trait['chinese_name']} >= {trait['min_score']}")
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        print(f"✓ 找到 {len(results)} 位符合條件的候選人")
        
        candidates = []
        for row in results:
            trait_results = enrich_trait_results(row[7] if row[7] else {})
            
            candidate = {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'company': row[4],
                'position': row[5],
                'project_name': row[6],
                'trait_results': trait_results,
                'category_results': row[8] if row[8] else {},
                'score_value': row[9],
                'prediction_value': row[10],
                'test_date': row[11].isoformat() if row[11] else None
            }
            candidates.append(candidate)
        
        cursor.close()
        return candidates
    
    async def smart_search(self, query: str, limit: int = 50, previous_candidate_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """智能搜索 - 使用 LLM 分析查詢並搜索匹配的候選人"""
        print(f"\n🔍 智能搜索: {query}")
        
        # 如果有上一輪的候選人 ID，顯示篩選資訊
        if previous_candidate_ids:
            print(f"   📌 在 {len(previous_candidate_ids)} 位候選人中進行篩選")
        
        # 1. 使用 LLM 分析查詢
        llm_result = await self.llm_service.analyze_query(query)
        
        if not llm_result['success']:
            print("⚠️ LLM 分析失敗，返回所有候選人")
            candidates = self.get_all_candidates(limit)
            for candidate in candidates:
                candidate['match_score'] = self.calculate_match_score(candidate, query)
                candidate['match_reason'] = self.generate_match_reason(candidate, candidate['match_score'])
            return {
                'candidates': candidates,
                'total': len(candidates),
                'analysis': {
                    'understanding': f"找到 {len(candidates)} 位候選人",
                    'matched_traits': []
                },
                'matched_traits': []
            }
        
        analysis = llm_result['analysis']
        matched_traits = analysis.get('matched_traits', [])
        
        if not matched_traits:
            print("⚠️ 沒有匹配的特質，返回所有候選人")
            if previous_candidate_ids:
                # 如果有上一輪結果，返回這些候選人
                candidates = self.get_candidates_by_ids(previous_candidate_ids)
            else:
                candidates = self.get_all_candidates(limit)
            for candidate in candidates:
                candidate['match_score'] = self.calculate_match_score(candidate, query)
                candidate['match_reason'] = self.generate_match_reason(candidate, candidate['match_score'])
            return {
                'candidates': candidates,
                'total': len(candidates),
                'analysis': analysis,
                'matched_traits': [],
                'is_refinement': previous_candidate_ids is not None
            }
        
        # 2. 根據匹配的特質搜索候選人（在上一輪結果中篩選）
        candidates = self.search_by_multiple_traits(matched_traits, limit, previous_candidate_ids)
        
        # 3. 計算匹配分數
        for candidate in candidates:
            candidate['match_score'] = self.calculate_trait_match_score(
                candidate, matched_traits
            )
            candidate['match_reason'] = await self.llm_service.generate_match_reason(
                candidate, query, matched_traits
            )
        
        # 4. 按匹配分數排序
        candidates.sort(key=lambda x: x['match_score'], reverse=True)
        
        return {
            'candidates': candidates,
            'total': len(candidates),
            'analysis': analysis,
            'matched_traits': matched_traits,
            'is_refinement': previous_candidate_ids is not None
        }
    
    def calculate_trait_match_score(self, candidate: Dict, matched_traits: List[Dict]) -> float:
        """根據匹配特質計算分數（歸一化到 0-1）"""
        trait_results = candidate.get('trait_results', {})
        
        if not trait_results or not matched_traits:
            return 0.1
        
        total_score = 0
        matched_count = 0
        
        for trait in matched_traits:
            system_name = trait['system_name']
            min_score = trait['min_score']
            
            if system_name in trait_results:
                trait_data = trait_results[system_name]
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 0)
                    if score >= min_score:
                        # 計算該特質的標準化分數
                        # 使用候選人分數直接除以 100，確保在 0-1 範圍內
                        normalized_score = min(score / 100, 1.0)
                        
                        # 超過最低要求給予額外權重（但保持在合理範圍）
                        if score > min_score:
                            # 額外獎勵最多 0.2（20%）
                            bonus = min((score - min_score) / 100 * 0.5, 0.2)
                            normalized_score = min(normalized_score + bonus, 1.0)
                        
                        total_score += normalized_score
                        matched_count += 1
        
        if matched_count > 0:
            # 計算平均分數，確保結果在 0-1 之間
            avg_score = total_score / matched_count
            return min(max(avg_score, 0.0), 1.0)
        else:
            return 0.1
    
    def calculate_match_score(self, candidate: Dict, query: str) -> float:
        """計算匹配分數"""
        trait_results = candidate.get('trait_results', {})
        
        if not trait_results:
            return 0.1
        
        # 計算平均分數
        scores = []
        for trait_data in trait_results.values():
            if isinstance(trait_data, dict) and 'score' in trait_data:
                scores.append(trait_data['score'])
        
        if scores:
            avg_score = sum(scores) / len(scores)
            return avg_score / 100  # 轉換為 0-1
        
        return 0.5
    
    def generate_match_reason(self, candidate: Dict, score: float) -> str:
        """生成匹配理由"""
        trait_results = candidate.get('trait_results', {})
        
        if not trait_results:
            return "尚未完成測評"
        
        # 找出高分特質
        high_traits = []
        for trait_key, trait_data in trait_results.items():
            if isinstance(trait_data, dict):
                trait_score = trait_data.get('score', 0)
                chinese_name = trait_data.get('chinese_name', trait_key)
                if trait_score >= 75:
                    high_traits.append(f"{chinese_name}({int(trait_score)}分)")
        
        if high_traits:
            return f"優勢特質：{', '.join(high_traits[:3])}"
        else:
            return f"已完成 {len(trait_results)} 項特質測評"

# API 端點
@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化"""
    print("正在初始化資料庫連接...")
    get_db_connection()
    load_trait_definitions()
    print("✓ 資料庫連接完成！")
    print("✓ 特質定義載入完成！")
    print("✓ LLM 智能搜索已啟用！")
    print("✓ 初始化完成！")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時清理資源"""
    global tunnel, db_conn
    if db_conn:
        db_conn.close()
    if tunnel:
        tunnel.stop()
    print("資源已清理")

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "人才聊天搜索 API v2.1 - 智能搜索版",
        "version": "2.1.0",
        "features": [
            "🤖 LLM 智能查詢分析",
            "🎯 根據特質精準匹配",
            "📊 使用 test_project_result 表（27 筆數據）",
            "🇨🇳 整合 trait 表顯示中文名稱",
            "📈 智能匹配分數計算",
            "🔍 多特質組合搜索"
        ],
        "endpoints": {
            "search": "/api/search - 智能搜索（使用 LLM）",
            "candidates": "/api/candidates - 獲取所有候選人",
            "traits": "/api/traits - 獲取特質列表",
            "health": "/health - 健康檢查"
        }
    }

@app.get("/health")
async def health_check():
    """健康檢查"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "traits_loaded": len(trait_cache),
            "llm_enabled": True,
            "version": "2.1.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_talents(query: SearchQuery):
    """智能搜索人才 - 使用 LLM 分析查詢（支援多輪對話）"""
    try:
        # 確保查詢字符串正確編碼
        query_text = query.query
        session_id = query.session_id or "default"
        
        print(f"\n📝 收到查詢: {query_text}")
        print(f"   會話 ID: {session_id}")
        print(f"   查詢長度: {len(query_text)} 字符")
        
        # 獲取或創建會話上下文
        context = conversation_manager.get_or_create_session(session_id)
        context.add_message('user', query_text)
        context.last_query = query_text
        
        # 分析上下文意圖
        context_analysis = conversation_manager.analyze_context_intent(context, query_text)
        
        print(f"   上下文分析: {context_analysis.get('is_follow_up', False)}")
        if context_analysis.get('is_follow_up'):
            print(f"   後續意圖: {context_analysis.get('follow_up_intent')}")
        
        engine = TalentSearchEngine()
        
        # 處理後續問題
        if context_analysis.get('is_follow_up'):
            follow_up_intent = context_analysis.get('follow_up_intent')
            scope = context_analysis.get('scope', 'all')
            
            # 處理從當前結果中篩選
            if follow_up_intent == 'filter_from_current' and scope == 'current':
                current_candidates = context.current_candidates
                previous_count = context_analysis.get('previous_count', len(current_candidates))
                
                if current_candidates:
                    print(f"\n📊 漸進式篩選模式")
                    print(f"   當前候選人數: {len(current_candidates)}")
                    print(f"   新篩選條件: {query_text}")
                    
                    # 使用 LLM 分析新的篩選條件
                    llm_result = await engine.llm_service.analyze_query(query_text)
                    
                    if llm_result['success']:
                        analysis = llm_result['analysis']
                        matched_traits = analysis.get('matched_traits', [])
                        
                        if matched_traits:
                            # 從當前候選人中篩選
                            filtered_candidates = engine.filter_candidates_by_traits(
                                current_candidates,
                                matched_traits
                            )
                            
                            # 計算匹配分數
                            for candidate in filtered_candidates:
                                candidate['match_score'] = engine.calculate_trait_match_score(
                                    candidate, matched_traits
                                )
                                candidate['match_reason'] = await engine.llm_service.generate_match_reason(
                                    candidate, query_text, matched_traits
                                )
                            
                            # 按分數排序
                            filtered_candidates.sort(key=lambda x: x['match_score'], reverse=True)
                            
                            search_result = {
                                'candidates': filtered_candidates,
                                'total': len(filtered_candidates),
                                'analysis': analysis,
                                'matched_traits': matched_traits,
                                'filter_mode': 'progressive',
                                'previous_count': previous_count
                            }
                        else:
                            # 沒有匹配的特質，返回當前列表
                            search_result = {
                                'candidates': current_candidates,
                                'total': len(current_candidates),
                                'analysis': analysis,
                                'matched_traits': [],
                                'filter_mode': 'none'
                            }
                    else:
                        # LLM 分析失敗，返回當前列表
                        search_result = {
                            'candidates': current_candidates,
                            'total': len(current_candidates),
                            'analysis': {'understanding': '無法分析篩選條件'},
                            'matched_traits': [],
                            'filter_mode': 'none'
                        }
                else:
                    # 沒有當前列表，執行新搜索
                    print("⚠️ 沒有當前候選人列表，執行新搜索")
                    search_result = await engine.smart_search(query_text, limit=50)
            
            # 處理新搜索意圖
            elif follow_up_intent == 'new_search':
                print(f"\n🔄 新搜索模式（清空之前的結果）")
                search_result = await engine.smart_search(query_text, limit=50)
            
            # 其他後續問題，執行新搜索
            else:
                search_result = await engine.smart_search(query_text, limit=50)
        else:
            # 新查詢，執行智能搜索
            print(f"\n🆕 新搜索模式")
            search_result = await engine.smart_search(query_text, limit=50)
        
        raw_candidates = search_result['candidates']
        analysis = search_result['analysis']
        matched_traits = search_result['matched_traits']
        
        # 更新會話上下文
        context.set_current_candidates(raw_candidates)
        if len(raw_candidates) == 1:
            context.set_current_candidate(raw_candidates[0])
        
        # 轉換為 Candidate 物件
        candidates = []
        for c in raw_candidates:
            candidates.append(Candidate(
                id=c['id'],
                name=c['name'],
                email=c['email'],
                phone=c.get('phone'),
                company=c.get('company'),
                position=c.get('position'),
                test_results=[],
                trait_results=c.get('trait_results', {}),
                match_score=c.get('match_score', 0.5),
                match_reason=c.get('match_reason', '已完成測評')
            ))
        
        # 生成查詢理解（根據篩選模式）
        filter_mode = search_result.get('filter_mode', 'none')
        previous_count = search_result.get('previous_count', 0)
        
        if filter_mode == 'progressive':
            # 漸進式篩選
            trait_names = [t['chinese_name'] for t in matched_traits]
            understanding = f"從 {previous_count} 位候選人中篩選出 {len(candidates)} 位符合「{', '.join(trait_names)}」條件的候選人"
        elif matched_traits:
            # 新搜索（有特質匹配）
            trait_names = [t['chinese_name'] for t in matched_traits]
            understanding = f"您正在尋找：{', '.join(trait_names)} 優秀的人才。找到 {len(candidates)} 位符合條件的候選人"
        else:
            # 新搜索（無特質匹配）
            understanding = analysis.get('understanding', f"找到 {len(candidates)} 位候選人")
        
        # 生成智能建議（基於上下文和篩選模式）
        suggestions = []
        
        if filter_mode == 'progressive' and len(candidates) > 0:
            # 漸進式篩選後的建議
            suggestions.append("從這些人中再篩選")
            suggestions.append("重新搜索（清空篩選）")
            if len(candidates) > 1:
                suggestions.append("比較這些候選人")
        elif len(candidates) > 1:
            # 多個候選人的建議
            suggestions.append("從這些人中再篩選")
            suggestions.append("排除某些候選人")
            suggestions.append("比較這些候選人")
        elif len(candidates) == 1:
            # 單個候選人的建議
            suggestions.append(f"告訴我更多關於 {candidates[0].name} 的資訊")
            suggestions.append("找類似的候選人")
        
        if len(candidates) > 0:
            suggestions.extend([
                "查看候選人詳細資料",
                "為候選人準備面試問題"
            ])
        
        if matched_traits and filter_mode != 'progressive':
            suggestions.insert(0, f"已根據 {len(matched_traits)} 個特質進行智能匹配")
        
        # 添加助手回應到上下文
        context.add_message('assistant', understanding)
        
        # 返回所有找到的候選人
        return SearchResponse(
            candidates=candidates,
            total=len(candidates),
            query_understanding=understanding,
            suggestions=suggestions
        )
    
    except Exception as e:
        print(f"搜索錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates")
async def get_candidates(limit: int = 20):
    """獲取候選人列表"""
    try:
        engine = TalentSearchEngine()
        candidates = engine.get_all_candidates(limit=limit)
        
        return {
            "candidates": candidates,
            "total": len(candidates),
            "message": f"成功獲取 {len(candidates)} 位候選人"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traits")
async def get_traits():
    """獲取所有特質定義"""
    try:
        traits = load_trait_definitions()
        
        return {
            "traits": list(traits.values()),
            "total": len(traits),
            "message": f"共有 {len(traits)} 個特質定義"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traits/{trait_name}")
async def search_by_trait(trait_name: str, min_score: float = 70):
    """按特質搜索候選人"""
    try:
        engine = TalentSearchEngine()
        candidates = engine.search_by_trait(trait_name, min_score)
        
        return {
            "candidates": candidates,
            "total": len(candidates),
            "trait_name": trait_name,
            "min_score": min_score,
            "message": f"找到 {len(candidates)} 位 {trait_name} >= {min_score} 的候選人"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/context")
async def get_session_context(session_id: str):
    """
    獲取會話上下文資訊
    
    返回當前會話的：
    - 對話歷史
    - 當前候選人
    - 候選人列表
    - 上下文摘要
    """
    try:
        context = conversation_manager.get_or_create_session(session_id)
        
        return {
            "session_id": session_id,
            "message_count": len(context.messages),
            "current_candidate": context.current_candidate,
            "candidates_count": len(context.current_candidates),
            "last_intent": context.last_intent,
            "context_summary": context.get_context_summary(),
            "conversation_history": context.get_conversation_history(limit=5)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """清除會話上下文"""
    try:
        if session_id in conversation_manager.sessions:
            conversation_manager.sessions[session_id].clear()
            return {
                "success": True,
                "message": f"會話 {session_id} 已清除"
            }
        else:
            return {
                "success": False,
                "message": f"會話 {session_id} 不存在"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/candidates/{candidate_id}/analyze")
async def analyze_candidate(candidate_id: int):
    """
    分析候選人特質 - 使用 LLM 生成深度分析
    
    返回：
    - personality_traits: 性格特徵
    - core_strengths: 核心優勢
    - suitable_positions: 適合職位
    - work_style: 工作風格
    - team_role: 團隊角色
    - development_suggestions: 發展建議
    - interview_focus: 面試重點
    - summary: 一句話總結
    """
    try:
        # 1. 獲取候選人資料
        engine = TalentSearchEngine()
        conn = engine.conn
        cursor = conn.cursor()
        
        sql = """
            SELECT 
                tiv.id,
                tiv.name,
                tiv.email,
                tiv.phone,
                tiv.company,
                tiv.position,
                tp.name as project_name,
                tpr.trait_results,
                tpr.category_results
            FROM test_project_result tpr
            INNER JOIN test_invitation ti ON tpr.test_invitation_id = ti.id
            INNER JOIN test_invitee tiv ON ti.invitee_id = tiv.id
            INNER JOIN test_project tp ON tpr.test_project_id = tp.id
            WHERE tiv.id = %s
              AND tpr.trait_results IS NOT NULL
            LIMIT 1;
        """
        
        cursor.execute(sql, (candidate_id,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="候選人不存在或沒有測驗結果")
        
        # 2. 準備候選人資料
        trait_results = enrich_trait_results(row[7] if row[7] else {})
        
        candidate = {
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'phone': row[3],
            'company': row[4],
            'position': row[5],
            'project_name': row[6],
            'trait_results': trait_results,
            'category_results': row[8] if row[8] else {}
        }
        
        # 3. 使用 LLM 分析
        analysis_service = TalentAnalysisService(
            api_key=LLM_CONFIG['api_key'],
            api_endpoint=LLM_CONFIG['endpoint'],
            model=LLM_CONFIG['model']
        )
        
        analysis_result = await analysis_service.analyze_candidate(candidate)
        
        if not analysis_result['success']:
            raise HTTPException(status_code=500, detail=analysis_result.get('error', '分析失敗'))
        
        # 4. 返回分析結果
        return {
            'candidate_id': candidate_id,
            'candidate_name': candidate['name'],
            'analysis': analysis_result['analysis'],
            'raw_traits': analysis_result.get('raw_traits', {}),
            'formatted_text': analysis_service.format_analysis_for_display(analysis_result)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"分析錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    print("=" * 60)
    print("人才聊天搜索 API v2.1 - 智能搜索版")
    print("=" * 60)
    print("✨ 新特性:")
    print("  • 🤖 LLM 智能查詢分析")
    print("  • 🎯 根據特質精準匹配")
    print("  • 📊 使用 test_project_result 表（27 筆數據）")
    print("  • 🇨🇳 整合 trait 表顯示中文名稱")
    print("  • 📈 智能匹配分數計算")
    print("=" * 60)
    print("啟動服務...")
    print("API 文檔: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
