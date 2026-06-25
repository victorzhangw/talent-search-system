import os
import sys

# Project root → sys.path so BackEnd.api_v2 package resolves correctly
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from waitress import serve
from BackEnd.api_v2.app import create_app

app = create_app()

host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', 5000))

print(f"Starting Waitress on {host}:{port}")
serve(
    app,
    host=host,
    port=port,
    threads=6,
    channel_timeout=300,
    outbuf_overflow=1048576,
    send_bytes=8192,
    recv_bytes=8192,
    asyncore_use_poll=True,
)
