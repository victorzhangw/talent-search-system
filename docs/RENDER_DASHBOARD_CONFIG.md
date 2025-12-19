# Render Dashboard 手動配置指南

## 問題診斷

重新部署後仍然返回 v2.1.0，說明 **Render 沒有使用 `render.yaml` 配置**。

可能原因：

1. 服務是手動創建的，沒有使用 Infrastructure as Code
2. Dashboard 中的配置覆蓋了 `render.yaml`
3. `render.yaml` 路徑不正確

## 解決方案：在 Dashboard 中手動修改配置

### 步驟 1: 進入服務設置

1. 登入 Render Dashboard：https://dashboard.render.com
2. 點擊 `talent-search-api` 服務
3. 點擊左側的 **"Settings"** 標籤

### 步驟 2: 修改啟動命令

找到 **"Build & Deploy"** 區域：

#### 2.1 修改 Start Command

**當前值（錯誤）：**

```bash
cd BackEnd && uvicorn talent_search_api:app --host 0.0.0.0 --port 8000
```

**修改為（正確）：**

```bash
cd BackEnd && uvicorn main_api:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75
```

**關鍵變更：**

- `talent_search_api:app` → `main_api:app`
- 添加 `--timeout-keep-alive 75`

#### 2.2 確認 Build Command

應該是：

```bash
pip install --upgrade pip && pip install -r requirements.txt
```

或者使用更詳細的版本：

```bash
echo "Checking Python version..." && \
python --version && \
echo "Upgrading pip..." && \
pip install --upgrade pip && \
echo "Installing dependencies..." && \
pip install -r requirements.txt && \
echo "Build complete!"
```

### 步驟 3: 檢查環境變數

在 **"Environment"** 標籤中，確認以下變數已設置：

**必需的環境變數：**

```
DB_SSH_HOST=<你的 SSH 主機>
DB_SSH_PORT=22
DB_SSH_USERNAME=<你的 SSH 用戶名>
DB_SSH_PRIVATE_KEY=<完整的私鑰內容>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=<資料庫名稱>
DB_USER=<資料庫用戶>
DB_PASSWORD=<資料庫密碼>
LLM_API_KEY=<你的 LLM API Key>
LLM_API_HOST=https://api.akashml.com
LLM_MODEL=deepseek-ai/DeepSeek-V3.1
LLM_MAX_RESPONSE_LENGTH=2000
LLM_MAX_TOKENS=3000
LLM_TEMPERATURE=0.7
ENVIRONMENT=production
```

**新增的環境變數（如果缺少）：**

- `LLM_MAX_RESPONSE_LENGTH=2000`
- `LLM_MAX_TOKENS=3000`
- `LLM_TEMPERATURE=0.7`

### 步驟 4: 保存並重新部署

1. 點擊頁面底部的 **"Save Changes"** 按鈕
2. Render 會自動觸發重新部署
3. 或者手動點擊 **"Manual Deploy"** → **"Clear build cache & deploy"**

### 步驟 5: 監控部署日誌

點擊 **"Logs"** 標籤，查看部署過程：

**成功的日誌應該包含：**

```
==> Starting service with 'cd BackEnd && uvicorn main_api:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75'

INFO:     Started server process [1]
INFO:     Waiting for application startup.
🚀 人才管理系統 API 啟動中...
🔄 正在載入人才搜索模組...
✅ 人才搜索模組載入成功
🔄 正在載入 HR 諮詢模組...
✅ HR 諮詢模組載入成功
🔄 正在初始化資料庫連接...
✅ 資料庫連接成功
🎉 人才管理系統 API 啟動成功！
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**如果看到錯誤：**

1. **ModuleNotFoundError: No module named 'main_api'**

   - 原因：`main_api.py` 不在正確位置
   - 解決：確認文件在 `BackEnd/main_api.py`

2. **ModuleNotFoundError: No module named 'hr_consultation_routes'**

   - 原因：依賴模組缺失
   - 解決：確認 `BackEnd/hr_consultation_routes.py` 存在

3. **Connection refused (資料庫)**
   - 原因：環境變數未正確設置
   - 解決：檢查 `DB_SSH_PRIVATE_KEY` 是否包含完整私鑰

### 步驟 6: 驗證部署

部署完成後，測試端點：

```bash
# 1. 健康檢查（應該返回 v2.0.0）
curl https://talent-search-system.onrender.com/health

# 預期結果：
# {"status":"healthy","service":"Main API","version":"2.0.0"}

# 2. 根路徑（應該顯示模組列表）
curl https://talent-search-system.onrender.com/

# 預期結果：
# {
#   "service": "人才管理系統 API",
#   "version": "2.0.0",
#   "modules": [
#     {"name": "人才搜索", "path": "/api/talent"},
#     {"name": "HR 諮詢", "path": "/api/hr-consult"}
#   ]
# }

# 3. HR 諮詢候選人列表
curl "https://talent-search-system.onrender.com/api/hr-consult/candidates?has_test_data=true&limit=10"

# 預期結果：
# {"success": true, "data": [...], "total": 123}
```

---

## 替代方案：使用 render.yaml（推薦）

如果你想讓 Render 使用 `render.yaml` 配置：

### 方法 1: 刪除並重新創建服務

1. 在 Render Dashboard 中刪除現有的 `talent-search-api` 服務
2. 點擊 **"New +"** → **"Blueprint"**
3. 連接 GitHub repository
4. Render 會自動檢測 `render.yaml` 並創建服務

### 方法 2: 使用 Render CLI

```bash
# 安裝 Render CLI
npm install -g @render/cli

# 登入
render login

# 使用 render.yaml 創建/更新服務
render blueprint sync
```

---

## 檢查清單

配置前確認：

- [ ] 在 Settings 中修改 Start Command 為 `main_api:app`
- [ ] 確認所有環境變數已設置
- [ ] 保存更改並觸發重新部署
- [ ] 查看日誌確認 `main_api` 啟動成功
- [ ] 測試 `/health` 端點返回 v2.0.0
- [ ] 測試 `/api/hr-consult/candidates` 返回數據

---

## 快速診斷命令

```bash
# 檢查當前版本
curl https://talent-search-system.onrender.com/health | grep version

# 檢查是否有 HR 諮詢模組
curl https://talent-search-system.onrender.com/ | grep "HR 諮詢"

# 測試 HR 諮詢端點
curl -I "https://talent-search-system.onrender.com/api/hr-consult/candidates?limit=1"
# 如果返回 404 = 舊版本
# 如果返回 200 = 新版本成功
```

---

**最後更新**: 2025-12-19  
**狀態**: 需要在 Dashboard 中手動修改 Start Command
