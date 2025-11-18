"""
環境配置模組 - 支持本地開發和雲端部署
"""
import os
import tempfile


def get_ssh_key_path():
    """
    獲取 SSH 私鑰路徑
    
    優先級：
    1. 環境變數 DB_SSH_PRIVATE_KEY（可以是文件路徑或私鑰內容）
    2. 本地文件 private-key-openssh.pem
    """
    private_key = os.getenv('DB_SSH_PRIVATE_KEY')
    
    if not private_key:
        # 本地開發：使用本地文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, 'private-key-openssh.pem')
    
    # 檢查是否是文件路徑
    if os.path.exists(private_key):
        return private_key
    
    # 如果是私鑰內容，寫入臨時文件
    if '-----BEGIN' in private_key:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
            f.write(private_key)
            os.chmod(f.name, 0o600)
            return f.name
    
    # 默認返回本地文件路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'private-key-openssh.pem')


# 數據庫配置
DB_CONFIG = {
    'ssh_host': os.getenv('DB_SSH_HOST', '54.199.255.239'),
    'ssh_port': int(os.getenv('DB_SSH_PORT', '22')),
    'ssh_username': os.getenv('DB_SSH_USERNAME', 'victor_cheng'),
    'ssh_private_key': get_ssh_key_path(),
    'db_host': os.getenv('DB_HOST', 'localhost'),
    'db_port': int(os.getenv('DB_PORT', '5432')),
    'db_name': os.getenv('DB_NAME', 'projectdb'),
    'db_user': os.getenv('DB_USER', 'projectuser'),
    'db_password': os.getenv('DB_PASSWORD', 'projectpass')
}

# LLM API 配置
LLM_API_HOST = os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn')

LLM_CONFIG = {
    'api_key': os.getenv('LLM_API_KEY', 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff'),
    'api_host': LLM_API_HOST,
    'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3'),
    'endpoint': f'{LLM_API_HOST}/v1/chat/completions'
}

# 應用配置
APP_CONFIG = {
    'host': os.getenv('HOST', '0.0.0.0'),
    'port': int(os.getenv('PORT', '8000')),
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',
    'environment': os.getenv('ENVIRONMENT', 'development')
}


def print_config_info():
    """打印配置信息（隱藏敏感信息）"""
    print("\n" + "=" * 60)
    print("配置信息")
    print("=" * 60)
    print(f"環境: {APP_CONFIG['environment']}")
    print(f"主機: {APP_CONFIG['host']}:{APP_CONFIG['port']}")
    print(f"數據庫 SSH: {DB_CONFIG['ssh_username']}@{DB_CONFIG['ssh_host']}")
    print(f"數據庫名稱: {DB_CONFIG['db_name']}")
    print(f"LLM API: {LLM_CONFIG['api_host']}")
    print(f"LLM 模型: {LLM_CONFIG['model']}")
    print("=" * 60 + "\n")
