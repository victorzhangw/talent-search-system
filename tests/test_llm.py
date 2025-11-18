#!/usr/bin/env python3
"""
測試 LLM 整合
"""

import asyncio
import httpx
import json

# LLM 配置
LLM_CONFIG = {
    'api_key': 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff',
    'api_host': 'https://api.siliconflow.cn',
    'model': 'deepseek-ai/DeepSeek-V3',
    'endpoint': 'https://api.siliconflow.cn/v1/chat/completions'
}

async def test_llm():
    """測試 LLM API 連接"""
    print("=" * 60)
    print("測試 LLM API 連接")
    print("=" * 60)
    
    test_query = "我需要一個善於溝通的銷售人員"
    
    print(f"\n測試查詢: {test_query}")
    print("\n正在調用 LLM API...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LLM_CONFIG['endpoint'],
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {LLM_CONFIG["api_key"]}'
                },
                json={
                    'model': LLM_CONFIG['model'],
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是一個人才搜索助手。請分析用戶的人才需求並以 JSON 格式回應。'
                        },
                        {
                            'role': 'user',
                            'content': f'請分析以下人才需求：{test_query}'
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500,
                    'response_format': {'type': 'json_object'}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                print("\n✅ LLM API 連接成功！")
                print("\n回應內容:")
                print("-" * 60)
                
                try:
                    parsed = json.loads(content)
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                except:
                    print(content)
                
                print("-" * 60)
                print("\n✅ 測試完成！LLM 整合正常運作。")
            else:
                print(f"\n❌ API 請求失敗: {response.status_code}")
                print(f"錯誤訊息: {response.text}")
    
    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        print("\n請檢查:")
        print("1. 網路連接是否正常")
        print("2. API Key 是否正確")
        print("3. API 服務是否可用")

if __name__ == '__main__':
    asyncio.run(test_llm())
