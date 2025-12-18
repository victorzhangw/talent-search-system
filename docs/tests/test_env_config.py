"""
測試環境變數配置是否正確載入
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_general_hr_consultation():
    """測試通用 HR 諮詢（不需要候選人資訊）"""
    
    print("=" * 60)
    print("測試通用 HR 諮詢（驗證環境變數配置）")
    print("=" * 60)
    
    payload = {
        "query": "如何提升團隊協作效率？"
    }
    
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/hr-consult/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"模式: {result.get('mode')}")
            print(f"諮詢結果: {result.get('consultation', '')}")
            print()
            print("✅ 環境變數配置正確，LLM API 正常工作")
        else:
            print(f"❌ 失敗")
            print(f"錯誤: {response.text}")
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    print()
    print("=" * 60)

def test_candidate_specific_consultation():
    """測試候選人特定諮詢"""
    
    print("=" * 60)
    print("測試候選人特定諮詢（驗證環境變數配置）")
    print("=" * 60)
    
    payload = {
        "query": "林孟德的優勢是什麼？",
        "candidate_id": 79,
        "candidate_name": "林孟德",
        "session_id": "test_env_config"
    }
    
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/hr-consult/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"候選人: {result.get('candidate', {}).get('name')}")
            print(f"諮詢結果: {result.get('consultation', '')[:150]}...")
            print()
            print("✅ 環境變數配置正確，候選人諮詢正常工作")
        else:
            print(f"❌ 失敗")
            print(f"錯誤: {response.text}")
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    print("\n🔍 測試環境變數配置\n")
    
    # 測試 1: 通用 HR 諮詢
    test_general_hr_consultation()
    
    print("\n")
    
    # 測試 2: 候選人特定諮詢
    test_candidate_specific_consultation()
    
    print("\n✅ 所有測試完成！")
