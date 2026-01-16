# IIS 反向代理部署指南 (Reverse Proxy Setup)

此方案解決了 `wfastcgi` 權限不足的問題，將 IIS 轉變為單純的流量轉發器，而 Python 應用程式則作為獨立服務執行。

## 步驟 1: 安裝 IIS 必要模組

請確認伺服器已安裝以下模組 (微軟官方下載)：
1.  **[URL Rewrite](https://www.iis.net/downloads/microsoft/url-rewrite)**
2.  **[Application Request Routing (ARR)](https://www.iis.net/downloads/microsoft/application-request-routing)**

### 啟用 ARR Proxy 功能 (關鍵！)
1. 安裝 ARR 後，打開 **IIS 管理員**。
2. 點選最頂層的伺服器節點 (您的電腦名稱)。
3. 在中間功能區找到 **Application Request Routing Cache**，點兩下進入。
4. 在右側動作面板，點選 **Server Proxy Settings...**。
5. 勾選最上面的 **Enable proxy**。
6. 點擊右側 **Apply**。

## 步驟 2: 部署檔案

將 `BackEnd/api_v2` 的所有檔案 (含新生成的 `web.config` 和 `run_waitress.py`) 複製到 `C:\inetpub\wwwroot\TalentChatAPI`。

請確認 `web.config` 內容如下 (只有 Rewrite 規則，沒有 handlers)：
```xml
<action type="Rewrite" url="http://127.0.0.1:5000/{R:1}" />
```

## 步驟 3: 啟動 Python 服務 (Waitress)

在伺服器上打開 PowerShell 或 CMD：

```powershell
cd C:\inetpub\wwwroot\TalentChatAPI
pip install waitress
python run_waitress.py
```

您應該會看到：
`Starting Waitress server on 0.0.0.0:5000`

**驗證**：
打開瀏覽器訪問 `http://localhost:5000/health`。如果成功，代表 Python 端 OK。

## 步驟 4: 測試 IIS

保持上面的 PowerShell 視窗開啟 (不要關閉)，打開瀏覽器訪問 IIS 的公開網址 (例如 `http://localhost/` 或您的域名)。
IIS 應該會將請求轉發給 Python，您應該能看到正常回應。

## 步驟 5: 將 Python 設為背景服務 (可選但推薦)

為了讓 Python 在伺服器重開機後自動啟動，建議使用 `NSSM` (Non-Sucking Service Manager) 將其註冊為服務。

1. 下載 [NSSM](https://nssm.cc/download)。
2. 解壓 `nssm.exe` (win64) 到 `C:\Windows\System32` (方便存取)。
3. 管理員 CMD 執行：
   ```cmd
   nssm install TalentChatAPI
   ```
4. 在視窗中填入：
   *   **Application Path**: `C:\inetpub\wwwroot\TalentChatAPI\venv\Scripts\python.exe`
   *   **Startup Directory**: `C:\inetpub\wwwroot\TalentChatAPI`
   *   **Arguments**: `run_waitress.py`
5. 點擊 **Install service**。
6. 啟動服務：`nssm start TalentChatAPI`。

這樣即使您登出，網站也會持續運作。

## 步驟 6: 切換至 Port 80 (正式環境)

若要讓外部使用者透過 `http://your-domain.com` (預設 Port 80) 存取，而不是 `http://your-domain.com:5050`，請依照以下步驟修改 IIS 繫結：

1.  **處理衝突**： IIS 預設的 **Default Web Site** 已經佔用了 Port 80。
    *   在左側列表選擇 **Default Web Site**。
    *   右側動作選單點擊 **停止 (Stop)**。
    *   或者：編輯繫結，將其改為 Port 8090 以避開。

2.  **修改 API 站台繫結**：
    *   選擇您的站台 `TalentChatAPI`。
    *   右側點擊 **繫結... (Bindings...)**。
    *   選擇現有的 `http` (5050) 項目，點擊 **編輯**。
    *   將連接埠 (Port) 改為 **80**。
    *   主機名稱 (Host Name) 可留空 (代表接受所有 IP)，或填入您的網域名稱。

3.  **確認防火牆**：
    *   確保 Windows 防火牆已允許 **World Wide Web 服務 (HTTP)** 通過。
    *   如果是雲端主機 (AWS/Azure)，請檢查 Security Group 是否開放 Port 80。
