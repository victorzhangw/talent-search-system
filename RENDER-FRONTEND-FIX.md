# Render 前端部署錯誤修正

## ❌ 錯誤訊息

```
npm error enoent Could not read package.json: Error: ENOENT: no such file or directory
```

## 🔍 原因

Render 在根目錄找不到 `package.json`，因為前端程式碼在 `frontend` 資料夾中。

---

## ✅ 解決方案（選擇一種）

### 方案 1：在 Dashboard 設定 Root Directory（最簡單）

1. **進入 Render Dashboard**

   - 選擇你的 Static Site

2. **進入 Settings**

   - 點擊左側的 "Settings"

3. **找到 Build & Deploy 區域**

   - 找到 **Root Directory** 欄位

4. **設定 Root Directory**

   - 輸入：`frontend`
   - 點擊 "Save Changes"

5. **重新部署**

   - 點擊 "Manual Deploy" > "Clear build cache & deploy"

6. **確認其他設定**
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`（不是 `frontend/dist`）

---

### 方案 2：修改 Build Command

如果 Root Directory 欄位不可用：

1. **進入 Settings**

2. **修改 Build Command**

   - 原本：`npm install && npm run build`
   - 改為：`cd frontend && npm install && npm run build`

3. **修改 Publish Directory**

   - 原本：`dist`
   - 改為：`frontend/dist`

4. **保存並重新部署**

---

### 方案 3：使用 Blueprint（render.yaml）

如果你想要自動化配置：

1. **刪除現有的 Static Site**

   - 在 Dashboard 中刪除

2. **使用 Blueprint 創建**

   - 點擊 "New +" > "Blueprint"
   - 選擇你的 repository
   - Render 會自動讀取 `render.yaml`

3. **確認 render.yaml 配置**
   ```yaml
   services:
     - type: web
       name: talent-search-frontend
       env: static
       rootDir: frontend # 關鍵設定
       buildCommand: npm install && npm run build
       staticPublishPath: ./dist
   ```

---

## 🎯 正確的配置

### 如果使用 Root Directory = `frontend`：

| 設定項目          | 值                             |
| ----------------- | ------------------------------ |
| Root Directory    | `frontend`                     |
| Build Command     | `npm install && npm run build` |
| Publish Directory | `dist`                         |

### 如果不使用 Root Directory：

| 設定項目          | 值                                            |
| ----------------- | --------------------------------------------- |
| Root Directory    | (空白)                                        |
| Build Command     | `cd frontend && npm install && npm run build` |
| Publish Directory | `frontend/dist`                               |

---

## 🧪 驗證設定

部署成功的標誌：

1. **建置日誌顯示：**

   ```
   ✓ built in XXXms
   ✓ XX modules transformed
   ```

2. **沒有錯誤訊息**

3. **可以訪問網站**

---

## 📸 設定截圖參考

### Root Directory 設定位置：

```
Dashboard > Your Static Site > Settings > Build & Deploy
└── Root Directory: [frontend]
```

### 完整設定範例：

```
Name: talent-search-frontend
Branch: main
Root Directory: frontend
Build Command: npm install && npm run build
Publish Directory: dist

Environment Variables:
- NODE_VERSION = 18
- VITE_API_BASE_URL = https://your-backend.onrender.com
```

---

## 🔄 重新部署步驟

1. 修改設定後
2. 點擊 "Manual Deploy"
3. 選擇 "Clear build cache & deploy"
4. 等待 3-5 分鐘
5. 檢查日誌確認成功

---

## ⚠️ 常見錯誤

### 錯誤 1：仍然找不到 package.json

- 確認 Root Directory 拼寫正確：`frontend`（小寫）
- 確認 repository 中確實有 `frontend/package.json`

### 錯誤 2：找不到 dist 目錄

- 確認 Publish Directory 設定正確
- 如果 Root Directory = `frontend`，則 Publish Directory = `dist`
- 如果沒有 Root Directory，則 Publish Directory = `frontend/dist`

### 錯誤 3：建置成功但無法訪問

- 檢查 Rewrite 規則是否設定
- Source: `/*` → Destination: `/index.html` (Rewrite)

---

## ✅ 檢查清單

修正後確認：

- [ ] Root Directory 設定為 `frontend`
- [ ] Build Command 正確
- [ ] Publish Directory 正確
- [ ] 環境變數已設定
- [ ] Rewrite 規則已設定
- [ ] 建置日誌沒有錯誤
- [ ] 可以訪問網站

---

## 💡 推薦配置

最簡單且不容易出錯的配置：

```
Root Directory: frontend
Build Command: npm install && npm run build
Publish Directory: dist

Environment Variables:
NODE_VERSION: 18
VITE_API_BASE_URL: https://your-backend.onrender.com

Redirects/Rewrites:
Source: /*
Destination: /index.html
Action: Rewrite
```

這樣設定後，Render 會：

1. 進入 `frontend` 資料夾
2. 執行 `npm install && npm run build`
3. 從 `frontend/dist` 發布靜態檔案
4. 所有路由重定向到 `index.html`

完成！
