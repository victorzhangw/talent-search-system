# Render 部署檢查清單

## ✅ 已修復的問題

### 1. 缺少 FastAPI 依賴

**問題**: `ModuleNotFoundError: No module named 'fastapi'`

**解決方案**: 已更新 `BackEnd/requirements.txt`，添加所有必要的依賴：

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
psycopg2-binary==2.9.9
sshtunnel==0.4.0
paramiko==3.4.0
httpx==0.25.1
python-multipart==0.0.6
```

---

## 📋 部署前檢查清單

### 1. 環境變數設定

在 Render Dashboard 中設定以下環境變數：

#### 必須設定的變數：

- ✅ `LLM_API_KEY` = `sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff`
- ✅ `DB_SSH_HOST` = `54.199.255.239`
- ✅ `DB_SSH_USERNAME` = `victor_cheng`
- ✅ `DB_NAME` = `projectdb`
- ✅ `DB_USER` = `projectuser`
- ✅ `DB_PASSWORD` = `projectpass`
- ✅ `DB_SSH_PRIVATE_KEY` = (SSH 私鑰內容)

#### 已有默認值的變數（可選）：

- `LLM_API_HOST` = `https://api.siliconflow.cn` (已設定)
- `LLM_MODEL` = `deepseek-ai/DeepSeek-V3` (已設定)
- `DB_HOST` = `localhost` (已設定)
- `DB_PORT` = `5432` (已設定)
- `DB_SSH_PORT` = `22` (已設定)

---

### 2. SSH 私鑰設定

**重要**: 需要將 `BackEnd/private-key-openssh.pem` 的內容設定為環境變數

#### 步驟：

1. 打開 `BackEnd/private-key-openssh.pem`
2. 複製完整內容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）
3. 在 Render Dashboard 中：
   - 找到 `DB_SSH_PRIVATE_KEY` 環境變數
   - 貼上私鑰內容
   - 保存

---

### 3. 文件檢查

確保以下文件存在且正確：

- ✅ `BackEnd/requirements.txt` - 已更新，包含所有依賴
- ✅ `render.yaml` - 配置正確
- ✅ `BackEnd/start_fixed_api.py` - 啟動腳本
- ✅ `BackEnd/config.py` - 配置文件
- ✅ `BackEnd/talent_search_api_v2.py` - 主 API
- ✅ `BackEnd/conversation_manager.py` - 對話管理
- ✅ `BackEnd/talent_analysis_service.py` - 分析服務
- ✅ `BackEnd/interview_api.py` - 面試 API

---

## 🚀 部署步驟

### 方法 1: 自動部署（推薦）

1. 提交更新到 Git：

   ```bash
   git add BackEnd/requirements.txt
   git commit -m "Fix: Add missing dependencies for Render deployment"
   git push origin main
   ```

2. Render 會自動檢測到更改並重新部署

3. 查看部署日誌，確認沒有錯誤

### 方法 2: 手動觸發部署

1. 登入 Render Dashboard
2. 找到 `talent-search-api` 服務
3. 點擊 "Manual Deploy" → "Deploy latest commit"
4. 等待部署完成

---

## 🔍 部署後驗證

### 1. 檢查服務狀態

訪問健康檢查端點：

```
https://your-app.onrender.com/health
```

預期回應：

```json
{
  "status": "healthy",
  "database": "connected",
  "traits_loaded": 50,
  "llm_enabled": true,
  "version": "2.1.0"
}
```

### 2. 測試 API 端點

訪問根路徑：

```
https://your-app.onrender.com/
```

預期回應：

```json
{
  "message": "人才聊天搜索 API v2.1 - 智能搜索版",
  "version": "2.1.0",
  "features": [...]
}
```

### 3. 測試搜索功能

使用 Postman 或 curl 測試：

```bash
curl -X POST https://your-app.onrender.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "找溝通能力強的人", "session_id": "test_session"}'
```

---

## ⚠️ 常見問題排查

### 問題 1: ModuleNotFoundError

**症狀**: `ModuleNotFoundError: No module named 'xxx'`

**解決方案**:

1. 確認 `BackEnd/requirements.txt` 包含該模組
2. 重新部署
3. 檢查 Render 的 Build Log

### 問題 2: SSH 連接失敗

**症狀**: `Connection refused` 或 `Authentication failed`

**解決方案**:

1. 確認 `DB_SSH_HOST` = `54.199.255.239`
2. 確認 `DB_SSH_USERNAME` = `victor_cheng`
3. 確認 `DB_SSH_PRIVATE_KEY` 已正確設定（包含完整的 BEGIN/END 標記）
4. 確認 SSH 私鑰格式正確（OpenSSH 格式）

### 問題 3: 資料庫連接失敗

**症狀**: `Connection to database failed`

**解決方案**:

1. 確認所有資料庫環境變數已設定
2. 確認 SSH Tunnel 已成功建立
3. 檢查資料庫伺服器是否允許來自 Render 的連接

### 問題 4: LLM API 錯誤

**症狀**: `LLM API 錯誤` 或 `401 Unauthorized`

**解決方案**:

1. 確認 `LLM_API_KEY` 已設定
2. 確認 API Key 有效且未過期
3. 檢查 SiliconFlow API 配額

---

## 📊 監控和日誌

### 查看日誌

1. 登入 Render Dashboard
2. 選擇 `talent-search-api` 服務
3. 點擊 "Logs" 標籤
4. 查看實時日誌

### 關鍵日誌訊息

**成功啟動**:

```
✓ 資料庫連接完成！
✓ 特質定義載入完成！
✓ LLM 智能搜索已啟用！
✓ 初始化完成！
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**錯誤訊息**:

- `❌ SSH 連接失敗` - 檢查 SSH 配置
- `❌ 資料庫連接失敗` - 檢查資料庫配置
- `❌ LLM API 錯誤` - 檢查 API Key

---

## 🔄 更新部署

### 更新代碼

1. 修改代碼
2. 提交到 Git：
   ```bash
   git add .
   git commit -m "Update: description of changes"
   git push origin main
   ```
3. Render 自動重新部署

### 更新環境變數

1. 登入 Render Dashboard
2. 選擇服務
3. 點擊 "Environment" 標籤
4. 修改或添加環境變數
5. 點擊 "Save Changes"
6. 服務會自動重啟

---

## 📞 支援資源

- **Render 文檔**: https://render.com/docs
- **FastAPI 文檔**: https://fastapi.tiangolo.com/
- **SiliconFlow API**: https://siliconflow.cn/

---

## ✅ 部署完成檢查

部署成功後，確認以下項目：

- [ ] 服務狀態顯示 "Live"
- [ ] `/health` 端點返回 healthy
- [ ] `/` 端點返回 API 資訊
- [ ] `/api/search` 可以正常搜索
- [ ] 資料庫連接正常
- [ ] LLM API 調用正常
- [ ] 日誌沒有錯誤訊息

---

## 🎉 下一步

部署成功後：

1. 更新前端 API 端點為 Render URL
2. 測試完整的前後端整合
3. 設定自定義域名（可選）
4. 配置 HTTPS（Render 自動提供）
5. 設定監控和告警
