#!/usr/bin/env python3
"""
分析 Stella 的測驗結果報告，反向推敲資料庫結構
"""

import re
import html

# 讀取 HTML 報告
with open('docs/Traitty結果報告＿ANI＿Stella.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# 簡單移除 HTML 標籤
text_content = re.sub(r'<[^>]+>', ' ', html_content)
text_content = html.unescape(text_content)

print("=" * 100)
print("Stella 測驗結果報告分析")
print("=" * 100)

# 1. 提取基本資訊
print("\n【基本資訊】")
email_match = re.search(r'stella24168@gmail\.com', text_content, re.IGNORECASE)
if email_match:
    print(f"✓ 找到 Email: stella24168@gmail.com")

name_match = re.search(r'受測者姓名\s*(\S+)', text_content)
if name_match:
    print(f"✓ 受測者姓名: {name_match.group(1)}")

role_match = re.search(r'職務角色\s*([^\n]+)', text_content)
if role_match:
    print(f"✓ 職務角色: {role_match.group(1).strip()}")

# 2. 提取特質分數
print("\n【特質分數】")
print("從報告中提取的特質與分數：\n")

# 尋找特質名稱和分數的模式
# 報告格式通常是：特質名稱 + 分數 + 描述
trait_patterns = [
    r'(AI科技素養|人際溝通|創造性思考|協商談判|好奇心|學習敏捷|問題解決|批判性思維|情緒智商|團隊合作|領導力|適應力|責任感|誠信|自我管理|壓力管理|時間管理|決策能力|策略思維|數據分析)\s*(\d{1,3})',
]

found_traits = {}
for pattern in trait_patterns:
    matches = re.finditer(pattern, text_content)
    for match in matches:
        trait_name = match.group(1)
        score = int(match.group(2))
        if trait_name not in found_traits or score > 0:
            found_traits[trait_name] = score

# 顯示找到的特質
for trait, score in sorted(found_traits.items(), key=lambda x: x[1], reverse=True):
    print(f"  {trait:<20} : {score:>3} 分")

# 3. 分析資料結構
print("\n" + "=" * 100)
print("【資料庫結構推論】")
print("=" * 100)

print("""
根據報告內容，資料應該來自以下資料表的組合：

1. 【core_user】- 使用者基本資料
   - email: stella24168@gmail.com
   - 用於識別受測者身份

2. 【test_result】- 測驗結果主表
   - user_id: 關聯到 core_user
   - test_project_id: 關聯到測驗專案
   - completed_at: 完成時間
   - status: 測驗狀態

3. 【test_result_trait】- 特質評分結果
   - test_result_id: 關聯到 test_result
   - trait_id: 關聯到 trait 特質表
   - score: 特質分數 (0-100)
   - percentile: 百分位數

4. 【trait】- 特質定義表
   - id: 特質ID
   - chinese_name: 中文名稱 (如：AI科技素養、人際溝通)
   - system_name: 系統名稱
   - description: 特質描述

5. 【test_project_category】- 測驗專案分類
   - name: 分類名稱 (如：AI時代人才潛能評鑑)
   
6. 【test_project_category_trait】- 分類與特質的關聯
   - category_id: 關聯到分類
   - trait_id: 關聯到特質
   - 定義哪些特質屬於哪個分類

資料查詢流程：
--------------
1. 透過 email 在 core_user 找到 user_id
2. 透過 user_id 在 test_result 找到測驗記錄
3. 透過 test_result_id 在 test_result_trait 找到所有特質分數
4. 透過 trait_id 在 trait 表找到特質名稱和描述
5. 透過 test_project_category_trait 找到特質所屬的分類
6. 合併所有資料生成報告

SQL 查詢範例：
-------------
SELECT 
    u.email,
    u.first_name,
    tr.completed_at,
    t.chinese_name as trait_name,
    t.description as trait_description,
    trt.score,
    trt.percentile,
    tpc.name as category_name
FROM core_user u
JOIN test_result tr ON u.id = tr.user_id
JOIN test_result_trait trt ON tr.id = trt.test_result_id
JOIN trait t ON trt.trait_id = t.id
LEFT JOIN test_project_category_trait tpct ON t.id = tpct.trait_id
LEFT JOIN test_project_category tpc ON tpct.category_id = tpc.id
WHERE u.email = 'stella24168@gmail.com'
ORDER BY trt.score DESC;
""")

print("\n" + "=" * 100)
print("分析完成！")
print("=" * 100)
