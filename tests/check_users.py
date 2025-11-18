#!/usr/bin/env python3
"""
檢查資料庫中的用戶
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder

# 資料庫配置
DB_CONFIG = {
    'ssh_host': '140.125.45.162',
    'ssh_port': 22,
    'ssh_username': 'service',
    'ssh_private_key': 'private-key-openssh.pem',
    'db_host': '127.0.0.1',
    'db_port': 5432,
    'db_name': 'postgres',
    'db_user': 'postgres',
    'db_password': 'Cych@1234'
}

# 建立 SSH 隧道
tunnel = SSHTunnelForwarder(
    (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
    ssh_username=DB_CONFIG['ssh_username'],
    ssh_pkey=DB_CONFIG['ssh_private_key'],
    remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
)

tunnel.start()
print(f"✅ SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")

# 連接資料庫
conn = psycopg2.connect(
    host='localhost',
    port=tunnel.local_bind_port,
    database=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_password']
)

print("✅ 資料庫連接成功\n")

cursor = conn.cursor()

# 1. 檢查所有用戶
print("="*80)
print("所有用戶列表")
print("="*80)

cursor.execute("""
    SELECT id, username, email, date_joined
    FROM core_user
    ORDER BY id
    LIMIT 20;
""")

users = cursor.fetchall()
print(f"\n找到 {len(users)} 個用戶:\n")
for user in users:
    print(f"ID: {user[0]:<5} 用戶名: {user[1]:<20} Email: {user[2]:<30} 註冊日期: {user[3]}")

# 2. 檢查是否有 Howard
print("\n" + "="*80)
print("搜索 Howard")
print("="*80)

cursor.execute("""
    SELECT id, username, email
    FROM core_user
    WHERE username ILIKE '%howard%' OR email ILIKE '%howard%'
""")

howard_users = cursor.fetchall()
if howard_users:
    print(f"\n找到 {len(howard_users)} 個相關用戶:\n")
    for user in howard_users:
        print(f"ID: {user[0]:<5} 用戶名: {user[1]:<20} Email: {user[2]}")
else:
    print("\n❌ 找不到 Howard 相關的用戶")

# 3. 檢查測評結果表
print("\n" + "="*80)
print("測評結果統計")
print("="*80)

cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT user_id) as unique_users
    FROM individual_test_result;
""")

result = cursor.fetchone()
print(f"\n測評結果總數: {result[0]}")
print(f"有測評的用戶數: {result[1]}")

# 4. 檢查是否有其他測評相關的表
print("\n" + "="*80)
print("檢查所有表")
print("="*80)

cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name;
""")

tables = cursor.fetchall()
print(f"\n資料庫中的表 ({len(tables)} 個):\n")
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
    count = cursor.fetchone()[0]
    print(f"  {table[0]:<40} {count:>6} 筆資料")

cursor.close()
conn.close()
tunnel.stop()

print("\n" + "="*80)
print("檢查完成！")
print("="*80)
