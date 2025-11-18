#!/usr/bin/env python3
"""測試 SSH 連接"""

import paramiko
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PATH = os.path.join(SCRIPT_DIR, 'private-key-openssh.pem')

DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': PRIVATE_KEY_PATH,
}

print("=" * 60)
print("測試 SSH 連接")
print("=" * 60)
print()

# 檢查私鑰文件
print(f"[1] 檢查私鑰文件...")
if os.path.exists(PRIVATE_KEY_PATH):
    print(f"✓ 私鑰文件存在: {PRIVATE_KEY_PATH}")
    print(f"  文件大小: {os.path.getsize(PRIVATE_KEY_PATH)} bytes")
else:
    print(f"✗ 私鑰文件不存在: {PRIVATE_KEY_PATH}")
    exit(1)

print()

# 測試 SSH 連接
print(f"[2] 測試 SSH 連接...")
print(f"  主機: {DB_CONFIG['ssh_host']}")
print(f"  端口: {DB_CONFIG['ssh_port']}")
print(f"  用戶: {DB_CONFIG['ssh_username']}")
print()

try:
    # 載入私鑰
    print("  載入私鑰...")
    ssh_key = paramiko.RSAKey.from_private_key_file(PRIVATE_KEY_PATH)
    print("  ✓ 私鑰載入成功")
    
    # 建立 SSH 客戶端
    print("  建立 SSH 連接...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # 嘗試連接
    client.connect(
        hostname=DB_CONFIG['ssh_host'],
        port=DB_CONFIG['ssh_port'],
        username=DB_CONFIG['ssh_username'],
        pkey=ssh_key,
        timeout=10
    )
    
    print("  ✓ SSH 連接成功！")
    
    # 執行測試命令
    print("  執行測試命令...")
    stdin, stdout, stderr = client.exec_command('echo "SSH connection test"')
    output = stdout.read().decode().strip()
    print(f"  輸出: {output}")
    
    client.close()
    print()
    print("=" * 60)
    print("✓ SSH 連接測試通過！")
    print("=" * 60)
    
except paramiko.AuthenticationException as e:
    print(f"  ✗ 認證失敗: {e}")
    print()
    print("可能的原因：")
    print("  1. 私鑰不正確")
    print("  2. 用戶名不正確")
    print("  3. 伺服器不接受此私鑰")
    exit(1)
    
except paramiko.SSHException as e:
    print(f"  ✗ SSH 錯誤: {e}")
    print()
    print("可能的原因：")
    print("  1. SSH 伺服器無法連接")
    print("  2. 網路問題")
    print("  3. 防火牆阻擋")
    exit(1)
    
except Exception as e:
    print(f"  ✗ 連接失敗: {e}")
    print(f"  錯誤類型: {type(e).__name__}")
    exit(1)
