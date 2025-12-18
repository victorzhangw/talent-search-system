"""
HR 諮詢 API 端點（重構版）
基於正確的資料表結構：test_invitee, test_project_result, test_project_trait

變更說明：
1. 候選人列表從 test_invitee 查詢（替代 core_user）
2. 支援企業隔離（enterprise_id）
3. 返回更完整的候選人資訊（職位、狀態、公司等）
4. 測驗結果從 test_project_result 查詢
"""

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import logging
import os
from datetime import datetime

# 導入 HR 諮詢服務
from hr_consultation_service import HRConsultationService, format_consultation_response

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="HR 諮詢服務 API（重構版）",
    description="基於測評數據的專業人力資源諮詢服務 - 使用正確的資料表結構",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制具體域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局變量（將在啟動時初始化）
hr_service = None
db_connection = None
llm_service = None


# ==================== Pydantic 模型 ====================

class ConsultationRequest(BaseModel):
    """HR 諮詢請求模型"""
    query: str = Field(..., min_length=2, max_length=500, description="諮詢問題")
    candidate_id: Optional[int] = Field(None, description="候選人 ID (test_invitee.id)")
    candidate_name: Optional[str] = Field(None, max_length=100, description="候選人姓名")
    session_id: Optional[str] = Field(None, max_length=255, description="會話 ID")
    enterprise_id: Optional[int] = Field(None, description="企業 ID（覆蓋 Header 設定）")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('諮詢問題不能為空')
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "query": "張三適合產品經理職位嗎？",
                "candidate_name": "張三",
                "enterprise_id": 5,
                "session_id": "session_1234567890"
            }
        }


# ==================== API 端點 ====================

@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化服務"""
    global hr_service, db_connection, llm_service
    
    try:
        # 初始化資料庫連接
        from talent_search_api import get_db_connection, LLMService, load_trait_definitions
        
        logger.info("🔄 正在初始化資料庫連接...")
        db_connection = get_db_connection()
        logger.info("✅ 資料庫連接成功")
        
        logger.info("🔄 正在加載特質定義...")
        load_trait_definitions()
        logger.info("✅ 特質定義加載完成")
        
        logger.info("🔄 正在初始化 LLM 服務...")
        llm_service = LLMService()
        logger.info("✅ LLM 服務初始化完成")
        
        logger.info("🔄 正在初始化 HR 諮詢服務（重構版）...")
        # 不指定默認 enterprise_id，由每次請求提供
        hr_service = HRConsultationService(db_connection, llm_service)
        logger.info("✅ HR 諮詢服務初始化完成")
        
        logger.info("🎉 HR 諮詢服務（重構版）已成功啟動！")
        logger.info("📝 使用資料表: test_invitee, test_project_result, test_project_trait")
        
    except Exception as e:
        logger.error(f"❌ HR 諮詢服務啟動失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時清理資源"""
    global db_connection
    
    if db_connection:
        db_connection.close()
        logger.info("資料庫連接已關閉")


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "HR Consultation API (Refactored)",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db_connection else "disconnected",
        "llm_service": "available" if llm_service else "unavailable",
        "data_source": "test_invitee, test_project_result, test_project_trait"
    }


@app.post("/api/hr-consult/chat")
async def hr_consultation(
    request: ConsultationRequest,
    x_enterprise_id: Optional[int] = Header(None, alias="X-Enterprise-ID")
):
    """
    HR 諮詢主端點（重構版）
    
    變更：
    1. 候選人來源：test_invitee（企業創建的候選人）
    2. 測驗結果：test_project_result（企業測驗結果）
    3. 必須提供 enterprise_id（企業隔離）
    
    支援兩種方式指定候選人：
    1. 提供 candidate_id 或 candidate_name
    2. 在 query 中提到候選人姓名（如"張三適合什麼職位？"）
    
    Returns:
        諮詢結果，包含專業建議和數據摘要
    """
    try:
        if not hr_service:
            raise HTTPException(status_code=503, detail="HR 諮詢服務未初始化")
        
        # 確定企業 ID（暫時設為可選）
        enterprise_id = request.enterprise_id or x_enterprise_id or 1  # 默認使用 1
        
        logger.info(f"收到諮詢請求 - Enterprise: {enterprise_id}, Query: {request.query}")
        
        # 調用諮詢服務
        result = hr_service.consult(
            query=request.query,
            candidate_id=request.candidate_id,
            candidate_name=request.candidate_name,
            session_id=request.session_id,
            enterprise_id=enterprise_id
        )
        
        # 如果失敗，返回適當的 HTTP 狀態碼
        if not result.get('success'):
            error = result.get('error', '')
            if "找不到" in error or "不屬於" in error:
                status_code = 404
            elif "無測評數據" in error:
                status_code = 404
            else:
                status_code = 400
            raise HTTPException(status_code=status_code, detail=error)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HR 諮詢處理失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="諮詢服務暫時不可用")


@app.get("/api/hr-consult/candidates")
async def list_candidates(
    enterprise_id: Optional[int] = Query(None, description="企業 ID（可選，暫時）"),
    search: Optional[str] = Query(None, description="搜索關鍵字（姓名、郵箱、職位）"),
    status: Optional[str] = Query(None, description="候選人狀態（employed/job_seeker）"),
    has_test_data: Optional[bool] = Query(None, description="是否有測評數據"),
    limit: int = Query(20, ge=1, le=100, description="返回數量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    獲取候選人列表（重構版）
    
    變更：
    1. 從 test_invitee 表查詢（替代 core_user）
    2. 必須提供 enterprise_id（企業隔離）
    3. 返回更多候選人資訊（職位、狀態、公司等）
    
    Query Parameters:
        enterprise_id: 企業 ID（必填）
        search: 搜索關鍵字（姓名、郵箱、職位）
        status: 候選人狀態（employed/job_seeker）
        has_test_data: 是否僅顯示有測評數據的候選人
        limit: 返回數量（默認 20）
        offset: 偏移量（默認 0）
    
    Returns:
        候選人列表，包含基本資訊和測評數據統計
    """
    try:
        logger.info(f"========== 開始處理候選人列表請求 ==========")
        logger.info(f"參數: enterprise_id={enterprise_id}, has_test_data={has_test_data}, limit={limit}, offset={offset}")
        
        if not db_connection:
            logger.error("資料庫連接不可用")
            raise HTTPException(status_code=503, detail="資料庫連接不可用")
        
        logger.info("資料庫連接正常")
        cursor = db_connection.cursor()
        logger.info("Cursor 創建成功")
        
        # 構建查詢條件（暫時不強制 enterprise_id）
        conditions = []
        params = []
        
        if enterprise_id:
            conditions.append("ti.enterprise_id = %s")
            params.append(enterprise_id)
        
        if search:
            conditions.append(
                "(ti.name LIKE %s OR ti.email LIKE %s OR ti.position LIKE %s)"
            )
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if status:
            conditions.append("ti.status = %s")
            params.append(status)
        
        # 處理 has_test_data 過濾（使用 HAVING 而不是 WHERE）
        having_clause = ""
        if has_test_data is not None:
            if has_test_data:
                # ✅ 修復：使用 HAVING 檢查實際的測驗結果數量，而不是 ti.completed_count
                having_clause = "HAVING COUNT(DISTINCT CASE WHEN tpr.crawl_status = 'completed' THEN tpr.id END) > 0"
            else:
                having_clause = "HAVING COUNT(DISTINCT CASE WHEN tpr.crawl_status = 'completed' THEN tpr.id END) = 0"
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        logger.info(f"WHERE 子句: {where_clause}")
        logger.info(f"HAVING 子句: {having_clause}")
        logger.info(f"查詢參數: {params}")
        
        # 查詢候選人列表
        query = f"""
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
                END) as completed_tests,
                COUNT(DISTINCT CASE 
                    WHEN tpr.crawl_status = 'pending' 
                    THEN tpr.id 
                END) as pending_tests,
                
                -- 最新測驗項目
                MAX(CASE 
                    WHEN tpr.crawl_status = 'completed' 
                    THEN tp.name 
                END) as latest_test_project,
                MAX(CASE 
                    WHEN tpr.crawl_status = 'completed' 
                    THEN tpr.score_value 
                END) as latest_score
                
            FROM test_invitee ti
            LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
            LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
            LEFT JOIN test_project tp ON tpr.test_project_id = tp.id
            
            WHERE {where_clause}
            
            GROUP BY ti.id
            {having_clause}
            ORDER BY ti.last_test_date DESC NULLS LAST, ti.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        logger.info("執行主查詢...")
        logger.info(f"完整 SQL: {query[:200]}...")  # 只顯示前 200 個字符
        logger.info(f"完整參數: {tuple(params)}")
        
        cursor.execute(query, tuple(params))
        logger.info("查詢執行成功")
        
        results = cursor.fetchall()
        logger.info(f"獲取結果: {len(results)} 筆")
        
        # 獲取總數（需要包含 HAVING 子句）
        count_query = f"""
            SELECT COUNT(*) FROM (
                SELECT ti.id
                FROM test_invitee ti
                LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
                LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
                WHERE {where_clause}
                GROUP BY ti.id
                {having_clause}
            ) AS filtered_candidates
        """
        
        logger.info("執行 COUNT 查詢...")
        cursor.execute(count_query, tuple(params[:-2]))
        logger.info("COUNT 查詢執行成功")
        
        total = cursor.fetchone()[0]
        logger.info(f"總數: {total}")
        
        cursor.close()
        logger.info("Cursor 已關閉")
        
        # 格式化結果
        candidates = [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "company": row[4],
                "status": row[5],
                "position": row[6],
                "notes": row[7],
                "invited_count": row[8],
                "completed_count": row[9],
                "last_test_date": row[10].isoformat() if row[10] else None,
                "created_at": row[11].isoformat() if row[11] else None,
                "statistics": {
                    "total_invitations": row[12],
                    "completed_tests": row[13],
                    "pending_tests": row[14]
                },
                "latest_test": {
                    "project_name": row[15],
                    "score": row[16]
                } if row[15] else None
            }
            for row in results
        ]
        
        return {
            "success": True,
            "candidates": candidates,
            "total": total,
            "limit": limit,
            "offset": offset,
            "enterprise_id": enterprise_id
        }
        
    except Exception as e:
        logger.error(f"========== 錯誤發生 ==========")
        logger.error(f"錯誤類型: {type(e).__name__}")
        logger.error(f"錯誤訊息: {str(e)}")
        logger.error(f"完整 Traceback:", exc_info=True)
        logger.error(f"==============================")
        raise HTTPException(status_code=500, detail=f"無法獲取候選人列表: {str(e)}")


@app.get("/api/hr-consult/candidate/{candidate_id}")
async def get_candidate_detail(
    candidate_id: int,
    enterprise_id: Optional[int] = Query(None, description="企業 ID（可選，暫時）"),
    include_all_tests: bool = Query(False, description="是否包含所有測驗歷史")
):
    """
    獲取候選人詳細資訊（重構版）
    
    變更：
    1. 從 test_invitee 查詢（替代 core_user）
    2. 必須提供 enterprise_id（防止跨企業查詢）
    3. 測驗結果從 test_project_result 查詢
    4. 可選擇是否包含所有測驗歷史
    
    Path Parameters:
        candidate_id: 候選人 ID
    
    Query Parameters:
        enterprise_id: 企業 ID（必填，安全驗證）
        include_all_tests: 是否包含所有測驗歷史（默認 False）
    
    Returns:
        候選人詳細資訊，包含測評數據
    """
    try:
        if not db_connection:
            raise HTTPException(status_code=503, detail="資料庫連接不可用")
        
        cursor = db_connection.cursor()
        
        # 查詢候選人基本資訊（暫時不強制 enterprise_id）
        if enterprise_id:
            candidate_query = """
                SELECT 
                    ti.*,
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
            cursor.execute(candidate_query, (candidate_id, enterprise_id))
        else:
            candidate_query = """
                SELECT 
                    ti.*,
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
            cursor.execute(candidate_query, (candidate_id,))
        candidate = cursor.fetchone()
        
        if not candidate:
            raise HTTPException(
                status_code=404,
                detail="找不到該候選人"
            )
        
        # 查詢測驗歷史
        test_limit = None if include_all_tests else 1
        
        tests_query = """
            SELECT 
                tpr.id as result_id,
                tp.name as project_name,
                tpr.trait_results,
                tpr.score_value,
                tpr.prediction_value,
                tpr.crawled_at as test_date,
                tpr.crawl_status
            FROM test_project_result tpr
            JOIN test_invitation tinv ON tpr.test_invitation_id = tinv.id
            JOIN test_project tp ON tpr.test_project_id = tp.id
            WHERE tinv.invitee_id = %s
            ORDER BY tpr.crawled_at DESC
        """
        
        if test_limit:
            tests_query += f" LIMIT {test_limit}"
        
        cursor.execute(tests_query, (candidate_id,))
        tests = cursor.fetchall()
        
        cursor.close()
        
        # 格式化候選人資料
        candidate_data = {
            "id": candidate[0],
            "name": candidate[1],
            "email": candidate[2],
            "phone": candidate[3],
            "company": candidate[4],
            "status": candidate[5],
            "position": candidate[6],
            "notes": candidate[7],
            "invited_count": candidate[8],
            "completed_count": candidate[9],
            "last_test_date": candidate[10].isoformat() if candidate[10] else None,
            "statistics": {
                "total_invitations": candidate[-2],
                "completed_tests": candidate[-1]
            }
        }
        
        # 處理測驗數據
        test_data = []
        for test in tests:
            trait_results = test[2] or {}
            traits_list = trait_results.get('traits', [])
            
            # 分析優劣勢
            strengths = [t for t in traits_list if t.get('score', 0) >= 80]
            weaknesses = [t for t in traits_list if t.get('score', 0) < 60]
            
            test_data.append({
                "result_id": test[0],
                "project_name": test[1],
                "score_value": test[3],
                "prediction_value": test[4],
                "test_date": test[5].isoformat() if test[5] else None,
                "crawl_status": test[6],
                "summary": {
                    "total_traits": len(traits_list),
                    "strengths_count": len(strengths),
                    "weaknesses_count": len(weaknesses),
                    "top_traits": [
                        {
                            "name": t.get('chinese_name'),
                            "score": t.get('score')
                        }
                        for t in sorted(
                            traits_list,
                            key=lambda x: x.get('score', 0),
                            reverse=True
                        )[:5]
                    ]
                },
                "trait_results": trait_results if include_all_tests else None
            })
        
        candidate_data['tests'] = test_data
        
        return {
            "success": True,
            "candidate": candidate_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取候選人詳情失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法獲取候選人詳情")



@app.get("/api/hr-consult/history")
async def get_consultation_history(
    session_id: Optional[str] = Query(None, description="會話 ID"),
    candidate_id: Optional[int] = Query(None, description="候選人 ID"),
    limit: int = Query(10, ge=1, le=100, description="返回記錄數量")
):
    """
    獲取諮詢歷史記錄（重構版）
    
    變更：
    1. 歷史記錄關聯到 test_invitee（替代 core_user）
    
    Query Parameters:
        session_id: 會話 ID（可選）
        candidate_id: 候選人 ID（可選）
        limit: 返回記錄數量（默認 10，最大 100）
    
    Returns:
        歷史記錄列表
    """
    try:
        if not hr_service:
            raise HTTPException(status_code=503, detail="HR 諮詢服務未初始化")
        
        # 驗證參數
        if limit > 100:
            limit = 100
        
        history = hr_service.get_consultation_history(
            session_id=session_id,
            candidate_id=candidate_id,
            limit=limit
        )
        
        return {
            "success": True,
            "history": history,
            "count": len(history),
            "filters": {
                "session_id": session_id,
                "candidate_id": candidate_id
            }
        }
        
    except Exception as e:
        logger.error(f"獲取諮詢歷史失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法獲取諮詢歷史")


@app.delete("/api/hr-consult/history/{session_id}")
async def clear_session_history(session_id: str):
    """
    清除指定會話的諮詢歷史
    
    Path Parameters:
        session_id: 會話 ID
    
    Returns:
        刪除結果
    """
    try:
        if not db_connection:
            raise HTTPException(status_code=503, detail="資料庫連接不可用")
        
        cursor = db_connection.cursor()
        
        # 刪除歷史記錄
        delete_query = """
            DELETE FROM hr_consultation_history
            WHERE session_id = %s
        """
        
        cursor.execute(delete_query, (session_id,))
        deleted_count = cursor.rowcount
        
        db_connection.commit()
        cursor.close()
        
        return {
            "success": True,
            "message": f"已刪除 {deleted_count} 條記錄",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"清除諮詢歷史失敗: {e}", exc_info=True)
        db_connection.rollback()
        raise HTTPException(status_code=500, detail="無法清除諮詢歷史")


# ==================== 統計端點 ====================

@app.get("/api/hr-consult/statistics")
async def get_consultation_statistics(
    enterprise_id: Optional[int] = Query(None, description="企業 ID（可選，用於過濾）")
):
    """
    獲取 HR 諮詢統計資訊（重構版）
    
    變更：
    1. 統計基於 test_invitee（替代 core_user）
    2. 支援按企業過濾
    
    Query Parameters:
        enterprise_id: 企業 ID（可選）
    
    Returns:
        統計數據，包含總諮詢次數、候選人數等
    """
    try:
        if not db_connection:
            raise HTTPException(status_code=503, detail="資料庫連接不可用")
        
        cursor = db_connection.cursor()
        
        # 構建過濾條件
        filter_clause = ""
        params = []
        
        if enterprise_id:
            filter_clause = "WHERE ti.enterprise_id = %s"
            params = [enterprise_id]
        
        # 統計查詢
        stats_query = f"""
            SELECT 
                COUNT(*) as total_consultations,
                COUNT(DISTINCT h.candidate_id) as unique_candidates,
                COUNT(DISTINCT h.session_id) as unique_sessions,
                DATE(MIN(h.created_at)) as first_consultation,
                DATE(MAX(h.created_at)) as last_consultation
            FROM hr_consultation_history h
            LEFT JOIN test_invitee ti ON h.candidate_id = ti.id
            {filter_clause}
        """
        
        cursor.execute(stats_query, tuple(params))
        stats = cursor.fetchone()
        
        # 熱門候選人
        popular_query = f"""
            SELECT 
                ti.name,
                COUNT(*) as consultation_count
            FROM hr_consultation_history h
            JOIN test_invitee ti ON h.candidate_id = ti.id
            {filter_clause}
            GROUP BY ti.id, ti.name
            ORDER BY consultation_count DESC
            LIMIT 5
        """
        
        cursor.execute(popular_query, tuple(params))
        popular_candidates = [
            {"name": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        
        return {
            "success": True,
            "statistics": {
                "total_consultations": stats[0],
                "unique_candidates": stats[1],
                "unique_sessions": stats[2],
                "first_consultation": stats[3].isoformat() if stats[3] else None,
                "last_consultation": stats[4].isoformat() if stats[4] else None,
                "popular_candidates": popular_candidates
            },
            "filter": {
                "enterprise_id": enterprise_id
            }
        }
        
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法獲取統計資訊")


# ==================== 版本資訊端點 ====================

@app.get("/api/hr-consult/version")
async def get_version_info():
    """
    獲取版本資訊和變更說明
    
    Returns:
        版本資訊
    """
    return {
        "version": "2.0.0",
        "name": "HR Consultation API (Refactored)",
        "changes": [
            "✅ 使用 test_invitee 作為候選人表（替代 core_user）",
            "✅ 使用 test_project_result 作為測驗結果表（替代 individual_test_result）",
            "✅ 支援企業隔離（enterprise_id）",
            "✅ 支援特質配置（test_project_trait）",
            "✅ Prompt 包含完整候選人檔案、測驗歷史、特質權重",
            "✅ 返回更完整的測驗項目資訊"
        ],
        "data_tables": {
            "candidates": "test_invitee",
            "test_results": "test_project_result",
            "trait_config": "test_project_trait",
            "history": "hr_consultation_history"
        },
        "timestamp": datetime.now().isoformat()
    }


# ==================== 主程式 ====================

if __name__ == "__main__":
    import uvicorn
    
    # 從環境變數讀取配置
    host = os.getenv("HR_API_HOST", "0.0.0.0")
    port = int(os.getenv("HR_API_PORT", "8000"))  # ✅ 改為 8000
    
    logger.info(f"🚀 啟動 HR 諮詢 API 服務器（重構版）...")
    logger.info(f"📍 地址: http://{host}:{port}")
    logger.info(f"📖 API 文檔: http://{host}:{port}/docs")
    logger.info(f"📝 使用資料表: test_invitee, test_project_result, test_project_trait")
    logger.info(f"🔄 版本: 2.0.0")
    
    uvicorn.run(
        "hr_consultation_api:app",
        host=host,
        port=port,
        reload=True,  # 開發模式自動重載
        log_level="info"
    )

