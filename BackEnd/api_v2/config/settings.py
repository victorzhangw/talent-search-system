
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Force absolute path to ensure .env is found regardless of CWD
_config_dir = os.path.dirname(os.path.abspath(__file__)) # .../config
_project_root = os.path.dirname(_config_dir)             # .../api_v2
_env_path = os.path.join(_project_root, '.env')

if os.path.exists(_env_path):
    print(f"Loading .env from: {_env_path}")
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)
    
    # MANUAL FALLBACK: If dotenv fails, read file directly
    if not os.getenv('LLM_API_KEY'):
        print("DEBUG: os.getenv failed. Trying manual parse...")
        try:
            # Use utf-8-sig to handle BOM automatically
            with open(_env_path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    # Remove BOM explicitly if present (though utf-8-sig handles it)
                    clean_line = line.strip().lstrip('\ufeff')
                    if clean_line.startswith('LLM_API_KEY='):
                        val = clean_line.split('=', 1)[1].strip()
                        os.environ['LLM_API_KEY'] = val
                        print(f"DEBUG: Manual parse set LLM_API_KEY to {val[:5]}...")
                        break
        except Exception as e:
            print(f"DEBUG: Manual parse failed: {e}")
            
    print(f"DEBUG: Final LLM_API_KEY status: {'FOUND' if os.getenv('LLM_API_KEY') else 'MISSING'}")
else:
    print(f"WARNING: .env not found at {_env_path}")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    INTEGRATION_MODE = os.getenv('INTEGRATION_MODE', 'REAL') # MOCK or REAL
    
    # Database: Use absolute path to ensure consistency regardless of CWD
    # Start from this file: .../BackEnd/api_v2/config/settings.py
    _basedir = os.path.abspath(os.path.dirname(__file__)) 
    _project_root = os.path.dirname(_basedir) # .../BackEnd/api_v2
    _db_path = os.path.join(_project_root, 'app.db')
    
    # On Windows, path separator might need handling for SQLite URI if using pure path?
    # SQLAlchemy handles Windows paths fine usually, but let's be safe.
    DATABASE_URI = os.getenv('DATABASE_URI', f'sqlite:///{_db_path}')
    
    # LLM Settings — default mirrors BackEnd/api_v2/.env (DeepSeek)
    LLM_API_KEY = os.getenv('LLM_API_KEY')                                     # 必填，無預設值：key 遺失時 rag_engine 會報錯而非靜默呼叫錯誤服務
    LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-v4-flash')
    LLM_API_BASE = os.getenv('LLM_API_BASE', 'https://api.deepseek.com/v1')

    # LOG 打包器（事項 01-16）。預設關閉：新舊路徑並存，關閉時 chat 走既有的
    # 模組 prompt + context_builder，開啟時走 assemble -> 分段閘門 -> 稽核。
    # 兩者輸出格式不同，不可同時生效；切換前請先在測試環境驗證。
    USE_LOG_PACKER = os.getenv('USE_LOG_PACKER', '0').strip().lower() in ('1', 'true', 'yes', 'on')
    # Conversation history depth (1 turn = user + assistant pair)
    MAX_HISTORY_TURNS = int(os.getenv('MAX_HISTORY_TURNS', 6))
    # Daily token budget (all users combined); 0 = unlimited
    DAILY_TOKEN_LIMIT = int(os.getenv('DAILY_TOKEN_LIMIT', 0))
    # IP allowlist for /chat/ and /api/v2/* — comma-separated; empty = disabled
    ALLOWED_IPS = [ip.strip() for ip in os.getenv('ALLOWED_IPS', '').split(',') if ip.strip()]
    
    # External API Settings
    TRAITTY_API_BASE = os.getenv('TRAITTY_API_BASE') # Must be provided in .env
    PARTY_A_API_BASE = os.getenv('PARTY_A_API_BASE')
    PARTY_A_PLUGIN_SECRET = os.getenv('PARTY_A_PLUGIN_SECRET')
