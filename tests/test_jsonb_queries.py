#!/usr/bin/env python3
"""
測試 JSONB 查詢功能
展示如何查詢和操作 trait_results JSONB 欄位
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'BackEnd'))

import psycopg2
from sshtunnel import SSHTunnelForwarder
import paramiko
import json

# 資料庫配置
DB_CONFIG = {
    'ssh_host': '61.216.152.8',
    'ssh_port': 22,
    'ssh_username': 'victor_cheng',
    'ssh_private_key': '../BackEnd/private-key-openssh.pem',
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'projectdb',
    'db_user': 'projectuser',
    'db_password': 'projectpass'
}

def load_ssh_key(key_path):
    """載入 SSH 私鑰"""
    return paramiko.RSAKey.from_private_key_file(key_path)

def connect_db():
    """建立數據庫連接"""
    ssh_key = load_ssh_key(DB_CONFIG['ssh_private_key'])
    tunnel = SSHTunnelForwarder(
        (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
        ssh_username=DB_CONFIG['ssh_username'],
        ssh_pkey=ssh_key,
        remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
    )
    
    tunnel.start()
    print(f"✅ SSH 隧道已建立，本地端口: {tunnel.local_bind_port}")
    
    conn = psycopg2.connect(
        host='localhost',
        port=tunnel.local_bind_port,
        database=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_password']
    )
    
    print("✅ 數據庫連接成功\n")
    return conn, tunnel

def test_1_view_jsonb_structure(conn):
    """測試 1: 查看 JSONB 數據結構"""
    print("=" * 80)
    print("測試 1: 查看 trait_results JSONB 數據結構")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # 獲取一筆測評結果
    cursor.execute("""
        SELECT 
            cu.username,
            itr.trait_results
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE itr.trait_results IS NOT NULL
        LIMIT 1;
    """)
    
    row = cursor.fetchone()
    if row:
        username, trait_results = row
        print(f"\n候選人: {username}")
        print(f"\ntrait_results 結構:")
        print(json.dumps(trait_results, indent=2, ensure_ascii=False))
        
        # 分析結構
        print(f"\n特質數量: {len(trait_results)}")
        print(f"特質列表: {', '.join(trait_results.keys())}")
        
        # 顯示第一個特質的詳細結構
        first_trait = list(trait_results.keys())[0]
        print(f"\n第一個特質 ({first_trait}) 的結構:")
        print(json.dumps(trait_results[first_trait], indent=2, ensure_ascii=False))
    else:
        print("⚠️ 沒有找到測評結果")
    
    cursor.close()

def test_2_query_specific_trait(conn):
    """測試 2: 查詢特定特質的分數"""
    print("\n" + "=" * 80)
    print("測試 2: 查詢特定特質的分數")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # 方法 1: 使用 ->> 操作符
    print("\n方法 1: 使用 ->> 操作符查詢")
    cursor.execute("""
        SELECT 
            cu.username,
            (trait_results->>'communication')::jsonb->>'score' as communication_score,
            (trait_results->>'communication')::jsonb->>'chinese_name' as chinese_name
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE trait_results->>'communication' IS NOT NULL
        LIMIT 5;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 筆結果:")
    for username, score, chinese_name in results:
        print(f"  {username}: {chinese_name} = {score} 分")
    
    cursor.close()

def test_3_query_by_score_threshold(conn):
    """測試 3: 查詢分數大於閾值的候選人"""
    print("\n" + "=" * 80)
    print("測試 3: 查詢溝通能力 >= 80 分的候選人")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cu.username,
            ((trait_results->>'communication')::jsonb->>'score')::float as score
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE ((trait_results->>'communication')::jsonb->>'score')::float >= 80
        ORDER BY score DESC
        LIMIT 10;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 位候選人:")
    for username, score in results:
        print(f"  {username}: {score:.1f} 分")
    
    cursor.close()

def test_4_query_by_chinese_name(conn):
    """測試 4: 通過中文名稱查詢特質"""
    print("\n" + "=" * 80)
    print("測試 4: 通過中文名稱查詢特質")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # 查詢「溝通能力」>= 75 分的候選人
    cursor.execute("""
        SELECT 
            cu.username,
            key as trait_key,
            value->>'chinese_name' as chinese_name,
            (value->>'score')::float as score
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id,
             jsonb_each(itr.trait_results)
        WHERE value->>'chinese_name' = '溝通能力'
          AND (value->>'score')::float >= 75
        ORDER BY score DESC
        LIMIT 10;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 位候選人:")
    for username, trait_key, chinese_name, score in results:
        print(f"  {username}: {chinese_name} ({trait_key}) = {score:.1f} 分")
    
    cursor.close()

def test_5_query_multiple_traits(conn):
    """測試 5: 查詢多個特質都符合條件的候選人"""
    print("\n" + "=" * 80)
    print("測試 5: 查詢溝通能力 >= 75 且領導力 >= 70 的候選人")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cu.username,
            ((trait_results->>'communication')::jsonb->>'score')::float as comm_score,
            ((trait_results->>'leadership')::jsonb->>'score')::float as lead_score
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE ((trait_results->>'communication')::jsonb->>'score')::float >= 75
          AND ((trait_results->>'leadership')::jsonb->>'score')::float >= 70
        ORDER BY comm_score DESC, lead_score DESC
        LIMIT 10;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 位候選人:")
    for username, comm_score, lead_score in results:
        print(f"  {username}: 溝通 {comm_score:.1f}, 領導 {lead_score:.1f}")
    
    cursor.close()

def test_6_list_all_traits(conn):
    """測試 6: 列出所有特質及其平均分數"""
    print("\n" + "=" * 80)
    print("測試 6: 列出所有特質及其平均分數")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            key as trait_key,
            MAX(value->>'chinese_name') as chinese_name,
            COUNT(*) as count,
            AVG((value->>'score')::float) as avg_score,
            MIN((value->>'score')::float) as min_score,
            MAX((value->>'score')::float) as max_score
        FROM individual_test_result,
             jsonb_each(trait_results)
        WHERE value->>'score' IS NOT NULL
        GROUP BY key
        ORDER BY avg_score DESC
        LIMIT 20;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 個特質:")
    print(f"\n{'特質名稱':<20} {'中文名稱':<15} {'樣本數':<8} {'平均':<8} {'最小':<8} {'最大':<8}")
    print("-" * 80)
    for trait_key, chinese_name, count, avg_score, min_score, max_score in results:
        print(f"{trait_key:<20} {chinese_name or 'N/A':<15} {count:<8} {avg_score:<8.1f} {min_score:<8.1f} {max_score:<8.1f}")
    
    cursor.close()

def test_7_count_high_score_traits(conn):
    """測試 7: 統計每位候選人的高分特質數量"""
    print("\n" + "=" * 80)
    print("測試 7: 統計每位候選人有多少個特質 >= 80 分")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cu.username,
            COUNT(*) as high_score_count,
            ARRAY_AGG(value->>'chinese_name') as high_score_traits
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id,
             jsonb_each(itr.trait_results)
        WHERE (value->>'score')::float >= 80
        GROUP BY cu.username
        HAVING COUNT(*) >= 3
        ORDER BY high_score_count DESC
        LIMIT 10;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 位候選人（至少 3 個高分特質）:")
    for username, count, traits in results:
        print(f"\n  {username}: {count} 個高分特質")
        print(f"    {', '.join(traits[:5])}")
    
    cursor.close()

def test_8_search_by_trait_pattern(conn):
    """測試 8: 模糊搜索特質名稱"""
    print("\n" + "=" * 80)
    print("測試 8: 搜索包含「溝通」的所有特質")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT
            key as trait_key,
            value->>'chinese_name' as chinese_name
        FROM individual_test_result,
             jsonb_each(trait_results)
        WHERE value->>'chinese_name' LIKE '%溝通%'
           OR key LIKE '%communication%'
        ORDER BY chinese_name;
    """)
    
    results = cursor.fetchall()
    print(f"\n找到 {len(results)} 個相關特質:")
    for trait_key, chinese_name in results:
        print(f"  {trait_key}: {chinese_name}")
    
    cursor.close()

def test_9_export_trait_data(conn):
    """測試 9: 導出特質數據為 JSON"""
    print("\n" + "=" * 80)
    print("測試 9: 導出候選人的特質數據")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cu.username,
            itr.trait_results
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE itr.trait_results IS NOT NULL
        LIMIT 3;
    """)
    
    results = cursor.fetchall()
    print(f"\n導出 {len(results)} 位候選人的數據:")
    
    export_data = []
    for username, trait_results in results:
        export_data.append({
            'username': username,
            'traits': trait_results
        })
    
    # 保存為 JSON 文件
    output_file = 'trait_data_export.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 數據已導出到: {output_file}")
    print(f"\n範例數據:")
    print(json.dumps(export_data[0], indent=2, ensure_ascii=False)[:500] + "...")
    
    cursor.close()

def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("JSONB 查詢功能測試")
    print("=" * 80 + "\n")
    
    try:
        # 建立連接
        conn, tunnel = connect_db()
        
        # 執行測試
        test_1_view_jsonb_structure(conn)
        test_2_query_specific_trait(conn)
        test_3_query_by_score_threshold(conn)
        test_4_query_by_chinese_name(conn)
        test_5_query_multiple_traits(conn)
        test_6_list_all_traits(conn)
        test_7_count_high_score_traits(conn)
        test_8_search_by_trait_pattern(conn)
        test_9_export_trait_data(conn)
        
        # 清理
        conn.close()
        tunnel.stop()
        
        print("\n" + "=" * 80)
        print("✅ 所有測試完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
