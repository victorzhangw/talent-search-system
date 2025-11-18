#!/usr/bin/env python3
"""
啟動修正後的人才搜索 API
使用 talent_search_engine_fixed.py
"""

import sys
import os

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
import httpx

# 導入修正後的搜索引擎
from talent_search_engine_fixed import TalentSearchEngineFixed

# 資料庫連接配置
DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': 'private-key-openssh.pem',
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
app = FastAPI(title="人才聊天搜索 API (修正版)", version="2.0.0")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域變數
tunnel = None
db_conn = None

# 資料模型
class SearchQuery(BaseModel):
    query: str
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

# 資料庫連接管理
def get_db_connection():
    """取得資料庫連接"""
    global tunnel, db_conn
    
    if db_conn is None or db_conn.closed:
        if tunnel is None or not tunnel.is_active:
            print("正在建立 SSH 隧道...")
            tunnel = SSHTunnelForwarder(
                (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
                ssh_username=DB_CONFIG['ssh_username'],
                ssh_pkey=DB_CONFIG['ssh_private_key'],
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

# API 端點
@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化資料庫連接"""
    print("\n" + "=" * 60)
    print("人才聊天搜索 API (修正版) 啟動中...")
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
        "message": "人才聊天搜索 API (修正版)",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "search": "/api/search",
            "candidates": "/api/candidates",
            "health": "/health"
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
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_talents(query: SearchQuery):
    """搜索人才 - 使用修正後的引擎"""
    try:
        print(f"\n🔍 收到搜索請求: {query.query}")
        
        # 使用修正後的搜索引擎
        conn = get_db_connection()
        engine = TalentSearchEngineFixed(conn)
        
        # 簡單測試：列出所有候選人
        if "列出" in query.query or "所有" in query.query:
            print("📋 列出所有候選人")
            candidates_data = engine.get_all_candidates(limit=20)
            
            candidates = []
            for c in candidates_data:
                # 計算平均分數
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
            # 提取姓名（簡單實現）
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

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("人才聊天搜索 API (修正版)")
    print("=" * 60)
    print("啟動服務...")
    print("API 文檔: http://localhost:8000/docs")
    print("健康檢查: http://localhost:8000/health")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
