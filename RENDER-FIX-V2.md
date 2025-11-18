# Render 部署修復 V2

## 🔧 最新修復（2024-11-18）

### 問題診斷

Render 無法找到或安裝 `fastapi` 模組，原因是：

1. Render 可能優先查找根目錄的 `requirements.txt`
2. buildCommand 可能沒有正確執行

### 解決方案

#### 1. 創建根目錄 requirements.txt

已創建 `requirements.txt`（根目錄），內容：

```txt
# Redirect to BackEnd requirements
-r BackEnd/requirements.txt
```

這樣 Render 會自動包含 `BackEnd/requirements.txt` 中的所有依賴。

#### 2. 更新 render.yaml

已更新 `render.yaml`：

- Python 版本改為 `3.11`（更穩定）
- buildCommand 改為使用根目錄的 `requirements.txt`
- 添加 `pip install --upgrade pip`

```yaml
buildCommand: pip install --upgrade pip && pip install -r requirements.txt
```

---

## 🚀 立即執行

### 步驟 1: 提交所有更改

```bash
git add requirements.txt BackEnd/requirements.txt render.yaml
git commit -m "Fix: Render deployment - add root requirements.txt and update config"
git push origin main
```

### 步驟 2: 清除 Render 緩存（重要！）

在 Render Dashboard 中：

1. 進入你的服務
2. 點擊 "Settings"
3. 找到 "Build & Deploy" 區域
4. 點擊 "Clear build cache"
5. 然後點擊 "Manual Deploy" → "Clear build cache & deploy"

這會強制 Render 重新安裝所有依賴。

---

## 📋 檢查清單

部署前確認：

- [x] 根目錄有 `requirements.txt`
- [x] `BackEnd/requirements.txt` 包含所有依賴
- [x] `render.yaml` 使用正確的 buildCommand
- [ ] Git 已提交並 push
- [ ] Render 緩存已清除
- [ ] 環境變數已設定（特別是 `LLM_API_KEY`）

---

## 🔍 驗證步驟

### 1. 查看 Build Log

在 Render 的 "Logs" 標籤中，應該看到：

```
==> Cloning from https://github.com/...
==> Checking out commit ...
==> Running 'pip install --upgrade pip && pip install -r requirements.txt'
Requirement already satisfied: pip in ...
Collecting fastapi==0.104.1
  Downloading fastapi-0.104.1-py3-none-any.whl (92 kB)
Collecting uvicorn[standard]==0.24.0
  Downloading uvicorn-0.24.0-py3-none-any.whl (59 kB)
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
==> Build successful 🎉
==> Running 'cd BackEnd && python start_fixed_api.py'
```

### 2. 查看 Runtime Log

應該看到：

```
正在初始化資料庫連接...
✓ 資料庫連接完成！
✓ 特質定義載入完成！
✓ LLM 智能搜索已啟用！
✓ 初始化完成！
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
```

### 3. 測試 API

```bash
curl https://your-app.onrender.com/health
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

---

## ⚠️ 如果還是失敗

### 方案 A: 檢查 Python 版本

在 render.yaml 中嘗試不同的 Python 版本：

```yaml
envVars:
  - key: PYTHON_VERSION
    value: "3.10" # 或 "3.11" 或 "3.9"
```

### 方案 B: 使用完整路徑

修改 render.yaml 的 buildCommand：

```yaml
buildCommand: |
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  pip list  # 列出已安裝的套件，用於調試
```

### 方案 C: 直接在 buildCommand 中安裝

如果上述方法都失敗，直接在 buildCommand 中列出所有依賴：

```yaml
buildCommand: |
  pip install --upgrade pip
  pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0
  pip install psycopg2-binary==2.9.9 sshtunnel==0.4.0 paramiko==3.4.0
  pip install httpx==0.25.1 python-multipart==0.0.6
```

---

## 📊 文件結構

確認你的專案結構如下：

```
project/
├── requirements.txt          ← 新增（根目錄）
├── render.yaml              ← 已更新
├── BackEnd/
│   ├── requirements.txt     ← 已更新
│   ├── start_fixed_api.py
│   ├── talent_search_api_v2.py
│   ├── conversation_manager.py
│   ├── talent_analysis_service.py
│   └── ...
└── frontend/
    └── ...
```

---

## 🎯 關鍵環境變數

確保在 Render Dashboard 中設定：

```
LLM_API_KEY=sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff
DB_SSH_HOST=54.199.255.239
DB_SSH_USERNAME=victor_cheng
DB_NAME=projectdb
DB_USER=projectuser
DB_PASSWORD=projectpass
DB_SSH_PRIVATE_KEY=<私鑰內容>
```

---

## ✅ 成功標誌

當你看到以下內容時，表示部署成功：

1. ✅ Build Log 顯示 "Successfully installed fastapi..."
2. ✅ Runtime Log 顯示 "Uvicorn running on..."
3. ✅ 服務狀態顯示 "Live" (綠色)
4. ✅ `/health` 端點返回 healthy

---

## 📞 還需要幫助？

如果問題持續，請提供：

1. 完整的 Build Log
2. 完整的 Runtime Log
3. render.yaml 的內容
4. requirements.txt 的內容（根目錄和 BackEnd/）

這樣我可以更精確地診斷問題。
