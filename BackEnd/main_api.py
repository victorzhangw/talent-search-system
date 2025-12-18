"""
主 API 應用 - 統一入口
整合所有子模組：人才搜索、HR 諮詢等

架構設計：
- main_api.py: 主應用，負責路由分發和中介軟體
- talent_search_api.py: 人才搜索模組（改為 APIRouter）
- hr_consultation_api.py: HR 諮詢模組（改為 APIRouter）
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數（必須在其他模組導入之前）
load_dotenv('.env.local')

# 導入並初始化日誌配置（必須在其他模組導入之前）
from logging_config import setup_logging, get_logger, get_log_files_info

# 設置日誌系統
setup_logging()
logger = get_logger(__name__)

logger.info(f"環境變數已載入 - LLM_API_KEY: {'已設定' if os.getenv('LLM_API_KEY') else '未設定'}")
logger.info(f"環境變數 - LLM_MAX_RESPONSE_LENGTH: {os.getenv('LLM_MAX_RESPONSE_LENGTH', '未設定')}")
logger.info(f"環境變數 - LLM_MAX_TOKENS: {os.getenv('LLM_MAX_TOKENS', '未設定')}")

# 創建主應用
app = FastAPI(
    title="人才管理系統 API",
    description="整合人才搜索、HR 諮詢等功能的統一 API",
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

from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"👉 INCOMING REQUEST: {request.method} {request.url.path}")
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"👈 RESPONSE STATUS: {response.status_code} | Time: {process_time:.2f}ms")
    return response

# ==================== 健康檢查 ====================

@app.get("/")
async def root():
    """根路徑"""
    return {
        "service": "人才管理系統 API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "modules": [
            {"name": "人才搜索", "path": "/api/talent"},
            {"name": "HR 諮詢", "path": "/api/hr-consult"},
        ]
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "service": "Main API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/logs/info")
async def get_logs_info():
    """
    獲取日誌文件信息
    返回所有日誌文件的路徑、大小、修改時間等信息
    """
    try:
        info = get_log_files_info()
        return {
            "success": True,
            "logs": info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"獲取日誌信息失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ==================== 掛載子模組路由 ====================

import traceback

# 導入子模組的路由
try:
    logger.info("🔄 正在載入人才搜索模組...")
    from talent_search_routes import router as talent_router
    app.include_router(talent_router, prefix="/api/talent", tags=["人才搜索"])
    logger.info("✅ 人才搜索模組載入成功")
except Exception as e:
    logger.error(f"❌ 人才搜索模組載入失敗: {e}")
    logger.error(traceback.format_exc())
    # 不拋出異常，讓其他模組嘗試載入

try:
    logger.info("🔄 正在載入 HR 諮詢模組...")
    # 這裡強制拋出異常以便在控制台看到錯誤
    from hr_consultation_routes import router as hr_router
    app.include_router(hr_router, prefix="/api/hr-consult", tags=["HR 諮詢"])
    logger.info("✅ HR 諮詢模組載入成功")
except Exception as e:
    logger.error(f"❌ HR 諮詢模組載入失敗: {e}")
    logger.error(traceback.format_exc())
    # 這裡我們希望看到錯誤，所以記錄完後再次拋出，或者確保用戶能在日誌中看到
    print("CRITICAL ERROR: HR Consultation module failed to load!")
    print(traceback.format_exc())


# ==================== 啟動事件 ====================

@app.on_event("startup")
async def startup_event():
    """應用啟動時執行"""
    logger.info("=" * 60)
    logger.info("  🚀 人才管理系統 API 啟動中...")
    logger.info("=" * 60)
    
    # 初始化共享資源（資料庫連接、LLM 服務等）
    try:
        from talent_search_api import get_db_connection, LLMService, load_trait_definitions
        
        logger.info("🔄 正在初始化資料庫連接...")
        db_connection = get_db_connection()
        logger.info("✅ 資料庫連接成功")
        
        logger.info("🔄 正在載入特質定義...")
        load_trait_definitions()
        logger.info("✅ 特質定義載入完成")
        
        logger.info("🔄 正在初始化 LLM 服務...")
        llm_service = LLMService()
        logger.info("✅ LLM 服務初始化完成")
        
        # 將共享資源存儲到 app.state（供子模組使用）
        app.state.db_connection = db_connection
        app.state.llm_service = llm_service
        
        logger.info("=" * 60)
        logger.info("  🎉 人才管理系統 API 啟動成功！")
        logger.info("=" * 60)
        logger.info(f"  📍 API 文檔: http://localhost:8000/docs")
        logger.info(f"  📍 人才搜索: http://localhost:8000/api/talent")
        logger.info(f"  📍 HR 諮詢: http://localhost:8000/api/hr-consult")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 應用啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時執行"""
    logger.info("=" * 60)
    logger.info("  👋 人才管理系統 API 關閉中...")
    logger.info("=" * 60)
    
    # 清理資源
    if hasattr(app.state, 'db_connection'):
        app.state.db_connection.close()
        logger.info("✅ 資料庫連接已關閉")
    
    logger.info("=" * 60)
    logger.info("  ✅ 人才管理系統 API 已關閉")
    logger.info("=" * 60)


# ==================== 主程式 ====================

if __name__ == "__main__":
    import uvicorn
    
    # 從環境變數讀取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"🚀 啟動主 API 服務器...")
    logger.info(f"📍 地址: http://{host}:{port}")
    
    uvicorn.run(
        "main_api:app",
        host=host,
        port=port,
        reload=True,  # 開發模式自動重載
        log_level="info",
        timeout_keep_alive=75,  # Keep-alive 超時（秒）
        timeout_graceful_shutdown=10  # 優雅關閉超時（秒）
    )
