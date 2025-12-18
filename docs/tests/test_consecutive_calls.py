"""
測試連續兩次 HR 諮詢 API 調用
模擬前端的實際使用場景
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_consecutive_calls():
    """測試連續兩次 API 調用"""
    
    session_id = "hr_session_test_consecutive"
    
    # 第一次調用
    print("=" * 60)
    print("第一次 API 調用")
    print("=" * 60)
    
    payload1 = {
        "query": "林孟德適合團隊合作嗎？",
        "candidate_id": 79,
        "candidate_name": "林孟德",
        "session_id": session_id
    }
    
    print(f"Payload: {json.dumps(payload1, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        response1 = requests.post(
            f"{API_BASE_URL}/api/hr-consult/chat",
            json=payload1,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response1.status_code}")
        
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ 成功")
            print(f"候選人: {result1.get('candidate', {}).get('name')}")
            print(f"諮詢結果: {result1.get('consultation', '')[:100]}...")
        else:
            print(f"❌ 失敗")
            print(f"錯誤: {response1.text}")
            return
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return
    
    print()
    print("等待 2 秒...")
    time.sleep(2)
    print()
    
    # 第二次調用
    print("=" * 60)
    print("第二次 API 調用")
    print("=" * 60)
    
    payload2 = {
        "query": "林孟德如何提升領導能力？",
        "candidate_id": 79,
        "candidate_name": "林孟德",
        "session_id": session_id
    }
    
    print(f"Payload: {json.dumps(payload2, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        response2 = requests.post(
            f"{API_BASE_URL}/api/hr-consult/chat",
            json=payload2,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {response2.status_code}")
        
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ 成功")
            print(f"候選人: {result2.get('candidate', {}).get('name')}")
            print(f"諮詢結果: {result2.get('consultation', '')[:100]}...")
        else:
            print(f"❌ 失敗")
            print(f"錯誤: {response2.text}")
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    print()
    print("=" * 60)
    print("測試完成")
    print("=" * 60)

if __name__ == "__main__":
    test_consecutive_calls()
