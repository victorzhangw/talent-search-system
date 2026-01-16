import os
import sys
from waitress import serve
from app import create_app

# 確保可以導入 app 模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run():
    # 建立 Flask 應用
    app = create_app()
    
    # 取得設定的 Port (預設 5000)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0') # 綁定所有網卡，方便 IIS 連接 127.0.0.1
    
    print(f"Starting Waitress server on {host}:{port}")
    print("Optimized for SSE streaming (Server-Sent Events)")
    
    # 啟動 Waitress with SSE-optimized settings
    # Critical parameters for streaming:
    # - channel_timeout: Extend timeout for long-running SSE connections
    # - outbuf_overflow: Increase output buffer overflow limit
    # - send_bytes: Reduce bytes per send to enable chunked streaming
    # - recv_bytes: Receive buffer size
    print("Waitress Server Running... (Check logs for requests)")
    
    serve(
        app, 
        host=host, 
        port=port, 
        threads=6,
        _quiet=False,
        # SSE Streaming optimization (only valid Waitress parameters)
        channel_timeout=300,      # 5 minutes for long SSE connections
        outbuf_overflow=1048576,  # 1MB overflow buffer
        send_bytes=8192,          # 8KB per send (enable chunked streaming)
        recv_bytes=8192,          # 8KB receive buffer
        asyncore_use_poll=True    # Use poll() instead of select() for better performance
    )

if __name__ == '__main__':
    run()


