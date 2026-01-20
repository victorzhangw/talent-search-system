
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
    try:
        # Scenario A: Flat structure (e.g. deployed with contents of api_v2 in root)
        from app import create_app
        print("[ASGI] Imported from local app.py")
    except ImportError:
        # Scenario B: Nested structure (e.g. local dev with BackEnd/api_v2)
        from BackEnd.api_v2.app import create_app
        print("[ASGI] Imported from BackEnd.api_v2.app")
    
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
