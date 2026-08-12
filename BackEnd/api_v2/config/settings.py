
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
    # deepseek-v4-flash 是推理模型：它會先串流 reasoning_content，答案要等推理跑完才開始，
    # 而打包器只取 content，所以那段時間畫面上完全沒有東西。實測同一份 6,014 字 payload：
    # 推理開啟時模型先產出 9,487 個推理 chunk（13,808 字），第一個答案 token 在 75.5 秒；
    # 關閉後第一個答案 token 1.1 秒、總時間 80.5 -> 12.9 秒，段落齊全檢查與出口掃描結果不變。
    # 預設關閉推理。若日後判定分析深度不足，設 LLM_DISABLE_THINKING=0 即可切回，不需改程式。
    LLM_DISABLE_THINKING = os.getenv('LLM_DISABLE_THINKING', '1').strip().lower() in ('1', 'true', 'yes', 'on')

    # 逐字重播（呈現層）。分段閘門一次釋出一整段——實測 13 段裡最長 359 字——前端若直接
    # 貼上，畫面就會靜止 2-3 秒再整塊跳出來。首字其實只要 2.1 秒（其中模型佔 2.02 秒、
    # 閘門佔 0.08 秒），慢的是流動感不是延遲，所以解法在前端而不是把分段切小：實測那 13 段
    # 全部由空行切出，沒有一段碰到 400 字上限，調低上限不會讓任何一段提早釋出。
    # 值由 meta 事件送給前端。關閉時前端維持原本的整段貼上。
    TYPEWRITER_ENABLED = os.getenv('TYPEWRITER_ENABLED', '1').strip().lower() in ('1', 'true', 'yes', 'on')
    # 重播的「地板」速度。實際速度會自適應加快以免落後於後端（實測產出約 115 字/秒），
    # 這個值只決定文字稀疏時看起來多快。
    TYPEWRITER_CHARS_PER_SEC = int(os.getenv('TYPEWRITER_CHARS_PER_SEC', 60))

    # LOG 打包器（事項 01-16）。預設開啟：chat 走 assemble -> 分段閘門 -> 稽核。
    # 舊路徑（模組 prompt + context_builder）仍保留為 fallback，兩者輸出格式不同、
    # 不可同時生效；設 USE_LOG_PACKER=0 可退回舊路徑。
    USE_LOG_PACKER = os.getenv('USE_LOG_PACKER', '1').strip().lower() in ('1', 'true', 'yes', 'on')
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
