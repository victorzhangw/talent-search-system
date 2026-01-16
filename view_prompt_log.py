"""
Prompt Log 查看工具

用途：查看和分析 RAG 系統的 Prompt Log
"""

import os
import re
from collections import Counter
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), 'BackEnd', 'api_v2', 'logs', 'prompts.log')

def read_log():
    """讀取 log 檔案"""
    if not os.path.exists(LOG_FILE):
        print(f"❌ Log 檔案不存在: {LOG_FILE}")
        return None
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def parse_entries(log_content):
    """解析 log 條目"""
    # 分割每個條目（使用分隔線）
    entries = re.split(r'={60,}', log_content)
    
    parsed = []
    for entry in entries:
        if not entry.strip():
            continue
        
        # 提取資訊
        time_match = re.search(r'TIME: (.+)', entry)
        session_match = re.search(r'SESSION: (.+?) \|', entry)
        uc_match = re.search(r'USE_CASE: (.+)', entry)
        query_match = re.search(r'\[USER QUERY\]\s*(.+?)(?:={60,}|$)', entry, re.DOTALL)
        
        if time_match and session_match and uc_match:
            parsed.append({
                'time': time_match.group(1).strip(),
                'session': session_match.group(1).strip(),
                'use_case': uc_match.group(1).strip(),
                'query': query_match.group(1).strip() if query_match else ''
            })
    
    return parsed

def show_statistics(entries):
    """顯示統計資訊"""
    print("\n" + "="*60)
    print("📊 Prompt Log 統計")
    print("="*60)
    
    print(f"\n總請求數: {len(entries)}")
    
    # Use Case 分布
    use_cases = Counter(e['use_case'] for e in entries)
    print("\n📋 Use Case 分布:")
    for uc, count in use_cases.most_common():
        percentage = (count / len(entries)) * 100
        print(f"  {uc}: {count} 次 ({percentage:.1f}%)")
    
    # 最近的請求
    print("\n🕒 最近 5 次請求:")
    for entry in entries[-5:]:
        print(f"\n  時間: {entry['time']}")
        print(f"  Use Case: {entry['use_case']}")
        print(f"  問題: {entry['query'][:50]}...")

def show_by_use_case(entries, use_case):
    """顯示特定 Use Case 的所有請求"""
    filtered = [e for e in entries if e['use_case'] == use_case]
    
    print(f"\n📋 Use Case: {use_case}")
    print(f"總計: {len(filtered)} 次請求\n")
    
    for i, entry in enumerate(filtered, 1):
        print(f"{i}. [{entry['time']}]")
        print(f"   問題: {entry['query'][:80]}")
        print()

def main():
    print("🔍 Prompt Log 查看工具")
    print("="*60)
    
    # 讀取 log
    log_content = read_log()
    if not log_content:
        return
    
    # 解析條目
    entries = parse_entries(log_content)
    if not entries:
        print("❌ 沒有找到任何 log 條目")
        return
    
    # 顯示統計
    show_statistics(entries)
    
    # 互動式選單
    while True:
        print("\n" + "="*60)
        print("選項:")
        print("  1. 查看所有 UC-GENERAL 請求")
        print("  2. 查看所有 UC-SEL-01 請求")
        print("  3. 查看所有 UC-CMP-01 請求")
        print("  4. 查看所有 UC-DEV-01 請求")
        print("  5. 重新載入統計")
        print("  0. 退出")
        
        choice = input("\n請選擇 (0-5): ").strip()
        
        if choice == '0':
            print("👋 再見！")
            break
        elif choice == '1':
            show_by_use_case(entries, 'UC-GENERAL')
        elif choice == '2':
            show_by_use_case(entries, 'UC-SEL-01')
        elif choice == '3':
            show_by_use_case(entries, 'UC-CMP-01')
        elif choice == '4':
            show_by_use_case(entries, 'UC-DEV-01')
        elif choice == '5':
            log_content = read_log()
            if log_content:
                entries = parse_entries(log_content)
                show_statistics(entries)
        else:
            print("❌ 無效的選項")

if __name__ == '__main__':
    main()
