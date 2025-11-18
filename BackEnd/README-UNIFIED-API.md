# 統一 API 使用說明

## 📦 新的統一架構

現在使用 `app.py` 作為唯一的 API 檔案，透過環境變數控制本地和雲端的不同行為。

---

## 🎯 優點

1. **單一程式碼來源**

   - 本地和雲端用同一個檔案
   - 不用維護多個版本

2. **環境變數控制**

   - 不同環境不同配置
   - 敏感資訊不寫在程式碼裡

3. **易於維護**
   - 修改一次，兩邊都更新
   - 減少版本不一致問題

---

## 🚀 本地開發

### 方法 1：使用啟動腳本（推薦）

```batch
cd BackEnd
start-local.bat
```

腳本會自動：

1. 載入 `.env.local` 環境變數
2. 啟動 API 服務

### 方法 2：手動設定環境變數

```batch
cd BackEnd
set ENVIRONMENT=development
python app.py
```

### 配置檔案

編輯 `BackEnd/.env.local` 修改本地配置：

```env
ENVIRONMENT=development
DB_SSH_PRIVATE_KEY_FILE=private-key-openssh.pem
DEBUG=True
```

---

## ☁️ 雲端部署（Render）

### 1. 更新 Render 設定

在 Render Dashboard 的 Web Service 設定：

**Start Command:**

```bash
cd BackEnd && python app.py
```

### 2. 設定環境變數

在 Render Dashboard > Environment 設定：

| 變數名稱             | 值                                   | 說明                 |
| -------------------- | ------------------------------------ | -------------------- |
| `ENVIRONMENT`        | `production`                         | 運行環境             |
| `DB_SSH_HOST`        | `54.199.255.239`                     | SSH 主機             |
| `DB_SSH_PORT`        | `22`                                 | SSH 端口             |
| `DB_SSH_USERNAME`    | `victor_cheng`                       | SSH 用戶名           |
| `DB_SSH_PRIVATE_KEY` | `-----BEGIN...`                      | SSH 私鑰（完整內容） |
| `DB_HOST`            | `localhost`                          | 資料庫主機           |
| `DB_PORT`            | `5432`                               | 資料庫端口           |
| `DB_NAME`            | `projectdb`                          | 資料庫名稱           |
| `DB_USER`            | `projectuser`                        | 資料庫用戶           |
| `DB_PASSWORD`        | `projectpass`                        | 資料庫密碼           |
| `LLM_API_KEY`        | `sk-xxx...`                          | LLM API 金鑰         |
| `FRONTEND_URL`       | `https://your-frontend.onrender.com` | 前端 URL             |
| `DEBUG`              | `False`                              | 除錯模式             |

### 3. 部署

提交程式碼後，Render 會自動部署。

---

## 🔧 環境變數說明

### 必需的環境變數

#### 本地開發：

- `ENVIRONMENT=development`
- `DB_SSH_PRIVATE_KEY_FILE=private-key-openssh.pem`

#### 生產環境：

- `ENVIRONMENT=production`
- `DB_SSH_PRIVATE_KEY=<完整的 SSH key 內容>`

### 可選的環境變數

| 變數           | 預設值    | 說明             |
| -------------- | --------- | ---------------- |
| `HOST`         | `0.0.0.0` | API 監聽地址     |
| `PORT`         | `8000`    | API 端口         |
| `DEBUG`        | `False`   | 除錯模式         |
| `FRONTEND_URL` | -         | 前端 URL（CORS） |

---

## 📋 API 端點

### 基本端點

- `GET /` - 根路徑，顯示 API 資訊
- `GET /health` - 健康檢查
- `GET /docs` - API 文檔（Swagger UI）

### 功能端點

- `POST /api/search` - 搜索人才
- `GET /api/candidates` - 獲取所有候選人
- `GET /api/traits` - 獲取特質定義

---

## 🔍 環境判斷邏輯

程式會根據 `ENVIRONMENT` 環境變數判斷運行環境：

### 開發環境 (`development`)

- 使用本地 SSH key 檔案
- CORS 允許所有來源
- 顯示詳細日誌
- 啟用除錯模式

### 生產環境 (`production`)

- 使用環境變數中的 SSH key
- CORS 只允許指定來源
- 簡化日誌
- 關閉除錯模式

---

## 🧪 測試

### 本地測試

1. 啟動 API：

   ```batch
   cd BackEnd
   start-local.bat
   ```

2. 訪問健康檢查：

   ```
   http://localhost:8000/health
   ```

3. 查看 API 文檔：
   ```
   http://localhost:8000/docs
   ```

### 生產環境測試

1. 訪問健康檢查：

   ```
   https://your-backend.onrender.com/health
   ```

2. 確認回應包含：
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "environment": "production",
     "version": "3.0.0"
   }
   ```

---

## 🔄 遷移步驟

### 從舊版本遷移到統一版本

1. **本地開發**

   ```batch
   # 停止舊的 API
   # 使用新的啟動腳本
   cd BackEnd
   start-local.bat
   ```

2. **Render 部署**

   - 在 Dashboard 更新 Start Command：
     ```bash
     cd BackEnd && python app.py
     ```
   - 確認所有環境變數已設定
   - 手動觸發重新部署

3. **驗證**
   - 檢查健康檢查端點
   - 測試搜索功能
   - 確認前端可以正常連接

---

## ⚠️ 注意事項

1. **SSH Key 格式**

   - 生產環境：完整的 key 內容（包含 BEGIN/END 標記）
   - 本地環境：檔案路徑

2. **環境變數優先級**

   - 環境變數 > 預設值
   - 確保生產環境設定了所有必需的變數

3. **CORS 設定**

   - 生產環境需要設定 `FRONTEND_URL`
   - 開發環境自動允許所有來源

4. **除錯模式**
   - 生產環境務必設定 `DEBUG=False`
   - 避免洩漏敏感資訊

---

## 📞 疑難排解

### 問題 1：找不到 SSH key

**錯誤：** `找不到 SSH key 檔案`

**解決：**

- 本地：確認 `private-key-openssh.pem` 在 `BackEnd` 資料夾
- 生產：確認 `DB_SSH_PRIVATE_KEY` 環境變數已設定

### 問題 2：資料庫連接失敗

**錯誤：** `database: disconnected`

**解決：**

1. 檢查 SSH 連線是否正常
2. 確認資料庫帳號密碼正確
3. 查看詳細日誌

### 問題 3：CORS 錯誤

**錯誤：** `Access-Control-Allow-Origin`

**解決：**

- 確認 `FRONTEND_URL` 環境變數正確
- 或暫時設定 `allow_origins=["*"]` 測試

---

## ✅ 檢查清單

部署前確認：

- [ ] `app.py` 已提交到 Git
- [ ] Render Start Command 已更新
- [ ] 所有環境變數已設定
- [ ] SSH key 格式正確
- [ ] 本地測試通過
- [ ] 健康檢查端點正常
- [ ] 前端可以連接後端

---

## 🎉 完成！

現在你有一個統一的 API，可以在本地和雲端無縫運行！
