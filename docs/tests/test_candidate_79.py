"""
測試腳本：檢查候選人 ID 79 是否存在
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# 載入環境變數
load_dotenv('.env.local')

def test_candidate_79():
    """測試候選人 79 是否存在"""
    
    # 獲取資料庫連接資訊
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'traitty_db'),
        'user': os.getenv('DB_USER', 'projectuser'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    print("=" * 60)
    print("測試候選人 ID 79")
    print("=" * 60)
    print(f"資料庫: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print()
    
    try:
        # 連接資料庫
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 查詢候選人 79
        print("1. 查詢候選人基本資訊...")
        query = """
            SELECT 
                ti.id,
                ti.name,
                ti.email,
                ti.phone,
                ti.company,
                ti.status,
                ti.position,
                ti.enterprise_id,
                ti.invited_count,
                ti.completed_count,
                ti.last_test_date,
                ti.created_at
            FROM test_invitee ti
            WHERE ti.id = 79
        """
        
        cursor.execute(query)
        candidate = cursor.fetchone()
        
        if candidate:
            print("✅ 找到候選人:")
            print(f"   ID: {candidate['id']}")
            print(f"   姓名: {candidate['name']}")
            print(f"   郵箱: {candidate['email']}")
            print(f"   企業 ID: {candidate['enterprise_id']}")
            print(f"   職位: {candidate['position']}")
            print(f"   狀態: {candidate['status']}")
            print(f"   已完成測驗: {candidate['completed_count']}")
            print()
            
            # 查詢測驗數據
            print("2. 查詢測驗數據...")
            test_query = """
                SELECT 
                    tpr.id as result_id,
                    tp.name as project_name,
                    tpr.crawl_status,
                    tpr.score_value,
                    tpr.crawled_at,
                    jsonb_array_length(tpr.trait_results->'traits') as trait_count
                FROM test_project_result tpr
                JOIN test_invitation tinv ON tpr.test_invitation_id = tinv.id
                JOIN test_project tp ON tpr.test_project_id = tp.id
                WHERE tinv.invitee_id = 79
                ORDER BY tpr.crawled_at DESC
            """
            
            cursor.execute(test_query)
            tests = cursor.fetchall()
            
            if tests:
                print(f"✅ 找到 {len(tests)} 筆測驗記錄:")
                for i, test in enumerate(tests, 1):
                    print(f"   [{i}] {test['project_name']}")
                    print(f"       狀態: {test['crawl_status']}")
                    print(f"       分數: {test['score_value']}")
                    print(f"       特質數: {test['trait_count']}")
                    print(f"       日期: {test['crawled_at']}")
                    print()
            else:
                print("❌ 沒有找到測驗記錄")
                print()
            
            # 測試 HR 諮詢查詢（不帶 enterprise_id）
            print("3. 測試 HR 諮詢查詢（不帶 enterprise_id）...")
            hr_query = """
                SELECT 
                    ti.id,
                    ti.name,
                    ti.email,
                    ti.enterprise_id,
                    COUNT(DISTINCT CASE 
                        WHEN tpr.crawl_status = 'completed' 
                        THEN tpr.id 
                    END) as completed_tests
                FROM test_invitee ti
                LEFT JOIN test_invitation tinv ON ti.id = tinv.invitee_id
                LEFT JOIN test_project_result tpr ON tinv.id = tpr.test_invitation_id
                WHERE ti.id = %s
                GROUP BY ti.id
            """
            
            cursor.execute(hr_query, (79,))
            hr_result = cursor.fetchone()
            
            if hr_result:
                print("✅ HR 諮詢查詢成功:")
                print(f"   候選人: {hr_result['name']}")
                print(f"   企業 ID: {hr_result['enterprise_id']}")
                print(f"   已完成測驗: {hr_result['completed_tests']}")
                print()
            else:
                print("❌ HR 諮詢查詢失敗")
                print()
            
        else:
            print("❌ 找不到候選人 ID 79")
            print()
            
            # 查詢所有候選人
            print("查詢所有候選人...")
            cursor.execute("SELECT id, name, enterprise_id FROM test_invitee ORDER BY id LIMIT 10")
            all_candidates = cursor.fetchall()
            
            if all_candidates:
                print(f"前 10 個候選人:")
                for c in all_candidates:
                    print(f"   ID: {c['id']}, 姓名: {c['name']}, 企業: {c['enterprise_id']}")
            else:
                print("資料庫中沒有任何候選人")
        
        cursor.close()
        conn.close()
        
        print("=" * 60)
        print("測試完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_candidate_79()
