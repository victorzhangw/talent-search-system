# 統一 API 設定指南

## 🎯 目標

使用新的 `BackEnd/app.py`，本地和雲端用同一個檔案，透過環境變數控制不同行為。

---

## 📦 已創建的檔案

1. **BackEnd/app.py** - 統一的 API 主程式
2. **BackEnd/.env.local** - 本地環境變數（不會被 commit）
3. **BackEnd/.env.production.example** - 生產環境變數範例
4. **BackEnd/start-local.bat** - 本地啟動腳本
5. **BackEnd/README-UNIFIED-API.md** - 詳細使用說明

---

## 🚀 本地開發設定

### 1. 確認檔案存在

確認 `BackEnd` 資料夾有：

- `app.py` ✅
- `.env.local` ✅
- `private-key-openssh.pem` ✅
- `start-local.bat` ✅

### 2. 啟動本地 API

```batch
cd BackEnd
start-local.bat
```

### 3. 測試

開啟瀏覽器訪問：

```
http://localhost:8000/health
```

應該看到：

```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "development",
  "version": "3.0.0"
}
```

---

## ☁️ Render 部署設定

### 1. 更新 Start Command

在 Render Dashboard > 你的 Web Service > Settings：

**找到 "Start Command"，改為：**

```bash
cd BackEnd && python app.py
```

### 2. 設定環境變數

在 Render Dashboard > Environment 標籤，新增以下變數：

#### 必需的變數：

```
ENVIRONMENT = production
DB_SSH_HOST = 54.199.255.239
DB_SSH_PORT = 22
DB_SSH_USERNAME = victor_cheng
DB_SSH_PRIVATE_KEY = -----BEGIN OPENSSH PRIVATE KEY-----
（貼上完整的 SSH key 內容）
-----END OPENSSH PRIVATE KEY-----
DB_HOST = localhost
DB_PORT = 5432
DB_NAME = projectdb
DB_USER = projectuser
DB_PASSWORD = projectpass
LLM_API_KEY = sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff
FRONTEND_URL = https://talent-search-frontend-68e7.onrender.com
```

#### 可選的變數：

```
DEBUG = False
HOST = 0.0.0.0
PORT = 8000
```

### 3. 保存並重新部署

1. 點擊 "Save Changes"
2. 點擊 "Manual Deploy" > "Deploy latest commit"
3. 等待 2-3 分鐘

### 4. 驗證部署

訪問：

```
https://your-backend.onrender.com/health
```

應該看到：

```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "production",
  "version": "3.0.0"
}
```

---

## 🔍 環境差異

### 本地開發環境

- `ENVIRONMENT=development`
- 使用本地 SSH key 檔案：`private-key-openssh.pem`
- CORS 允許所有來源
- 顯示詳細日誌
- 除錯模式開啟

### 生產環境（Render）

- `ENVIRONMENT=production`
- 使用環境變數中的 SSH key 內容
- CORS 只允許指定的前端 URL
- 簡化日誌
- 除錯模式關閉

---

## ✅ 優點

### 1. 單一程式碼來源

- 本地和雲端用同一個 `app.py`
- 不用維護多個版本
- 修改一次，兩邊都更新

### 2. 環境變數控制

- 不同環境不同配置
- 敏感資訊不寫在程式碼裡
- 安全且靈活

### 3. 易於維護

- 減少版本不一致問題
- 容易追蹤變更
- 簡化部署流程

---

## 🧪 測試檢查清單

### 本地測試

- [ ] 執行 `start-local.bat` 成功啟動
- [ ] 訪問 `http://localhost:8000/health` 正常
- [ ] 訪問 `http://localhost:8000/docs` 可以看到 API 文檔
- [ ] 測試搜索功能正常

### 生產環境測試

- [ ] Render 部署成功（狀態顯示 "Live"）
- [ ] 訪問 `/health` 端點正常
- [ ] 前端可以連接後端
- [ ] 搜索功能正常
- [ ] 沒有 CORS 錯誤

---

## ⚠️ 常見問題

### 問題 1：本地找不到 SSH key

**錯誤：** `找不到 SSH key 檔案: private-key-openssh.pem`

**解決：**
確認 `BackEnd/private-key-openssh.pem` 檔案存在

### 問題 2：Render 部署失敗

**錯誤：** `No password or public key available!`

**解決：**

1. 確認 `DB_SSH_PRIVATE_KEY` 環境變數已設定
2. 確認 key 內容完整（包含 BEGIN/END 標記）
3. 確認沒有多餘的空格或換行

### 問題 3：前端 CORS 錯誤

**錯誤：** `Access-Control-Allow-Origin`

**解決：**

1. 確認 `FRONTEND_URL` 環境變數正確
2. 確認 URL 沒有尾隨斜線
3. 重新部署後端

---

## 📞 需要幫助？

查看詳細文檔：

- `BackEnd/README-UNIFIED-API.md` - 完整使用說明
- `BackEnd/.env.production.example` - 環境變數範例

---

## 🎉 完成！

現在你有：

- ✅ 統一的 API 程式碼
- ✅ 本地開發環境
- ✅ 雲端部署配置
- ✅ 環境變數控制

本地和雲端都用同一個 `app.py`，透過環境變數自動適應不同環境！
