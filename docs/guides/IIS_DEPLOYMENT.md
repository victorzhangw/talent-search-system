# IIS 部署指南 (api_v2 / Flask)

本指南協助您部署 `api_v2` (Flask 版本) 到 IIS。

## 為什麼之前會失敗？
`api_v2/app.py` 使用了 `create_app()` 工廠模式，這在開發時很好用，但 IIS 的 `wfastcgi` 需要一個已實例化的 `app` 變數。如果直接指向 `app.app`，會找不到該變數。

## 解決方案
我們新增了 **`wsgi.py`** 作為專門的 IIS 入口點。

## 部署步驟

### 1. 確保檔案齊全
請確認您的部署資料夾 (例如 `C:\inetpub\wwwroot\TalentChatAPI`) 包含以下新增/修改的檔案：

*   **`wsgi.py`**: 作為入口點，負責呼叫 `create_app()`。
*   **`web.config`**: 已設定 `WSGI_HANDLER` 為 `wsgi.app`。
*   **`requirements.txt`**: 確保包含 `wfastcgi`。

### 2. 安裝依賴
在伺服器上進入虛擬環境並安裝依賴：

```powershell
pip install -r requirements.txt
```

### 3. 設定 web.config (關鍵)
確保 `web.config` 中的路徑正確：

*   **scriptProcessor**: 指向您的 venv python 和 wfastcgi.py (您之前提供的路徑看起來是正確的)。
*   **PYTHONPATH**: 指向應用程式根目錄 (例如 `C:\inetpub\wwwroot\TalentChatAPI`)。
*   **WSGI_HANDLER**: 必須是 `wsgi.app`。

### 4. 權限設定
*   確保 IIS 用戶對 `logs` 資料夾有寫入權限 (web.config 中設定的 `WSGI_LOG` 路徑)。
*   確保 IIS 用戶對整個應用目錄有讀取/執行權限。

### 5. 重啟 IIS 應用程式集區
部署檔案後，重啟 App Pool 以載入新設定。

## 驗證
瀏覽您的 API 網址 (例如 `http://localhost:5000/api/v2/candidates/health` 或 `/health` 視您的路由而定)。
應該能看到正確的回應。

如果出現 500 錯誤，請檢查 `logs\wfastcgi.log`。
