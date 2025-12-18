"""
HR 諮詢模組路由
從 hr_consultation_api.py 提取的路由部分
"""

from fastapi import APIRouter, HTTPException, Header, Query, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import logging
from datetime import datetime

# 導入 HR 諮詢服務
from hr_consultation_service import HRConsultationService, format_consultation_response
from prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter()


# ==================== 輔助函數 ====================

def ensure_db_connection(request: Request):
    """
    確保資料庫連接可用，如果連接已關閉則重新連接
    
    Args:
        request: FastAPI Request 對象
        
    Returns:
        可用的資料庫連接
        
    Raises:
        HTTPException: 如果無法建立連接
    """
    db_connection = request.app.state.db_connection
    
    if not db_connection:
        logger.error("資料庫連接不可用")
        raise HTTPException(status_code=503, detail="資料庫連接不可用")
    
    try:
        # 檢查連接是否已關閉
        if db_connection.closed:
            logger.warning("資料庫連接已關閉，嘗試重新連接...")
            from talent_search_api import get_db_connection
            db_connection = get_db_connection()
            request.app.state.db_connection = db_connection
            logger.info("✅ 資料庫重新連接成功")
        else:
            # 清除任何未完成的事務
            db_connection.rollback()
    except Exception as e:
        logger.warning(f"連接檢查警告: {e}")
        # 嘗試重新連接
        try:
            logger.warning("嘗試重新建立資料庫連接...")
            from talent_search_api import get_db_connection
            db_connection = get_db_connection()
            request.app.state.db_connection = db_connection
            logger.info("✅ 資料庫重新連接成功")
        except Exception as reconnect_error:
            logger.error(f"❌ 重新連接失敗: {reconnect_error}")
            raise HTTPException(status_code=503, detail="資料庫連接失敗")
    
    return db_connection


# ==================== Pydantic 模型 ====================

class ConsultationRequest(BaseModel):
    """HR 諮詢請求模型"""
    query: str = Field(..., min_length=2, max_length=500, description="諮詢問題")
    candidate_id: Optional[int] = Field(None, description="候選人 ID (test_invitee.id)")
    candidate_name: Optional[str] = Field(None, max_length=100, description="候選人姓名")
    session_id: Optional[str] = Field(None, max_length=255, description="會話 ID")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('諮詢問題不能為空')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "張三適合產品經理職位嗎？",
                "candidate_name": "張三",
                "session_id": "session_1234567890"
            }
        }


# ==================== 路由初始化 ====================

@router.on_event("startup")
async def startup():
    """路由啟動時初始化服務"""
    # 這裡暫時不初始化，將在 main_api.py 統一初始化
    pass


# ==================== API 端點 ====================

@router.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "HR Consultation Module",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/chat")
async def hr_consultation(
    request: ConsultationRequest,
    fastapi_request: Request,
    x_enterprise_id: Optional[int] = Header(None, alias="X-Enterprise-ID")
):
    """
    HR 諮詢主端點
    
    支持两种模式：
    1. 候选人特定咨询：需要提供 candidate_id 或 candidate_name
    2. 通用 HR 咨询：不需要候选人信息，提供一般性建议
    
    基於正確的資料表結構：test_invitee, test_project_result, test_project_trait
    """
    try:
        # 從 app.state 獲取共享資源
        db_connection = ensure_db_connection(fastapi_request)
        llm_service = fastapi_request.app.state.llm_service
        
        # 確定企業 ID（暫時設為可選，默認使用 None 以不限制企業）
        # TODO: 生產環境應該從認證 token 中獲取真實的 enterprise_id
        enterprise_id = x_enterprise_id or None
        
        logger.info(f"收到諮詢請求 - Enterprise: {enterprise_id}, Query: {request.query}, "
                   f"CandidateID: {request.candidate_id}, CandidateName: {request.candidate_name}")
        
        # 检查是否为候选人特定咨询
        is_candidate_specific = request.candidate_id or request.candidate_name
        
        if is_candidate_specific:
            # 候选人特定咨询 - 每次都創建新實例以確保環境變數生效
            hr_service_instance = HRConsultationService(db_connection, llm_service)
            
            # 調用諮詢服務
            result = hr_service_instance.consult(
                query=request.query,
                candidate_id=request.candidate_id,
                candidate_name=request.candidate_name,
                session_id=request.session_id,
                enterprise_id=enterprise_id
            )
            
            # 如果失敗，返回適當的 HTTP 狀態碼
            if not result.get('success'):
                error = result.get('error', '')
                if "找不到" in error or "不屬於" in error or "無法識別" in error:
                    status_code = 404
                elif "無測評數據" in error:
                    status_code = 404
                else:
                    status_code = 400
                raise HTTPException(status_code=status_code, detail=error)
            
            return result
        else:
            # 通用 HR 咨询 - 提供一般性建议
            logger.info("处理通用 HR 咨询（无候选人信息）")
            
            try:
                import httpx
                import os
                
                # 從環境變數獲取 LLM 配置
                api_key = os.getenv('LLM_API_KEY')
                if not api_key:
                    logger.error("LLM_API_KEY 未設定")
                    raise HTTPException(status_code=503, detail="AI 服務配置錯誤")
                
                api_host = os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn')
                api_endpoint = f"{api_host}/v1/chat/completions"
                model = os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3')
                temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
                max_tokens = int(os.getenv('LLM_MAX_TOKENS', '500'))
                max_response_length = int(os.getenv('LLM_MAX_RESPONSE_LENGTH', '150'))
                
                # 使用 Prompt 管理器構建通用 HR 諮詢的 Prompt
                prompt_manager = get_prompt_manager()
                system_prompt, user_prompt = prompt_manager.get_hr_general_prompts(
                    query=request.query,
                    max_response_length=max_response_length
                )
                
                # 调用 LLM
                request_data = {
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens
                }
                
                # 記錄 LLM API 調用開始（通用 HR 諮詢）
                logger.info("=" * 80)
                logger.info("🚀 開始調用 LLM API（通用 HR 諮詢）")
                logger.info(f"📍 API 端點: {api_endpoint}")
                logger.info(f"🤖 模型: {model}")
                logger.info(f"🌡️ Temperature: {temperature}")
                logger.info(f"📊 Max Tokens: {max_tokens}")
                logger.info(f"📝 System Prompt 長度: {len(system_prompt)} 字符")
                logger.info(f"📝 User Prompt 長度: {len(user_prompt)} 字符")
                logger.info(f"❓ 用戶問題: {request.query}")
                logger.info(f"⏰ 請求時間: {datetime.now().isoformat()}")
                
                import time
                start_time = time.time()
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        api_endpoint,
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {api_key}'
                        },
                        json=request_data
                    )
                    
                    elapsed_time = time.time() - start_time
                    
                    # 記錄響應狀態
                    logger.info(f"⏱️ API 響應時間: {elapsed_time:.2f} 秒")
                    logger.info(f"📡 HTTP 狀態碼: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.error(f"❌ LLM API 返回错误: {response.status_code}")
                        logger.error(f"📄 響應內容: {response.text[:500]}")
                        logger.info("=" * 80)
                        raise HTTPException(status_code=503, detail="AI 服务暂时不可用")
                    
                    result = response.json()
                    
                    # 記錄響應詳情
                    logger.info(f"✅ API 調用成功")
                    if 'usage' in result:
                        usage = result['usage']
                        logger.info(f"📊 Token 使用統計:")
                        logger.info(f"   - Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                        logger.info(f"   - Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                        logger.info(f"   - Total Tokens: {usage.get('total_tokens', 'N/A')}")
                    
                    answer = result['choices'][0]['message']['content'].strip()
                    logger.info(f"💬 原始回答長度: {len(answer)} 字符")
                    
                    # 强制字数限制
                    if len(answer) > max_response_length:
                        truncate_pos = max_response_length
                        min_pos = max(int(max_response_length * 0.8), 0)
                        for i in range(max_response_length - 1, min_pos, -1):
                            if i < len(answer) and answer[i] in ['。', '！', '？', '.', '!', '?']:
                                truncate_pos = i + 1
                                break
                        answer = answer[:truncate_pos] + "..."
                        logger.info(f"✂️ 回答已截斷至 {len(answer)} 字符")
                    
                    logger.info(f"✅ 通用 HR 諮詢完成")
                    logger.info("=" * 80)
                    
                    return {
                        "success": True,
                        "question": request.query,
                        "consultation": answer,
                        "mode": "general",
                        "note": "这是基于 HR 最佳实践的一般性建议。如需针对特定候选人的建议，请提供候选人姓名或 ID。",
                        "timestamp": datetime.now().isoformat()
                    }
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"通用 HR 咨询处理失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="咨询服务暂时不可用")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HR 諮詢處理失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="諮詢服務暫時不可用")


@router.get("/candidates")
async def list_candidates(
    request: Request,
    enterprise_id: Optional[int] = Query(None, description="企業 ID（可選，暫時）"),
    search: Optional[str] = Query(None, description="搜索關鍵字（姓名、郵箱、職位）"),
    status: Optional[str] = Query(None, description="候選人狀態（employed/job_seeker）"),
    has_test_data: Optional[bool] = Query(None, description="是否有測評數據"),
    sort_by: Optional[str] = Query("last_test_date", description="排序欄位（last_test_date/name/created_at）"),
    sort_order: Optional[str] = Query("desc", description="排序順序（asc/desc）"),
    limit: int = Query(20, ge=1, le=100, description="返回數量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    獲取候選人列表
    
    從 test_invitee 表查詢，包含測驗數據統計
    """
    try:
        logger.info(f"========== 開始處理候選人列表請求 ==========")
        logger.info(f"參數: enterprise_id={enterprise_id}, has_test_data={has_test_data}, limit={limit}, offset={offset}")
        
        # 確保資料庫連接可用
        db_connection = ensure_db_connection(request)
        logger.info("資料庫連接正常")
        
        cursor = db_connection.cursor()
        logger.info("Cursor 創建成功")
        
        # 構建查詢條件
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
                having_clause = "HAVING COUNT(DISTINCT CASE WHEN tpr.crawl_status = 'completed' THEN tpr.id END) > 0"
            else:
                having_clause = "HAVING COUNT(DISTINCT CASE WHEN tpr.crawl_status = 'completed' THEN tpr.id END) = 0"
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 驗證並構建排序子句
        valid_sort_fields = {
            'last_test_date': 'ti.last_test_date',
            'name': 'ti.name',
            'created_at': 'ti.created_at'
        }
        
        sort_field = valid_sort_fields.get(sort_by, 'ti.last_test_date')
        sort_direction = 'ASC' if sort_order.lower() == 'asc' else 'DESC'
        
        # 對於 last_test_date，NULL 值應該排在最後
        if sort_by == 'last_test_date':
            order_clause = f"ORDER BY {sort_field} {sort_direction} NULLS LAST, ti.created_at DESC"
        else:
            order_clause = f"ORDER BY {sort_field} {sort_direction}, ti.created_at DESC"
        
        logger.info(f"WHERE 子句: {where_clause}")
        logger.info(f"HAVING 子句: {having_clause}")
        logger.info(f"ORDER 子句: {order_clause}")
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
            {order_clause}
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        logger.info("執行主查詢...")
        cursor.execute(query, tuple(params))
        logger.info("查詢執行成功")
        
        results = cursor.fetchall()
        logger.info(f"獲取結果: {len(results)} 筆")
        
        # 獲取總數
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
            "sort_by": sort_by,
            "sort_order": sort_order,
            "enterprise_id": enterprise_id
        }
        
    except Exception as e:
        logger.error(f"========== 錯誤發生 ==========")
        logger.error(f"錯誤類型: {type(e).__name__}")
        logger.error(f"錯誤訊息: {str(e)}")
        logger.error(f"完整 Traceback:", exc_info=True)
        logger.error(f"==============================")
        raise HTTPException(status_code=500, detail=f"無法獲取候選人列表: {str(e)}")


@router.get("/candidate/{candidate_id}")
async def get_candidate_detail(
    request: Request,
    candidate_id: int,
    enterprise_id: Optional[int] = Query(None, description="企業 ID（可選，暫時）"),
    include_all_tests: bool = Query(False, description="是否包含所有測驗歷史")
):
    """
    獲取候選人詳細資訊
    
    從 test_invitee 查詢，包含測驗結果
    """
    try:
        # 確保資料庫連接可用
        db_connection = ensure_db_connection(request)
        
        cursor = db_connection.cursor()
        
        # 查詢候選人基本資訊
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
        
        # 查詢測驗歷史（略，與原代碼相同）
        # ... 省略詳細實作
        
        cursor.close()
        
        return {
            "success": True,
            "candidate": {
                "id": candidate[0],
                "name": candidate[1],
                # ... 其他欄位
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取候選人詳情失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="無法獲取候選人詳情")


@router.get("/history")
async def get_consultation_history(
    request: Request,
    session_id: Optional[str] = Query(None, description="會話 ID"),
    candidate_id: Optional[int] = Query(None, description="候選人 ID"),
    limit: int = Query(10, ge=1, le=100, description="返回記錄數量")
):
    """
    獲取諮詢歷史記錄
    """
    try:
        # 從 app.state 獲取 HR 服務
        db_connection = ensure_db_connection(request)
        llm_service = request.app.state.llm_service
        
        # 每次都創建新實例以確保環境變數生效
        hr_service_instance = HRConsultationService(db_connection, llm_service)
        
        if limit > 100:
            limit = 100
        
        history = hr_service_instance.get_consultation_history(
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


@router.get("/version")
async def get_version_info():
    """
    獲取版本資訊和變更說明
    """
    return {
        "version": "2.0.0",
        "name": "HR Consultation Module (Refactored)",
        "changes": [
            "✅ 使用 test_invitee 作為候選人表（替代 core_user）",
            "✅ 使用 test_project_result 作為測驗結果表",
            "✅ 支援特質配置（test_project_trait）",
            "✅ Prompt 包含完整候選人檔案、測驗歷史、特質權重",
            "✅ 模組化設計，整合到主 API"
        ],
        "data_tables": {
            "candidates": "test_invitee",
            "test_results": "test_project_result",
            "trait_config": "test_project_trait",
            "history": "hr_consultation_history"
        },
        "timestamp": datetime.now().isoformat()
    }


