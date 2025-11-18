#!/usr/bin/env python3
"""
資料庫診斷腳本
檢查資料庫中的候選人和測評數據
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import json

# 資料庫連接配置
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

def diagnose_database():
    """診斷資料庫狀態"""
    
    print("=" * 60)
    print("資料庫診斷工具")
    print("=" * 60)
    print()
    
    # 建立 SSH 隧道
    print("[1/5] 建立 SSH 隧道...")
    tunnel = SSHTunnelForwarder(
        (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
        ssh_username=DB_CONFIG['ssh_username'],
        ssh_pkey=DB_CONFIG['ssh_private_key'],
        remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
    )
    tunnel.start()
    print(f"✓ SSH 隧道已建立 (本地端口: {tunnel.local_bind_port})")
    print()
    
    # 連接資料庫
    print("[2/5] 連接資料庫...")
    conn = psycopg2.connect(
        host='localhost',
        port=tunnel.local_bind_port,
        database=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_password']
    )
    print("✓ 資料庫連接成功")
    print()
    
    cursor = conn.cursor()
    
    # 檢查候選人總數
    print("[3/5] 檢查候選人數據...")
    cursor.execute("""
        SELECT COUNT(*) FROM core_user WHERE username IS NOT NULL;
    """)
    total_users = cursor.fetchone()[0]
    print(f"✓ 總候選人數: {total_users}")
    
    # 檢查測評結果
    cursor.execute("""
        SELECT COUNT(*) FROM individual_test_result;
    """)
    total_tests = cursor.fetchone()[0]
    print(f"✓ 總測評記錄數: {total_tests}")
    
    # 檢查有 trait_results 的記錄
    cursor.execute("""
        SELECT COUNT(*) 
        FROM individual_test_result 
        WHERE trait_results IS NOT NULL 
          AND trait_results != '{}'::jsonb;
    """)
    tests_with_traits = cursor.fetchone()[0]
    print(f"✓ 有特質數據的測評: {tests_with_traits}")
    print()
    
    # 檢查候選人與測評的關聯
    print("[4/5] 檢查候選人與測評關聯...")
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT cu.id) as users_with_tests
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE cu.username IS NOT NULL
          AND itr.trait_results IS NOT NULL
          AND itr.trait_results != '{}'::jsonb;
    """)
    users_with_tests = cursor.fetchone()[0]
    print(f"✓ 有測評數據的候選人: {users_with_tests}")
    print()
    
    # 顯示前 10 個候選人的詳細信息
    print("[5/5] 顯示前 10 個候選人的詳細信息...")
    print("-" * 60)
    
    cursor.execute("""
        SELECT DISTINCT ON (cu.id)
            cu.id,
            cu.username as name,
            cu.email,
            itr.trait_results,
            itr.test_completion_date
        FROM core_user cu
        LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE cu.username IS NOT NULL
        ORDER BY cu.id, itr.test_completion_date DESC NULLS LAST
        LIMIT 10;
    """)
    
    results = cursor.fetchall()
    
    for i, row in enumerate(results, 1):
        user_id, name, email, trait_results, test_date = row
        
        print(f"\n候選人 #{i}:")
        print(f"  ID: {user_id}")
        print(f"  姓名: {name}")
        print(f"  Email: {email or '(無)'}")
        print(f"  測評日期: {test_date or '(無)'}")
        
        if trait_results:
            trait_count = len(trait_results)
            print(f"  特質數量: {trait_count}")
            
            # 顯示前 3 個特質
            traits_list = list(trait_results.items())[:3]
            for trait_name, trait_data in traits_list:
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 'N/A')
                    chinese_name = trait_data.get('chinese_name', trait_name)
                    print(f"    • {chinese_name}: {score}")
                else:
                    print(f"    • {trait_name}: {trait_data}")
            
            if trait_count > 3:
                print(f"    ... 還有 {trait_count - 3} 個特質")
        else:
            print(f"  特質數量: 0 (尚未完成測評)")
    
    print()
    print("-" * 60)
    
    # 統計特質分布
    print("\n[額外] 特質分布統計...")
    cursor.execute("""
        SELECT 
            key as trait_name,
            COUNT(*) as count,
            AVG((value->>'score')::float) as avg_score
        FROM individual_test_result,
             jsonb_each(trait_results)
        WHERE trait_results IS NOT NULL
          AND trait_results != '{}'::jsonb
        GROUP BY key
        ORDER BY count DESC
        LIMIT 10;
    """)
    
    trait_stats = cursor.fetchall()
    
    if trait_stats:
        print("\n最常見的特質:")
        for trait_name, count, avg_score in trait_stats:
            print(f"  • {trait_name}: {count} 次測評, 平均分數 {avg_score:.1f}")
    else:
        print("  (無特質數據)")
    
    print()
    print("=" * 60)
    print("診斷完成！")
    print("=" * 60)
    
    # 清理
    cursor.close()
    conn.close()
    tunnel.stop()

if __name__ == '__main__':
    try:
        diagnose_database()
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
