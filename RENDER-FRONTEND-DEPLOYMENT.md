# Render 前端部署指南

## 🎯 在 Render 部署 Vue 3 前端

Render 支援靜態網站（Static Site），完全免費且自動 HTTPS。

---

## 📋 部署步驟

### 方法 1：使用 Render Dashboard（推薦）

#### 1. 登入 Render

- 前往 https://render.com
- 使用 GitHub/Bitbucket 帳號登入

#### 2. 創建新的 Static Site

- 點擊 "New +" 按鈕
- 選擇 "Static Site"

#### 3. 連接 Repository

- 選擇你的 Git repository
- 如果是第一次，需要授權 Render 訪問你的 repo

#### 4. 配置專案

填寫以下資訊：

| 欄位                  | 值                             |
| --------------------- | ------------------------------ |
| **Name**              | `talent-search-frontend`       |
| **Root Directory**    | `frontend`                     |
| **Build Command**     | `npm install && npm run build` |
| **Publish Directory** | `dist`                         |
| **Branch**            | `main`                         |

#### 5. 設定環境變數

點擊 "Advanced" 展開進階設定，新增環境變數：

| Key                 | Value                               |
| ------------------- | ----------------------------------- |
| `NODE_VERSION`      | `18`                                |
| `VITE_API_BASE_URL` | `https://your-backend.onrender.com` |

**重要：** 將 `your-backend` 替換為你的後端服務名稱！

#### 6. 創建 Static Site

- 點擊 "Create Static Site"
- 等待 3-5 分鐘建置完成
- 完成後會得到一個 URL：`https://talent-search-frontend.onrender.com`

---

### 方法 2：使用 render.yaml（自動化）

如果你的 repo 根目錄有 `render.yaml`，Render 會自動偵測並配置。

#### 1. 創建完整的 render.yaml

在專案根目錄創建或更新 `render.yaml`：

```yaml
services:
  # 後端 API
  - type: web
    name: talent-search-backend
    env: python
    region: singapore
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: cd BackEnd && python start_fixed_api.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DB_SSH_HOST
        sync: false
      - key: DB_SSH_USERNAME
        sync: false
      - key: DB_SSH_PRIVATE_KEY
        sync: false
      - key: DB_NAME
        sync: false
      - key: DB_USER
        sync: false
      - key: DB_PASSWORD
        sync: false

  # 前端靜態網站
  - type: web
    name: talent-search-frontend
    env: static
    buildCommand: cd frontend && npm install && npm run build
    staticPublishPath: ./frontend/dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: NODE_VERSION
        value: 18
      - key: VITE_API_BASE_URL
        value: https://talent-search-backend.onrender.com
```

#### 2. 部署

- Push 到 Git
- Render 會自動偵測並部署兩個服務

---

## 🔧 配置詳解

### 環境變數說明

#### 必需的環境變數：

1. **VITE_API_BASE_URL**

   - 後端 API 的完整 URL
   - 格式：`https://your-backend.onrender.com`
   - 不要加尾隨斜線

2. **NODE_VERSION**（可選）
   - Node.js 版本
   - 建議：`18` 或 `20`

### 建置設定

- **Build Command**: `npm install && npm run build`
  - 安裝依賴並建置專案
- **Publish Directory**: `dist`

  - Vite 的輸出目錄

- **Root Directory**: `frontend`
  - 前端程式碼所在目錄

---

## 🔄 路由配置

為了支援 Vue Router 的 history 模式，需要設定 rewrite 規則：

在 Render Dashboard 中：

1. 進入 Static Site 設定
2. 找到 "Redirects/Rewrites"
3. 新增規則：
   - Source: `/*`
   - Destination: `/index.html`
   - Action: `Rewrite`

或使用 `render.yaml` 中的 `routes` 配置（已包含在上面的範例中）。

---

## 🧪 測試部署

部署完成後：

### 1. 檢查建置日誌

- 在 Render Dashboard 查看 "Logs"
- 確認沒有錯誤訊息

### 2. 訪問網站

- 開啟 Render 提供的 URL
- 例如：`https://talent-search-frontend.onrender.com`

### 3. 測試功能

- 開啟瀏覽器開發者工具（F12）
- 測試搜索功能
- 檢查 Network 標籤，確認 API 請求正常

### 4. 常見問題排查

**問題 1：白屏或 404**

- 檢查 Publish Directory 是否正確設為 `dist`
- 檢查 rewrite 規則是否設定

**問題 2：API 請求失敗**

- 檢查 `VITE_API_BASE_URL` 是否正確
- 檢查後端 CORS 設定
- 確認後端服務正在運行

**問題 3：環境變數未生效**

- 環境變數必須以 `VITE_` 開頭才能在前端使用
- 修改環境變數後需要重新部署

---

## 🔐 更新後端 CORS

前端部署後，需要更新後端允許的來源。

在 `BackEnd/start_fixed_api.py` 中：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://talent-search-frontend.onrender.com",  # 你的前端 URL
        "http://localhost:3000",  # 本地開發
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

或暫時允許所有來源（僅用於測試）：

```python
allow_origins=["*"]
```

---

## 🚀 自動部署

### 設定自動部署：

1. **連接 Git Repository**
   - Render 會監聽 Git push
2. **選擇分支**

   - 預設監聽 `main` 分支
   - 可以在設定中修改

3. **自動觸發**
   - 每次 push 到指定分支
   - Render 自動重新建置和部署

### 手動重新部署：

1. 進入 Render Dashboard
2. 選擇 Static Site
3. 點擊 "Manual Deploy" > "Clear build cache & deploy"

---

## 💰 費用說明

### Render 免費方案限制：

- ✅ 靜態網站完全免費
- ✅ 自動 HTTPS
- ✅ 全球 CDN
- ✅ 自動部署
- ✅ 100GB 頻寬/月
- ⚠️ 後端服務閒置 15 分鐘後會休眠（首次訪問需要 30-60 秒啟動）

### 組合方案：

- **前端**：Render Static Site（免費）
- **後端**：Render Web Service（免費，但會休眠）

或

- **前端**：Vercel/Netlify（免費，更快）
- **後端**：Render Web Service（免費）

---

## 📊 監控和日誌

### 查看日誌：

1. 進入 Render Dashboard
2. 選擇 Static Site
3. 點擊 "Logs" 標籤
4. 查看建置和部署日誌

### 監控流量：

1. 在 Dashboard 查看 "Metrics"
2. 監控請求數量和頻寬使用

---

## 🎨 自訂域名（可選）

### 設定自訂域名：

1. 在 Render Dashboard 中選擇 Static Site
2. 進入 "Settings" > "Custom Domain"
3. 新增你的域名
4. 更新 DNS 記錄：

   - 類型：`CNAME`
   - 名稱：`www` 或 `@`
   - 值：Render 提供的 CNAME 目標

5. 等待 DNS 傳播（通常 5-30 分鐘）
6. Render 會自動配置 SSL 憑證

---

## ✅ 部署檢查清單

部署前：

- [ ] 後端已成功部署並可訪問
- [ ] 已在本地測試 `npm run build`
- [ ] 已準備好後端 URL

部署時：

- [ ] Root Directory 設為 `frontend`
- [ ] Build Command 正確
- [ ] Publish Directory 設為 `dist`
- [ ] 環境變數 `VITE_API_BASE_URL` 已設定
- [ ] Rewrite 規則已設定

部署後：

- [ ] 前端可以正常訪問
- [ ] API 請求成功
- [ ] 沒有 Console 錯誤
- [ ] 後端 CORS 已更新
- [ ] 搜索功能正常

---

## 🆘 疑難排解

### 建置失敗

**錯誤：`npm: command not found`**

- 確認 `NODE_VERSION` 環境變數已設定

**錯誤：`Module not found`**

- 檢查 `package.json` 中的依賴
- 確認 Build Command 包含 `npm install`

### 部署成功但無法訪問

**白屏**

- 檢查瀏覽器 Console
- 確認 Publish Directory 正確
- 檢查 rewrite 規則

**API 錯誤**

- 確認 `VITE_API_BASE_URL` 正確
- 檢查後端是否運行
- 檢查 CORS 設定

---

## 📞 需要幫助？

- Render 文檔：https://render.com/docs/static-sites
- Render 社群：https://community.render.com
- Vite 文檔：https://vitejs.dev

---

## 🎉 完成！

部署成功後，你會有：

- 前端：`https://talent-search-frontend.onrender.com`
- 後端：`https://talent-search-backend.onrender.com`

兩個服務都在 Render 上，方便統一管理！
