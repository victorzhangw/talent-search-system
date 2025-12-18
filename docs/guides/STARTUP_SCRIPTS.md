# 啟動腳本使用指南

## 概述

本專案提供了統一的啟動腳本，可以一鍵啟動前端和後端服務。

## 可用腳本

### Windows

| 腳本名稱                | 用途     | 說明                     |
| ----------------------- | -------- | ------------------------ |
| `start.bat`             | 啟動系統 | 同時啟動前端和後端服務   |
| `stop.bat`              | 停止系統 | 停止所有運行中的服務     |
| `check-environment.bat` | 環境檢查 | 檢查系統環境是否配置正確 |

### Linux/Mac

| 腳本名稱   | 用途     | 說明                   |
| ---------- | -------- | ---------------------- |
| `start.sh` | 啟動系統 | 同時啟動前端和後端服務 |
| `stop.sh`  | 停止系統 | 停止所有運行中的服務   |

## 使用方法

### Windows 用戶

#### 1. 首次使用前檢查環境

```batch
check-environment.bat
```

這將檢查：

- Python 是否安裝
- Node.js 是否安裝
- 環境變數文件是否存在
- 依賴是否安裝
- 配置文件是否完整

#### 2. 啟動系統

雙擊 `start.bat` 或在命令提示符中運行：

```batch
start.bat
```

**啟動流程**：

1. 檢查環境和依賴
2. 自動創建虛擬環境（如果不存在）
3. 自動安裝依賴（如果不存在）
4. 啟動後端 API 服務（端口 8000）
5. 啟動前端開發服務器（端口 5173）
6. 自動打開瀏覽器

**啟動後會看到兩個命令窗口**：

- `人才管理系統 - 後端 API`
- `人才管理系統 - 前端`

#### 3. 停止系統

雙擊 `stop.bat` 或在命令提示符中運行：

```batch
stop.bat
```

這將：

- 停止後端服務（端口 8000）
- 停止前端服務（端口 5173）
- 關閉相關的命令窗口

### Linux/Mac 用戶

#### 1. 設置執行權限（首次使用）

```bash
chmod +x start.sh stop.sh
```

#### 2. 啟動系統

```bash
./start.sh
```

**啟動流程**：

1. 檢查環境和依賴
2. 自動創建虛擬環境（如果不存在）
3. 自動安裝依賴（如果不存在）
4. 啟動後端 API 服務（後台運行）
5. 啟動前端開發服務器（後台運行）
6. 在 Mac 上自動打開瀏覽器

**進程 ID 保存在**：

- `backend.pid` - 後端進程 ID
- `frontend.pid` - 前端進程 ID

**日誌文件**：

- `backend.log` - 後端日誌
- `frontend.log` - 前端日誌

#### 3. 停止系統

```bash
./stop.sh
```

這將：

- 停止後端服務
- 停止前端服務
- 清理 PID 文件

## 訪問地址

啟動成功後，可以訪問：

### 後端 API

- **API 文檔**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/health
- **人才搜索**: http://localhost:8000/api/talent
- **HR 諮詢**: http://localhost:8000/api/hr-consult

### 前端界面

- **主界面**: http://localhost:5173

## 首次啟動

### 必要的準備工作

1. **配置環境變數**

   複製環境變數範例文件：

   ```batch
   # Windows
   copy BackEnd\.env.example BackEnd\.env.local

   # Linux/Mac
   cp BackEnd/.env.example BackEnd/.env.local
   ```

   編輯 `BackEnd/.env.local` 並填入實際值：

   - 資料庫配置
   - LLM API Key
   - 其他必要配置

   詳細配置說明請參考：[環境變數配置文檔](../configuration/README_ENV.md)

2. **準備 SSH 金鑰**（如果使用遠端資料庫）

   將 SSH 私鑰放在 `BackEnd/` 目錄下，命名為 `private-key-openssh.pem`

3. **運行環境檢查**（Windows）

   ```batch
   check-environment.bat
   ```

### 自動安裝依賴

首次運行 `start.bat` 或 `start.sh` 時，腳本會自動：

1. 創建 Python 虛擬環境（如果不存在）
2. 安裝後端依賴（從 `BackEnd/requirements.txt`）
3. 安裝前端依賴（從 `frontend/package.json`）

這個過程可能需要幾分鐘，請耐心等待。

## 常見問題

### Q1: 啟動失敗，提示找不到 Python

**解決方案**：

1. 確認已安裝 Python 3.10+
2. 確認 Python 已添加到系統 PATH
3. 在命令提示符中運行 `python --version` 驗證

### Q2: 啟動失敗，提示找不到 .env.local

**解決方案**：

1. 複製 `BackEnd/.env.example` 為 `BackEnd/.env.local`
2. 編輯 `.env.local` 並填入實際配置
3. 參考 [環境變數配置文檔](../configuration/README_ENV.md)

### Q3: 端口被佔用

**錯誤訊息**：

```
Error: listen EADDRINUSE: address already in use :::8000
```

**解決方案**：

Windows:

```batch
# 查找佔用端口的進程
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# 終止進程
taskkill /PID <PID> /F
```

Linux/Mac:

```bash
# 查找並終止進程
lsof -ti:8000 | xargs kill
lsof -ti:5173 | xargs kill
```

或直接運行停止腳本：

```batch
# Windows
stop.bat

# Linux/Mac
./stop.sh
```

### Q4: 後端啟動失敗

**檢查步驟**：

1. 查看後端窗口的錯誤訊息（Windows）
2. 查看 `backend.log` 文件（Linux/Mac）
3. 檢查環境變數配置是否正確
4. 檢查資料庫連接是否正常
5. 檢查 LLM API Key 是否有效

### Q5: 前端啟動失敗

**檢查步驟**：

1. 查看前端窗口的錯誤訊息（Windows）
2. 查看 `frontend.log` 文件（Linux/Mac）
3. 確認 `node_modules` 已安裝
4. 嘗試手動安裝依賴：
   ```bash
   cd frontend
   npm install
   ```

### Q6: 瀏覽器無法訪問

**檢查步驟**：

1. 確認服務已啟動（查看命令窗口或日誌）
2. 檢查防火牆設置
3. 嘗試訪問 http://localhost:8000/health 檢查後端
4. 嘗試訪問 http://localhost:5173 檢查前端

## 手動啟動（進階）

如果自動啟動腳本遇到問題，可以手動啟動：

### 手動啟動後端

Windows:

```batch
cd BackEnd
venv\Scripts\activate
python main_api.py
```

Linux/Mac:

```bash
cd BackEnd
source venv/bin/activate
python main_api.py
```

### 手動啟動前端

```bash
cd frontend
npm run dev
```

## 開發模式 vs 生產模式

### 開發模式（當前腳本）

- 前端使用 Vite 開發服務器
- 支援熱重載
- 顯示詳細錯誤訊息
- 適合開發和調試

### 生產模式

生產環境部署請參考：[部署指南](DEPLOYMENT.md)

## 日誌和調試

### Windows

- 後端日誌：查看後端命令窗口
- 前端日誌：查看前端命令窗口

### Linux/Mac

- 後端日誌：`tail -f backend.log`
- 前端日誌：`tail -f frontend.log`

### 查看實時日誌

Linux/Mac:

```bash
# 同時查看兩個日誌
tail -f backend.log frontend.log
```

## 腳本工作原理

### start.bat / start.sh

1. **環境檢查**

   - 檢查 Python 和 Node.js 是否安裝
   - 檢查環境變數文件是否存在
   - 檢查依賴是否安裝

2. **依賴安裝**（如果需要）

   - 創建 Python 虛擬環境
   - 安裝後端依賴
   - 安裝前端依賴

3. **啟動服務**

   - 啟動後端 API（新窗口或後台）
   - 等待後端啟動完成
   - 啟動前端開發服務器（新窗口或後台）
   - 等待前端啟動完成

4. **打開瀏覽器**
   - 自動打開前端界面

### stop.bat / stop.sh

1. **查找進程**

   - 通過端口號查找後端進程（8000）
   - 通過端口號查找前端進程（5173）

2. **終止進程**

   - 終止後端進程
   - 終止前端進程
   - 關閉相關命令窗口（Windows）

3. **清理**
   - 刪除 PID 文件（Linux/Mac）

## 自定義配置

### 修改端口

如果需要修改默認端口：

1. **後端端口**（默認 8000）

   編輯 `BackEnd/.env.local`：

   ```
   PORT=8001
   ```

2. **前端端口**（默認 5173）

   編輯 `frontend/vite.config.js`：

   ```javascript
   export default defineConfig({
     server: {
       port: 5174,
     },
   });
   ```

3. **更新啟動腳本**

   修改 `start.bat` 或 `start.sh` 中的端口檢查和顯示

## 相關資源

- [快速開始指南](GETTING_STARTED.md)
- [環境變數配置](../configuration/README_ENV.md)
- [部署指南](DEPLOYMENT.md)
- [故障排除](TROUBLESHOOTING.md)

## 獲取幫助

如果遇到問題：

1. 運行 `check-environment.bat`（Windows）檢查環境
2. 查看 [故障排除指南](TROUBLESHOOTING.md)
3. 查看日誌文件
4. 聯繫開發團隊
