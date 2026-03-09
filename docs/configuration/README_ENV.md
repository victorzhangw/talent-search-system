# 環境變數配置說明

## 概述

本專案使用環境變數來管理敏感配置和可調整參數，確保安全性和靈活性。

## 配置文件

- **`.env.example`**: 配置模板文件（已提交到 Git）
- **`.env.local`**: 實際配置文件（不提交到 Git，包含敏感資訊）
- **`.env.production.example`**: 生產環境配置模板

## 快速開始

1. 複製範例文件：

   ```bash
   cp .env.example .env.local
   ```

2. 編輯 `.env.local`，填入實際值：

   ```bash
   # 使用你喜歡的編輯器
   nano .env.local
   # 或
   code .env.local
   ```

3. 重啟應用以載入新配置

## 配置項說明

### 資料庫配置

| 變數名                    | 說明                        | 範例值                    |
| ------------------------- | --------------------------- | ------------------------- |
| `DB_SSH_HOST`             | SSH 跳板機地址              | `54.199.255.239`          |
| `DB_SSH_PORT`             | SSH 端口                    | `22`                      |
| `DB_SSH_USERNAME`         | SSH 用戶名                  | `your_username`           |
| `DB_SSH_PRIVATE_KEY_FILE` | SSH 私鑰文件名              | `private-key-openssh.pem` |
| `DB_HOST`                 | 資料庫主機（通過 SSH 隧道） | `localhost`               |
| `DB_PORT`                 | 資料庫端口                  | `5432`                    |
| `DB_NAME`                 | 資料庫名稱                  | `ai_chatbot_v2`               |
| `DB_USER`                 | 資料庫用戶                  | `projectuser`             |
| `DB_PASSWORD`             | 資料庫密碼                  | `your_password`           |

### LLM API 配置

| 變數名                    | 說明                  | 預設值                       | 範例值                   |
| ------------------------- | --------------------- | ---------------------------- | ------------------------ |
| `LLM_API_KEY`             | LLM 服務 API 金鑰     | **必填**                     | `sk-xxxxx`               |
| `LLM_API_HOST`            | LLM 服務基礎 URL      | `https://api.siliconflow.cn` | `https://api.openai.com` |
| `LLM_MODEL`               | 使用的模型名稱        | `deepseek-ai/DeepSeek-V3`    | `gpt-4`                  |
| `LLM_MAX_RESPONSE_LENGTH` | 回答最大字數          | `150`                        | `200`                    |
| `LLM_TEMPERATURE`         | 創意度參數（0.0-1.0） | `0.7`                        | `0.8`                    |
| `LLM_MAX_TOKENS`          | 最大 Token 數         | `500`                        | `1000`                   |

#### LLM 參數說明

- **LLM_MAX_RESPONSE_LENGTH**: 控制 HR 諮詢回答的最大字數，避免回答過長
- **LLM_TEMPERATURE**:
  - `0.0`: 最確定性，回答一致
  - `0.7`: 平衡創意和一致性（推薦）
  - `1.0`: 最有創意，回答多樣
- **LLM_MAX_TOKENS**: 限制 LLM 生成的最大 token 數，控制成本

### 應用配置

| 變數名        | 說明         | 預設值        |
| ------------- | ------------ | ------------- |
| `ENVIRONMENT` | 運行環境     | `development` |
| `HOST`        | 服務監聽地址 | `0.0.0.0`     |
| `PORT`        | 服務端口     | `8000`        |
| `DEBUG`       | 調試模式     | `True`        |

## 安全注意事項

### ⚠️ 重要提醒

1. **永遠不要提交 `.env.local` 到 Git**

   - 已在 `.gitignore` 中排除
   - 包含敏感的 API 金鑰和密碼

2. **保護 API 金鑰**

   - 定期輪換 API 金鑰
   - 不要在日誌中輸出完整金鑰
   - 使用環境變數而非硬編碼

3. **SSH 私鑰管理**
   - 私鑰文件（`.pem`）已在 `.gitignore` 中排除
   - 確保私鑰文件權限為 `600`
   - 不要共享私鑰文件

## 不同環境的配置

### 開發環境（Development）

使用 `.env.local`：

```bash
ENVIRONMENT=development
DEBUG=True
LLM_API_HOST=https://api.siliconflow.cn
```

### 生產環境（Production）

使用 `.env.production`：

```bash
ENVIRONMENT=production
DEBUG=False
LLM_API_HOST=https://api.your-production-llm.com
```

## 故障排除

### 問題：應用啟動失敗，提示 "LLM_API_KEY 環境變數未設定"

**解決方案**：

1. 確認 `.env.local` 文件存在
2. 確認文件中有 `LLM_API_KEY=your_key_here`
3. 重啟應用

### 問題：LLM 回答過長或過短

**解決方案**：
調整 `.env.local` 中的 `LLM_MAX_RESPONSE_LENGTH` 值：

```bash
# 更長的回答
LLM_MAX_RESPONSE_LENGTH=200

# 更短的回答
LLM_MAX_RESPONSE_LENGTH=100
```

### 問題：LLM 回答不夠創意或太隨機

**解決方案**：
調整 `LLM_TEMPERATURE` 值：

```bash
# 更確定性的回答
LLM_TEMPERATURE=0.5

# 更有創意的回答
LLM_TEMPERATURE=0.9
```

## 載入環境變數

應用使用 `python-dotenv` 自動載入環境變數：

```python
from dotenv import load_dotenv
import os

# 載入 .env.local
load_dotenv('.env.local')

# 讀取變數
api_key = os.getenv('LLM_API_KEY')
```

## 檢查配置

使用以下命令檢查當前配置（不顯示敏感值）：

```bash
cd BackEnd
python -c "
import os
from dotenv import load_dotenv

load_dotenv('.env.local')

print('環境配置檢查：')
print(f'  環境: {os.getenv(\"ENVIRONMENT\")}')
print(f'  LLM Host: {os.getenv(\"LLM_API_HOST\")}')
print(f'  LLM Model: {os.getenv(\"LLM_MODEL\")}')
print(f'  API Key: {\"已設定\" if os.getenv(\"LLM_API_KEY\") else \"未設定\"}')
print(f'  最大回答長度: {os.getenv(\"LLM_MAX_RESPONSE_LENGTH\")} 字')
"
```

## 更多資訊

- [python-dotenv 文檔](https://github.com/theskumar/python-dotenv)
- [環境變數最佳實踐](https://12factor.net/config)

## Prompt 配置

### Prompt 模板文件

Prompt 模板存放在 `BackEnd/prompts/` 目錄下，使用 JSON 格式配置。

#### HR 諮詢 Prompts

文件位置：`BackEnd/prompts/hr_consultation_prompts.json`

包含兩種類型的 Prompt：

1. **候選人特定諮詢** (`candidate_specific`)

   - `system_prompt_template`: System Prompt 模板
   - `user_prompt_template`: User Prompt 模板
   - 用於針對特定候選人的 HR 諮詢

2. **通用 HR 諮詢** (`general`)
   - `system_prompt_template`: System Prompt 模板
   - `user_prompt_template`: User Prompt 模板
   - 用於不涉及特定候選人的一般性 HR 問題

### 修改 Prompt

1. 編輯 `BackEnd/prompts/hr_consultation_prompts.json`
2. 修改對應的 `system_prompt_template` 或 `user_prompt_template`
3. 使用 `{變數名}` 作為佔位符（例如：`{candidate_name}`、`{query}`）
4. 重啟應用以載入新的 Prompt

### Prompt 變數

#### 候選人特定諮詢可用變數

- `{candidate_name}`: 候選人姓名
- `{candidate_email}`: 候選人郵箱
- `{candidate_position}`: 候選人職位
- `{candidate_status}`: 候選人狀態
- `{candidate_company}`: 候選人公司
- `{candidate_notes}`: 候選人備註
- `{invited_count}`: 總受邀次數
- `{completed_count}`: 已完成次數
- `{completion_rate}`: 完成率
- `{last_test_date}`: 最後測驗日期
- `{test_project_name}`: 測驗項目名稱
- `{test_date}`: 測驗時間
- `{overall_score}`: 總評分數
- `{total_traits}`: 總特質數
- `{primary_traits_detail}`: 主要特質詳情
- `{all_traits_detail}`: 所有特質詳情
- `{strengths_detail}`: 優勢特質詳情
- `{weaknesses_detail}`: 待提升特質詳情
- `{excellent_count}`: 優秀特質數量
- `{good_count}`: 良好特質數量
- `{average_count}`: 中等特質數量
- `{below_average_count}`: 待提升特質數量
- `{prediction_value}`: 預測結果
- `{max_response_length}`: 最大回答長度
- `{query}`: 用戶問題

#### 通用 HR 諮詢可用變數

- `{query}`: 用戶問題
- `{max_response_length}`: 最大回答長度

### Prompt 管理器

系統使用 `prompt_manager.py` 來管理所有 Prompt 模板：

```python
from prompt_manager import get_prompt_manager

# 獲取 Prompt 管理器
prompt_manager = get_prompt_manager()

# 獲取候選人特定諮詢 Prompts
system_prompt, user_prompt = prompt_manager.get_hr_candidate_prompts(
    candidate_name="張三",
    query="適合什麼職位？",
    # ... 其他變數
)

# 獲取通用 HR 諮詢 Prompts
system_prompt, user_prompt = prompt_manager.get_hr_general_prompts(
    query="如何提升團隊協作？",
    max_response_length=150
)

# 重新載入 Prompts（無需重啟應用）
prompt_manager.reload_prompts()
```

### 優勢

1. **無需修改代碼**：調整 Prompt 只需編輯 JSON 文件
2. **版本控制**：Prompt 變更可以通過 Git 追蹤
3. **易於測試**：可以快速測試不同的 Prompt 版本
4. **集中管理**：所有 Prompt 集中在一個地方
5. **支援多語言**：可以輕鬆添加不同語言的 Prompt 模板
