#!/usr/bin/env python3
"""
測試混合搜索策略
"""

import asyncio
from talent_search_api import TalentSearchEngine

async def test_hybrid_search():
    print("=" * 80)
    print("測試混合搜索策略")
    print("=" * 80)
    
    engine = TalentSearchEngine()
    
    test_queries = [
        "我需要一個能帶領團隊、善於溝通、有創意的人",
        "找一個適合做產品經理的人",
        "推薦幾個優秀的候選人",
        "需要分析能力強的數據分析師",
        "找一個有創造力的設計師"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"測試 {i}: {query}")
        print(f"{'='*80}")
        
        # 步驟 1: LLM 解析查詢
        print("\n[步驟 1] LLM 解析查詢...")
        parsed_query = await engine.parse_query(query)
        
        intent = parsed_query.get('intent', 'search')
        print(f"查詢意圖: {intent}")
        
        if intent != 'search':
            print(f"非搜索查詢，跳過測試")
            continue
        
        matched_traits = parsed_query.get('matched_traits', [])
        print(f"匹配的特質: {len(matched_traits)} 個")
        for trait in matched_traits[:3]:
            print(f"  - {trait.get('chinese_name', '')} ({trait.get('system_name', '')})")
        
        # 步驟 2: 寬鬆查詢召回
        print("\n[步驟 2] 寬鬆查詢召回候選人...")
        raw_candidates = engine.search_candidates(parsed_query)
        print(f"召回候選人數: {len(raw_candidates)}")
        
        if not raw_candidates:
            print("❌ 沒有召回任何候選人")
            continue
        
        # 步驟 3: 記憶體中評分
        print("\n[步驟 3] 記憶體中計算匹配分數...")
        scored_candidates = []
        
        for candidate in raw_candidates:
            score = engine.calculate_match_score(candidate, parsed_query)
            candidate['match_score'] = score
            scored_candidates.append(candidate)
        
        # 步驟 4: 排序
        print("\n[步驟 4] 按分數排序...")
        scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
        
        # 顯示前 10 名
        print("\n🏆 前 10 名候選人:")
        print("-" * 80)
        print(f"{'排名':<4} {'姓名':<15} {'匹配度':<8} {'特質數量':<8} {'說明'}")
        print("-" * 80)
        
        for rank, candidate in enumerate(scored_candidates[:10], 1):
            name = candidate.get('name', '未知')
            score = candidate.get('match_score', 0)
            trait_count = len(candidate.get('trait_results', {}))
            
            # 簡單的說明
            if score >= 0.8:
                desc = "高度匹配"
            elif score >= 0.6:
                desc = "良好匹配"
            elif score >= 0.4:
                desc = "部分匹配"
            else:
                desc = "基礎匹配"
            
            print(f"{rank:<4} {name:<15} {score:<8.1%} {trait_count:<8} {desc}")
        
        # 分析結果
        print("\n📊 結果分析:")
        high_score = len([c for c in scored_candidates if c['match_score'] >= 0.7])
        medium_score = len([c for c in scored_candidates if 0.4 <= c['match_score'] < 0.7])
        low_score = len([c for c in scored_candidates if c['match_score'] < 0.4])
        
        print(f"  高分候選人 (≥70%): {high_score} 個")
        print(f"  中分候選人 (40-70%): {medium_score} 個")
        print(f"  低分候選人 (<40%): {low_score} 個")
        
        if high_score > 0:
            print("  ✅ 找到高質量匹配")
        elif medium_score > 0:
            print("  ⚠️ 找到中等匹配")
        else:
            print("  ❌ 沒有找到好的匹配")
        
        print("\n" + "-" * 80)
    
    print("\n" + "=" * 80)
    print("測試完成！")
    print("=" * 80)
    
    # 總結
    print("\n混合搜索策略的優勢:")
    print("✅ 寬鬆查詢確保召回足夠的候選人")
    print("✅ 記憶體中評分提供精確的排序")
    print("✅ 多階段處理提升搜索質量")
    print("✅ 總是能返回結果，提升用戶體驗")

if __name__ == '__main__':
    asyncio.run(test_hybrid_search())
