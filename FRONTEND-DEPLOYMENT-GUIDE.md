# 前端部署完整指南

## 🎯 目標

將 Vue 3 前端部署到免費平台（Vercel 或 Netlify）

---

## ⚡ 快速開始（推薦：Vercel）

### 方法 A：使用網頁介面（最簡單）

1. **前往 Vercel**

   - 網址：https://vercel.com
   - 使用 GitHub/Bitbucket 帳號登入

2. **Import Project**

   - 點擊 "Add New..." > "Project"
   - 連接你的 Git repository
   - 選擇 `talent-search-system` repo

3. **配置專案**

   - Framework Preset: `Vite`
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

4. **設定環境變數**

   ```
   VITE_API_BASE_URL = https://your-backend.onrender.com
   ```

   （替換為你的 Render 後端 URL）

5. **Deploy**
   - 點擊 "Deploy" 按鈕
   - 等待 2-3 分鐘
   - 完成！你會得到一個 URL

---

### 方法 B：使用命令列

1. **進入前端資料夾**

   ```bash
   cd frontend
   ```

2. **執行部署腳本**

   ```bash
   deploy-vercel.bat
   ```

   或

   ```bash
   deploy-netlify.bat
   ```

3. **按照提示操作**

   - 第一次會要求登入
   - 選擇專案設定
   - 等待部署完成

4. **設定環境變數**
   - 前往 Dashboard
   - Settings > Environment Variables
   - 新增 `VITE_API_BASE_URL`

---

## 📋 部署前檢查清單

- [ ] 後端已成功部署到 Render
- [ ] 後端 URL 可以訪問（例如：https://xxx.onrender.com/health）
- [ ] 已安裝 Node.js 18+
- [ ] 已在 `frontend` 資料夾執行 `npm install`
- [ ] 已測試本地建置：`npm run build`

---

## 🔧 配置說明

### 1. 環境變數

在部署平台設定以下環境變數：

| 變數名稱            | 值                                  | 說明          |
| ------------------- | ----------------------------------- | ------------- |
| `VITE_API_BASE_URL` | `https://your-backend.onrender.com` | 後端 API 地址 |

### 2. 更新後端 CORS

確保後端允許前端域名，在 `BackEnd/start_fixed_api.py` 中：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",  # 加入你的前端 URL
        "*"  # 或暫時允許所有（不建議用於生產環境）
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🚀 部署步驟詳解

### Vercel 部署

#### 使用 CLI：

```bash
# 1. 安裝 Vercel CLI
npm install -g vercel

# 2. 登入
vercel login

# 3. 進入前端資料夾
cd frontend

# 4. 部署
vercel --prod

# 5. 設定環境變數（在 Dashboard）
# 前往 https://vercel.com/dashboard
# 選擇專案 > Settings > Environment Variables
# 新增 VITE_API_BASE_URL
```

#### 自動部署：

1. 連接 Git repository
2. 每次 push 到 main 分支自動部署
3. 預覽分支自動建立預覽環境

---

### Netlify 部署

#### 使用 CLI：

```bash
# 1. 安裝 Netlify CLI
npm install -g netlify-cli

# 2. 登入
netlify login

# 3. 進入前端資料夾
cd frontend

# 4. 部署
netlify deploy --prod

# 5. 設定環境變數（在 Dashboard）
# 前往 https://app.netlify.com
# 選擇 Site > Site settings > Environment variables
# 新增 VITE_API_BASE_URL
```

---

## 🧪 測試部署

部署完成後：

1. **開啟前端 URL**

   - 例如：https://your-app.vercel.app

2. **開啟瀏覽器開發者工具**

   - 按 F12
   - 切換到 Console 標籤

3. **測試功能**

   - 輸入搜索查詢
   - 檢查是否有錯誤訊息
   - 確認 API 請求成功

4. **常見問題**
   - CORS 錯誤：檢查後端 CORS 設定
   - 404 錯誤：檢查 API URL 是否正確
   - 連線逾時：檢查後端是否正常運行

---

## 🔄 更新部署

### 自動更新（推薦）

如果連接了 Git：

1. 修改程式碼
2. Commit 並 push
3. 自動重新部署

### 手動更新

```bash
cd frontend
vercel --prod
# 或
netlify deploy --prod
```

---

## 💡 最佳實踐

1. **使用環境變數**

   - 不要在程式碼中寫死 API URL
   - 使用 `.env.production` 管理配置

2. **啟用自動部署**

   - 連接 Git repository
   - 設定自動部署規則

3. **監控效能**

   - 使用 Vercel/Netlify Analytics
   - 檢查載入時間

4. **設定自訂域名**（可選）
   - 在 Dashboard 中設定
   - 更新 DNS 記錄

---

## 📞 需要幫助？

- Vercel 文檔：https://vercel.com/docs
- Netlify 文檔：https://docs.netlify.com
- Vite 文檔：https://vitejs.dev

---

## ✅ 完成檢查

部署成功後確認：

- [ ] 前端可以正常訪問
- [ ] 可以連接到後端 API
- [ ] 搜索功能正常運作
- [ ] 沒有 Console 錯誤
- [ ] HTTPS 正常啟用
- [ ] 已設定環境變數
- [ ] 已更新後端 CORS 設定
