"""
IIS WSGI 入口點
因為 app.py 使用工廠模式 (create_app)，IIS 無法直接調用。
此檔案負責建立應用實例供 wfastcgi 使用。
"""
import sys
import os
import logging
from utils.logger import get_daily_logger

def get_wsgi_logger():
    return get_daily_logger("WSGI_Logger", "wsgi.log", level=logging.ERROR)

# 將當前目錄加入 sys.path，確保能導入 app 模組
# 假設此檔案位於應用程式根目錄 (例如 C:\inetpub\wwwroot\TalentChatAPI)
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 導入 create_app
try:
    from app import create_app
    # 建立應用實例
    # wfastcgi 會尋找並執行此變數
    app = create_app()
except ImportError as ie:
    # 紀錄載入模組錯誤
    logger = get_wsgi_logger()
    logger.error(f"ImportError while loading app: {ie}", exc_info=True)
    raise
except Exception as e:
    # 紀錄初始化錯誤
    logger = get_wsgi_logger()
    logger.error(f"Error creating app: {e}", exc_info=True)
    raise
