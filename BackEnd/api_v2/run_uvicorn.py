import os
import sys
import uvicorn
from app import create_app
from asgiref.wsgi import WsgiToAsgi

# 確保路徑正確
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run():
    # 建立 Flask 應用 (WSGI)
    flask_app = create_app()
    
    # 將 Flask 轉換為 ASGI (讓 Uvicorn 可以執行)
    asgi_app = WsgiToAsgi(flask_app)
    
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting Uvicorn server on {host}:{port}")
    print("Mode: ASGI (via asgiref adapter)")
    
    # 啟動 Uvicorn
    uvicorn.run(
        asgi_app, 
        host=host, 
        port=port,
        log_level="info",
        # 關鍵參數：保持連線超時時間 (對應 Waitress 的 channel_timeout)
        timeout_keep_alive=300 
    )

if __name__ == '__main__':
    run()
