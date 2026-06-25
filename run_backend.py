import os
import sys

# Project root → sys.path so BackEnd.api_v2 package resolves correctly
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from BackEnd.api_v2.app import create_app

app = create_app()

host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', 5000))

print(f"Starting Flask on {host}:{port}")
# threaded=True enables concurrent SSE streams; use_reloader=False avoids double-start
app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
