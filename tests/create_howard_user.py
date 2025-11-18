#!/usr/bin/env python3
"""
創建 Howard 用戶並導入測評資料
基於 Traitty 評鑑結果_Howard.pdf 的資料
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
import json
from datetime import datetime

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

# Howard 的測評資料（從 PDF 提取）
HOWARD_TRAIT_RESULTS = {
    "協調溝通": {
        "score": 85,
        "percentile": 75,
        "description": "能有效理解他人需求並清晰表達想法，善於協調不同意見"
    },
    "分析性思考": {
        "score": 78,
        "percentile": 68,
        "description": "能運用邏輯思維分析問題，找出關鍵因素"
    },
    "創造性思考": {
        "score": 92,
        "percentile": 88,
        "description": "具備優秀的創新思維能力，能提出獨特見解"
    },
    "領導能力": {
        "score": 80,
        "percentile": 72,
        "description": "具備良好的領導潛力，能激勵團隊成員"
    },
    "問題解決": {
        "score": 88,
        "percentile": 82,
        "description": "面對複雜問題時能系統性地分析並提出解決方案"
    },
    "團隊合作": {
        "score": 83,
        "percentile": 76,
        "description": "善於與他人合作，能在團隊中發揮積極作用"
    },
    "適應能力": {
        "score": 76,
        "percentile": 65,
        "description": "能適應環境變化，保持彈性思維"
    },
    "學習能力": {
        "score": 90,
        "percentile": 85,
        "description": "具備快速學習新知識和技能的能力"
    }
}

def main():
    print("=" * 80)
    print("創建 Howard 用戶並導入測評資料")
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
    conn.autocommit = False  # 使用事務
    print("✅ 資料庫連接成功\n")
    
    cursor = conn.cursor()
    
    try:
        # 1. 檢查 Howard 是否已存在
        print("步驟 1: 檢查 Howard 用戶是否已存在...")
        cursor.execute("""
            SELECT id, username FROM core_user WHERE username = 'Howard';
        """)
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"⚠️ Howard 用戶已存在 (ID: {existing_user[0]})")
            user_id = existing_user[0]
        else:
            # 2. 創建 Howard 用戶
            print("步驟 2: 創建 Howard 用戶...")
            cursor.execute("""
                INSERT INTO core_user (
                    username, 
                    email, 
                    first_name, 
                    last_name, 
                    password, 
                    is_active,
                    is_staff,
                    is_superuser,
                    user_type,
                    is_email_verified,
                    email_verification_token,
                    password_reset_token,
                    date_joined,
                    created_at,
                    updated_at
                )
                VALUES (
                    'Howard',
                    'tank_howard@hotmail.com',
                    'Howard',
                    'Tank',
                    'pbkdf2_sha256$600000$dummy$hash',
                    true,
                    false,
                    false,
                    'individual',
                    true,
                    gen_random_uuid(),
                    gen_random_uuid(),
                    NOW(),
                    NOW(),
                    NOW()
                )
                RETURNING id;
            """)
            user_id = cursor.fetchone()[0]
            print(f"✅ Howard 用戶已創建 (ID: {user_id})")
        
        # 3. 檢查個人檔案是否存在
        print("\n步驟 3: 檢查個人檔案...")
        cursor.execute("""
            SELECT id FROM individual_profile WHERE user_id = %s;
        """, (user_id,))
        existing_profile = cursor.fetchone()
        
        if existing_profile:
            print(f"⚠️ 個人檔案已存在 (ID: {existing_profile[0]})")
        else:
            # 創建個人檔案
            cursor.execute("""
                INSERT INTO individual_profile (user_id, real_name, birth_date)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (user_id, 'Howard Tank', '1990-01-01'))
            profile_id = cursor.fetchone()[0]
            print(f"✅ 個人檔案已創建 (ID: {profile_id})")
        
        # 4. 檢查測評結果是否存在
        print("\n步驟 4: 檢查測評結果...")
        cursor.execute("""
            SELECT id FROM individual_test_result WHERE user_id = %s;
        """, (user_id,))
        existing_test = cursor.fetchone()
        
        if existing_test:
            print(f"⚠️ 測評結果已存在 (ID: {existing_test[0]})")
            print("是否要更新測評結果？(y/n): ", end='')
            response = input().strip().lower()
            
            if response == 'y':
                cursor.execute("""
                    UPDATE individual_test_result
                    SET trait_results = %s,
                        test_completion_date = NOW(),
                        score_value = %s,
                        updated_at = NOW()
                    WHERE user_id = %s;
                """, (
                    json.dumps(HOWARD_TRAIT_RESULTS, ensure_ascii=False),
                    85.0,
                    user_id
                ))
                print("✅ 測評結果已更新")
            else:
                print("⏭️ 跳過更新測評結果")
        else:
            # 創建測評結果
            print("步驟 5: 創建測評結果...")
            cursor.execute("""
                INSERT INTO individual_test_result (
                    user_id,
                    test_project_id,
                    individual_test_record_id,
                    test_completion_date,
                    trait_results,
                    category_results,
                    raw_data,
                    processed_data,
                    score_value,
                    prediction_value,
                    external_test_id,
                    test_url,
                    result_status,
                    crawl_attempts,
                    crawl_error_message,
                    report_generated,
                    report_path,
                    allow_sharing,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s,
                    1,
                    1,
                    NOW(),
                    %s,
                    '{}',
                    '{}',
                    '{}',
                    %s,
                    'high_performer',
                    'HOWARD_TEST_001',
                    'https://test.traitty.com/howard',
                    'completed',
                    1,
                    '',
                    true,
                    '/reports/howard.pdf',
                    true,
                    'Howard 測評結果',
                    NOW(),
                    NOW()
                )
                RETURNING id;
            """, (
                user_id,
                json.dumps(HOWARD_TRAIT_RESULTS, ensure_ascii=False),
                85.0
            ))
            test_id = cursor.fetchone()[0]
            print(f"✅ 測評結果已創建 (ID: {test_id})")
        
        # 提交事務
        conn.commit()
        print("\n" + "=" * 80)
        print("✅ 所有資料已成功創建/更新！")
        print("=" * 80)
        
        # 驗證資料
        print("\n驗證資料...")
        cursor.execute("""
            SELECT 
                cu.id,
                cu.username,
                cu.email,
                itr.trait_results,
                itr.score_value
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username = 'Howard';
        """)
        result = cursor.fetchone()
        
        if result:
            print(f"\n用戶 ID: {result[0]}")
            print(f"用戶名: {result[1]}")
            print(f"Email: {result[2]}")
            print(f"總體分數: {result[4]}")
            print(f"\n特質分數:")
            
            if result[3]:
                trait_results = result[3]
                for trait_name, trait_data in trait_results.items():
                    score = trait_data.get('score', 0)
                    print(f"  • {trait_name}: {score} 分")
            else:
                print("  ⚠️ 沒有測評結果")
        
        print("\n" + "=" * 80)
        print("現在可以搜索 Howard 了！")
        print("=" * 80)
        print("\n測試查詢:")
        print('  curl -X POST http://localhost:8000/api/search \\')
        print('       -H "Content-Type: application/json" \\')
        print('       -d \'{"query": "找到 Howard"}\'')
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        cursor.close()
        conn.close()
        tunnel.stop()
        print("\n資料庫連接已關閉")

if __name__ == '__main__':
    main()
