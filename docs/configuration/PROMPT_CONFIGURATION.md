# Prompt 配置說明

## 概述

此目錄包含所有 LLM Prompt 模板配置文件。通過修改這些 JSON 文件，您可以調整 AI 的回答風格和內容，而無需修改代碼。

## 文件結構

```
prompts/
├── README.md                          # 本文件
└── hr_consultation_prompts.json       # HR 諮詢 Prompt 模板
```

## HR 諮詢 Prompts

### 文件：`hr_consultation_prompts.json`

包含兩種類型的 Prompt 模板：

#### 1. 候選人特定諮詢 (`candidate_specific`)

用於針對特定候選人的 HR 諮詢，包含完整的候選人檔案和測評數據。

**可用變數：**

| 變數名                    | 說明           | 範例              |
| ------------------------- | -------------- | ----------------- |
| `{candidate_name}`        | 候選人姓名     | 張三              |
| `{candidate_email}`       | 候選人郵箱     | zhang@example.com |
| `{candidate_position}`    | 候選人職位     | 產品經理          |
| `{candidate_status}`      | 候選人狀態     | 在職/求職中       |
| `{candidate_company}`     | 候選人公司     | ABC 公司          |
| `{candidate_notes}`       | 候選人備註     | 有 5 年經驗       |
| `{invited_count}`         | 總受邀次數     | 3                 |
| `{completed_count}`       | 已完成次數     | 2                 |
| `{completion_rate}`       | 完成率         | 66.7              |
| `{last_test_date}`        | 最後測驗日期   | 2025-12-17        |
| `{test_project_name}`     | 測驗項目名稱   | CIA 綜合評鑑      |
| `{test_date}`             | 測驗時間       | 2025-12-15        |
| `{overall_score}`         | 總評分數       | 75                |
| `{total_traits}`          | 總特質數       | 51                |
| `{primary_traits_detail}` | 主要特質詳情   | 格式化的特質列表  |
| `{all_traits_detail}`     | 所有特質詳情   | 格式化的特質列表  |
| `{strengths_detail}`      | 優勢特質詳情   | 格式化的優勢列表  |
| `{weaknesses_detail}`     | 待提升特質詳情 | 格式化的弱項列表  |
| `{excellent_count}`       | 優秀特質數量   | 5                 |
| `{good_count}`            | 良好特質數量   | 10                |
| `{average_count}`         | 中等特質數量   | 20                |
| `{below_average_count}`   | 待提升特質數量 | 3                 |
| `{prediction_value}`      | 預測結果       | 適合管理職位      |
| `{max_response_length}`   | 最大回答長度   | 150               |
| `{query}`                 | 用戶問題       | 適合什麼職位？    |

#### 2. 通用 HR 諮詢 (`general`)

用於不涉及特定候選人的一般性 HR 問題。

**可用變數：**

| 變數名                  | 說明         | 範例               |
| ----------------------- | ------------ | ------------------ |
| `{query}`               | 用戶問題     | 如何提升團隊協作？ |
| `{max_response_length}` | 最大回答長度 | 150                |

## 修改 Prompt

### 步驟

1. 打開 `hr_consultation_prompts.json`
2. 找到要修改的 Prompt 類型（`candidate_specific` 或 `general`）
3. 修改 `system_prompt_template` 或 `user_prompt_template`
4. 保存文件
5. 重啟應用以載入新的 Prompt

### 注意事項

1. **保持 JSON 格式正確**：確保所有引號、逗號、括號都正確配對
2. **使用正確的變數名**：變數名必須用 `{變數名}` 格式包裹
3. **保留必要的變數**：某些變數是必需的，刪除可能導致錯誤
4. **測試修改**：修改後務必測試以確保 Prompt 正常工作
5. **備份原始文件**：修改前建議備份原始 Prompt

### 範例：修改回答風格

**原始 Prompt（專業正式）：**

```
你是一位資深的人力資源專家，擁有 20+ 年的人才評估和職業發展諮詢經驗。
```

**修改為友善親切風格：**

```
你是一位經驗豐富且親切的 HR 顧問，擅長用簡單易懂的方式幫助候選人了解自己的優勢和發展方向。
```

### 範例：調整回答結構

**原始要求：**

```
## 回答要求
1. **基於數據**: 所有分析和建議必須基於上述測評分數和候選人檔案
2. **字數限制**: 回答控制在 {max_response_length} 字以內
```

**修改為更具體的結構：**

```
## 回答要求
1. **開場**：用一句話總結候選人的整體表現
2. **優勢分析**：列出 2-3 個主要優勢特質
3. **改進建議**：針對待提升特質給出具體建議
4. **字數限制**：回答控制在 {max_response_length} 字以內
```

## 最佳實踐

### 1. Prompt 設計原則

- **清晰明確**：明確告訴 AI 它的角色和任務
- **結構化**：使用標題、列表等結構化格式
- **具體要求**：給出具體的回答要求和限制
- **禁止事項**：明確列出不應該做的事情

### 2. 變數使用

- **必需變數**：確保所有必需的變數都被使用
- **格式一致**：保持變數格式的一致性
- **有意義的名稱**：使用描述性的變數名

### 3. 測試和驗證

- **單元測試**：修改後運行測試腳本
- **邊界情況**：測試極端情況（如空值、超長文本）
- **用戶反饋**：收集實際使用者的反饋

### 4. 版本控制

- **提交訊息**：清楚描述 Prompt 的修改內容
- **標記版本**：重大修改時創建 Git 標籤
- **文檔更新**：同步更新相關文檔

## 故障排除

### 問題：Prompt 變數未被替換

**原因**：變數名拼寫錯誤或格式不正確

**解決方案**：

1. 檢查變數名是否正確（區分大小寫）
2. 確保使用 `{變數名}` 格式
3. 查看日誌中的錯誤訊息

### 問題：JSON 解析錯誤

**原因**：JSON 格式不正確

**解決方案**：

1. 使用 JSON 驗證工具檢查格式
2. 確保所有字符串都用雙引號包裹
3. 檢查是否有多餘或缺少的逗號

### 問題：回答質量下降

**原因**：Prompt 修改不當

**解決方案**：

1. 恢復到之前的版本
2. 逐步修改，每次只改一小部分
3. 對比修改前後的回答質量

## 進階功能

### 動態 Prompt 載入

系統支援在運行時重新載入 Prompt，無需重啟應用：

```python
from prompt_manager import get_prompt_manager

prompt_manager = get_prompt_manager()
prompt_manager.reload_prompts()
```

### 多語言支援

可以創建不同語言的 Prompt 文件：

```
prompts/
├── hr_consultation_prompts.json       # 中文
├── hr_consultation_prompts_en.json    # 英文
└── hr_consultation_prompts_ja.json    # 日文
```

然後在代碼中根據用戶語言選擇對應的 Prompt 文件。

## 相關資源

- [環境變數配置文檔](../README_ENV.md)
- [API 文檔](http://localhost:8000/docs)
- [測試腳本](../test_env_config.py)

## 聯繫支援

如有問題或建議，請聯繫開發團隊。
