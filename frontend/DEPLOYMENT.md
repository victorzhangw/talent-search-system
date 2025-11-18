# 前端部署指南

## 方案一：Vercel（推薦）

### 步驟：

1. **安裝 Vercel CLI**

   ```bash
   npm install -g vercel
   ```

2. **登入 Vercel**

   ```bash
   vercel login
   ```

3. **部署**

   ```bash
   cd frontend
   vercel
   ```

4. **設定環境變數**

   - 在 Vercel Dashboard 中設定：
   - `VITE_API_BASE_URL` = `https://your-backend-app.onrender.com`

5. **重新部署**
   ```bash
   vercel --prod
   ```

### 優點：

- 完全免費
- 自動 HTTPS
- 全球 CDN
- 自動從 Git 部署
- 零配置

---

## 方案二：Netlify

### 步驟：

1. **安裝 Netlify CLI**

   ```bash
   npm install -g netlify-cli
   ```

2. **登入 Netlify**

   ```bash
   netlify login
   ```

3. **部署**

   ```bash
   cd frontend
   netlify deploy --prod
   ```

4. **設定環境變數**
   - 在 Netlify Dashboard 中設定：
   - `VITE_API_BASE_URL` = `https://your-backend-app.onrender.com`

### 優點：

- 完全免費
- 自動 HTTPS
- 表單處理
- 無伺服器函數支援

---

## 方案三：GitHub Pages（靜態部署）

### 步驟：

1. **修改 vite.config.js**

   ```javascript
   export default defineConfig({
     base: "/talent-search-system/", // 你的 repo 名稱
     // ... 其他配置
   });
   ```

2. **建置**

   ```bash
   npm run build
   ```

3. **部署到 gh-pages**

   ```bash
   npm install -g gh-pages
   gh-pages -d dist
   ```

4. **在 GitHub Settings > Pages 啟用**
   - Source: gh-pages branch

### 限制：

- 只能用於靜態網站
- 需要手動更新環境變數

---

## 快速開始（推薦 Vercel）

### 使用 Vercel 網頁介面：

1. 前往 https://vercel.com
2. 點擊 "Import Project"
3. 連接你的 Bitbucket/GitHub
4. 選擇 `frontend` 資料夾
5. 設定環境變數：
   - `VITE_API_BASE_URL` = 你的後端 URL
6. 點擊 Deploy

完成！你會得到一個 `https://your-app.vercel.app` 的網址。

---

## 更新 API URL

部署後，記得更新 `frontend/.env.production`：

```env
VITE_API_BASE_URL=https://your-actual-backend.onrender.com
```

然後重新部署。

---

## 測試

部署完成後測試：

1. 開啟前端 URL
2. 檢查瀏覽器 Console 是否有 CORS 錯誤
3. 測試搜索功能

如果有 CORS 問題，確認後端的 CORS 設定允許前端域名。
