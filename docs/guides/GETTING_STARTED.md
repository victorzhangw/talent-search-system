# 快速開始指南

## 概述

本指南將幫助您快速設置和運行人才管理系統。

## 系統要求

- Python 3.10+
- Node.js 16+
- PostgreSQL 資料庫（遠端或本地）
- SSH 訪問權限（如果使用遠端資料庫）

## 安裝步驟

### 1. 克隆專案

```bash
git clone <repository-url>
cd AI-Character-Chatbot
```

### 2. 後端設置

#### 2.1 安裝 Python 依賴

```bash
cd BackEnd
pip install -r requirements.txt
```

#### 2.2 配置環境變數

複製環境變數範例文件：

```bash
copy .env.example .env.local
```

編輯 `.env.local` 並填入實際值：

```bash
# 資料庫配置
DB_SSH_HOST=your_ssh_host
DB_SSH_PORT=22
DB_SSH_USERNAME=your_ssh_username
DB_SSH_PRIVATE_KEY_FILE=private-key-openssh.pem
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password

# LLM API 配置
LLM_API_KEY=your_llm_api_key
LLM_API_HOST=https://api.siliconflow.cn
LLM_MODEL=deepseek-ai/DeepSeek-V3
LLM_MAX_RESPONSE_LENGTH=150
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

詳細配置說明請參考：[環境變數配置文檔](../configuration/README_ENV.md)

#### 2.3 配置 SSH 金鑰（如果使用遠端資料庫）

將您的 SSH 私鑰放在 `BackEnd/` 目錄下，並命名為 `private-key-openssh.pem`。

### 3. 前端設置

#### 3.1 安裝 Node.js 依賴

```bash
cd frontend
npm install
```

#### 3.2 配置前端環境變數（可選）

如果需要自定義 API 端點，編輯 `frontend/.env`。

### 4. 啟動應用

#### 方法 1: 使用啟動腳本（推薦）

在專案根目錄執行：

```bash
# Windows
START.bat

# Linux/Mac
./start-all-services.sh
```

這將同時啟動後端和前端服務。

#### 方法 2: 分別啟動

**啟動後端：**

```bash
cd BackEnd
python main_api.py
```

後端將在 `http://localhost:8000` 運行。

**啟動前端：**

```bash
cd frontend
npm run dev
```

前端將在 `http://localhost:5173` 運行。

## 驗證安裝

### 1. 檢查後端 API

訪問 `http://localhost:8000/docs` 查看 API 文檔。

### 2. 檢查前端

訪問 `http://localhost:5173` 查看前端界面。

### 3. 運行測試

```bash
cd docs/tests
python test_env_config.py
```

如果所有測試通過，說明系統配置正確。

## 常見問題

### 資料庫連接失敗

**問題**：無法連接到資料庫

**解決方案**：

1. 檢查 SSH 金鑰是否正確
2. 確認資料庫配置是否正確
3. 檢查防火牆設置

### LLM API 調用失敗

**問題**：API 返回 401 或 403 錯誤

**解決方案**：

1. 檢查 `LLM_API_KEY` 是否正確
2. 確認 API Key 是否有效
3. 檢查 API 配額是否用盡

### 前端無法連接後端

**問題**：前端顯示網絡錯誤

**解決方案**：

1. 確認後端是否正在運行
2. 檢查後端端口是否為 8000
3. 檢查 CORS 配置

## 下一步

- [環境變數配置](../configuration/README_ENV.md)
- [Prompt 配置](../configuration/PROMPT_CONFIGURATION.md)
- [API 文檔](http://localhost:8000/docs)
- [部署指南](DEPLOYMENT.md)

## 獲取幫助

如有問題，請查看：

- [常見問題文檔](FAQ.md)
- [故障排除指南](TROUBLESHOOTING.md)
- 或聯繫開發團隊
