# 🚀 Render 手動部署指南（不使用 Blueprint）

## 概述

本指南將教你如何在 Render 上手動創建和部署服務，不使用 Blueprint 功能。

## 前置準備

### 1. 準備 GitHub Repository

```bash
# 初始化 Git（如果還沒有）
git init
git add .
git commit -m "Ready for deployment"

# 推送到 GitHub
git remote add origin https://github.com/你的用戶名/你的repo名稱.git
git push -u origin main
```

### 2. 準備環境變數

準備以下資訊（稍後會用到）：

| 變數名稱             | 說明         | 範例值              |
| -------------------- | ------------ | ------------------- |
| `DB_SSH_HOST`        | SSH 主機地址 | `54.199.255.239`    |
| `DB_SSH_USERNAME`    | SSH 用戶名   | `victor_cheng`      |
| `DB_SSH_PRIVATE_KEY` | SSH 私鑰內容 | 完整的 PEM 文件內容 |
| `DB_NAME`            | 數據庫名稱   | `projectdb`         |
| `DB_USER`            | 數據庫用戶   | `projectuser`       |
| `DB_PASSWORD`        | 數據庫密碼   | 你的密碼            |
| `LLM_API_KEY`        | LLM API 密鑰 | `sk-xxx...`         |

#### 如何獲取 SSH 私鑰內容：

**Windows (PowerShell)**:

```powershell
Get-Content BackEnd\private-key-openssh.pem
```

**Windows (CMD)**:

```cmd
type BackEnd\private-key-openssh.pem
```

複製完整內容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）

---

## 部署步驟

### 步驟 1: 登入 Render

1. 訪問 https://render.com
2. 使用 GitHub 帳號登入
3. 授權 Render 訪問你的 repositories

### 步驟 2: 創建後端 API 服務

#### 2.1 創建新服務

1. 在 Render Dashboard，點擊 **"New +"** 按鈕
2. 選擇 **"Web Service"**
3. 選擇你的 GitHub repository

#### 2.2 基本設定

填寫以下資訊：

| 欄位               | 值                                        |
| ------------------ | ----------------------------------------- |
| **Name**           | `talent-search-api`（或你喜歡的名稱）     |
| **Region**         | `Singapore (Southeast Asia)` 或最近的區域 |
| **Branch**         | `main`                                    |
| **Root Directory** | 留空                                      |
| **Runtime**        | `Python 3`                                |
| **Build Command**  | `pip install -r BackEnd/requirements.txt` |
| **Start Command**  | `cd BackEnd && python start_fixed_api.py` |

#### 2.3 設定環境變數

在 **Environment Variables** 區域，點擊 **"Add Environment Variable"**，逐一添加：

**基本配置：**

```
PYTHON_VERSION = 3.10.0
```

**數據庫 SSH 配置：**

```
DB_SSH_HOST = 54.199.255.239
DB_SSH_PORT = 22
DB_SSH_USERNAME = victor_cheng
DB_SSH_PRIVATE_KEY = [貼上完整的 SSH 私鑰內容]
```

**數據庫配置：**

```
DB_HOST = localhost
DB_PORT = 5432
DB_NAME = projectdb
DB_USER = projectuser
DB_PASSWORD = [你的數據庫密碼]
```

**LLM API 配置：**

```
LLM_API_KEY = [你的 LLM API 密鑰]
LLM_API_HOST = https://api.siliconflow.cn
LLM_MODEL = deepseek-ai/DeepSeek-V3
```

#### 2.4 選擇方案

- 選擇 **"Free"** 方案（每月 750 小時免費）

#### 2.5 高級設定（可選）

展開 **"Advanced"** 區域：

- **Health Check Path**: `/health`
- **Auto-Deploy**: `Yes`（啟用自動部署）

#### 2.6 創建服務

1. 點擊 **"Create Web Service"** 按鈕
2. Render 會開始構建和部署
3. 等待 5-10 分鐘

### 步驟 3: 驗證後端部署

#### 3.1 檢查部署狀態

在服務頁面，查看：

- **Status** 應該顯示 `Live`（綠色）
- **Logs** 應該顯示服務啟動成功

#### 3.2 測試 API

訪問你的服務 URL（例如：`https://talent-search-api.onrender.com/health`）

應該看到：

```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 步驟 4: 創建前端服務（可選）

如果你有前端需要部署：

#### 4.1 創建新服務

1. 點擊 **"New +"** → **"Static Site"**
2. 選擇同一個 GitHub repository

#### 4.2 基本設定

| 欄位                  | 值                             |
| --------------------- | ------------------------------ |
| **Name**              | `talent-search-frontend`       |
| **Branch**            | `main`                         |
| **Root Directory**    | `frontend`                     |
| **Build Command**     | `npm install && npm run build` |
| **Publish Directory** | `dist`                         |

#### 4.3 設定環境變數

```
VITE_API_URL = https://talent-search-api.onrender.com
```

（將 URL 替換為你的後端服務 URL）

#### 4.4 創建服務

點擊 **"Create Static Site"**

---

## 部署後管理

### 查看日誌

1. 進入服務頁面
2. 點擊 **"Logs"** 標籤
3. 查看實時日誌輸出

### 更新環境變數

1. 進入服務頁面
2. 點擊 **"Environment"** 標籤
3. 修改或添加變數
4. 點擊 **"Save Changes"**
5. 服務會自動重新部署

### 手動重新部署

1. 進入服務頁面
2. 點擊右上角的 **"Manual Deploy"** 按鈕
3. 選擇 **"Deploy latest commit"**

### 暫停服務

1. 進入服務頁面
2. 點擊 **"Settings"** 標籤
3. 滾動到底部
4. 點擊 **"Suspend Service"**

---

## 免費方案限制與解決方案

### 限制

1. **服務休眠**

   - 閒置 15 分鐘後自動休眠
   - 首次喚醒需要 30-60 秒

2. **運行時間**
   - 每月 750 小時免費
   - 足夠單個服務全天候運行

### 解決方案：保持服務活躍

使用 **UptimeRobot** 免費監控服務：

#### 設定步驟：

1. 訪問 https://uptimerobot.com 並註冊
2. 點擊 **"Add New Monitor"**
3. 填寫資訊：
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `Talent Search API`
   - **URL**: `https://talent-search-api.onrender.com/health`
   - **Monitoring Interval**: `5 minutes`
4. 點擊 **"Create Monitor"**

這樣服務每 5 分鐘會被 ping 一次，不會休眠。

---

## 自動部署設定

### 啟用自動部署

1. 進入服務頁面
2. 點擊 **"Settings"** 標籤
3. 找到 **"Auto-Deploy"** 區域
4. 選擇 **"Yes"**
5. 點擊 **"Save Changes"**

### 工作流程

設定完成後：

- 每次推送到 GitHub `main` 分支
- Render 會自動檢測變更
- 自動重新構建和部署
- 無需手動操作

---

## 常見問題排查

### 1. 部署失敗

**檢查項目：**

- 查看 **Logs** 標籤的錯誤訊息
- 確認 Build Command 正確
- 確認 requirements.txt 存在且正確

**解決方法：**

```bash
# 本地測試構建命令
pip install -r BackEnd/requirements.txt
```

### 2. 數據庫連接失敗

**檢查項目：**

- SSH 私鑰是否完整複製（包括開頭和結尾）
- SSH 主機是否可以從外部訪問
- 數據庫用戶名和密碼是否正確

**測試方法：**
查看日誌中的錯誤訊息，通常會顯示具體的連接問題。

### 3. 服務啟動後立即崩潰

**檢查項目：**

- Start Command 是否正確
- 端口設定（Render 會自動設定 PORT 環境變數）
- Python 版本是否匹配

**解決方法：**
確保你的應用監聽 `0.0.0.0` 和環境變數 `PORT`：

```python
import os
port = int(os.getenv('PORT', 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

### 4. Health Check 失敗

**檢查項目：**

- `/health` 端點是否存在
- 端點是否返回 200 狀態碼

**解決方法：**
在服務設定中暫時禁用 Health Check，或確保端點正確實現。

### 5. 環境變數未生效

**檢查項目：**

- 變數名稱是否正確（區分大小寫）
- 是否點擊了 "Save Changes"
- 服務是否重新部署

**解決方法：**
修改環境變數後，手動觸發重新部署。

---

## 監控與維護

### 查看服務狀態

在 Render Dashboard：

- **綠色圓點**：服務正常運行
- **黃色圓點**：服務正在部署
- **紅色圓點**：服務出現問題

### 查看資源使用

1. 進入服務頁面
2. 點擊 **"Metrics"** 標籤
3. 查看：
   - CPU 使用率
   - 記憶體使用率
   - 請求數量
   - 響應時間

### 設定告警（付費功能）

如果升級到付費方案，可以設定：

- 服務下線告警
- 高 CPU 使用率告警
- 高記憶體使用率告警

---

## 成本估算

### 免費方案

- **Web Service**: 750 小時/月（約 31 天）
- **Static Site**: 100 GB 流量/月
- **適合**: 個人項目、測試環境

### 付費方案

如果需要更多資源：

| 方案         | 價格   | 特點                 |
| ------------ | ------ | -------------------- |
| **Starter**  | $7/月  | 不休眠、更多資源     |
| **Standard** | $25/月 | 更高性能、優先支援   |
| **Pro**      | $85/月 | 專業級性能、SLA 保證 |

---

## 下一步

### 部署成功後

1. ✅ 測試所有 API 端點
2. ✅ 設定 UptimeRobot 監控
3. ✅ 配置自定義域名（可選）
4. ✅ 設定 HTTPS（Render 自動提供）

### 進階配置

- **自定義域名**: 在 Settings → Custom Domain 添加
- **環境隔離**: 創建 staging 和 production 環境
- **CI/CD**: 整合 GitHub Actions 進行測試

---

## 獲取幫助

- **Render 文檔**: https://render.com/docs
- **Render 社群**: https://community.render.com
- **GitHub Issues**: 在你的 repository 創建 issue

---

## 總結

使用手動部署方式的優點：

✅ **完全控制**: 清楚每個設定的作用
✅ **靈活性**: 可以隨時調整配置
✅ **學習機會**: 理解部署流程
✅ **易於調試**: 問題更容易定位

相比 Blueprint：

- 需要手動設定每個服務
- 但更容易理解和維護
- 適合學習和小型專案

**恭喜！你已經成功在 Render 上手動部署服務！** 🎉
