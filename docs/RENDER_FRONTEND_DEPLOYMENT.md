# Render 前端部署指南

## 問題描述

本地端可以正確顯示結構化的 HR 諮詢回應，但 Render 上顯示原始 JSON 字符串。

**原因**：Render 上的前端代碼是舊版本，沒有包含最新的結構化顯示功能。

## 解決方案

### 方案 1：使用 Render Static Site（推薦）

#### 步驟 1：在 Render Dashboard 創建新服務

1. 登入 [Render Dashboard](https://dashboard.render.com/)
2. 點擊 "New +" → "Static Site"
3. 連接你的 GitHub 倉庫
4. 配置如下：

**基本設置**：

- Name: `talent-search-frontend`
- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `dist`

**環境變數**：

```
VITE_API_BASE_URL=https://talent-search-api.onrender.com
VITE_HR_API_BASE_URL=https://talent-search-api.onrender.com
VITE_ENTERPRISE_ID=1
VITE_API_TIMEOUT=90000
```

5. 點擊 "Create Static Site"

#### 步驟 2：等待部署完成

部署完成後，你會得到一個 URL，例如：

```
https://talent-search-frontend.onrender.com
```

#### 步驟 3：更新後端 CORS 設置

如果前端和後端在不同的域名，需要更新後端的 CORS 設置。

編輯 `BackEnd/main_api.py`，確保 CORS 允許前端域名：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://talent-search-frontend.onrender.com",  # 添加前端 URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 方案 2：使用 render.yaml 自動部署

已經更新了 `render.yaml`，添加了前端服務配置。

#### 步驟 1：提交更改

```bash
git add render.yaml
git commit -m "Add frontend service to render.yaml"
git push origin main
```

#### 步驟 2：在 Render Dashboard 應用配置

1. 進入你的 Render Dashboard
2. 找到你的服務
3. 點擊 "Settings" → "YAML"
4. 點擊 "Sync" 或 "Apply"

Render 會自動創建新的前端服務。

### 方案 3：手動構建並上傳（臨時方案）

如果你使用的是其他托管服務（如 Vercel、Netlify），可以手動構建：

```bash
cd frontend
npm install
npm run build
```

然後將 `frontend/dist` 目錄上傳到你的托管服務。

## 驗證部署

部署完成後，訪問前端 URL，測試 HR 諮詢功能：

1. 選擇一個候選人
2. 提問：「這個候選人適合什麼職位？」
3. 檢查回應是否正確顯示為結構化格式（有摘要、章節、要點）

### 預期結果

✅ **正確顯示**：

- 藍色背景的摘要框
- 分段的章節標題和內容
- 灰色背景的關鍵要點列表

❌ **錯誤顯示**：

- 顯示原始 JSON 字符串
- 所有文字擠在一起，沒有格式

## 調試步驟

如果部署後仍然顯示 JSON，請檢查：

### 1. 檢查前端版本

在瀏覽器控制台執行：

```javascript
console.log(import.meta.env.VITE_API_BASE_URL);
```

確認 API URL 正確。

### 2. 檢查 API 回應

在瀏覽器控制台的 Network 標籤中：

1. 找到 `/api/hr-consult/chat` 請求
2. 查看 Response
3. 確認 `parsed_answer` 欄位存在且有值

### 3. 檢查前端代碼

在瀏覽器控制台查看是否有 JavaScript 錯誤。

### 4. 強制刷新

按 `Ctrl + Shift + R`（Windows）或 `Cmd + Shift + R`（Mac）強制刷新頁面，清除緩存。

## 常見問題

### Q: 為什麼本地可以，Render 不行？

A: 因為 Render 上運行的是舊版本的前端代碼。需要重新部署前端。

### Q: 我需要重新部署後端嗎？

A: 不需要。後端已經正確返回 `parsed_answer`。只需要更新前端。

### Q: 部署需要多久？

A: Render Static Site 通常需要 2-5 分鐘完成部署。

### Q: 部署後還是顯示 JSON？

A: 檢查：

1. 瀏覽器緩存是否清除（強制刷新）
2. API URL 是否正確配置
3. 後端是否返回 `parsed_answer`（檢查 Network 標籤）

## 相關文件

- `frontend/src/components/ChatArea.vue` - 前端顯示邏輯
- `BackEnd/hr_consultation_service.py` - 後端 JSON 解析
- `BackEnd/prompts/hr_consultation_prompts.json` - Prompt 模板
- `render.yaml` - Render 部署配置

## 更新日誌

- 2024-12-19: 創建文檔，添加前端部署指南
- 2024-12-19: 更新 render.yaml，添加前端服務配置
