#!/usr/bin/env python3
"""
人才聊天搜索 API - 統一版本
支援本地開發和雲端部署，使用環境變數控制行為
"""

import sys
import os
import tempfile
from pathlib import Path

# 確保可以導入本地模塊
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import uvicorn

# 導入搜索引擎
from talent_search_engine_fixed import TalentSearchEngineFixed

# ============================================
# 環境配置
# ============================================

# 判斷運行環境
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

print(f"\n{'='*60}")
print(f"🚀 運行環境: {ENVIRONMENT.upper()}")
print(f"{'='*60}\n")

# 資料庫配置 - 從環境變數讀取
DB_CONFIG = {
    'ssh_host': os.getenv('DB_SSH_HOST', '54.199.255.239'),
    'ssh_port': int(os.getenv('DB_SSH_PORT', '22')),
    'ssh_username': os.getenv('DB_SSH_USERNAME', 'victor_cheng'),
    'ssh_private_key': os.getenv('DB_SSH_PRIVATE_KEY'),  # 生產環境必須設定
    'ssh_private_key_file': os.getenv('DB_SSH_PRIVATE_KEY_FILE', 'private-key-openssh.pem'),  # 本地開發用
    'db_host': os.getenv('DB_HOST', 'localhost'),
    'db_port': int(os.getenv('DB_PORT', '5432')),
    'db_name': os.getenv('DB_NAME', 'projectdb'),
    'db_user': os.getenv('DB_USER', 'projectuser'),
    'db_password': os.getenv('DB_PASSWORD', 'projectpass')
}

# LLM API 配置
LLM_CONFIG = {
    'api_key': os.getenv('LLM_API_KEY', 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff'),
    'api_host': os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn'),
    'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3'),
}

# 應用配置
APP_CONFIG = {
    'host': os.getenv('HOST', '0.0.0.0'),
    'port': int(os.getenv('PORT', '8000')),
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',
}

# ============================================
# FastAPI 應用
# ============================================

app = FastAPI(
    title="人才聊天搜索 API",
    version="3.0.0",
    description="統一版本 - 支援本地開發和雲端部署"
)

# CORS 設定 - 根據環境調整
if IS_PRODUCTION:
    # 生產環境：指定允許的來源
    allowed_origins = [
        os.getenv('FRONTEND_URL', 'https://talent-search-frontend-68e7.onrender.com'),
        "https://talent-search-frontend.vercel.app",  # Vercel 部署
        "https://talent-search-frontend.netlify.app",  # Netlify 部署
        "http://localhost:3000",  # 本地測試
        "http://localhost:5173",  # Vite 開發服務器
        "http://127.0.0.1:5173",  # Vite 開發服務器
    ]
    # 支持通配符匹配 (Render/Vercel/Netlify 的預覽部署)
    allow_origin_regex = r"https://.*\.(onrender\.com|vercel\.app|netlify\.app)$"
else:
    # 開發環境：允許所有來源
    allowed_origins = ["*"]
    allow_origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex if IS_PRODUCTION else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# 全域變數
# ============================================

tunnel = None
db_conn = None

# ============================================
# 資料模型
# ============================================

class SearchQuery(BaseModel):
    query: str
    session_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class Candidate(BaseModel):
    id: int
    name: str
    email: str
    test_results: List[Dict[str, Any]]
    match_score: float
    match_reason: str

class SearchResponse(BaseModel):
    candidates: List[Candidate]
    total: int
    query_understanding: str
    suggestions: List[str]

# ============================================
# 資料庫連接管理
# ============================================

def get_db_connection():
    """取得資料庫連接 - 根據環境使用不同策略"""
    global tunnel, db_conn
    
    if db_conn is None or db_conn.closed:
        if tunnel is None or not tunnel.is_active:
            print("正在建立 SSH 隧道...")
            
            # 處理 SSH private key
            ssh_key = DB_CONFIG['ssh_private_key']
            
            if ssh_key:
                # 生產環境：從環境變數讀取 key 內容
                print("✅ 使用環境變數中的 SSH key")
                temp_key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
                temp_key_file.write(ssh_key)
                temp_key_file.close()
                ssh_pkey = temp_key_file.name
            else:
                # 開發環境：使用本地檔案
                ssh_key_file = DB_CONFIG['ssh_private_key_file']
                if os.path.isfile(ssh_key_file):
                    print(f"✅ 使用本地 SSH key 檔案: {ssh_key_file}")
                    ssh_pkey = ssh_key_file
                else:
                    raise ValueError(f"找不到 SSH key 檔案: {ssh_key_file}")
            
            tunnel = SSHTunnelForwarder(
                (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
                ssh_username=DB_CONFIG['ssh_username'],
                ssh_pkey=ssh_pkey,
                remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
            )
            tunnel.start()
            print(f"✅ SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")
        
        print("正在連接資料庫...")
        db_conn = psycopg2.connect(
            host='localhost',
            port=tunnel.local_bind_port,
            database=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_password']
        )
        print("✅ 資料庫連接成功")
    
    return db_conn

# ============================================
# API 端點
# ============================================

@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化"""
    print("\n" + "=" * 60)
    print(f"人才聊天搜索 API 啟動中... ({ENVIRONMENT})")
    print("=" * 60)
    get_db_connection()
    print("✅ 初始化完成")
    print("=" * 60 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時清理資源"""
    global tunnel, db_conn
    if db_conn:
        db_conn.close()
        print("✅ 資料庫連接已關閉")
    if tunnel:
        tunnel.stop()
        print("✅ SSH 隧道已關閉")

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "人才聊天搜索 API",
        "version": "3.0.0",
        "environment": ENVIRONMENT,
        "status": "running",
        "endpoints": {
            "search": "/api/search",
            "candidates": "/api/candidates",
            "traits": "/api/traits",
            "health": "/health",
            "docs": "/docs"
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
            "environment": ENVIRONMENT,
            "version": "3.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "environment": ENVIRONMENT,
            "error": str(e)
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_talents(query: SearchQuery):
    """搜索人才"""
    try:
        print(f"\n🔍 收到搜索請求: {query.query}")
        if query.session_id:
            print(f"📝 會話 ID: {query.session_id}")
        
        conn = get_db_connection()
        engine = TalentSearchEngineFixed(conn)
        
        # 簡單實現：列出所有候選人
        if "列出" in query.query or "所有" in query.query:
            print("📋 列出所有候選人")
            candidates_data = engine.get_all_candidates(limit=20)
            
            candidates = []
            for c in candidates_data:
                trait_results = c.get('trait_results', {})
                if trait_results:
                    scores = [
                        t.get('score', 0) 
                        for t in trait_results.values() 
                        if isinstance(t, dict)
                    ]
                    avg_score = sum(scores) / len(scores) if scores else 0
                else:
                    avg_score = 0
                
                candidates.append(Candidate(
                    id=c['id'],
                    name=c['name'],
                    email=c['email'] or '',
                    test_results=[],
                    match_score=avg_score / 100,
                    match_reason=f"已完成 {len(trait_results)} 項特質測評" if trait_results else "尚未完成測評"
                ))
            
            print(f"✅ 找到 {len(candidates)} 位候選人")
            
            return SearchResponse(
                candidates=candidates,
                total=len(candidates),
                query_understanding=f"找到 {len(candidates)} 位候選人",
                suggestions=[
                    "搜索特定特質：「找一個溝通能力強的人」",
                    "查看候選人詳細資料",
                    "按姓名搜索：「找到 Howard」"
                ]
            )
        
        # 按姓名搜索
        if "找到" in query.query or "找" in query.query:
            words = query.query.replace("找到", "").replace("找", "").strip().split()
            if words:
                name = words[0]
                print(f"🔍 搜索候選人: {name}")
                
                candidate_data = engine.find_candidate_by_name(name)
                
                if candidate_data:
                    trait_results = candidate_data.get('trait_results', {})
                    if trait_results:
                        scores = [
                            t.get('score', 0) 
                            for t in trait_results.values() 
                            if isinstance(t, dict)
                        ]
                        avg_score = sum(scores) / len(scores) if scores else 0
                    else:
                        avg_score = 0
                    
                    candidate = Candidate(
                        id=candidate_data['id'],
                        name=candidate_data['name'],
                        email=candidate_data['email'] or '',
                        test_results=[],
                        match_score=avg_score / 100,
                        match_reason=f"找到候選人 {name}，已完成 {len(trait_results)} 項特質測評"
                    )
                    
                    print(f"✅ 找到候選人: {name}")
                    
                    return SearchResponse(
                        candidates=[candidate],
                        total=1,
                        query_understanding=f"✅ 找到候選人：{name}",
                        suggestions=[
                            f"查看 {name} 的詳細測評",
                            "搜索類似特質的人才",
                            "列出所有候選人"
                        ]
                    )
                else:
                    print(f"❌ 找不到候選人: {name}")
                    return SearchResponse(
                        candidates=[],
                        total=0,
                        query_understanding=f"❌ 找不到候選人：{name}",
                        suggestions=[
                            "列出所有候選人",
                            "檢查姓名拼寫",
                            "搜索特定特質的人才"
                        ]
                    )
        
        # 默認：返回所有候選人
        print("📋 默認：列出所有候選人")
        candidates_data = engine.get_all_candidates(limit=10)
        
        candidates = []
        for c in candidates_data:
            trait_results = c.get('trait_results', {})
            if trait_results:
                scores = [
                    t.get('score', 0) 
                    for t in trait_results.values() 
                    if isinstance(t, dict)
                ]
                avg_score = sum(scores) / len(scores) if scores else 0
            else:
                avg_score = 0
            
            candidates.append(Candidate(
                id=c['id'],
                name=c['name'],
                email=c['email'] or '',
                test_results=[],
                match_score=avg_score / 100,
                match_reason=f"已完成 {len(trait_results)} 項特質測評" if trait_results else "尚未完成測評"
            ))
        
        print(f"✅ 找到 {len(candidates)} 位候選人")
        
        return SearchResponse(
            candidates=candidates,
            total=len(candidates),
            query_understanding=f"找到 {len(candidates)} 位候選人",
            suggestions=[
                "搜索特定特質的人才",
                "按姓名搜索候選人",
                "查看候選人詳細資料"
            ]
        )
    
    except Exception as e:
        print(f"❌ 搜索錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates")
async def get_all_candidates():
    """獲取所有候選人"""
    try:
        conn = get_db_connection()
        engine = TalentSearchEngineFixed(conn)
        candidates_data = engine.get_all_candidates(limit=50)
        
        return {
            "total": len(candidates_data),
            "candidates": candidates_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traits")
async def get_traits():
    """獲取特質定義"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 先檢查表是否存在
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%trait%'
        """)
        
        tables = cursor.fetchall()
        print(f"📋 找到的特質相關表: {tables}")
        
        # 嘗試從不同的表查詢
        traits = []
        
        # 方案 1：嘗試從 stella_trait_mapping 查詢
        try:
            cursor.execute("""
                SELECT DISTINCT 
                    trait_name,
                    trait_chinese_name,
                    trait_description
                FROM stella_trait_mapping
                WHERE trait_name IS NOT NULL
                ORDER BY trait_chinese_name
            """)
            rows = cursor.fetchall()
            for row in rows:
                traits.append({
                    "name": row[0],
                    "chinese_name": row[1],
                    "description": row[2] or ""
                })
        except Exception as e1:
            print(f"⚠️ stella_trait_mapping 不存在: {e1}")
            
            # 方案 2：返回預設的特質列表
            traits = [
                {"name": "communication", "chinese_name": "溝通能力", "description": "與他人有效交流的能力"},
                {"name": "leadership", "chinese_name": "領導力", "description": "引導和激勵團隊的能力"},
                {"name": "creativity", "chinese_name": "創造力", "description": "產生新想法和解決方案的能力"},
                {"name": "analytical", "chinese_name": "分析能力", "description": "邏輯思考和數據分析的能力"},
                {"name": "teamwork", "chinese_name": "團隊合作", "description": "與他人協作完成目標的能力"},
            ]
            print("✅ 使用預設特質列表")
        
        cursor.close()
        
        return {
            "total": len(traits),
            "traits": traits
        }
    except Exception as e:
        print(f"❌ 獲取特質定義錯誤: {str(e)}")
        # 即使出錯也返回預設列表，不要讓前端崩潰
        return {
            "total": 5,
            "traits": [
                {"name": "communication", "chinese_name": "溝通能力", "description": "與他人有效交流的能力"},
                {"name": "leadership", "chinese_name": "領導力", "description": "引導和激勵團隊的能力"},
                {"name": "creativity", "chinese_name": "創造力", "description": "產生新想法和解決方案的能力"},
                {"name": "analytical", "chinese_name": "分析能力", "description": "邏輯思考和數據分析的能力"},
                {"name": "teamwork", "chinese_name": "團隊合作", "description": "與他人協作完成目標的能力"},
            ]
        }

# ============================================
# 主程式入口
# ============================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("人才聊天搜索 API")
    print("=" * 60)
    print(f"環境: {ENVIRONMENT}")
    print(f"API 文檔: http://{APP_CONFIG['host']}:{APP_CONFIG['port']}/docs")
    print(f"健康檢查: http://{APP_CONFIG['host']}:{APP_CONFIG['port']}/health")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        app,
        host=APP_CONFIG['host'],
        port=APP_CONFIG['port'],
        log_level="debug" if APP_CONFIG['debug'] else "info"
    )
