#!/usr/bin/env python3
"""
測試新的搜索流程
1. 特質必須來自資料庫
2. LLM 生成 SQL 查詢
"""

import asyncio
import sys
sys.path.append('.')

from talent_search_api import TalentSearchEngine, get_db_connection

async def test_search():
    print("=" * 80)
    print("測試新的人才搜索流程")
    print("=" * 80)
    
    # 初始化搜索引擎
    engine = TalentSearchEngine()
    
    # 測試查詢
    test_queries = [
        "我需要一個善於溝通的銷售人員",
        "找一個有創造力的設計師",
        "尋找分析能力強的數據分析師"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"查詢: {query}")
        print(f"{'='*80}")
        
        # 步驟 1: LLM 解析查詢
        print("\n[步驟 1] LLM 解析查詢...")
        parsed_query = await engine.parse_query(query)
        
        print(f"\n解析結果:")
        print(f"  匹配的特質: {parsed_query.get('matched_traits', [])}")
        print(f"  SQL 條件: {parsed_query.get('sql_conditions', [])}")
        print(f"  摘要: {parsed_query.get('summary', '')}")
        
        if parsed_query.get('clarification'):
            print(f"  需要澄清: {parsed_query['clarification']}")
        
        # 步驟 2: 使用 SQL 查詢資料庫
        print("\n[步驟 2] 查詢資料庫...")
        candidates = engine.search_candidates(parsed_query)
        
        print(f"\n找到 {len(candidates)} 位候選人")
        
        # 步驟 3: 計算匹配分數
        print("\n[步驟 3] 計算匹配分數...")
        scored_candidates = []
        for candidate in candidates[:5]:  # 只處理前 5 個
            score = engine.calculate_match_score(candidate, parsed_query)
            scored_candidates.append({
                'name': candidate['name'],
                'score': score,
                'trait_results': candidate.get('trait_results', {})
            })
        
        # 排序
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        print("\n前 5 名候選人:")
        for i, candidate in enumerate(scored_candidates, 1):
            print(f"\n  {i}. {candidate['name']}")
            print(f"     匹配度: {candidate['score']:.2%}")
            if candidate['trait_results']:
                print(f"     特質數量: {len(candidate['trait_results'])}")
        
        print("\n" + "-" * 80)
    
    print("\n測試完成！")

if __name__ == '__main__':
    asyncio.run(test_search())
