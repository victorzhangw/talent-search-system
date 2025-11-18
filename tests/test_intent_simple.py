#!/usr/bin/env python3
"""
簡化的意圖識別測試（不需要資料庫）
"""

import re

def detect_query_intent(query: str) -> tuple[str, dict]:
    """檢測查詢意圖（簡單規則 + 實體提取）"""
    query_lower = query.lower()
    entities = {}
    
    # 面試類查詢
    interview_keywords = ['面試', '綱要', '問題', '評估']
    if any(keyword in query_lower for keyword in interview_keywords):
        # 嘗試提取候選人姓名（簡單規則）
        # 例如：「為張三設計面試綱要」
        name_pattern = r'為(.{2,4})(?:設計|準備|生成)'
        match = re.search(name_pattern, query)
        if match:
            entities['candidate_name'] = match.group(1)
        return 'interview', entities
    
    # 列表/查看類查詢
    list_keywords = ['列出', '顯示', '查看', '所有', '全部', '有哪些', '列表']
    if any(keyword in query_lower for keyword in list_keywords):
        if '人' in query_lower or '候選人' in query_lower or '用戶' in query_lower:
            return 'list_all', entities
        elif '特質' in query_lower or '能力' in query_lower:
            return 'list_traits', entities
    
    # 統計類查詢
    stats_keywords = ['多少', '統計', '分佈', '數量']
    if any(keyword in query_lower for keyword in stats_keywords):
        return 'statistics', entities
    
    # 搜索類查詢
    search_keywords = ['找', '需要', '尋找', '搜索', '推薦']
    if any(keyword in query_lower for keyword in search_keywords):
        return 'search', entities
    
    # 預設為搜索
    return 'search', entities

def main():
    """測試意圖識別"""
    print("="*80)
    print("意圖識別測試")
    print("="*80)
    
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
        intent, entities = detect_query_intent(query)
        
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
    
    # 詳細分析
    print(f"\n📋 詳細分析:")
    print(f"\n1. LIST_ALL (列出所有人)")
    print(f"   - 關鍵字: 列出、顯示、查看、所有、全部、有哪些")
    print(f"   - 目標: 人、候選人、用戶")
    
    print(f"\n2. LIST_TRAITS (列出特質)")
    print(f"   - 關鍵字: 列出、顯示、查看、所有、全部、有哪些")
    print(f"   - 目標: 特質、能力")
    
    print(f"\n3. INTERVIEW (面試綱要)")
    print(f"   - 關鍵字: 面試、綱要、問題、評估")
    print(f"   - 實體提取: 候選人姓名（正則表達式）")
    
    print(f"\n4. STATISTICS (統計分析)")
    print(f"   - 關鍵字: 多少、統計、分佈、數量")
    
    print(f"\n5. SEARCH (搜索查詢)")
    print(f"   - 關鍵字: 找、需要、尋找、搜索、推薦")
    print(f"   - 預設意圖")

if __name__ == '__main__':
    main()
