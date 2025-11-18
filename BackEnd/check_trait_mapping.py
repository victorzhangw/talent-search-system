#!/usr/bin/env python3
"""檢查 trait 表和 trait_results 的對應關係"""

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

tunnel = SSHTunnelForwarder(
    (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
    ssh_username=DB_CONFIG['ssh_username'],
    ssh_pkey=DB_CONFIG['ssh_private_key'],
    remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
)

tunnel.start()
conn = psycopg2.connect(
    host='localhost',
    port=tunnel.local_bind_port,
    database=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_password']
)

cursor = conn.cursor()

# 1. 查詢 trait 表中的所有特質
print("\n" + "=" * 80)
print("trait 表中的特質 (前20個)")
print("=" * 80)

cursor.execute("""
    SELECT id, system_name, chinese_name 
    FROM trait 
    ORDER BY id
    LIMIT 20;
""")

trait_map = {}
print(f"\n{'ID':<5} | {'system_name':<30} | {'chinese_name':<20}")
print("-" * 80)
for row in cursor.fetchall():
    trait_id, system_name, chinese_name = row
    trait_map[system_name] = chinese_name
    print(f"{trait_id:<5} | {system_name:<30} | {chinese_name:<20}")

# 2. 查詢 trait_results 中實際使用的 key
print("\n" + "=" * 80)
print("trait_results 中實際使用的 keys (第一筆數據)")
print("=" * 80)

cursor.execute("""
    SELECT trait_results
    FROM test_project_result
    WHERE trait_results IS NOT NULL
      AND trait_results != '{}'::jsonb
    LIMIT 1;
""")

row = cursor.fetchone()
if row:
    trait_results = row[0]
    
    print(f"\n找到 {len(trait_results)} 個特質")
    print(f"\n{'trait_results key':<30} | {'對應的中文名稱':<20}")
    print("-" * 80)
    
    for key in list(trait_results.keys())[:10]:
        chinese_from_db = trait_map.get(key, '❌ 未找到')
        chinese_in_data = trait_results[key].get('chinese_name', '無')
        print(f"{key:<30} | DB: {chinese_from_db:<15} | Data: {chinese_in_data}")

# 3. 檢查 Creative Thinking 和 Cognitive Flexibility
print("\n" + "=" * 80)
print("檢查特定特質")
print("=" * 80)

cursor.execute("""
    SELECT system_name, chinese_name, description
    FROM trait 
    WHERE system_name IN ('Creative Thinking', 'Cognitive Flexibility')
    ORDER BY system_name;
""")

print(f"\n{'system_name':<30} | {'chinese_name':<20} | {'description':<40}")
print("-" * 100)
for row in cursor.fetchall():
    system_name, chinese_name, description = row
    desc_short = (description or '')[:40]
    print(f"{system_name:<30} | {chinese_name:<20} | {desc_short}")

cursor.close()
conn.close()
tunnel.stop()

print("\n✓ 檢查完成")
