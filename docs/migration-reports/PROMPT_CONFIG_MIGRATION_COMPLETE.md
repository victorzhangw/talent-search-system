# Prompt 配置遷移完成報告

## 任務概述

將所有 LLM Prompt 從代碼中遷移到配置文件中，實現 Prompt 的集中管理和靈活調整。

## 完成狀態

✅ **已完成並測試通過**

## 修改內容

### 1. 新增文件

#### Prompt 配置文件

- **`BackEnd/prompts/hr_consultation_prompts.json`**
  - 候選人特定諮詢 Prompt 模板
  - 通用 HR 諮詢 Prompt 模板
  - 使用 JSON 格式，支援變數替換

#### Prompt 管理器

- **`BackEnd/prompt_manager.py`**
  - `PromptManager` 類：負責載入和管理 Prompt 模板
  - `get_prompt_manager()` 函數：獲取全局 Prompt 管理器實例
  - 支援動態重新載入 Prompt

#### 文檔

- **`BackEnd/prompts/README.md`**
  - Prompt 配置完整說明文檔
  - 變數列表和使用範例
  - 最佳實踐和故障排除指南

### 2. 修改文件

#### `BackEnd/hr_consultation_service.py`

- 添加 `from prompt_manager import get_prompt_manager`
- 在 `__init__` 中初始化 `self.prompt_manager`
- 修改 `_build_hr_system_prompt` 方法使用 Prompt 管理器
- 修改 `_build_user_prompt` 方法使用 Prompt 管理器

#### `BackEnd/hr_consultation_routes.py`

- 添加 `from prompt_manager import get_prompt_manager`
- 修改通用 HR 諮詢部分使用 Prompt 管理器

#### `BackEnd/.env.local` 和 `BackEnd/.env.example`

- 添加 Prompt 配置說明註釋

#### `BackEnd/README_ENV.md`

- 添加完整的 Prompt 配置章節
- 說明 Prompt 變數和使用方法

## 架構設計

### Prompt 管理流程

```
┌─────────────────────────────────────────────────────────┐
│                    應用啟動                              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              PromptManager 初始化                        │
│  - 載入 hr_consultation_prompts.json                    │
│  - 解析 JSON 並存儲模板                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           HRConsultationService 初始化                   │
│  - 獲取 PromptManager 實例                              │
│  - 準備使用 Prompt 模板                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 API 請求處理                             │
│  1. 收集候選人數據和測評結果                             │
│  2. 調用 PromptManager.get_hr_candidate_prompts()       │
│  3. 傳入變數，獲取填充後的 Prompt                        │
│  4. 調用 LLM API                                        │
│  5. 返回結果                                            │
└─────────────────────────────────────────────────────────┘
```

### 文件結構

```
BackEnd/
├── prompts/                              # Prompt 配置目錄
│   ├── README.md                         # Prompt 配置說明
│   └── hr_consultation_prompts.json      # HR 諮詢 Prompt 模板
├── prompt_manager.py                     # Prompt 管理器
├── hr_consultation_service.py            # HR 諮詢服務（已修改）
├── hr_consultation_routes.py             # HR 諮詢路由（已修改）
├── .env.local                            # 環境變數（已更新）
├── .env.example                          # 環境變數範例（已更新）
└── README_ENV.md                         # 環境變數文檔（已更新）
```

## Prompt 模板結構

### 候選人特定諮詢 Prompt

```json
{
  "candidate_specific": {
    "system_prompt_template": "你是一位資深的人力資源專家...",
    "user_prompt_template": "用戶問題：{query}..."
  }
}
```

**支援 25+ 個變數**，包括：

- 候選人基本資訊（姓名、郵箱、職位等）
- 測驗歷史統計
- 測評數據詳情
- 特質分析結果
- 用戶問題

### 通用 HR 諮詢 Prompt

```json
{
  "general": {
    "system_prompt_template": "你是一位資深的人力資源專家...",
    "user_prompt_template": "用戶問題：{query}..."
  }
}
```

**支援 2 個變數**：

- 用戶問題
- 最大回答長度

## 測試結果

### 測試 1: 環境變數配置測試

```bash
python test_env_config.py
```

- ✅ 通用 HR 諮詢成功 (Status 200)
- ✅ 候選人特定諮詢成功 (Status 200)
- ✅ Prompt 正確載入和使用

### 測試 2: 連續 API 調用測試

```bash
python test_consecutive_calls.py
```

- ✅ 第一次調用成功 (Status 200)
- ✅ 第二次調用成功 (Status 200)
- ✅ 無資料庫連接狀態問題
- ✅ Prompt 在多次調用中保持一致

### 測試 3: 代碼診斷

```bash
getDiagnostics
```

- ✅ `hr_consultation_service.py` - 無錯誤
- ✅ `hr_consultation_routes.py` - 無錯誤
- ✅ `prompt_manager.py` - 無錯誤

## 優勢和好處

### 1. 靈活性

- ✅ 無需修改代碼即可調整 Prompt
- ✅ 支援快速測試不同的 Prompt 版本
- ✅ 可以根據不同場景使用不同的 Prompt

### 2. 可維護性

- ✅ Prompt 集中管理，易於查找和修改
- ✅ 版本控制友好，可追蹤 Prompt 變更歷史
- ✅ 減少代碼重複，提高代碼質量

### 3. 可擴展性

- ✅ 易於添加新的 Prompt 類型
- ✅ 支援多語言 Prompt
- ✅ 可以為不同用戶群體定制 Prompt

### 4. 安全性

- ✅ Prompt 與代碼分離，降低代碼洩露風險
- ✅ 可以對 Prompt 文件進行訪問控制
- ✅ 支援動態載入，無需重啟應用

## 使用方法

### 修改 Prompt

1. 打開 `BackEnd/prompts/hr_consultation_prompts.json`
2. 找到要修改的 Prompt 類型
3. 修改 `system_prompt_template` 或 `user_prompt_template`
4. 保存文件
5. 重啟應用（或調用 `reload_prompts()`）

### 添加新變數

1. 在 Prompt 模板中添加 `{新變數名}`
2. 在調用 `get_hr_candidate_prompts()` 時傳入新變數的值
3. 測試確保變數正確替換

### 動態重新載入

```python
from prompt_manager import get_prompt_manager

prompt_manager = get_prompt_manager()
prompt_manager.reload_prompts()
```

## 最佳實踐

### 1. Prompt 設計

- 使用清晰的角色定位
- 提供具體的回答要求
- 明確列出禁止事項
- 使用結構化格式（標題、列表等）

### 2. 變數命名

- 使用描述性的變數名
- 保持命名一致性
- 避免使用特殊字符

### 3. 測試

- 修改後立即測試
- 測試邊界情況
- 收集用戶反饋

### 4. 版本控制

- 提交時寫清楚修改內容
- 重大修改時創建標籤
- 保留歷史版本以便回滾

## 後續建議

### 1. 多語言支援

- 創建不同語言的 Prompt 文件
- 根據用戶語言自動選擇 Prompt
- 統一管理多語言 Prompt

### 2. A/B 測試

- 創建多個 Prompt 版本
- 隨機分配給不同用戶
- 收集數據分析效果

### 3. Prompt 優化

- 定期分析 LLM 回答質量
- 根據用戶反饋調整 Prompt
- 使用 Prompt Engineering 最佳實踐

### 4. 監控和日誌

- 記錄 Prompt 使用情況
- 監控 Prompt 載入錯誤
- 分析 Prompt 效果指標

## 相關文件

- `BackEnd/prompts/hr_consultation_prompts.json` - Prompt 配置文件
- `BackEnd/prompts/README.md` - Prompt 配置說明
- `BackEnd/prompt_manager.py` - Prompt 管理器
- `BackEnd/README_ENV.md` - 環境變數配置文檔
- `BackEnd/test_env_config.py` - 測試腳本

## 完成時間

2025-12-17

## 測試人員

Kiro AI Assistant

## 總結

成功將所有 LLM Prompt 從代碼遷移到配置文件，實現了：

1. ✅ Prompt 集中管理
2. ✅ 無需修改代碼即可調整 Prompt
3. ✅ 支援動態重新載入
4. ✅ 完整的文檔和測試
5. ✅ 所有功能正常運行

系統現在具有更好的靈活性、可維護性和可擴展性。
