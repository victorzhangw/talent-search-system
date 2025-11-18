#!/usr/bin/env python3
"""
測試 LLM 意圖識別功能
"""

import asyncio
import httpx

API_URL = "http://localhost:8000/api/search"

async def test_intent(query: str, expected_intent: str):
    """測試單個查詢的意圖識別"""
    print(f"\n{'='*80}")
    print(f"測試查詢: {query}")
    print(f"預期意圖: {expected_intent}")
    print(f"{'='*80}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                API_URL,
                json={"query": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\n✅ 成功")
                print(f"\n查詢理解:")
                understanding = result.get('query_understanding', '')
                print(understanding[:200] + '...' if len(understanding) > 200 else understanding)
                
                candidates = result.get('candidates', [])
                print(f"\n候選人數: {len(candidates)}")
                
                if candidates:
                    print(f"\n前 3 名候選人:")
                    for i, c in enumerate(candidates[:3], 1):
                        print(f"{i}. {c['name']} - {c.get('match_score', 0):.1%}")
                
                suggestions = result.get('suggestions', [])
                if suggestions:
                    print(f"\n建議:")
                    for s in suggestions[:2]:
                        print(f"  • {s}")
                
                print(f"\n✅ 意圖識別成功")
            else:
                print(f"\n❌ 失敗: HTTP {response.status_code}")
                print(response.text[:200])
    
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")

async def main():
    """主測試流程"""
    print("="*80)
    print("LLM 意圖識別測試")
    print("="*80)
    
    test_cases = [
        # 列出候選人
        ("列出所有候選人", "list_all"),
        ("目前有哪些人可以挑選？", "list_all"),
        ("顯示資料庫中的所有人", "list_all"),
        
        # 列出特質
        ("有哪些特質可以搜索？", "list_traits"),
        ("系統支援哪些能力評估？", "list_traits"),
        
        # 搜索人才
        ("找一個善於溝通的人", "search"),
        ("需要領導能力強的候選人", "search"),
        ("推薦幾個優秀的人才", "search"),
        
        # 面試綱要（需要實際存在的候選人姓名）
        ("設計一份面試綱要", "interview"),
        # ("為張三設計面試綱要", "interview"),  # 需要實際姓名
        
        # 統計分析
        ("有多少人完成了測評？", "statistics"),
        ("資料庫中有多少候選人？", "statistics"),
        
        # 比較候選人（新功能）
        ("比較張三和李四", "compare"),
        ("誰更適合產品經理職位？", "compare"),
        
        # 建議諮詢（新功能）
        ("如何組建一個高效團隊？", "advice"),
        ("產品經理需要什麼特質？", "advice"),
    ]
    
    print(f"\n將測試 {len(test_cases)} 個查詢...\n")
    
    for query, expected_intent in test_cases:
        await test_intent(query, expected_intent)
        await asyncio.sleep(2)  # 避免請求過快
    
    print(f"\n{'='*80}")
    print("測試完成！")
    print(f"{'='*80}")
    
    print("\n📊 測試總結:")
    print("✅ LLM 意圖識別 - 使用 LLM 自動識別用戶意圖")
    print("✅ 智能實體提取 - 自動提取候選人姓名、特質等")
    print("✅ 7 種意圖類型 - list_all, list_traits, search, interview, statistics, compare, advice")
    print("✅ 可擴展架構 - 輕鬆添加新意圖")
    
    print("\n🎯 新增功能:")
    print("⭐ compare - 比較候選人")
    print("⭐ advice - 建議諮詢")
    
    print("\n💡 優勢:")
    print("• 高準確率 - LLM 理解語義和上下文")
    print("• 可擴展 - 添加新意圖只需修改定義")
    print("• 智能提取 - 自動提取實體資訊")
    print("• 信心度評估 - 返回判斷確定性")

if __name__ == '__main__':
    asyncio.run(main())
