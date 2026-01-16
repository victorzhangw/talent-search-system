"""
IIS WSGI 入口點
因為 app.py 使用工廠模式 (create_app)，IIS 無法直接調用。
此檔案負責建立應用實例供 wfastcgi 使用。
"""
import sys
import os

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
except ImportError:
    # 如果找不到 app 模組，可能是路徑問題，嘗試上一層或其他修正
    # 但在標準部署結構下，app.py 應與 wsgi.py 同層
    raise
except Exception as e:
    # 紀錄初始化錯誤
    print(f"Error creating app: {e}")
    raise
