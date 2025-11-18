#!/usr/bin/env python3
"""調試 trait_results 的數據結構"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PATH = os.path.join(SCRIPT_DIR, 'private-key-openssh.pem')

DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': PRIVATE_KEY_PATH,
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'projectdb',
    'db_user': 'projectuser',
    'db_password': 'projectpass'
}

# 建立 SSH 隧道
tunnel = SSHTunnelForwarder(
    (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
    ssh_username=DB_CONFIG['ssh_username'],
    ssh_pkey=DB_CONFIG['ssh_private_key'],
    remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
)

tunnel.start()
print(f"✓ SSH 隧道已建立")

# 連接資料庫
conn = psycopg2.connect(
    host='localhost',
    port=tunnel.local_bind_port,
    database=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_password']
)

cursor = conn.cursor()

# 查詢一筆 trait_results 數據
print("\n" + "=" * 80)
print("查詢 trait_results 的數據結構")
print("=" * 80)

cursor.execute("""
    SELECT 
        tiv.name,
        tpr.trait_results
    FROM test_project_result tpr
    INNER JOIN test_invitation ti ON tpr.test_invitation_id = ti.id
    INNER JOIN test_invitee tiv ON ti.invitee_id = tiv.id
    WHERE tpr.trait_results IS NOT NULL
      AND tpr.trait_results != '{}'::jsonb
    LIMIT 1;
""")

row = cursor.fetchone()
if row:
    name = row[0]
    trait_results = row[1]
    
    print(f"\n候選人: {name}")
    print(f"\ntrait_results 的 keys:")
    print("-" * 80)
    
    for key in list(trait_results.keys())[:5]:
        print(f"  • {key}")
        if isinstance(trait_results[key], dict):
            print(f"    內容: {json.dumps(trait_results[key], ensure_ascii=False, indent=6)}")
    
    print(f"\n總共有 {len(trait_results)} 個特質")

# 查詢 trait 表的對應關係
print("\n" + "=" * 80)
print("trait 表的 system_name 對應")
print("=" * 80)

cursor.execute("""
    SELECT system_name, chinese_name 
    FROM trait 
    WHERE system_name IN ('Creative Thinking', 'Cognitive Flexibility', 'communication', 'leadership')
    ORDER BY system_name;
""")

print("\nsystem_name -> chinese_name:")
print("-" * 80)
for row in cursor.fetchall():
    print(f"  {row[0]:<30} -> {row[1]}")

cursor.close()
conn.close()
tunnel.stop()

print("\n✓ 調試完成")
