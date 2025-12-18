"""
人才搜索模組路由
從 talent_search_api.py 提取的路由部分
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

# 導入人才搜索服務
from conversation_manager import ConversationManager
from conversation_enhanced_search import ConversationEnhancedSearch

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter()

# 全局變量（將從 main_api.py 的 app.state 獲取）
conversation_manager = None
conversation_search = None


# ==================== Pydantic 模型 ====================

class QueryRequest(BaseModel):
    """查詢請求模型"""
    query: str
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = None
    top_k: Optional[int] = 10


class ConversationRequest(BaseModel):
    """對話請求模型"""
    query: str
    user_id: str = "default_user"
    session_id: Optional[str] = None


# ==================== API 端點 ====================

@router.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "Talent Search Module",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/query")
async def talent_query(
    request: QueryRequest,
    fastapi_request: Request
):
    """
    人才查詢端點（直接搜索）
    """
    try:
        # 從 app.state 獲取服務
        global conversation_search
        if not conversation_search:
            db_connection = fastapi_request.app.state.db_connection
            llm_service = fastapi_request.app.state.llm_service
            conversation_search = ConversationEnhancedSearch(db_connection, llm_service)
        
        logger.info(f"收到人才查詢請求: {request.query}")
        
        # 執行搜索
        results = conversation_search.search(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id,
            top_k=request.top_k
        )
        
        return {
            "success": True,
            "query": request.query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"人才查詢失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@router.post("/conversation")
async def talent_conversation(
    request: ConversationRequest,
    fastapi_request: Request
):
    """
    人才對話端點（多輪對話）
    """
    try:
        # 從 app.state 獲取服務
        global conversation_manager
        if not conversation_manager:
            db_connection = fastapi_request.app.state.db_connection
            llm_service = fastapi_request.app.state.llm_service
            conversation_manager = ConversationManager(db_connection, llm_service)
        
        logger.info(f"收到對話請求: {request.query} (user: {request.user_id})")
        
        # 處理對話
        response = conversation_manager.process_query(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        return {
            "success": True,
            "query": request.query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"對話處理失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"對話失敗: {str(e)}")


@router.get("/conversation/history")
async def get_conversation_history(
    request: Request,
    user_id: str = Query(..., description="用戶 ID"),
    session_id: Optional[str] = Query(None, description="會話 ID"),
    limit: int = Query(10, ge=1, le=100, description="返回記錄數量")
):
    """
    獲取對話歷史
    """
    try:
        global conversation_manager
        if not conversation_manager:
            db_connection = request.app.state.db_connection
            llm_service = request.app.state.llm_service
            conversation_manager = ConversationManager(db_connection, llm_service)
        
        # 獲取歷史記錄
        history = conversation_manager.get_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"獲取歷史記錄失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法獲取歷史記錄")


@router.delete("/conversation/history")
async def clear_conversation_history(
    request: Request,
    user_id: str = Query(..., description="用戶 ID"),
    session_id: Optional[str] = Query(None, description="會話 ID（可選）")
):
    """
    清除對話歷史
    """
    try:
        global conversation_manager
        if not conversation_manager:
            db_connection = request.app.state.db_connection
            llm_service = request.app.state.llm_service
            conversation_manager = ConversationManager(db_connection, llm_service)
        
        # 清除歷史
        deleted_count = conversation_manager.clear_history(
            user_id=user_id,
            session_id=session_id
        )
        
        return {
            "success": True,
            "message": f"已清除 {deleted_count} 條記錄",
            "user_id": user_id,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"清除歷史記錄失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法清除歷史記錄")


@router.get("/traits")
async def get_traits(request: Request):
    """
    獲取所有特質定義
    """
    try:
        from talent_search_api import trait_definitions
        
        return {
            "success": True,
            "traits": trait_definitions,
            "count": len(trait_definitions)
        }
        
    except Exception as e:
        logger.error(f"獲取特質定義失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法獲取特質定義")


@router.get("/version")
async def get_version_info():
    """
    獲取版本資訊
    """
    return {
        "version": "2.0.0",
        "name": "Talent Search Module",
        "features": [
            "✅ 意圖識別和多意圖處理",
            "✅ 漸進式篩選",
            "✅ 多輪對話支援",
            "✅ 向量搜索和混合搜索",
            "✅ LLM 增強搜索"
        ],
        "timestamp": datetime.now().isoformat()
    }
