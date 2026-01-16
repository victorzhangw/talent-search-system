"""
測試批次報告 API 的簡單腳本
"""
import requests
import json

# 配置
API_URL = "http://localhost:5000/api/v2/reports/batch"
TOKEN = "YOUR_TOKEN_HERE"  # 請從前端 Console 複製實際的 token

# 測試 payload
payload = {
    "assessment_ids": [62, 63, 64, 61]
}

print("=" * 60)
print("測試批次報告 API")
print("=" * 60)
print(f"API URL: {API_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("=" * 60)

try:
    # 發送請求
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}"
        },
        json=payload
    )
    
    print(f"\n回應狀態碼: {response.status_code}")
    print(f"回應 Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ 成功！")
        print(f"收到 {len(data.get('reports', []))} 個報告")
        print(f"\n完整回應:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"\n❌ 失敗！")
        print(f"錯誤內容: {response.text}")
        
except Exception as e:
    print(f"\n❌ 發生錯誤: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
