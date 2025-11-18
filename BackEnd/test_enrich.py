#!/usr/bin/env python3
"""測試 enrich_trait_results 函數"""

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

# 全域變數
tunnel = None
db_conn = None
trait_cache = {}

def get_db_connection():
    global tunnel, db_conn
    
    if db_conn is None or db_conn.closed:
        if tunnel is None or not tunnel.is_active:
            tunnel = SSHTunnelForwarder(
                (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
                ssh_username=DB_CONFIG['ssh_username'],
                ssh_pkey=DB_CONFIG['ssh_private_key'],
                remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
            )
            tunnel.start()
        
        db_conn = psycopg2.connect(
            host='localhost',
            port=tunnel.local_bind_port,
            database=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_password']
        )
    
    return db_conn

def load_trait_definitions():
    global trait_cache
    
    if trait_cache:
        return trait_cache
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, chinese_name, system_name, description
        FROM trait
        ORDER BY id;
    """)
    
    for row in cursor.fetchall():
        trait_id, chinese_name, system_name, description = row
        trait_cache[system_name] = {
            'id': trait_id,
            'chinese_name': chinese_name,
            'system_name': system_name,
            'description': description
        }
    
    cursor.close()
    print(f"✓ 載入 {len(trait_cache)} 個特質定義")
    return trait_cache

def enrich_trait_results(trait_results):
    """豐富特質結果，添加中文名稱和描述"""
    if not trait_results:
        return {}
    
    traits = load_trait_definitions()
    enriched = {}
    
    for trait_key, trait_data in trait_results.items():
        if trait_key in traits:
            trait_def = traits[trait_key]
            
            if isinstance(trait_data, dict):
                enriched[trait_key] = {
                    **trait_data,
                    'chinese_name': trait_def['chinese_name'],
                    'description': trait_def['description']
                }
            else:
                enriched[trait_key] = {
                    'score': trait_data,
                    'chinese_name': trait_def['chinese_name'],
                    'description': trait_def['description']
                }
        else:
            if isinstance(trait_data, dict):
                enriched[trait_key] = trait_data
            else:
                enriched[trait_key] = {'score': trait_data, 'chinese_name': trait_key}
    
    return enriched

# 測試
print("\n" + "=" * 80)
print("測試 enrich_trait_results 函數")
print("=" * 80)

conn = get_db_connection()
cursor = conn.cursor()

# 獲取一筆 trait_results
cursor.execute("""
    SELECT tiv.name, tpr.trait_results
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
    original_trait_results = row[1]
    
    print(f"\n候選人: {name}")
    print(f"\n原始 trait_results (前3個):")
    print("-" * 80)
    for i, (key, value) in enumerate(list(original_trait_results.items())[:3]):
        print(f"\n{i+1}. Key: {key}")
        print(f"   原始 chinese_name: {value.get('chinese_name', '無')}")
        print(f"   分數: {value.get('score', 0)}")
    
    # 執行 enrich
    enriched = enrich_trait_results(original_trait_results)
    
    print(f"\n\n豐富後的 trait_results (前3個):")
    print("-" * 80)
    for i, (key, value) in enumerate(list(enriched.items())[:3]):
        print(f"\n{i+1}. Key: {key}")
        print(f"   ✅ 新 chinese_name: {value.get('chinese_name', '無')}")
        print(f"   分數: {value.get('score', 0)}")
        print(f"   描述: {value.get('description', '無')[:50]}...")

cursor.close()
conn.close()
tunnel.stop()

print("\n\n✓ 測試完成")
