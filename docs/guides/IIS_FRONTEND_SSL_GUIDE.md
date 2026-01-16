# IIS 前端部署與 SSL 指南

## Part 1: 前端部署

您之前的 `chat-widget` 似乎是設定為「Library Mode (元件庫模式)」，這通常是為了嵌入到別人網站用的，而不是獨立的 SPA 網站。

如果您希望它變成一個**可以獨立訪問的網站** (像 dashboard)，您需要：

### 1. 建置前端
在開發機執行：
```powershell
cd frontend/chat-widget
npm install
npm run build
```

檢查 `dist` 資料夾：
- 如果原本是用 Library Mode，裡面可能只有 `loader.js` 和 `style.css`，沒有 `index.html`。
- 如果需要獨立網站，請將根目錄的 `index.html` 手動複製進 `dist`，並修改裡面引入 JS/CSS 的路徑。

### 2. 複製檔案
將 `frontend/chat-widget/dist` 內的所有檔案，**複製** 到伺服器的 `C:\inetpub\wwwroot\TalentChatAPI`。

此時您的資料夾結構應如下：
```text
C:\inetpub\wwwroot\TalentChatAPI\
├── start_waitress.py      (後端啟動腳本)
├── web.config             (路由設定)
├── index.html             (前端入口)
├── loader.js / assets/    (前端資源)
├── ...
```

### 3. (重要) 更新 web.config
請使用我剛剛為您生成的 `web.config`，它已經設定好：
*   `/api/*` -> 轉發給 Python (Port 5000)
*   其他 -> 視為靜態檔案，若找不到則回傳 `index.html` (SPA Fallback)。

---

## Part 2: SSL 憑證安裝 (HTTPS)

為了安全性 (與現代瀏覽器相容性)，強烈建議啟用 HTTPS。

### 使用 win-acme (免費 Let's Encrypt)

1.  **下載工具**：
    前往 [win-acme 官網](https://www.win-acme.com/) 下載最新版 (x64)。
2.  **解壓縮** 到伺服器某個固定位置 (例如 `C:\tools\win-acme`)。
3.  **執行** `wacs.exe` (以管理員身分)。
4.  **操作步驟**：
    *   選擇 `N` (Create new certificate)。
    *   選擇 `1` (Single binding of an IIS site)。
    *   找到您的網站 `TalentChatAPI`，輸入其對應的編號。
    *   按照提示一路按 Enter (預設即可)。
    *   同意服務條款。

**完成！**
工具會自動：
1.  驗證域名所有權 (需確保您的域名 DNS 已指向此伺服器)。
2.  下載憑證並安裝到 IIS。
3.  自動設定 443 Port 的繫結。
4.  建立排程任務，自動續約。

### 強制 HTTPS (可選)
安裝完 SSL 後，若要強制使用者走 HTTPS，請安裝 [IIS URL Rewrite] 模組，win-acme 有時候會問你要不要自動加這個規則，選是即可。若要手動加，請參考網路上標準的 "IIS Force HTTPS config"。
