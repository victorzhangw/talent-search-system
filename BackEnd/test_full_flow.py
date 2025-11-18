#!/usr/bin/env python3
"""測試完整的數據流程"""

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

def generate_match_reason(candidate, score):
    """生成匹配理由"""
    trait_results = candidate.get('trait_results', {})
    
    if not trait_results:
        return "尚未完成測評"
    
    # 找出高分特質
    high_traits = []
    for trait_key, trait_data in trait_results.items():
        if isinstance(trait_data, dict):
            trait_score = trait_data.get('score', 0)
            chinese_name = trait_data.get('chinese_name', trait_key)
            if trait_score >= 75:
                high_traits.append(f"{chinese_name}({trait_score:.0f}分)")
    
    if high_traits:
        return f"優勢特質：{', '.join(high_traits[:3])}"
    else:
        return f"已完成 {len(trait_results)} 項特質測評"

# 測試完整流程
print("\n" + "=" * 80)
print("測試完整數據流程")
print("=" * 80)

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        tiv.id,
        tiv.name,
        tiv.email,
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
    # 模擬候選人數據
    candidate = {
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'trait_results': enrich_trait_results(row[3])
    }
    
    print(f"\n候選人: {candidate['name']}")
    print(f"Email: {candidate['email']}")
    
    # 生成匹配理由
    match_reason = generate_match_reason(candidate, 0.8)
    
    print(f"\n✅ 匹配理由: {match_reason}")
    
    # 顯示前3個特質
    print(f"\n特質詳情 (前3個):")
    print("-" * 80)
    for i, (key, value) in enumerate(list(candidate['trait_results'].items())[:3]):
        print(f"{i+1}. {value.get('chinese_name', key)}: {value.get('score', 0)}分")

cursor.close()
conn.close()
tunnel.stop()

print("\n✓ 測試完成")
