#!/usr/bin/env python3
"""
診斷資料庫狀態 - 找出搜索結果為空的原因
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import paramiko
import json

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

def load_ssh_key(key_path):
    return paramiko.RSAKey.from_private_key_file(key_path)

print("=" * 80)
print("資料庫狀態診斷")
print("=" * 80)

# 建立連接
ssh_key = load_ssh_key(DB_CONFIG['ssh_private_key'])
tunnel = SSHTunnelForwarder(
    (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
    ssh_username=DB_CONFIG['ssh_username'],
    ssh_pkey=ssh_key,
    remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
)

tunnel.start()
print(f"\n✅ SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")

conn = psycopg2.connect(
    host='localhost',
    port=tunnel.local_bind_port,
    database=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_password']
)

print("✅ 資料庫連接成功\n")

cursor = conn.cursor()

# 檢查 1: 用戶數量
print("=" * 80)
print("檢查 1: 用戶數量")
print("=" * 80)

cursor.execute("SELECT COUNT(*) FROM core_user;")
user_count = cursor.fetchone()[0]
print(f"core_user 表: {user_count} 個用戶")

cursor.execute("SELECT COUNT(*) FROM individual_profile;")
profile_count = cursor.fetchone()[0]
print(f"individual_profile 表: {profile_count} 個檔案")

cursor.execute("SELECT COUNT(*) FROM individual_test_result;")
result_count = cursor.fetchone()[0]
print(f"individual_test_result 表: {result_count} 個測評結果")

# 檢查 2: 有測評結果的用戶
print("\n" + "=" * 80)
print("檢查 2: 有測評結果的用戶")
print("=" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT cu.id)
    FROM core_user cu
    JOIN individual_test_result itr ON cu.id = itr.user_id
    WHERE itr.trait_results IS NOT NULL;
""")
users_with_results = cursor.fetchone()[0]
print(f"有測評結果的用戶: {users_with_results} 個")

# 檢查 3: trait_results 的結構
print("\n" + "=" * 80)
print("檢查 3: trait_results JSON 結構")
print("=" * 80)

cursor.execute("""
    SELECT trait_results
    FROM individual_test_result
    WHERE trait_results IS NOT NULL
    LIMIT 1;
""")

result = cursor.fetchone()
if result:
    trait_results = result[0]
    print(f"trait_results 類型: {type(trait_results)}")
    print(f"\n範例 trait_results (前 500 字元):")
    print(json.dumps(trait_results, ensure_ascii=False, indent=2)[:500])
    
    # 檢查鍵
    if isinstance(trait_results, dict):
        keys = list(trait_results.keys())
        print(f"\n包含的特質鍵 (前 10 個):")
        for key in keys[:10]:
            print(f"  - {key}")
            if isinstance(trait_results[key], dict):
                print(f"    值: {trait_results[key]}")
else:
    print("❌ 沒有找到 trait_results 資料")

# 檢查 4: 測試查詢
print("\n" + "=" * 80)
print("檢查 4: 測試基礎查詢")
print("=" * 80)

test_sql = """
    SELECT 
        cu.id,
        cu.username,
        cu.email,
        (SELECT phone FROM individual_profile WHERE user_id = cu.id LIMIT 1) as phone,
        itr.trait_results
    FROM core_user cu
    LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
    WHERE cu.username IS NOT NULL
      AND itr.trait_results IS NOT NULL
    LIMIT 5;
"""

print("執行 SQL:")
print(test_sql)

cursor.execute(test_sql)
results = cursor.fetchall()

print(f"\n找到 {len(results)} 筆結果")

for i, row in enumerate(results, 1):
    print(f"\n{i}. 用戶 ID: {row[0]}")
    print(f"   姓名: {row[1]}")
    print(f"   Email: {row[2]}")
    print(f"   電話: {row[3]}")
    if row[4]:
        trait_keys = list(row[4].keys()) if isinstance(row[4], dict) else []
        print(f"   特質數量: {len(trait_keys)}")

# 檢查 5: 測試特質查詢
print("\n" + "=" * 80)
print("檢查 5: 測試特質查詢")
print("=" * 80)

# 先找出一個存在的特質
cursor.execute("""
    SELECT DISTINCT jsonb_object_keys(trait_results) as trait_name
    FROM individual_test_result
    WHERE trait_results IS NOT NULL
    LIMIT 10;
""")

available_traits = [row[0] for row in cursor.fetchall()]
print(f"資料庫中實際存在的特質 (前 10 個):")
for trait in available_traits:
    print(f"  - {trait}")

if available_traits:
    test_trait = available_traits[0]
    print(f"\n測試查詢特質: {test_trait}")
    
    # 測試不同的查詢方式
    test_queries = [
        f"trait_results ? '{test_trait}'",
        f"trait_results->'{test_trait}' IS NOT NULL",
        f"jsonb_typeof(trait_results->'{test_trait}') = 'object'",
    ]
    
    for test_query in test_queries:
        try:
            sql = f"""
                SELECT COUNT(*)
                FROM individual_test_result
                WHERE {test_query};
            """
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            print(f"  ✅ {test_query}: {count} 筆")
        except Exception as e:
            print(f"  ❌ {test_query}: {str(e)}")

# 檢查 6: 特質分數結構
print("\n" + "=" * 80)
print("檢查 6: 特質分數結構")
print("=" * 80)

if available_traits:
    test_trait = available_traits[0]
    cursor.execute(f"""
        SELECT trait_results->'{test_trait}' as trait_data
        FROM individual_test_result
        WHERE trait_results ? '{test_trait}'
        LIMIT 3;
    """)
    
    print(f"特質 '{test_trait}' 的資料結構:")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"\n範例 {i}:")
        print(json.dumps(row[0], ensure_ascii=False, indent=2))

# 總結
print("\n" + "=" * 80)
print("診斷總結")
print("=" * 80)

print(f"""
資料統計:
- 總用戶數: {user_count}
- 有測評結果的用戶: {users_with_results}
- 測評結果總數: {result_count}

問題分析:
""")

if users_with_results == 0:
    print("❌ 沒有用戶有測評結果！")
    print("   建議: 檢查資料是否正確匯入")
elif result_count == 0:
    print("❌ individual_test_result 表是空的！")
    print("   建議: 需要匯入測評資料")
else:
    print("✅ 資料庫有資料")
    print(f"   可用特質: {len(available_traits)} 個")
    print("   建議: 檢查 SQL 查詢條件是否正確")

cursor.close()
conn.close()
tunnel.stop()

print("\n診斷完成！")
