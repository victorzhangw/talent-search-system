#!/usr/bin/env python3
"""
檢查 core_user 表的實際結構
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder

DB_CONFIG = {
    'ssh_host': '61.216.152.8',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': 'private-key-openssh.pem',
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

# 查詢 core_user 表結構
cursor.execute("""
    SELECT 
        column_name, 
        data_type, 
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = 'core_user'
    ORDER BY ordinal_position;
""")

print("core_user 表結構:")
print("=" * 100)
print(f"{'欄位名稱':<30} {'資料類型':<20} {'可為NULL':<10} {'預設值':<30}")
print("=" * 100)

for row in cursor.fetchall():
    column_name = row[0]
    data_type = row[1]
    is_nullable = row[2]
    column_default = row[3] if row[3] else ''
    print(f"{column_name:<30} {data_type:<20} {is_nullable:<10} {column_default:<30}")

# 查詢 individual_profile 表結構
cursor.execute("""
    SELECT 
        column_name, 
        data_type, 
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = 'individual_profile'
    ORDER BY ordinal_position;
""")

print("\n\nindividual_profile 表結構:")
print("=" * 100)
print(f"{'欄位名稱':<30} {'資料類型':<20} {'可為NULL':<10} {'預設值':<30}")
print("=" * 100)

for row in cursor.fetchall():
    column_name = row[0]
    data_type = row[1]
    is_nullable = row[2]
    column_default = row[3] if row[3] else ''
    print(f"{column_name:<30} {data_type:<20} {is_nullable:<10} {column_default:<30}")

# 查詢 individual_test_result 表結構
cursor.execute("""
    SELECT 
        column_name, 
        data_type, 
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = 'individual_test_result'
    ORDER BY ordinal_position;
""")

print("\n\nindividual_test_result 表結構:")
print("=" * 100)
print(f"{'欄位名稱':<30} {'資料類型':<20} {'可為NULL':<10} {'預設值':<30}")
print("=" * 100)

for row in cursor.fetchall():
    column_name = row[0]
    data_type = row[1]
    is_nullable = row[2]
    column_default = row[3] if row[3] else ''
    print(f"{column_name:<30} {data_type:<20} {is_nullable:<10} {column_default:<30}")


cursor.close()
conn.close()
tunnel.stop()
