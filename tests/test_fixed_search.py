#!/usr/bin/env python3
"""
測試修正後的搜索功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'BackEnd'))

import psycopg2
from sshtunnel import SSHTunnelForwarder
import paramiko
from talent_search_engine_fixed import TalentSearchEngineFixed

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

def test_database_connection():
    """測試數據庫連接"""
    print("=" * 80)
    print("測試 1: 數據庫連接")
    print("=" * 80)
    
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
    
    print("✅ 數據庫連接成功")
    
    return conn, tunnel

def test_table_structure(conn):
    """測試表結構"""
    print("\n" + "=" * 80)
    print("測試 2: 驗證表結構")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # 檢查 core_user 表
    cursor.execute("""
        SELECT COUNT(*) FROM core_user;
    """)
    user_count = cursor.fetchone()[0]
    print(f"✅ core_user 表存在，共 {user_count} 筆記錄")
    
    # 檢查 individual_test_result 表
    cursor.execute("""
        SELECT COUNT(*) FROM individual_test_result;
    """)
    result_count = cursor.fetchone()[0]
    print(f"✅ individual_test_result 表存在，共 {result_count} 筆記錄")
    
    # 檢查有測評結果的用戶數
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) 
        FROM individual_test_result 
        WHERE trait_results IS NOT NULL;
    """)
    users_with_results = cursor.fetchone()[0]
    print(f"✅ 有測評結果的用戶: {users_with_results} 位")
    
    cursor.close()

def test_get_all_candidates(conn):
    """測試獲取所有候選人"""
    print("\n" + "=" * 80)
    print("測試 3: 獲取所有候選人")
    print("=" * 80)
    
    engine = TalentSearchEngineFixed(conn)
    candidates = engine.get_all_candidates(limit=10)
    
    print(f"✅ 找到 {len(candidates)} 位候選人")
    
    for i, candidate in enumerate(candidates[:3], 1):
        print(f"\n候選人 {i}:")
        print(f"  姓名: {candidate['name']}")
        print(f"  Email: {candidate['email']}")
        print(f"  電話: {candidate['phone']}")
        print(f"  測評項目數: {len(candidate['trait_results'])}")
        
        if candidate['trait_results']:
            print(f"  特質範例:")
            for trait_name, trait_data in list(candidate['trait_results'].items())[:3]:
                if isinstance(trait_data, dict):
                    score = trait_data.get('score', 0)
                    chinese_name = trait_data.get('chinese_name', trait_name)
                    print(f"    - {chinese_name}: {score} 分")

def test_find_candidate_by_name(conn):
    """測試按姓名查找候選人"""
    print("\n" + "=" * 80)
    print("測試 4: 按姓名查找候選人")
    print("=" * 80)
    
    engine = TalentSearchEngineFixed(conn)
    
    # 先獲取一個候選人的姓名
    candidates = engine.get_all_candidates(limit=1)
    if candidates:
        test_name = candidates[0]['name']
        print(f"搜索候選人: {test_name}")
        
        candidate = engine.find_candidate_by_name(test_name)
        
        if candidate:
            print(f"✅ 找到候選人")
            print(f"  姓名: {candidate['name']}")
            print(f"  Email: {candidate['email']}")
            print(f"  測評項目數: {len(candidate['trait_results'])}")
        else:
            print(f"❌ 找不到候選人: {test_name}")
    else:
        print("⚠️ 數據庫中沒有候選人")

def test_search_by_trait(conn):
    """測試按特質搜索"""
    print("\n" + "=" * 80)
    print("測試 5: 按特質搜索")
    print("=" * 80)
    
    engine = TalentSearchEngineFixed(conn)
    
    # 模擬 LLM 解析後的查詢
    parsed_query = {
        'matched_traits': [
            {
                'chinese_name': '溝通能力',
                'system_name': 'communication',
                'min_score': 70,
                'weight': 1.0
            }
        ],
        'sql_conditions': [
            "((trait_results->>'communication')::jsonb->>'score')::float >= 70"
        ],
        'summary': '搜索溝通能力強的候選人'
    }
    
    candidates = engine.search_candidates(parsed_query)
    
    print(f"✅ 找到 {len(candidates)} 位符合條件的候選人")
    
    for i, candidate in enumerate(candidates[:3], 1):
        score = engine.calculate_match_score(candidate, parsed_query)
        print(f"\n候選人 {i}:")
        print(f"  姓名: {candidate['name']}")
        print(f"  匹配度: {score:.2%}")
        
        # 顯示溝通能力分數
        trait_results = candidate['trait_results']
        if 'communication' in trait_results:
            comm_data = trait_results['communication']
            if isinstance(comm_data, dict):
                print(f"  溝通能力: {comm_data.get('score', 0)} 分")

def test_match_score_calculation(conn):
    """測試匹配分數計算"""
    print("\n" + "=" * 80)
    print("測試 6: 匹配分數計算")
    print("=" * 80)
    
    engine = TalentSearchEngineFixed(conn)
    candidates = engine.get_all_candidates(limit=5)
    
    if not candidates:
        print("⚠️ 沒有候選人可供測試")
        return
    
    # 測試查詢
    parsed_query = {
        'matched_traits': [
            {
                'chinese_name': '溝通能力',
                'system_name': 'communication',
                'min_score': 70,
                'weight': 1.0
            },
            {
                'chinese_name': '領導力',
                'system_name': 'leadership',
                'min_score': 60,
                'weight': 0.8
            }
        ]
    }
    
    print("測試查詢: 溝通能力 >= 70, 領導力 >= 60")
    print("\n匹配結果:")
    
    for candidate in candidates:
        score = engine.calculate_match_score(candidate, parsed_query)
        print(f"\n{candidate['name']}: {score:.2%}")
        
        trait_results = candidate['trait_results']
        if trait_results:
            # 顯示相關特質分數
            for trait in parsed_query['matched_traits']:
                trait_name = trait['system_name']
                if trait_name in trait_results:
                    trait_data = trait_results[trait_name]
                    if isinstance(trait_data, dict):
                        actual_score = trait_data.get('score', 0)
                        chinese_name = trait_data.get('chinese_name', trait_name)
                        print(f"  {chinese_name}: {actual_score} 分")

def main():
    """主測試函數"""
    print("\n" + "=" * 80)
    print("修正後的搜索功能測試")
    print("=" * 80 + "\n")
    
    try:
        # 建立連接
        conn, tunnel = test_database_connection()
        
        # 執行測試
        test_table_structure(conn)
        test_get_all_candidates(conn)
        test_find_candidate_by_name(conn)
        test_search_by_trait(conn)
        test_match_score_calculation(conn)
        
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
