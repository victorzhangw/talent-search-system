
import os
import psycopg2
from sshtunnel import SSHTunnelForwarder
import tempfile
from contextlib import contextmanager

# Global instances
_tunnel = None
_db_pool = None

def get_db_config():
    """Retrieve database config from environment variables."""
    return {
        'ssh_host': os.getenv('DB_SSH_HOST', '54.199.255.239'),
        'ssh_port': int(os.getenv('DB_SSH_PORT', '22')),
        'ssh_username': os.getenv('DB_SSH_USERNAME', 'victor_cheng'),
        'ssh_private_key': os.getenv('DB_SSH_PRIVATE_KEY'),
        'ssh_private_key_file': os.getenv('DB_SSH_PRIVATE_KEY_FILE'),
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_port': int(os.getenv('DB_PORT', '5432')),
        'db_name': os.getenv('DB_NAME', 'projectdb'),
        'db_user': os.getenv('DB_USER', 'projectuser'),
        'db_password': os.getenv('DB_PASSWORD', 'projectpass')
    }

def get_ssh_tunnel():
    """Start SSH Tunnel if not already active."""
    global _tunnel
    config = get_db_config()
    
    if _tunnel is not None and _tunnel.is_active:
        return _tunnel

    ssh_key = config['ssh_private_key']
    ssh_pkey_file = config['ssh_private_key_file']
    
    # Prioritize key content (Production env var) -> file path -> default file
    final_key_path = None
    
    if ssh_key:
        # Create temp file for key content
        temp_key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        temp_key_file.write(ssh_key)
        temp_key_file.close()
        final_key_path = temp_key_file.name
    elif ssh_pkey_file and os.path.exists(ssh_pkey_file):
        final_key_path = ssh_pkey_file
    else:
        # Check standard location relative to this file? Or let caller handle it?
        # For now, if no key, we might be in local dev without SSH needed?
        # But this project SEEMS to require SSH.
        # Fallback to looking in parent directory?
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # api_v2 root
        possible_key = os.path.join(os.path.dirname(base_dir), 'private-key-openssh.pem') # backend root?
        if os.path.exists(possible_key):
             final_key_path = possible_key

    if not final_key_path:
        # Assume direct connection if key not found (Localhost DB?)
        # Or raise error if strict
        print("[WARN] No SSH Key found, attempting direct connection...")
        return None

    _tunnel = SSHTunnelForwarder(
        (config['ssh_host'], config['ssh_port']),
        ssh_username=config['ssh_username'],
        ssh_pkey=final_key_path,
        remote_bind_address=(config['db_host'], config['db_port'])
    )
    _tunnel.start()
    print(f"✅ SSH Tunnel established on port {_tunnel.local_bind_port}")
    return _tunnel


def get_db_connection():
    """Get a fresh PostgreSQL connection."""
    config = get_db_config()
    tunnel = get_ssh_tunnel()
    
    port = config['db_port']
    host = config['db_host']
    
    if tunnel:
        port = tunnel.local_bind_port
        host = 'localhost'
        
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=config['db_name'],
        user=config['db_user'],
        password=config['db_password']
    )
    return conn

@contextmanager
def get_db_cursor():
    """Context manager for DB cursor, handles commit/rollback."""
    conn = get_db_connection()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
