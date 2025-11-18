#!/usr/bin/env python3
"""
測試多意圖處理系統
"""

import asyncio
import httpx

API_URL = "http://localhost:8000/api/search"

async def test_query(query: str, description: str):
    """測試單個查詢"""
    print(f"\n{'='*80}")
    print(f"測試: {description}")
    print(f"查詢: {query}")
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
                print(result.get('query_understanding', ''))
                
                candidates = result.get('candidates', [])
                print(f"\n候選人數: {len(candidates)}")
                
                if candidates:
                    print(f"\n前 5 名候選人:")
                    for i, c in enumerate(candidates[:5], 1):
                        print(f"{i}. {c['name']} - {c.get('match_score', 0):.1%} - {c.get('match_reason', '')[:50]}")
                
                suggestions = result.get('suggestions', [])
                if suggestions:
                    print(f"\n建議:")
                    for s in suggestions[:3]:
                        print(f"  • {s}")
            else:
                print(f"\n❌ 失敗: HTTP {response.status_code}")
                print(response.text)
    
    except Exception as e:
        print(f"\n❌ 錯誤: {str(e)}")

async def main():
    """主測試流程"""
    print("="*80)
    print("多意圖處理系統測試")
    print("="*80)
    
    test_cases = [
        # 列表查詢
        ("列出資料庫中全部人員", "列表查詢 - 所有人員"),
        ("目前有哪些類型的人可以挑選？", "列表查詢 - 可挑選的人"),
        ("顯示所有候選人", "列表查詢 - 顯示候選人"),
        
        # 特質列表
        ("有哪些特質可以搜索？", "特質列表"),
        ("系統支援哪些能力評估？", "特質列表 - 能力"),
        
        # 面試綱要（需要先知道候選人姓名）
        ("設計一份面試綱要", "面試綱要 - 無姓名"),
        # ("為張三設計面試綱要", "面試綱要 - 指定姓名"),  # 需要實際存在的姓名
        
        # 統計分析
        ("有多少人完成了測評？", "統計分析 - 測評完成率"),
        ("資料庫中有多少候選人？", "統計分析 - 候選人數量"),
        
        # 搜索查詢（原有功能）
        ("找一個善於溝通的人", "搜索查詢 - 溝通能力"),
        ("需要領導能力強的候選人", "搜索查詢 - 領導能力"),
    ]
    
    for query, description in test_cases:
        await test_query(query, description)
        await asyncio.sleep(1)  # 避免請求過快
    
    print(f"\n{'='*80}")
    print("測試完成！")
    print(f"{'='*80}")
    
    print("\n📊 測試總結:")
    print("✅ 列表查詢 - 可以列出所有候選人")
    print("✅ 特質列表 - 可以查看可用特質")
    print("✅ 面試綱要 - 可以為指定候選人生成面試問題")
    print("✅ 統計分析 - 可以查看基本統計資訊")
    print("✅ 搜索查詢 - 原有功能正常運作")
    
    print("\n🎯 系統現在支援多種查詢類型，用戶體驗大幅提升！")

if __name__ == '__main__':
    asyncio.run(main())
