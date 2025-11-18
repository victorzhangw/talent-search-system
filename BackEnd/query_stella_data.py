#!/usr/bin/env python3
"""
查詢 Stella 的實際測驗資料，驗證資料庫結構推論
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import paramiko
import json

import os

DB_CONFIG = {
    'ssh_host': '54.199.255.239',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': os.path.join('BackEnd', 'private-key-openssh.pem'),
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

print("\n" + "=" * 100)
print("查詢 Stella (stella24168@gmail.com) 的測驗資料")
print("=" * 100)

# 1. 查詢使用者基本資料
print("\n【步驟 1】查詢使用者基本資料")
cursor.execute("""
    SELECT id, email, first_name, last_name, user_type, created_at
    FROM core_user
    WHERE email ILIKE '%stella24168%'
    LIMIT 5;
""")

users = cursor.fetchall()
if users:
    print(f"\n找到 {len(users)} 個使用者：")
    for user in users:
        print(f"  User ID: {user[0]}")
        print(f"  Email: {user[1]}")
        print(f"  Name: {user[2]} {user[3]}")
        print(f"  Type: {user[4]}")
        print(f"  Created: {user[5]}")
        user_id = user[0]
else:
    print("  ✗ 未找到使用者")
    cursor.close()
    conn.close()
    tunnel.stop()
    exit()

# 2. 查詢測驗結果
print("\n【步驟 2】查詢測驗結果記錄")
cursor.execute("""
    SELECT id, test_project_id, status, completed_at, created_at
    FROM test_result
    WHERE user_id = %s
    ORDER BY created_at DESC
    LIMIT 10;
""", (user_id,))

test_results = cursor.fetchall()
if test_results:
    print(f"\n找到 {len(test_results)} 筆測驗結果：")
    for tr in test_results:
        print(f"\n  Test Result ID: {tr[0]}")
        print(f"  Test Project ID: {tr[1]}")
        print(f"  Status: {tr[2]}")
        print(f"  Completed: {tr[3]}")
        print(f"  Created: {tr[4]}")
        test_result_id = tr[0]
else:
    print("  ✗ 未找到測驗結果")
    cursor.close()
    conn.close()
    tunnel.stop()
    exit()

# 3. 查詢特質分數
print("\n【步驟 3】查詢特質評分結果")
cursor.execute("""
    SELECT 
        trt.id,
        trt.trait_id,
        t.chinese_name,
        t.system_name,
        trt.score,
        trt.percentile,
        t.description
    FROM test_result_trait trt
    JOIN trait t ON trt.trait_id = t.id
    WHERE trt.test_result_id = %s
    ORDER BY trt.score DESC;
""", (test_result_id,))

trait_scores = cursor.fetchall()
if trait_scores:
    print(f"\n找到 {len(trait_scores)} 個特質分數：\n")
    print(f"{'特質(中文)':<20} | {'分數':<6} | {'百分位':<8} | {'系統名稱':<30}")
    print("-" * 100)
    for ts in trait_scores:
        chinese_name = ts[2] or ''
        system_name = ts[3] or ''
        score = ts[4] if ts[4] is not None else 'N/A'
        percentile = ts[5] if ts[5] is not None else 'N/A'
        print(f"{chinese_name:<20} | {str(score):<6} | {str(percentile):<8} | {system_name:<30}")
else:
    print("  ✗ 未找到特質分數")

# 4. 查詢測驗專案和分類資訊
print("\n【步驟 4】查詢測驗專案和分類資訊")
cursor.execute("""
    SELECT 
        tp.id,
        tp.name,
        tpc.name as category_name,
        tpc.description
    FROM test_project tp
    LEFT JOIN test_project_category tpc ON tp.category_id = tpc.id
    WHERE tp.id = %s;
""", (test_results[0][1],))

project_info = cursor.fetchone()
if project_info:
    print(f"\n  測驗專案 ID: {project_info[0]}")
    print(f"  測驗專案名稱: {project_info[1]}")
    print(f"  分類名稱: {project_info[2]}")
    print(f"  分類描述: {project_info[3]}")

# 5. 查詢完整的關聯資料（模擬報告生成）
print("\n【步驟 5】完整關聯查詢（模擬報告生成）")
cursor.execute("""
    SELECT 
        u.email,
        u.first_name,
        u.last_name,
        tr.completed_at,
        tp.name as project_name,
        tpc.name as category_name,
        t.chinese_name as trait_name,
        t.system_name,
        t.description as trait_description,
        trt.score,
        trt.percentile
    FROM core_user u
    JOIN test_result tr ON u.id = tr.user_id
    JOIN test_project tp ON tr.test_project_id = tp.id
    LEFT JOIN test_project_category tpc ON tp.category_id = tpc.id
    JOIN test_result_trait trt ON tr.id = trt.test_result_id
    JOIN trait t ON trt.trait_id = t.id
    WHERE u.id = %s AND tr.id = %s
    ORDER BY trt.score DESC
    LIMIT 20;
""", (user_id, test_result_id))

full_data = cursor.fetchall()
if full_data:
    print(f"\n完整資料（前20筆）：\n")
    print(f"受測者: {full_data[0][1]} {full_data[0][2]} ({full_data[0][0]})")
    print(f"測驗專案: {full_data[0][4]}")
    print(f"分類: {full_data[0][5]}")
    print(f"完成時間: {full_data[0][3]}")
    print(f"\n特質評分：")
    print(f"{'特質':<20} | {'分數':<6} | {'百分位':<8} | {'描述':<50}")
    print("-" * 100)
    for row in full_data:
        trait_name = row[6] or ''
        score = row[9] if row[9] is not None else 'N/A'
        percentile = row[10] if row[10] is not None else 'N/A'
        description = (row[8] or '')[:50]
        print(f"{trait_name:<20} | {str(score):<6} | {str(percentile):<8} | {description:<50}")

# 6. 檢查資料表結構
print("\n【步驟 6】驗證資料表結構")
tables_to_check = [
    'core_user',
    'test_result',
    'test_result_trait',
    'trait',
    'test_project',
    'test_project_category',
    'test_project_category_trait'
]

for table in tables_to_check:
    cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        ORDER BY ordinal_position;
    """)
    columns = cursor.fetchall()
    if columns:
        print(f"\n  ✓ {table} ({len(columns)} 欄位)")
        for col in columns[:5]:  # 只顯示前5個欄位
            print(f"    - {col[0]}: {col[1]}")
        if len(columns) > 5:
            print(f"    ... 還有 {len(columns) - 5} 個欄位")

cursor.close()
conn.close()
tunnel.stop()

print("\n" + "=" * 100)
print("查詢完成！")
print("=" * 100)
