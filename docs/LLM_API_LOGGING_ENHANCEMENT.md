# LLM API 調用日誌增強

## 更新日期

2025-12-17

## 更新概述

為所有 LLM API 調用添加詳細的日誌記錄，便於監控、調試和性能分析。

## 更新的文件

### 1. HR 諮詢服務 (`BackEnd/hr_consultation_service.py`)

**功能**: 候選人特定 HR 諮詢

#### 新增日誌內容

- ✅ API 端點和模型信息
- ✅ 請求參數（Temperature, Max Tokens）
- ✅ Prompt 長度統計
- ✅ 請求時間戳
- ✅ API 響應時間
- ✅ HTTP 狀態碼
- ✅ Token 使用統計（Prompt/Completion/Total）
- ✅ 原始回答長度
- ✅ 完成原因（finish_reason）
- ✅ 截斷後長度
- ✅ 錯誤詳情（如果失敗）

#### 日誌示例

```
================================================================================
🚀 開始調用 LLM API
📍 API 端點: https://api.siliconflow.cn/v1/chat/completions
🤖 模型: deepseek-ai/DeepSeek-V3
🌡️ Temperature: 0.7
📊 Max Tokens: 500
📝 System Prompt 長度: 1234 字符
📝 User Prompt 長度: 567 字符
⏰ 請求時間: 2025-12-17T10:30:45.123456
⏱️ API 響應時間: 2.34 秒
📡 HTTP 狀態碼: 200
✅ API 調用成功
📊 Token 使用統計:
   - Prompt Tokens: 1500
   - Completion Tokens: 300
   - Total Tokens: 1800
💬 原始回答長度: 450 字符
🏁 完成原因: stop
✂️ 截斷後長度: 450 字符 (限制: 500)
✅ LLM 回答生成成功
================================================================================
```

### 2. HR 諮詢路由 (`BackEnd/hr_consultation_routes.py`)

**功能**: 通用 HR 諮詢（無候選人）

#### 新增日誌內容

- ✅ API 端點和模型信息
- ✅ 請求參數
- ✅ 用戶問題
- ✅ Prompt 長度統計
- ✅ 請求時間戳
- ✅ API 響應時間
- ✅ HTTP 狀態碼
- ✅ Token 使用統計
- ✅ 原始回答長度
- ✅ 截斷信息
- ✅ 錯誤詳情

#### 日誌示例

```
================================================================================
🚀 開始調用 LLM API（通用 HR 諮詢）
📍 API 端點: https://api.siliconflow.cn/v1/chat/completions
🤖 模型: deepseek-ai/DeepSeek-V3
🌡️ Temperature: 0.7
📊 Max Tokens: 500
📝 System Prompt 長度: 800 字符
📝 User Prompt 長度: 200 字符
❓ 用戶問題: 如何提升團隊協作能力？
⏰ 請求時間: 2025-12-17T10:31:00.000000
⏱️ API 響應時間: 1.89 秒
📡 HTTP 狀態碼: 200
✅ API 調用成功
📊 Token 使用統計:
   - Prompt Tokens: 1000
   - Completion Tokens: 250
   - Total Tokens: 1250
💬 原始回答長度: 380 字符
✅ 通用 HR 諮詢完成
================================================================================
```

### 3. 人才搜索 API (`BackEnd/talent_search_api.py`)

**功能**: 查詢分析和人才匹配

#### 新增日誌內容

- ✅ API 端點和模型信息
- ✅ 用戶查詢內容
- ✅ 請求參數
- ✅ Prompt 長度統計
- ✅ Response Format 配置
- ✅ 請求時間戳
- ✅ API 響應時間
- ✅ HTTP 狀態碼
- ✅ Token 使用統計
- ✅ 原始返回內容（完整）
- ✅ 字符 repr（用於調試）
- ✅ JSON 解析結果

#### 日誌示例

```
================================================================================
🚀 開始調用 LLM API（人才搜索 - 查詢分析）
📍 API 端點: https://api.siliconflow.cn/v1/chat/completions
🤖 模型: deepseek-ai/DeepSeek-V3
❓ 用戶查詢: 尋找有領導力的產品經理
⏰ 請求時間: 2025-12-17T10:32:00.000000
🌡️ Temperature: 0.3
📊 Max Tokens: 3000
📝 System Prompt 長度: 2000 字符
📝 User Prompt 長度: 150 字符
   ✅ 使用 response_format: json_object
⏱️ API 響應時間: 3.45 秒
📡 HTTP 狀態碼: 200
📊 Token 使用統計:
   - Prompt Tokens: 2100
   - Completion Tokens: 800
   - Total Tokens: 2900

================================================================================
📥 LLM 原始返回內容
================================================================================
內容長度: 1234 字符

--- 開始完整內容 ---
{"traits": [...], "weights": {...}}
--- 結束完整內容 ---

前 100 字符的 repr:
'{"traits": ["leadership", "product_management"], "weights": {"leadership": 0.9, "product_management": 0.8}}'

================================================================================
✅ JSON 解析成功
🤖 LLM 分析結果:
...
```

### 4. 面試 API (`BackEnd/interview_api.py`)

**功能**: 面試問題生成

#### 新增日誌內容

- ✅ API 端點和模型信息
- ✅ 重試次數信息
- ✅ 請求參數
- ✅ 消息數量和大小
- ✅ 消息內容摘要
- ✅ 請求時間戳
- ✅ API 響應時間
- ✅ HTTP 狀態碼
- ✅ Token 使用統計
- ✅ 生成的問題長度
- ✅ 重試和錯誤詳情

#### 日誌示例

```
================================================================================
🚀 開始調用 LLM API（面試問題生成 - 第 1/3 次）
📍 API 端點: https://api.akashml.com/v1/chat/completions
🤖 模型: deepseek-ai/DeepSeek-V3.1
⏰ 請求時間: 2025-12-17T10:33:00.000000
🌡️ Temperature: 0.7
📊 Max Tokens: 2000
💬 消息數量: 3
📝 請求資料大小: 5678 字元
   消息 1: system (1200 字符)
   消息 2: user (300 字符)
   消息 3: assistant (150 字符)
⏱️ API 響應時間: 4.56 秒
📡 HTTP 狀態碼: 200
📊 Token 使用統計:
   - Prompt Tokens: 1800
   - Completion Tokens: 600
   - Total Tokens: 2400
💬 生成的問題長度: 1234 字符
✅ 面試問題生成成功
================================================================================
```

## 日誌級別說明

### 信息級別（INFO）

- 🚀 API 調用開始
- ✅ API 調用成功
- 📊 統計信息
- 💬 內容長度
- ⏱️ 響應時間

### 警告級別（WARNING）

- ⚠️ 重試通知
- ⚠️ 配置提示

### 錯誤級別（ERROR）

- ❌ API 錯誤
- ❌ 解析失敗
- ❌ 連線錯誤

## 日誌格式統一

所有 LLM API 調用日誌都使用統一的格式：

```
================================================================================
🚀 開始調用 LLM API（功能描述）
[詳細信息]
⏱️ API 響應時間: X.XX 秒
📡 HTTP 狀態碼: XXX
[響應詳情]
✅ 調用成功/❌ 調用失敗
================================================================================
```

## 日誌用途

### 1. 性能監控

- 追蹤 API 響應時間
- 監控 Token 使用量
- 識別性能瓶頸

### 2. 成本分析

- 統計 Token 消耗
- 計算 API 調用成本
- 優化 Prompt 長度

### 3. 調試支持

- 查看完整請求/響應
- 追蹤錯誤原因
- 驗證 Prompt 內容

### 4. 質量保證

- 檢查回答長度
- 驗證 JSON 格式
- 監控完成原因

## 安全考慮

### API Key 保護

在日誌中，API Key 會被部分隱藏：

```python
'Authorization': f'Bearer {api_key[:10]}...{api_key[-4:]}'
```

示例：`Bearer sk-abc123...xyz9`

### 敏感信息

- ❌ 不記錄完整 API Key
- ❌ 不記錄用戶個人隱私數據
- ✅ 記錄數據長度和統計信息
- ✅ 記錄錯誤類型和狀態碼

## 配置建議

### 生產環境

```python
# 設置日誌級別
logging.basicConfig(level=logging.INFO)

# 或使用環境變數
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

### 開發環境

```python
# 更詳細的日誌
logging.basicConfig(level=logging.DEBUG)
```

### 日誌輪轉

建議配置日誌輪轉以避免日誌文件過大：

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'llm_api.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## 監控指標

基於這些日誌，可以監控以下指標：

1. **API 調用次數**: 每小時/每天的調用量
2. **平均響應時間**: 識別性能問題
3. **Token 使用量**: 成本控制
4. **錯誤率**: 服務穩定性
5. **重試次數**: API 可靠性

## 日誌分析工具

推薦使用以下工具分析日誌：

1. **ELK Stack** (Elasticsearch, Logstash, Kibana)
2. **Grafana + Loki**
3. **CloudWatch** (AWS)
4. **Application Insights** (Azure)

## 相關文件

- `BackEnd/hr_consultation_service.py` - HR 諮詢服務
- `BackEnd/hr_consultation_routes.py` - HR 諮詢路由
- `BackEnd/talent_search_api.py` - 人才搜索 API
- `BackEnd/interview_api.py` - 面試 API

## 測試驗證

### 驗證步驟

1. 啟動後端服務
2. 調用各個 API 端點
3. 檢查控制台輸出
4. 驗證日誌格式和內容

### 預期結果

- ✅ 所有 API 調用都有完整日誌
- ✅ 日誌格式統一
- ✅ 包含所有關鍵信息
- ✅ 錯誤信息清晰
- ✅ 無診斷錯誤

## 總結

通過這次更新，所有 LLM API 調用都有了詳細的日誌記錄，包括：

- 📊 完整的請求/響應信息
- ⏱️ 性能指標
- 💰 成本統計
- 🐛 調試信息
- 🔒 安全保護

這將大大提升系統的可觀測性和可維護性。
