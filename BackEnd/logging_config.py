"""
統一的日誌配置模組
配置日誌同時輸出到控制台和文件
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 日誌目錄
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')

# 確保日誌目錄存在
os.makedirs(LOG_DIR, exist_ok=True)

# 日誌文件路徑
LOG_FILES = {
    'main': os.path.join(LOG_DIR, 'main.log'),
    'llm_api': os.path.join(LOG_DIR, 'llm_api.log'),
    'hr_consultation': os.path.join(LOG_DIR, 'hr_consultation.log'),
    'talent_search': os.path.join(LOG_DIR, 'talent_search.log'),
    'interview': os.path.join(LOG_DIR, 'interview.log'),
    'error': os.path.join(LOG_DIR, 'error.log'),
}

# 日誌格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日誌級別（從環境變數讀取，默認 INFO）
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


_logging_initialized = False

def setup_logging():
    """
    設置日誌系統
    - 控制台輸出：INFO 及以上級別
    - 文件輸出：所有級別，按類型分文件
    - 自動輪轉：每個文件最大 10MB，保留 5 個備份
    """
    global _logging_initialized
    
    # 如果已經初始化過，直接返回
    if _logging_initialized:
        return
    
    # 獲取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 設置為 DEBUG 以捕獲所有日誌
    
    # 清除現有的 handlers（避免重複）
    root_logger.handlers.clear()
    
    # 創建格式化器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # 1. 控制台 Handler（INFO 及以上）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 主日誌文件 Handler（所有級別）
    main_handler = RotatingFileHandler(
        LOG_FILES['main'],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(formatter)
    root_logger.addHandler(main_handler)
    
    # 3. LLM API 專用日誌 Handler
    llm_handler = RotatingFileHandler(
        LOG_FILES['llm_api'],
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    llm_handler.setLevel(logging.DEBUG)
    llm_handler.setFormatter(formatter)
    
    # 為 LLM 相關的 logger 添加專用 handler
    llm_loggers = [
        'hr_consultation_service',
        'hr_consultation_routes',
        'talent_search_api',
        'interview_api',
    ]
    for logger_name in llm_loggers:
        logger = logging.getLogger(logger_name)
        logger.addHandler(llm_handler)
        # 防止日誌向上傳播到根 logger（避免重複記錄）
        logger.propagate = False
    
    # 4. 錯誤日誌 Handler（ERROR 及以上）
    error_handler = RotatingFileHandler(
        LOG_FILES['error'],
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # 記錄日誌系統啟動信息
    logging.info("=" * 80)
    logging.info("📝 日誌系統已啟動")
    logging.info(f"📁 日誌目錄: {LOG_DIR}")
    logging.info(f"📊 日誌級別: {LOG_LEVEL}")
    logging.info(f"📄 主日誌: {LOG_FILES['main']}")
    logging.info(f"🤖 LLM API 日誌: {LOG_FILES['llm_api']}")
    logging.info(f"❌ 錯誤日誌: {LOG_FILES['error']}")
    logging.info(f"⏰ 啟動時間: {datetime.now().isoformat()}")
    logging.info("=" * 80)
    
    # 標記為已初始化
    _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    獲取指定名稱的 logger
    
    Args:
        name: logger 名稱（通常使用 __name__）
    
    Returns:
        logging.Logger: 配置好的 logger 實例
    """
    return logging.getLogger(name)


def get_log_files_info():
    """
    獲取所有日誌文件的信息
    
    Returns:
        dict: 日誌文件信息
    """
    info = {}
    for name, path in LOG_FILES.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            size_mb = size / (1024 * 1024)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            info[name] = {
                'path': path,
                'size': size,
                'size_mb': f"{size_mb:.2f} MB",
                'modified': mtime.isoformat(),
                'exists': True
            }
        else:
            info[name] = {
                'path': path,
                'exists': False
            }
    return info


# 自動初始化（當模組被導入時）
if __name__ != '__main__':
    setup_logging()
