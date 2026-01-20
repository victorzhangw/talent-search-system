
import os
import sys

# -----------------------------
# ASGI ENTRY (For Uvicorn/Production)
# -----------------------------

# 1. Setup Path
# Adjust this to point to the directory containing 'BackEnd'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    # 2. Import existing Factory
    # 2. Import existing Factory
    # Check if app.py exists in current directory (UAT Flat Structure)
    if os.path.exists(os.path.join(BASE_DIR, 'app.py')):
        print("[ASGI] Found app.py in root. Importing...")
        from app import create_app
    else:
        # Scenario B: Nested structure (Local Dev)
        print("[ASGI] app.py not found in root. Trying BackEnd.api_v2...")
        from BackEnd.api_v2.app import create_app
    
    # 3. Create Flask App
    _flask_app = create_app()
    
    # 4. Wrap with WsgiToAsgi
    # Ensure 'asgiref' is installed (pip install asgiref)
    from asgiref.wsgi import WsgiToAsgi
    
    app = WsgiToAsgi(_flask_app)
    print("✅ ASGI App initialized successfully. Ready for Uvicorn.")

except Exception as e:
    print(f"❌ Failed to initialize ASGI app: {e}")
    import traceback
    traceback.print_exc()
