# 日誌系統配置完成

## 更新日期

2025-12-17

## 概述

為系統配置了完整的日誌記錄系統，日誌同時輸出到控制台和文件，支持自動輪轉和分類管理。

## 日誌存放位置

### 主目錄

```
BackEnd/logs/
```

### 日誌文件列表

| 文件名                | 說明             | 級別   | 大小限制 |
| --------------------- | ---------------- | ------ | -------- |
| `main.log`            | 主日誌文件       | DEBUG+ | 10MB     |
| `llm_api.log`         | LLM API 專用日誌 | DEBUG+ | 10MB     |
| `hr_consultation.log` | HR 諮詢日誌      | DEBUG+ | 10MB     |
| `talent_search.log`   | 人才搜索日誌     | DEBUG+ | 10MB     |
| `interview.log`       | 面試日誌         | DEBUG+ | 10MB     |
| `error.log`           | 錯誤日誌         | ERROR+ | 10MB     |

## 新增文件

### 1. `BackEnd/logging_config.py`

統一的日誌配置模組

**功能**:

- ✅ 自動創建日誌目錄
- ✅ 配置多個日誌處理器（控制台 + 文件）
- ✅ 日誌輪轉（10MB，保留 5 個備份）
- ✅ 分類日誌（主日誌、LLM API、錯誤等）
- ✅ 統一的日誌格式
- ✅ 環境變數配置日誌級別

**主要函數**:

```python
setup_logging()  # 初始化日誌系統
get_logger(name)  # 獲取 logger 實例
get_log_files_info()  # 獲取日誌文件信息
```

### 2. `BackEnd/logs/README.md`

日誌目錄說明文檔

**內容**:

- 日誌文件說明
- 日誌級別說明
- 日誌格式說明
- 查看和分析日誌的方法
- 故障排查指南

## 更新的文件

### 1. `BackEnd/main_api.py`

**變更**:

```python
# 舊代碼
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 新代碼
from logging_config import setup_logging, get_logger, get_log_files_info
setup_logging()
logger = get_logger(__name__)
```

**新增 API 端點**:

```
GET /logs/info
```

返回所有日誌文件的信息（路徑、大小、修改時間等）。

## 日誌輸出位置

### 1. 控制台輸出

- **級別**: INFO 及以上（可通過 `LOG_LEVEL` 環境變數調整）
- **用途**: 實時監控系統運行狀態
- **格式**: 彩色輸出（如果終端支持）

### 2. 文件輸出

#### 主日誌文件 (`main.log`)

- **級別**: DEBUG 及以上
- **內容**: 所有模組的日誌
- **用途**: 完整的系統運行記錄

#### LLM API 日誌 (`llm_api.log`)

- **級別**: DEBUG 及以上
- **內容**: 所有 LLM API 調用的詳細信息
- **包含模組**:
  - `hr_consultation_service`
  - `hr_consultation_routes`
  - `talent_search_api`
  - `interview_api`

#### 錯誤日誌 (`error.log`)

- **級別**: ERROR 及以上
- **內容**: 所有錯誤和嚴重錯誤
- **用途**: 快速定位問題

## 日誌格式

### 標準格式

```
2025-12-17 10:30:45 - module_name - INFO - 日誌消息
```

### LLM API 調用格式

```
================================================================================
🚀 開始調用 LLM API（功能描述）
📍 API 端點: https://api.example.com/v1/chat/completions
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
✅ 調用完成
================================================================================
```

## 配置選項

### 環境變數

#### `LOG_LEVEL`

設置日誌級別（控制台輸出）

**可選值**:

- `DEBUG`: 最詳細，包含所有調試信息
- `INFO`: 一般信息（默認）
- `WARNING`: 僅警告和錯誤
- `ERROR`: 僅錯誤
- `CRITICAL`: 僅嚴重錯誤

**設置方法**:

```bash
# Windows
set LOG_LEVEL=DEBUG

# Linux/Mac
export LOG_LEVEL=DEBUG

# .env 文件
LOG_LEVEL=DEBUG
```

## 使用方法

### 1. 在代碼中使用

```python
from logging_config import get_logger

logger = get_logger(__name__)

# 記錄不同級別的日誌
logger.debug("調試信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("錯誤信息")
logger.critical("嚴重錯誤")
```

### 2. 查看日誌

#### 方法 A: 直接查看文件

```bash
# Windows
type BackEnd\logs\main.log

# Linux/Mac
cat BackEnd/logs/main.log
tail -f BackEnd/logs/main.log  # 實時監控
```

#### 方法 B: 使用 API

```bash
curl http://localhost:8000/logs/info
```

### 3. 搜索日誌

```bash
# 搜索錯誤
grep "ERROR" BackEnd/logs/main.log

# 搜索 LLM API 調用
grep "🚀 開始調用 LLM API" BackEnd/logs/llm_api.log

# 搜索特定時間
grep "2025-12-17 10:" BackEnd/logs/main.log
```

## 日誌輪轉

### 自動輪轉規則

- **觸發條件**: 文件大小達到 10MB
- **保留數量**: 5 個備份文件
- **命名規則**: `文件名.log.1`, `文件名.log.2`, ...

### 示例

```
main.log          # 當前日誌（最新）
main.log.1        # 第 1 個備份
main.log.2        # 第 2 個備份
main.log.3        # 第 3 個備份
main.log.4        # 第 4 個備份
main.log.5        # 第 5 個備份（最舊）
```

當 `main.log` 達到 10MB 時：

1. `main.log.5` 被刪除
2. `main.log.4` → `main.log.5`
3. `main.log.3` → `main.log.4`
4. `main.log.2` → `main.log.3`
5. `main.log.1` → `main.log.2`
6. `main.log` → `main.log.1`
7. 創建新的 `main.log`

## 監控和分析

### 1. 實時監控

```bash
# Linux/Mac
tail -f BackEnd/logs/main.log

# Windows PowerShell
Get-Content BackEnd\logs\main.log -Wait -Tail 50
```

### 2. 統計分析

```bash
# 統計錯誤數量
grep -c "ERROR" BackEnd/logs/error.log

# 統計 API 調用次數
grep -c "🚀 開始調用 LLM API" BackEnd/logs/llm_api.log

# 統計 Token 使用量
grep "Total Tokens:" BackEnd/logs/llm_api.log | awk '{sum+=$NF} END {print sum}'
```

### 3. 使用 API 查詢

```python
import requests

response = requests.get('http://localhost:8000/logs/info')
logs_info = response.json()

for name, info in logs_info['logs'].items():
    if info['exists']:
        print(f"{name}: {info['size_mb']}")
```

## 安全考慮

### 1. 敏感信息保護

- ✅ API Key 在日誌中部分隱藏
- ✅ 不記錄用戶密碼
- ✅ 不記錄完整的個人隱私數據

### 2. 文件權限

- 日誌文件僅應用程序可寫
- 建議設置適當的文件權限

### 3. Git 排除

- 日誌文件已在 `.gitignore` 中排除
- 不會被提交到版本控制

## 故障排查

### 問題 1: 日誌文件未生成

**可能原因**:

- 目錄權限不足
- 磁盤空間不足
- 配置未正確初始化

**解決方法**:

1. 檢查 `BackEnd/logs/` 目錄是否存在
2. 檢查磁盤空間
3. 查看控制台錯誤信息

### 問題 2: 日誌文件過大

**可能原因**:

- 日誌級別設置為 DEBUG
- 輪轉配置未生效

**解決方法**:

1. 設置 `LOG_LEVEL=INFO`
2. 檢查輪轉配置
3. 手動清理舊日誌

### 問題 3: 找不到特定日誌

**可能原因**:

- 日誌級別過高
- 模組名稱不正確

**解決方法**:

1. 降低日誌級別
2. 查看 `main.log` 中的所有日誌
3. 檢查模組配置

## 性能影響

### 日誌級別對性能的影響

| 級別    | 日誌量 | 性能影響 | 建議使用場景     |
| ------- | ------ | -------- | ---------------- |
| DEBUG   | 非常多 | 較大     | 開發和調試       |
| INFO    | 適中   | 較小     | 生產環境（默認） |
| WARNING | 較少   | 很小     | 穩定的生產環境   |
| ERROR   | 很少   | 極小     | 僅關注錯誤       |

### 優化建議

1. 生產環境使用 INFO 或 WARNING 級別
2. 定期清理舊日誌文件
3. 考慮使用專業日誌管理工具

## 未來改進

### 短期

- [ ] 添加日誌查看 Web 界面
- [ ] 支持日誌搜索 API
- [ ] 添加日誌統計儀表板

### 長期

- [ ] 整合 ELK Stack（Elasticsearch, Logstash, Kibana）
- [ ] 配置日誌告警規則
- [ ] 實現日誌中央化管理
- [ ] 添加日誌分析和可視化

## 相關文檔

- `BackEnd/logs/README.md` - 日誌目錄說明
- `docs/LLM_API_LOGGING_ENHANCEMENT.md` - LLM API 日誌詳細文檔
- `docs/LLM_LOGGING_SUMMARY.md` - LLM 日誌快速總結

## 總結

✅ 日誌系統已完整配置
✅ 支持控制台和文件雙輸出
✅ 自動輪轉和分類管理
✅ 詳細的 LLM API 調用記錄
✅ 提供 API 查詢接口
✅ 完整的文檔和使用指南

日誌文件位置：`BackEnd/logs/`
