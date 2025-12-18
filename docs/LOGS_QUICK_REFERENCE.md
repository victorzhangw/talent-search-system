# 日誌系統 - 快速參考

## 📁 日誌位置

```
BackEnd/logs/
```

## 📄 日誌文件

| 文件          | 內容         |
| ------------- | ------------ |
| `main.log`    | 所有日誌     |
| `llm_api.log` | LLM API 調用 |
| `error.log`   | 僅錯誤       |

## 🔍 快速查看

### Windows

```cmd
type BackEnd\logs\main.log
type BackEnd\logs\llm_api.log
type BackEnd\logs\error.log
```

### Linux/Mac

```bash
cat BackEnd/logs/main.log
tail -f BackEnd/logs/main.log  # 實時監控
```

## 🔎 搜索日誌

```bash
# 搜索錯誤
grep "ERROR" BackEnd/logs/main.log

# 搜索 LLM API 調用
grep "🚀 開始調用 LLM API" BackEnd/logs/llm_api.log

# 搜索今天的日誌
grep "2025-12-17" BackEnd/logs/main.log
```

## 🌐 API 查詢

```
GET http://localhost:8000/logs/info
```

返回所有日誌文件的信息（大小、修改時間等）。

## ⚙️ 配置日誌級別

### 環境變數

```bash
# Windows
set LOG_LEVEL=DEBUG

# Linux/Mac
export LOG_LEVEL=DEBUG
```

### 可選值

- `DEBUG` - 最詳細
- `INFO` - 一般信息（默認）
- `WARNING` - 僅警告
- `ERROR` - 僅錯誤

## 🧹 清理日誌

```bash
# 刪除所有日誌
rm BackEnd/logs/*.log*

# 僅刪除備份
rm BackEnd/logs/*.log.[1-9]
```

## 📊 統計

```bash
# 錯誤數量
grep -c "ERROR" BackEnd/logs/error.log

# API 調用次數
grep -c "🚀 開始調用 LLM API" BackEnd/logs/llm_api.log
```

## 📚 詳細文檔

- `BackEnd/logs/README.md` - 日誌目錄說明
- `docs/LOG_SYSTEM_SETUP.md` - 完整配置文檔
- `docs/LLM_API_LOGGING_ENHANCEMENT.md` - LLM API 日誌文檔
