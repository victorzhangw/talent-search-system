#!/usr/bin/env python3
"""查詢資料庫中的 traits"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import paramiko

DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': 'private-key-openssh.pem',
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'projectdb',
    'db_user': 'projectuser',
    'db_password': 'projectpass'
}

def load_ssh_key(key_path):
    """載入 SSH 私鑰"""
    return paramiko.RSAKey.from_private_key_file(key_path)

# 建立 SSH 隧道
ssh_key = load_ssh_key(DB_CONFIG['ssh_private_key'])
tunnel = SSHTunnelForwarder(
    (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
    ssh_username=DB_CONFIG['ssh_username'],
    ssh_pkey=ssh_key,
    remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
)

tunnel.start()
print(f"SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")

# 連接資料庫
conn = psycopg2.connect(
    host='localhost',
    port=tunnel.local_bind_port,
    database=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_password']
)

cursor = conn.cursor()

# 查詢所有 traits
print("\n" + "=" * 100)
print("資料庫中的 Traits (特質)")
print("=" * 100)

cursor.execute("""
    SELECT id, chinese_name, system_name, description 
    FROM trait 
    ORDER BY id
    LIMIT 50;
""")

rows = cursor.fetchall()

print(f"\n找到 {len(rows)} 個特質：\n")
print(f"{'ID':<5} | {'中文名稱':<20} | {'系統名稱':<30} | {'描述':<40}")
print("-" * 100)

for row in rows:
    trait_id = row[0]
    chinese_name = row[1] or ''
    system_name = row[2] or ''
    description = (row[3] or '')[:40]
    
    print(f"{trait_id:<5} | {chinese_name:<20} | {system_name:<30} | {description:<40}")

# 查詢 test_project_category 看看有哪些分類
print("\n" + "=" * 100)
print("測評專案分類 (Categories)")
print("=" * 100)

cursor.execute("""
    SELECT id, name, description 
    FROM test_project_category 
    ORDER BY id
    LIMIT 20;
""")

categories = cursor.fetchall()
print(f"\n找到 {len(categories)} 個分類：\n")
print(f"{'ID':<5} | {'分類名稱':<30} | {'描述':<50}")
print("-" * 100)

for cat in categories:
    cat_id = cat[0]
    cat_name = cat[1] or ''
    cat_desc = (cat[2] or '')[:50]
    print(f"{cat_id:<5} | {cat_name:<30} | {cat_desc:<50}")

# 查詢 trait 與 category 的關聯
print("\n" + "=" * 100)
print("特質與分類的關聯")
print("=" * 100)

cursor.execute("""
    SELECT 
        tpct.id,
        tpc.name as category_name,
        t.chinese_name as trait_name,
        t.system_name
    FROM test_project_category_trait tpct
    JOIN test_project_category tpc ON tpct.category_id = tpc.id
    JOIN trait t ON tpct.trait_id = t.id
    ORDER BY tpc.name, t.chinese_name
    LIMIT 50;
""")

relations = cursor.fetchall()
print(f"\n找到 {len(relations)} 個關聯：\n")
print(f"{'分類':<30} | {'特質(中文)':<20} | {'特質(系統名)':<30}")
print("-" * 100)

for rel in relations:
    category = rel[1] or ''
    trait_cn = rel[2] or ''
    trait_sys = rel[3] or ''
    print(f"{category:<30} | {trait_cn:<20} | {trait_sys:<30}")

cursor.close()
conn.close()
tunnel.stop()

print("\n查詢完成！")
