# 雲端 API 問題排查指南

## 🔍 問題描述

**症狀**:

- 雲端 API 的 `/health` 端點返回 404
- 雲端 API 的 `/api/traits` 端點行為與本地不同
- 本地 API 工作正常，但雲端 API 有問題

## 📋 可能的原因

### 1. 路由配置問題

- Render 使用的啟動腳本可能不正確
- API 端點沒有正確註冊

### 2. 環境變數問題

- 必要的環境變數未設定
- 環境變數值不正確

### 3. 資料庫連接問題

- SSH 隧道建立失敗
- 資料庫憑證錯誤

### 4. CORS 配置問題

- 前端域名未加入白名單
- CORS 中間件配置錯誤

### 5. 代碼版本不一致

- 雲端部署的代碼版本較舊
- 本地修改未推送到 Git

## 🛠️ 排查步驟

### 步驟 1: 檢查 Render 部署狀態

1. 登入 Render Dashboard
2. 找到 `talent-search-api` 服務
3. 查看部署狀態：
   - ✅ **Live**: 服務正在運行
   - ⚠️ **Build Failed**: 構建失敗
   - ❌ **Deploy Failed**: 部署失敗

### 步驟 2: 查看 Render 日誌

```bash
# 在 Render Dashboard 中
1. 點擊服務名稱
2. 切換到 "Logs" 標籤
3. 查看最新的日誌輸出
```

**關鍵日誌訊息**:

```
✅ 正常啟動:
- "人才聊天搜索 API (修正版) 啟動中..."
- "SSH 隧道已建立"
- "資料庫連接成功"
- "Application startup complete"

❌ 錯誤訊息:
- "ModuleNotFoundError": 缺少依賴
- "Connection refused": 資料庫連接失敗
- "Permission denied": SSH 金鑰問題
- "404 Not Found": 路由問題
```

### 步驟 3: 驗證環境變數

在 Render Dashboard 中檢查以下環境變數：

```bash
必須設定的變數:
✅ DB_SSH_HOST=54.199.255.239
✅ DB_SSH_PORT=22
✅ DB_SSH_USERNAME=victor_cheng
✅ DB_SSH_PRIVATE_KEY=<完整的私鑰內容>
✅ DB_HOST=localhost
✅ DB_PORT=5432
✅ DB_NAME=projectdb
✅ DB_USER=projectuser
✅ DB_PASSWORD=<資料庫密碼>
✅ LLM_API_KEY=<LLM API 金鑰>
✅ ENVIRONMENT=production

可選變數:
- LLM_API_HOST=https://api.siliconflow.cn
- LLM_MODEL=deepseek-ai/DeepSeek-V3
- FRONTEND_URL=<前端 URL>
```

### 步驟 4: 測試 API 端點

使用診斷工具測試：

```bash
# 方法 1: 使用瀏覽器
打開: diagnose-cloud-api.html

# 方法 2: 使用 curl
curl https://talent-search-api.onrender.com/health
curl https://talent-search-api.onrender.com/
curl https://talent-search-api.onrender.com/api/traits
```

**預期結果**:

```json
// GET /health
{
  "status": "healthy",
  "database": "connected",
  "version": "2.0.0"
}

// GET /
{
  "message": "人才聊天搜索 API (修正版)",
  "version": "2.0.0",
  "status": "running",
  "endpoints": {
    "search": "/api/search",
    "candidates": "/api/candidates",
    "health": "/health"
  }
}

// GET /api/traits
{
  "total": 5,
  "traits": [
    {
      "name": "communication",
      "chinese_name": "溝通能力",
      "description": "與他人有效交流的能力"
    },
    ...
  ]
}
```

### 步驟 5: 檢查啟動命令

在 `render.yaml` 中確認：

```yaml
startCommand: cd BackEnd && python start_fixed_api.py
```

**驗證**:

1. 確認 `start_fixed_api.py` 存在
2. 確認文件有執行權限
3. 確認 Python 版本正確 (3.11)

### 步驟 6: 檢查代碼版本

```bash
# 1. 確認本地修改已提交
git status

# 2. 推送到遠端
git add .
git commit -m "修正雲端 API 問題"
git push origin main

# 3. 在 Render 中觸發重新部署
# Dashboard > Manual Deploy > Deploy latest commit
```

## 🔧 常見問題解決方案

### 問題 1: `/health` 返回 404

**原因**: 路由未正確註冊或啟動腳本錯誤

**解決方案**:

1. 確認 `start_fixed_api.py` 中有 `@app.get("/health")` 裝飾器
2. 確認 Render 使用正確的啟動命令
3. 重新部署服務

```python
# 確認這段代碼存在於 start_fixed_api.py
@app.get("/health")
async def health_check():
    """健康檢查"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return {
            "status": "healthy",
            "database": "connected",
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
```

### 問題 2: `/api/traits` 行為不同

**原因**: 資料庫查詢失敗或表不存在

**解決方案**:

1. 已更新 `start_fixed_api.py` 添加錯誤處理
2. 如果表不存在，返回預設特質列表
3. 重新部署服務

```python
# 新的錯誤處理邏輯
@app.get("/api/traits")
async def get_traits():
    try:
        # 嘗試從資料庫查詢
        cursor.execute("SELECT ...")
        # ...
    except Exception as e:
        # 返回預設列表，不讓前端崩潰
        return {
            "total": 5,
            "traits": [預設特質列表]
        }
```

### 問題 3: CORS 錯誤

**原因**: 前端域名未加入 CORS 白名單

**解決方案**:

1. 已更新 `start_fixed_api.py` 的 CORS 配置
2. 支持正則表達式匹配
3. 重新部署服務

```python
# 新的 CORS 配置
if IS_PRODUCTION:
    allowed_origins = [
        "https://talent-search-frontend-68e7.onrender.com",
        "https://talent-search-frontend.vercel.app",
        "https://talent-search-frontend.netlify.app",
        # ...
    ]
    allow_origin_regex = r"https://.*\.(onrender\.com|vercel\.app|netlify\.app)$"
```

### 問題 4: 資料庫連接失敗

**原因**: SSH 金鑰或資料庫憑證錯誤

**解決方案**:

1. 檢查 `DB_SSH_PRIVATE_KEY` 環境變數
2. 確認金鑰格式正確（包含 BEGIN 和 END 行）
3. 檢查資料庫憑證

```bash
# SSH 金鑰格式
-----BEGIN OPENSSH PRIVATE KEY-----
<金鑰內容>
-----END OPENSSH PRIVATE KEY-----
```

### 問題 5: 服務啟動失敗

**原因**: 依賴缺失或 Python 版本不對

**解決方案**:

1. 檢查 `requirements.txt` 是否完整
2. 確認 `runtime.txt` 指定 Python 3.11
3. 查看構建日誌

```txt
# runtime.txt
python-3.11.0

# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
psycopg2-binary==2.9.9
sshtunnel==0.4.0
pydantic==2.5.0
httpx==0.25.1
```

## 📊 使用診斷工具

### 工具 1: diagnose-cloud-api.html

**功能**:

- 自動測試所有 API 端點
- 比較本地和雲端的差異
- 提供詳細的錯誤訊息

**使用方法**:

```bash
1. 在瀏覽器打開 diagnose-cloud-api.html
2. 確認 API URL 正確
3. 點擊「開始診斷」
4. 查看結果並根據建議修正
```

### 工具 2: check-deployment.html

**功能**:

- 檢查前端環境檢測
- 測試 API 連接
- 驗證 CORS 配置

**使用方法**:

```bash
1. 在瀏覽器打開 check-deployment.html
2. 點擊「開始檢查」
3. 查看所有檢查項目的結果
```

## 🚀 重新部署步驟

### 完整重新部署流程

```bash
# 1. 確認本地修改
git status
git diff

# 2. 提交修改
git add BackEnd/start_fixed_api.py
git commit -m "修正雲端 API 端點問題"

# 3. 推送到遠端
git push origin main

# 4. 在 Render Dashboard 中
# - 進入服務頁面
# - 點擊 "Manual Deploy"
# - 選擇 "Deploy latest commit"
# - 等待部署完成

# 5. 查看部署日誌
# - 確認沒有錯誤
# - 確認服務啟動成功

# 6. 測試 API
curl https://talent-search-api.onrender.com/health
curl https://talent-search-api.onrender.com/api/traits

# 7. 測試前端
# - 打開前端 URL
# - 測試搜索功能
# - 確認沒有 CORS 錯誤
```

## ✅ 驗證清單

部署後請逐項驗證：

```
後端 API:
□ /health 端點返回 200
□ / 端點返回正確的 JSON
□ /api/traits 端點返回特質列表
□ /api/candidates 端點返回候選人
□ /api/search 端點可以搜索
□ 沒有 500 錯誤
□ 日誌沒有錯誤訊息

前端連接:
□ 前端可以連接到後端
□ 沒有 CORS 錯誤
□ 搜索功能正常
□ 候選人列表顯示正常
□ 連接狀態顯示「已連線」

數據一致性:
□ 雲端和本地搜索結果一致
□ 特質列表相同
□ 候選人數據相同
```

## 📞 需要幫助？

如果問題仍然存在：

1. **收集信息**:

   - Render 日誌截圖
   - 瀏覽器 Console 錯誤
   - 診斷工具結果

2. **檢查文檔**:

   - API-CONFIG.md
   - DEPLOYMENT-FIX-2024-11-18.md
   - 快速驗證指南.md

3. **使用診斷工具**:
   - diagnose-cloud-api.html
   - check-deployment.html

## 📝 更新記錄

- **2024-11-18**:
  - ✅ 更新 start_fixed_api.py
  - ✅ 改善 CORS 配置
  - ✅ 添加 /api/traits 錯誤處理
  - ✅ 創建診斷工具
