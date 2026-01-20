
import sys
import os

# Explicitly add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Starting Backend from: {project_root}")

try:
    from BackEnd.api_v2.app import create_app
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Startup Failed: {e}")
