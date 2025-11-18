#!/usr/bin/env python3
"""
智能版：創建 Howard 用戶
自動檢測必要欄位並使用預設值
"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
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

HOWARD_TRAIT_RESULTS = {
    "協調溝通": {"score": 85, "percentile": 75, "description": "能有效理解他人需求並清晰表達想法"},
    "分析性思考": {"score": 78, "percentile": 68, "description": "能運用邏輯思維分析問題"},
    "創造性思考": {"score": 92, "percentile": 88, "description": "具備優秀的創新思維能力"},
    "領導能力": {"score": 80, "percentile": 72, "description": "具備良好的領導潛力"},
    "問題解決": {"score": 88, "percentile": 82, "description": "能系統性地分析並提出解決方案"},
    "團隊合作": {"score": 83, "percentile": 76, "description": "善於與他人合作"},
    "適應能力": {"score": 76, "percentile": 65, "description": "能適應環境變化"},
    "學習能力": {"score": 90, "percentile": 85, "description": "具備快速學習能力"}
}

def main():
    print("=" * 80)
    print("創建 Howard 用戶（智能版）")
    print("=" * 80)
    
    tunnel = SSHTunnelForwarder(
        (DB_CONFIG['ssh_host'], DB_CONFIG['ssh_port']),
        ssh_username=DB_CONFIG['ssh_username'],
        ssh_pkey=DB_CONFIG['ssh_private_key'],
        remote_bind_address=(DB_CONFIG['db_host'], DB_CONFIG['db_port'])
    )
    tunnel.start()
    print(f"✅ SSH 隧道已建立")
    
    conn = psycopg2.connect(
        host='localhost',
        port=tunnel.local_bind_port,
        database=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_password']
    )
    conn.autocommit = False
    print("✅ 資料庫連接成功\n")
    
    cursor = conn.cursor()
    
    try:
        # 檢查 Howard 是否已存在
        cursor.execute("SELECT id FROM core_user WHERE username = 'Howard';")
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️ Howard 用戶已存在 (ID: {existing[0]})")
            user_id = existing[0]
        else:
            # 創建用戶
            print("步驟 1: 創建 Howard 用戶...")
            cursor.execute("""
                INSERT INTO core_user (
                    username, email, first_name, last_name, password,
                    is_active, is_staff, is_superuser, user_type,
                    is_email_verified, email_verification_token, password_reset_token,
                    date_joined, created_at, updated_at
                )
                VALUES (
                    'Howard', 'tank_howard@hotmail.com', 'Howard', 'Tank',
                    'pbkdf2_sha256$600000$dummy$hash',
                    true, false, false, 'individual',
                    true, gen_random_uuid(), gen_random_uuid(),
                    NOW(), NOW(), NOW()
                )
                RETURNING id;
            """)
            user_id = cursor.fetchone()[0]
            print(f"✅ 用戶已創建 (ID: {user_id})")
        
        # 檢查個人檔案
        cursor.execute("SELECT id FROM individual_profile WHERE user_id = %s;", (user_id,))
        existing_profile = cursor.fetchone()
        
        if not existing_profile:
            print("\n步驟 2: 創建個人檔案...")
            cursor.execute("""
                INSERT INTO individual_profile (user_id, real_name, birth_date)
                VALUES (%s, 'Howard Tank', '1990-01-01')
                RETURNING id;
            """, (user_id,))
            profile_id = cursor.fetchone()[0]
            print(f"✅ 個人檔案已創建 (ID: {profile_id})")
        else:
            print(f"\n步驟 2: 個人檔案已存在 (ID: {existing_profile[0]})")
        
        # 檢查測評結果
        cursor.execute("SELECT id FROM individual_test_result WHERE user_id = %s;", (user_id,))
        existing_result = cursor.fetchone()
        
        if existing_result:
            print(f"\n步驟 3: 測評結果已存在 (ID: {existing_result[0]})")
            print("更新測評結果...")
            cursor.execute("""
                UPDATE individual_test_result
                SET trait_results = %s,
                    score_value = %s,
                    test_completion_date = NOW(),
                    updated_at = NOW()
                WHERE user_id = %s;
            """, (
                json.dumps(HOWARD_TRAIT_RESULTS, ensure_ascii=False),
                85.0,
                user_id
            ))
            print("✅ 測評結果已更新")
        else:
            # 獲取必要的 ID
            print("\n步驟 3: 準備創建測評結果...")
            
            # 獲取 test_project_id
            cursor.execute("SELECT id FROM test_project LIMIT 1;")
            project = cursor.fetchone()
            project_id = project[0] if project else 1
            print(f"  使用測評專案 ID: {project_id}")
            
            # 獲取或創建 individual_test_record（使用所有必要欄位）
            cursor.execute("""
                SELECT id FROM individual_test_record 
                WHERE user_id = %s LIMIT 1;
            """, (user_id,))
            record = cursor.fetchone()
            
            if record:
                record_id = record[0]
                print(f"  使用現有測評記錄 ID: {record_id}")
            else:
                print("  創建測評記錄...")
                cursor.execute("""
                    INSERT INTO individual_test_record (
                        user_id, 
                        test_project_id, 
                        purchase_date,
                        access_count,
                        status,
                        points_consumed,
                        notes,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, NOW(), 1, 'completed', 0, 'Howard 測評記錄', NOW(), NOW())
                    RETURNING id;
                """, (user_id, project_id))
                record_id = cursor.fetchone()[0]
                print(f"  ✅ 測評記錄已創建 ID: {record_id}")
            
            # 創建測評結果
            print("\n步驟 4: 創建測評結果...")
            cursor.execute("""
                INSERT INTO individual_test_result (
                    user_id, test_project_id, individual_test_record_id,
                    test_completion_date, trait_results, category_results,
                    raw_data, processed_data, score_value, prediction_value,
                    external_test_id, test_url, result_status,
                    crawl_attempts, crawl_error_message, report_generated,
                    report_path, allow_sharing, notes,
                    created_at, updated_at
                )
                VALUES (
                    %s, %s, %s,
                    NOW(), %s, '{}',
                    '{}', '{}', %s, 'high_performer',
                    'HOWARD_TEST_001', 'https://test.traitty.com/howard', 'completed',
                    1, '', true,
                    '/reports/howard.pdf', true, 'Howard 測評結果',
                    NOW(), NOW()
                )
                RETURNING id;
            """, (
                user_id, project_id, record_id,
                json.dumps(HOWARD_TRAIT_RESULTS, ensure_ascii=False),
                85.0
            ))
            result_id = cursor.fetchone()[0]
            print(f"✅ 測評結果已創建 (ID: {result_id})")
        
        conn.commit()
        print("\n" + "=" * 80)
        print("✅ Howard 用戶創建/更新成功！")
        print("=" * 80)
        
        # 驗證
        cursor.execute("""
            SELECT cu.id, cu.username, cu.email, itr.trait_results, itr.score_value
            FROM core_user cu
            LEFT JOIN individual_test_result itr ON cu.id = itr.user_id
            WHERE cu.username = 'Howard';
        """)
        result = cursor.fetchone()
        
        if result:
            print(f"\n✅ 驗證成功！")
            print(f"   用戶 ID: {result[0]}")
            print(f"   用戶名: {result[1]}")
            print(f"   Email: {result[2]}")
            print(f"   總體分數: {result[4]}")
            print(f"\n   特質分數:")
            
            if result[3]:
                for trait_name, trait_data in result[3].items():
                    score = trait_data.get('score', 0)
                    print(f"     • {trait_name}: {score} 分")
        
        print("\n" + "=" * 80)
        print("🎉 現在可以搜索 Howard 了！")
        print("=" * 80)
        print("\n測試查詢:")
        print('  1. 搜索 Howard: "找到 Howard"')
        print('  2. 按特質搜索: "找一個創造性思考能力強的人"')
        print('  3. 列出所有人: "列出所有候選人"')
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        cursor.close()
        conn.close()
        tunnel.stop()

if __name__ == '__main__':
    main()
