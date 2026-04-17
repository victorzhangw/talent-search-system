"""
從 CSV 萃取 Prompt 原文，自動產生：
1. config/quick_modules.json
2. prompts/modules/*.txt (所有單人/多人 Prompt 檔案)
"""
import csv, json, os, re

CSV_PATH = r'd:\python\AI-Character-Chatbot\docs\0417-Prompt規範.tmp.csv'
BACKEND = r'd:\python\AI-Character-Chatbot\BackEnd\api_v2'
MODULES_DIR = os.path.join(BACKEND, 'prompts', 'modules')
CONFIG_PATH = os.path.join(BACKEND, 'config', 'quick_modules.json')

os.makedirs(MODULES_DIR, exist_ok=True)

# 模組 ID 映射表（手動定義以確保 ID 穩定且語意清晰）
MODULE_MAP = {
    ("招募", "快速面試提問指南"): {"id": "recruit_interview", "mode": "single_only"},
    ("招募", "工作中的主要優勢與潛力"): {"id": "recruit_strengths", "mode": "both"},
    ("招募", "在團隊合作中適合的角色"): {"id": "recruit_team_role", "mode": "both"},
    ("招募", "需注意的管理問題或潛在風險"): {"id": "recruit_risk", "mode": "both"},
    ("管理", "如何面對困難、壓力、挑戰"): {"id": "mgmt_pressure", "mode": "both"},
    ("管理", "合適的管理方式與風格"): {"id": "mgmt_style", "mode": "both"},
    ("管理", "展現何種領導風格"): {"id": "mgmt_leadership", "mode": "both"},
    ("管理", "入職前 90 天的帶領重點"): {"id": "mgmt_onboarding", "mode": "both"},
    ("管理", "個人使用說明書(主管)"): {"id": "mgmt_manual_mgr", "mode": "single_only"},
    ("管理", "個人使用說明書(個人)"): {"id": "mgmt_manual_self", "mode": "single_only"},
    ("管理", "變動(AI/轉型)情境的角色與風險"): {"id": "mgmt_change", "mode": "both"},
    ("管理", "高潛人才識別要點"): {"id": "mgmt_hipo", "mode": "both"},
    ("團隊合作", "有效的溝通方法／模式"): {"id": "team_comm", "mode": "both"},
    ("團隊合作", "團隊合作的互補與摩擦"): {"id": "team_complement", "mode": "both"},
    ("團隊合作", "打造高效會議團隊"): {"id": "team_meeting", "mode": "multi_only"},
    ("留才", "離職風險因素分析"): {"id": "retain_turnover", "mode": "both"},
    ("留才", "穩定性和投入度的驅動動機"): {"id": "retain_engagement", "mode": "both"},
    ("培育發展", "培育重點與發展方向"): {"id": "dev_direction", "mode": "both"},
    ("培育發展", "適合的培訓方式與學習節奏"): {"id": "dev_training", "mode": "both"},
    ("培育發展", "適合承擔的任務與專案"): {"id": "dev_assignment", "mode": "both"},
    ("深度分析", "領導風格與潛能分析"): {"id": "deep_leadership", "mode": "both"},
    ("深度分析", "高效溝通模式解析"): {"id": "deep_communication", "mode": "both"},
}

# 讀取 CSV
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    
    quick_modules = {}
    current_category = ''
    
    for row in reader:
        if len(row) < 4:
            continue
        category = row[0].strip()
        topic = row[1].strip()
        single_prompt = row[2].strip()
        multi_prompt = row[3].strip()
        
        if not category:
            continue
        current_category = category
        
        # 嘗試匹配
        key = (current_category, topic)
        if key not in MODULE_MAP:
            # 嘗試模糊匹配（處理微小差異）
            matched = False
            for mk, mv in MODULE_MAP.items():
                if mk[0] == current_category and (mk[1] in topic or topic in mk[1]):
                    key = mk
                    matched = True
                    break
            if not matched:
                print(f"[SKIP] 未匹配: {key}")
                continue
        
        mod_info = MODULE_MAP[key]
        mod_id = mod_info['id']
        mod_mode = mod_info['mode']
        
        # 準備 Prompt 檔案路徑
        single_file = None
        multi_file = None
        
        # 寫入單人 Prompt
        if mod_mode in ('single_only', 'both') and single_prompt and single_prompt != '僅適用多人':
            single_filename = f"{mod_id}_single.txt"
            single_file = f"modules/{single_filename}"
            filepath = os.path.join(MODULES_DIR, single_filename)
            
            # 加入標準資料注入區塊（若原文不含佔位符）
            content = single_prompt
            if '{base_analysis}' not in content:
                content += "\n\n---\n\n## 【輸入數據】\n\n【基礎特質分析資料】\n{base_analysis}\n\n【特質交互作用加強分析】\n{interactions}\n\n【約束條件】\n{constraints}"
            
            with open(filepath, 'w', encoding='utf-8') as pf:
                pf.write(content)
            print(f"[OK] 寫入: {single_filename} ({len(content)} chars)")
        
        # 寫入多人 Prompt
        if mod_mode in ('multi_only', 'both') and multi_prompt and multi_prompt != '僅適用單人':
            multi_filename = f"{mod_id}_multi.txt"
            multi_file = f"modules/{multi_filename}"
            filepath = os.path.join(MODULES_DIR, multi_filename)
            
            content = multi_prompt
            if '{base_analysis}' not in content:
                content += "\n\n---\n\n## 【輸入數據】\n\n【基礎特質分析資料】\n{base_analysis}\n\n【特質交互作用加強分析】\n{interactions}\n\n【約束條件】\n{constraints}"
            
            with open(filepath, 'w', encoding='utf-8') as pf:
                pf.write(content)
            print(f"[OK] 寫入: {multi_filename} ({len(content)} chars)")
        
        # 組裝模組註冊表
        quick_modules[mod_id] = {
            "category": current_category,
            "display_name": topic,
            "single_prompt_file": single_file,
            "multi_prompt_file": multi_file,
            "candidate_mode": mod_mode
        }

# 寫入 quick_modules.json
with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(quick_modules, f, ensure_ascii=False, indent=2)
print(f"\n[DONE] quick_modules.json 已產生，共 {len(quick_modules)} 個模組")

# 統計
total_files = len([f for f in os.listdir(MODULES_DIR) if f.endswith('.txt')])
print(f"[DONE] prompts/modules/ 目錄共 {total_files} 個 Prompt 檔案")
