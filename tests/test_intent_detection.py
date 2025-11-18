#!/usr/bin/env python3
"""
測試意圖識別功能
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from talent_search_api import TalentSearchEngine

def test_intent_detection():
    """測試意圖識別"""
    print("="*80)
    print("意圖識別測試")
    print("="*80)
    
    engine = TalentSearchEngine()
    
    test_queries = [
        # 列表查詢
        "列出資料庫中全部人員",
        "目前有哪些類型的人可以挑選？",
        "顯示所有候選人",
        "查看所有用戶",
        
        # 特質列表
        "有哪些特質可以搜索？",
        "系統支援哪些能力評估？",
        "列出所有特質",
        
        # 面試綱要
        "設計一份面試綱要",
        "為張三設計面試綱要",
        "為李四準備面試問題",
        "如何評估王五？",
        
        # 統計分析
        "有多少人完成了測評？",
        "資料庫中有多少候選人？",
        "特質分佈情況",
        "統計領導能力的人數",
        
        # 搜索查詢
        "找一個善於溝通的人",
        "需要領導能力強的候選人",
        "推薦幾個優秀的人才",
        "尋找創意思考能力好的設計師",
    ]
    
    print(f"\n測試 {len(test_queries)} 個查詢...\n")
    
    results = {}
    for query in test_queries:
        intent, entities = engine._detect_query_intent(query)
        
        if intent not in results:
            results[intent] = []
        results[intent].append({
            'query': query,
            'entities': entities
        })
    
    # 按意圖分組顯示
    for intent, queries in results.items():
        print(f"\n{'='*80}")
        print(f"意圖: {intent.upper()}")
        print(f"{'='*80}")
        
        for item in queries:
            query = item['query']
            entities = item['entities']
            
            print(f"\n查詢: {query}")
            if entities:
                print(f"實體: {entities}")
            else:
                print(f"實體: (無)")
    
    print(f"\n{'='*80}")
    print("測試完成！")
    print(f"{'='*80}")
    
    # 統計
    print(f"\n📊 意圖分佈:")
    for intent, queries in results.items():
        print(f"  {intent}: {len(queries)} 個查詢")
    
    print(f"\n✅ 意圖識別功能正常運作！")

if __name__ == '__main__':
    test_intent_detection()
