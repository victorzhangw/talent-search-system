#!/usr/bin/env python3
"""
診斷 Howard 用戶問題
檢查資料庫中是否存在 Howard 相關的資料
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import json

# 資料庫連接配置
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

def main():
    print("=" * 80)
    print("診斷 Howard 用戶問題")
    print("=" * 80)
    
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
    print("=" * 80)
    print("1. 檢查所有用戶")
    print("=" * 80)
    cursor.execute("""
        SELECT id, username, email, date_joined
        FROM core_user
        ORDER BY id;
    """)
    users = cursor.fetchall()
    print(f"找到 {len(users)} 個用戶:\n")
    for user in users:
        print(f"ID: {user[0]:3d}  用戶名: {user[1]:20s}  Email: {user[2]:30s}")
    
    # 2. 模糊搜索 Howard
    print("\n" + "=" * 80)
    print("2. 模糊搜索 'Howard' (不區分大小寫)")
    print("=" * 80)
    cursor.execute("""
        SELECT id, username, email, first_name, last_name
        FROM core_user
        WHERE LOWER(username) LIKE LOWER('%Howard%')
           OR LOWER(email) LIKE LOWER('%Howard%')
           OR LOWER(first_name) LIKE LOWER('%Howard%')
           OR LOWER(last_name) LIKE LOWER('%Howard%');
    """)
    howard_users = cursor.fetchall()
    
    if howard_users:
        print(f"找到 {len(howard_users)} 個相關用戶:\n")
        for user in howard_users:
            print(f"ID: {user[0]}")
            print(f"  用戶名: {user[1]}")
            print(f"  Email: {user[2]}")
            print(f"  名字: {user[3]}")
            print(f"  姓氏: {user[4]}")
            print()
    else:
        print("❌ 找不到任何包含 'Howard' 的用戶")
    
    # 3. 檢查 individual_profile 表
    print("=" * 80)
    print("3. 檢查 individual_profile 表")
    print("=" * 80)
    cursor.execute("""
        SELECT COUNT(*) FROM individual_profile;
    """)
    profile_count = cursor.fetchone()[0]
    print(f"individual_profile 表中有 {profile_count} 筆資料")
    
    if profile_count > 0:
        cursor.execute("""
            SELECT ip.id, ip.user_id, cu.username
            FROM individual_profile ip
            JOIN core_user cu ON ip.user_id = cu.id
            LIMIT 5;
        """)
        profiles = cursor.fetchall()
        print("\n前 5 筆資料:")
        for profile in profiles:
            print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Username: {profile[2]}")
    
    # 4. 檢查 individual_test_result 表
    print("\n" + "=" * 80)
    print("4. 檢查 individual_test_result 表")
    print("=" * 80)
    cursor.execute("""
        SELECT COUNT(*) FROM individual_test_result;
    """)
    test_count = cursor.fetchone()[0]
    print(f"individual_test_result 表中有 {test_count} 筆資料")
    
    if test_count > 0:
        cursor.execute("""
            SELECT itr.id, itr.user_id, cu.username, 
                   jsonb_object_keys(itr.trait_results) as trait_name
            FROM individual_test_result itr
            JOIN core_user cu ON itr.user_id = cu.id
            LIMIT 10;
        """)
        tests = cursor.fetchall()
        print("\n前 10 筆測評資料:")
        for test in tests:
            print(f"  Test ID: {test[0]}, User ID: {test[1]}, Username: {test[2]}, Trait: {test[3]}")
    
    # 5. 檢查是否有測評結果但沒有關聯到用戶
    print("\n" + "=" * 80)
    print("5. 檢查孤立的測評結果")
    print("=" * 80)
    cursor.execute("""
        SELECT itr.id, itr.user_id
        FROM individual_test_result itr
        LEFT JOIN core_user cu ON itr.user_id = cu.id
        WHERE cu.id IS NULL;
    """)
    orphan_tests = cursor.fetchall()
    
    if orphan_tests:
        print(f"⚠️ 找到 {len(orphan_tests)} 筆孤立的測評結果（沒有對應的用戶）:")
        for test in orphan_tests:
            print(f"  Test ID: {test[0]}, User ID: {test[1]}")
    else:
        print("✅ 沒有孤立的測評結果")
    
    # 6. 建議的解決方案
    print("\n" + "=" * 80)
    print("6. 解決方案建議")
    print("=" * 80)
    
    if not howard_users:
        print("""
❌ 資料庫中確實沒有 Howard 用戶

可能的原因：
1. Howard 用戶尚未在系統中註冊
2. 用戶名稱拼寫不同（例如：howard, HOWARD, Howard_Tank）
3. 資料可能在其他資料庫或環境中

建議的解決方案：

方案 1: 創建 Howard 測試用戶
---------------------------------------
INSERT INTO core_user (username, email, first_name, last_name, password)
VALUES ('Howard', 'tank_howard@hotmail.com', 'Howard', 'Tank', 'pbkdf2_sha256$...');

-- 創建個人檔案
INSERT INTO individual_profile (user_id, phone)
VALUES ((SELECT id FROM core_user WHERE username = 'Howard'), '0912-345-678');

-- 創建測評結果（需要從 PDF 或其他來源導入）
INSERT INTO individual_test_result (user_id, trait_results, test_completion_date)
VALUES (
    (SELECT id FROM core_user WHERE username = 'Howard'),
    '{"協調溝通": {"score": 85, "description": "..."}, ...}'::jsonb,
    NOW()
);

方案 2: 檢查其他可能的用戶名
---------------------------------------
可能的用戶名變體：
- howard (小寫)
- HOWARD (大寫)
- Howard_Tank
- tank_howard
- h.tank

方案 3: 從 PDF 導入資料
---------------------------------------
如果有 'Traitty 評鑑結果_Howard.pdf'，可以：
1. 手動提取測評結果
2. 創建用戶和測評記錄
3. 導入到資料庫

方案 4: 使用現有用戶進行測試
---------------------------------------
可以使用現有的用戶進行測試，例如：
- admin
- test0907
- alice, bob, charlie 等
""")
    
    # 7. 提供快速創建腳本
    print("\n" + "=" * 80)
    print("7. 快速創建 Howard 用戶的 SQL")
    print("=" * 80)
    print("""
-- 步驟 1: 創建用戶
INSERT INTO core_user (username, email, first_name, last_name, password, is_active)
VALUES (
    'Howard',
    'tank_howard@hotmail.com',
    'Howard',
    'Tank',
    'pbkdf2_sha256$600000$dummy$hash',  -- 需要替換為真實密碼
    true
)
RETURNING id;

-- 步驟 2: 創建個人檔案（假設 user_id = 19）
INSERT INTO individual_profile (user_id, phone, city, country)
VALUES (
    19,  -- 替換為實際的 user_id
    '0912-345-678',
    '台北市',
    '台灣'
);

-- 步驟 3: 創建測評結果（範例）
INSERT INTO individual_test_result (
    user_id,
    test_type,
    test_completion_date,
    trait_results,
    overall_score,
    is_valid
)
VALUES (
    19,  -- 替換為實際的 user_id
    'traitty',
    NOW(),
    '{
        "協調溝通": {"score": 85, "percentile": 75, "description": "能有效理解他人需求"},
        "分析性思考": {"score": 78, "percentile": 68, "description": "能運用邏輯思維"},
        "創造性思考": {"score": 92, "percentile": 88, "description": "具備優秀的創新思維"}
    }'::jsonb,
    85.0,
    true
);
""")
    
    cursor.close()
    conn.close()
    tunnel.stop()
    
    print("\n" + "=" * 80)
    print("診斷完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()
