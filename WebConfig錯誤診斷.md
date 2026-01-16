# Web.config 錯誤診斷清單

## 🔍 請提供以下資訊

### 1. 完整的錯誤訊息

請複製**完整的**錯誤訊息，包括：
- 錯誤代碼（例如：500.19, 500.0）
- 錯誤描述
- 錯誤來源
- 詳細錯誤資訊

**範例**：
```
HTTP Error 500.19 - Internal Server Error
The requested page cannot be accessed because the related configuration data for the page is invalid.

Module: IIS Web Core
Notification: Unknown
Handler: Not yet determined
Error Code: 0x8007000d
Config Error: Cannot add duplicate collection entry of type 'add'
Config File: \\?\C:\inetpub\wwwroot\web.config
```

---

### 2. 錯誤出現的位置

- [ ] IIS 錯誤頁面（白色背景，詳細錯誤資訊）
- [ ] 瀏覽器 Console（F12 → Console 標籤）
- [ ] Network 標籤（F12 → Network）
- [ ] Waitress terminal 輸出
- [ ] 其他：___________

---

### 3. 當前使用的 web.config

請確認你正在使用哪個版本：
- [ ] 原始版本（你最初提供的）
- [ ] 修改版本（包含 serverVariables）
- [ ] web.config.simple
- [ ] web.config.minimal
- [ ] 其他：___________

---

### 4. IIS 應用程式池狀態

```powershell
# 檢查應用程式池狀態
Get-WebAppPoolState -Name "YourAppPoolName"
```

**結果**：
- [ ] Started（正常）
- [ ] Stopped（已停止）
- [ ] 其他：___________

---

### 5. Waitress 狀態

**Waitress 是否正在運行？**
- [ ] 是，正在運行
- [ ] 否，已停止
- [ ] 不確定

**測試 Waitress 直接連線**：
```
http://localhost:5000/api/v2/candidates/
```

**結果**：
- [ ] 可以訪問（返回資料）
- [ ] 無法訪問（錯誤訊息：_________）

---

## 🔧 診斷步驟

### 步驟 1：測試最簡版本

使用 `web.config.minimal`（不包含任何壓縮配置）：

```powershell
# 備份當前 web.config
copy web.config web.config.current

# 使用最簡版本
copy web.config.minimal web.config

# 重啟應用程式池
Restart-WebAppPool -Name "YourAppPoolName"
```

**測試結果**：
- [ ] 正常（可以訪問網站）
- [ ] 錯誤（錯誤訊息：_________）

---

### 步驟 2：檢查 IIS 模組

確認是否安裝了 URL Rewrite 模組：

```powershell
# 列出 IIS 模組
Get-WebGlobalModule | Where-Object {$_.Name -like "*rewrite*"}
```

**結果**：
- [ ] 有 RewriteModule
- [ ] 沒有 RewriteModule（需要安裝）

**如果沒有**，下載安裝：
https://www.iis.net/downloads/microsoft/url-rewrite

---

### 步驟 3：檢查 applicationHost.config

查看是否有衝突的全域配置：

```powershell
# 查看 httpCompression 配置
C:\Windows\System32\inetsrv\appcmd.exe list config -section:system.webServer/httpCompression
```

**檢查是否有**：
- `<add mimeType="text/event-stream" ...>` 已存在
- 其他衝突的配置

---

### 步驟 4：檢查檔案權限

確認 IIS 應用程式池使用者有權限讀取 web.config：

```powershell
# 檢查檔案權限
icacls "C:\inetpub\wwwroot\web.config"
```

**應該看到**：
- `IIS_IUSRS:(R)` 或類似的讀取權限

---

### 步驟 5：驗證 XML 格式

確認 web.config 的 XML 格式正確：

```powershell
# 使用 PowerShell 驗證 XML
[xml]$xml = Get-Content "C:\inetpub\wwwroot\web.config"
$xml
```

**結果**：
- [ ] 成功（顯示 XML 內容）
- [ ] 失敗（錯誤訊息：_________）

---

## 🐛 常見錯誤類型

### 錯誤 1：重複的 mimeMap

**錯誤訊息**：
```
Cannot add duplicate collection entry of type 'add' with unique key attribute 'fileExtension' set to '.json'
```

**原因**：`.json` 或 `.vue` 的 mimeMap 已經在父級配置中定義

**解決方法**：移除 `<staticContent>` 區塊

---

### 錯誤 2：重複的 mimeType（httpCompression）

**錯誤訊息**：
```
Cannot add duplicate collection entry of type 'add' with unique key attribute 'mimeType' set to 'text/event-stream'
```

**原因**：`text/event-stream` 已經在 applicationHost.config 中定義

**解決方法**：
1. 先移除，再添加：
```xml
<httpCompression>
    <dynamicTypes>
        <remove mimeType="text/event-stream" />
        <add mimeType="text/event-stream" enabled="false" />
    </dynamicTypes>
</httpCompression>
```

2. 或完全移除 `<httpCompression>` 區塊

---

### 錯誤 3：CORS 錯誤

**錯誤訊息**（瀏覽器 Console）：
```
Access to fetch at 'http://...' from origin 'http://...' has been blocked by CORS policy
```

**原因**：Flask 的 CORS 配置問題，與 web.config 無關

**解決方法**：檢查 Flask 的 CORS 設定：
```python
# app.py
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

### 錯誤 4：502 Bad Gateway

**錯誤訊息**：
```
HTTP Error 502.3 - Bad Gateway
The operation timed out
```

**原因**：Waitress 沒有運行或無法連線

**解決方法**：
1. 確認 Waitress 正在運行
2. 測試 `http://localhost:5000`
3. 檢查防火牆設定

---

## 📝 最簡版本 web.config

如果所有版本都有問題，使用這個**最簡版本**（`web.config.minimal`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="API Proxy" stopProcessing="true">
                    <match url="^(api|auth|chat|health)(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:5000/{R:0}" />
                </rule>
                <rule name="SPA Fallback" stopProcessing="true">
                    <match url=".*" />
                    <conditions logicalGrouping="MatchAll">
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                        <add input="{REQUEST_URI}" pattern="^/(api|auth|chat|health)" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="index.html" />
                </rule>
            </rules>
        </rewrite>
        <staticContent>
            <mimeMap fileExtension=".vue" mimeType="text/plain" />
            <mimeMap fileExtension=".json" mimeType="application/json" />
        </staticContent>
    </system.webServer>
</configuration>
```

**特點**：
- ✅ 只有 API 代理和 SPA Fallback
- ✅ 沒有壓縮配置（避免衝突）
- ✅ 最小化配置（最不容易出錯）

**注意**：這個版本**不會**優化 SSE 串流，但可以用來測試基本功能是否正常。

---

## 🎯 下一步

### 如果最簡版本可以運行

表示問題在壓縮配置，可以嘗試：
1. 逐步添加壓縮配置
2. 使用 `<remove>` 先移除再添加

### 如果最簡版本也有錯誤

表示問題在基本配置，需要檢查：
1. IIS 模組是否正確安裝
2. applicationHost.config 是否有衝突
3. 檔案權限是否正確

---

## 📞 請提供資訊

為了幫你解決問題，請提供：

1. ✅ **完整的錯誤訊息**（截圖或文字）
2. ✅ **錯誤出現的位置**（IIS / 瀏覽器 / Waitress）
3. ✅ **使用 web.config.minimal 的測試結果**
4. ✅ **Waitress 直接連線測試結果**（`http://localhost:5000`）

有了這些資訊，我可以精確定位問題！
