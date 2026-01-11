
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    
    # LLM Settings
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'mock_key_dev')
    DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    
    # External API Settings
    TRAITTY_API_BASE = os.getenv('TRAITTY_API_BASE', 'https://uat.traitty.com') # Configurable UAT/PROD
    PARTY_A_API_BASE = os.getenv('PARTY_A_API_BASE')
    PARTY_A_PLUGIN_SECRET = os.getenv('PARTY_A_PLUGIN_SECRET')
