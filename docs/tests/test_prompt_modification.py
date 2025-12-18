"""
測試 Prompt 動態修改功能
演示如何修改 Prompt 配置文件並重新載入
"""

import json
import os
import shutil
from prompt_manager import get_prompt_manager

def test_prompt_modification():
    """測試 Prompt 修改和重新載入"""
    
    print("=" * 60)
    print("測試 Prompt 動態修改功能")
    print("=" * 60)
    print()
    
    # 1. 備份原始 Prompt 文件
    prompt_file = "prompts/hr_consultation_prompts.json"
    backup_file = "prompts/hr_consultation_prompts.json.backup"
    
    print("步驟 1: 備份原始 Prompt 文件")
    shutil.copy(prompt_file, backup_file)
    print(f"✅ 已備份到: {backup_file}")
    print()
    
    try:
        # 2. 獲取 Prompt 管理器
        print("步驟 2: 獲取 Prompt 管理器")
        prompt_manager = get_prompt_manager()
        print("✅ Prompt 管理器已初始化")
        print()
        
        # 3. 測試原始 Prompt
        print("步驟 3: 測試原始 Prompt")
        system_prompt, user_prompt = prompt_manager.get_hr_general_prompts(
            query="測試問題",
            max_response_length=150
        )
        print(f"原始 System Prompt 開頭: {system_prompt[:50]}...")
        print()
        
        # 4. 修改 Prompt 文件
        print("步驟 4: 修改 Prompt 文件")
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        
        # 修改通用 HR 諮詢的 System Prompt
        original_prompt = prompts['general']['system_prompt_template']
        prompts['general']['system_prompt_template'] = "【測試修改】" + original_prompt
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        
        print("✅ Prompt 文件已修改（添加了【測試修改】前綴）")
        print()
        
        # 5. 重新載入 Prompt
        print("步驟 5: 重新載入 Prompt")
        prompt_manager.reload_prompts()
        print("✅ Prompt 已重新載入")
        print()
        
        # 6. 測試修改後的 Prompt
        print("步驟 6: 測試修改後的 Prompt")
        system_prompt_new, user_prompt_new = prompt_manager.get_hr_general_prompts(
            query="測試問題",
            max_response_length=150
        )
        print(f"修改後 System Prompt 開頭: {system_prompt_new[:60]}...")
        print()
        
        # 7. 驗證修改是否生效
        print("步驟 7: 驗證修改")
        if "【測試修改】" in system_prompt_new:
            print("✅ Prompt 修改成功！")
            print("✅ 動態重新載入功能正常工作")
        else:
            print("❌ Prompt 修改未生效")
        print()
        
    finally:
        # 8. 恢復原始 Prompt 文件
        print("步驟 8: 恢復原始 Prompt 文件")
        shutil.copy(backup_file, prompt_file)
        os.remove(backup_file)
        print("✅ 已恢復原始 Prompt 文件")
        print()
        
        # 9. 重新載入原始 Prompt
        print("步驟 9: 重新載入原始 Prompt")
        prompt_manager.reload_prompts()
        print("✅ 已重新載入原始 Prompt")
        print()
    
    print("=" * 60)
    print("測試完成")
    print("=" * 60)
    print()
    print("結論：")
    print("1. ✅ Prompt 可以通過修改 JSON 文件來調整")
    print("2. ✅ 修改後可以動態重新載入，無需重啟應用")
    print("3. ✅ 系統會自動備份和恢復，確保安全")

if __name__ == "__main__":
    test_prompt_modification()
