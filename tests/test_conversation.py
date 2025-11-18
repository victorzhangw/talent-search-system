#!/usr/bin/env python3
"""
測試對話增強搜索
演示多輪對話功能
"""

import asyncio
import sys
sys.path.append('.')

from talent_search_api import TalentSearchEngine, LLMService, get_db_connection
from conversation_enhanced_search import ConversationEnhancedSearch
from conversation_manager import conversation_manager


async def test_conversation():
    """測試多輪對話"""
    
    print("=" * 80)
    print("對話增強搜索測試")
    print("=" * 80)
    
    # 初始化
    conn = get_db_connection()
    engine = TalentSearchEngine()
    enhanced_search = ConversationEnhancedSearch(engine.llm_service, engine)
    
    # 模擬會話 ID
    session_id = "test_session_001"
    
    # 測試場景：多輪對話
    conversations = [
        "找到 Howard",
        "描述一下他的特質",
        "為他設計面試綱要",
        "他適合什麼職位？"
    ]
    
    print("\n開始對話測試...\n")
    
    for i, query in enumerate(conversations, 1):
        print(f"\n{'=' * 80}")
        print(f"第 {i} 輪對話")
        print(f"{'=' * 80}")
        print(f"👤 用戶: {query}")
        print()
        
        # 處理查詢
        result = await enhanced_search.process_query_with_context(query, session_id)
        
        # 顯示結果
        if result.get('success'):
            print(f"🤖 助手:")
            print(result.get('response', '無回應'))
            
            if result.get('suggestions'):
                print(f"\n💡 建議:")
                for suggestion in result['suggestions'][:3]:
                    print(f"   • {suggestion}")
        else:
            print(f"❌ 錯誤: {result.get('response', '未知錯誤')}")
        
        print()
        
        # 顯示上下文狀態
        context = conversation_manager.get_or_create_session(session_id)
        print(f"📊 上下文狀態: {context.get_context_summary()}")
        
        # 暫停一下
        await asyncio.sleep(1)
    
    print("\n" + "=" * 80)
    print("對話測試完成！")
    print("=" * 80)
    
    # 顯示完整對話歷史
    context = conversation_manager.get_or_create_session(session_id)
    print("\n完整對話歷史:")
    for msg in context.messages:
        role = "👤 用戶" if msg['role'] == 'user' else "🤖 助手"
        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        print(f"{role}: {content}")


async def test_follow_up_detection():
    """測試後續問題檢測"""
    
    print("\n" + "=" * 80)
    print("後續問題檢測測試")
    print("=" * 80)
    
    conn = get_db_connection()
    engine = TalentSearchEngine()
    enhanced_search = ConversationEnhancedSearch(engine.llm_service, engine)
    
    session_id = "test_session_002"
    
    # 先搜索一個候選人
    print("\n1. 搜索候選人...")
    result1 = await enhanced_search.process_query_with_context("找到 Howard", session_id)
    print(f"   結果: {result1.get('success')}")
    
    # 測試各種後續問題
    follow_up_queries = [
        "描述一下他的特質",
        "他怎麼樣？",
        "介紹一下",
        "為他準備面試",
        "更多細節",
        "他的優勢是什麼？"
    ]
    
    print("\n2. 測試後續問題檢測...")
    context = conversation_manager.get_or_create_session(session_id)
    
    for query in follow_up_queries:
        analysis = conversation_manager.analyze_context_intent(context, query)
        
        print(f"\n   查詢: {query}")
        print(f"   是否為後續問題: {analysis.get('is_follow_up')}")
        if analysis.get('is_follow_up'):
            print(f"   後續意圖: {analysis.get('follow_up_intent')}")
            print(f"   增強查詢: {analysis.get('enhanced_query')}")


if __name__ == '__main__':
    print("選擇測試:")
    print("1. 完整對話測試")
    print("2. 後續問題檢測測試")
    print("3. 全部測試")
    
    choice = input("\n請選擇 (1-3): ").strip()
    
    if choice == '1':
        asyncio.run(test_conversation())
    elif choice == '2':
        asyncio.run(test_follow_up_detection())
    elif choice == '3':
        asyncio.run(test_follow_up_detection())
        asyncio.run(test_conversation())
    else:
        print("無效選擇")
