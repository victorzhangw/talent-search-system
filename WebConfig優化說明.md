# Web.config SSE 優化說明

## 📋 修改對比

### 原始 web.config（可用）

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

---

### SSE 優化後的 web.config

**檔案**：`web.config.sse-optimized`

**新增的配置**：

#### 1. 禁用 URL 壓縮

```xml
<!-- 在 <system.webServer> 開頭添加 -->
<urlCompression doStaticCompression="false" doDynamicCompression="false" />
```

**原因**：壓縮會破壞 SSE 串流

---

#### 2. 移除 Accept-Encoding Header

```xml
<rule name="API Proxy" stopProcessing="true">
    <match url="^(api|auth|chat|health)(.*)" />
    <action type="Rewrite" url="http://127.0.0.1:5000/{R:0}" />
    <!-- 新增 serverVariables -->
    <serverVariables>
        <set name="HTTP_X_ORIGINAL_ACCEPT_ENCODING" value="{HTTP_ACCEPT_ENCODING}" />
        <set name="HTTP_ACCEPT_ENCODING" value="" />
    </serverVariables>
</rule>
```

**原因**：防止 IIS 嘗試壓縮回應

---

#### 3. 恢復 Accept-Encoding（輸出規則）

```xml
<outboundRules>
    <rule name="RestoreAcceptEncoding" preCondition="NeedsRestoringAcceptEncoding">
        <match serverVariable="HTTP_ACCEPT_ENCODING" pattern="^(.*)" />
        <action type="Rewrite" value="{HTTP_X_ORIGINAL_ACCEPT_ENCODING}" />
    </rule>
    <preConditions>
        <preCondition name="NeedsRestoringAcceptEncoding">
            <add input="{HTTP_X_ORIGINAL_ACCEPT_ENCODING}" pattern=".+" />
        </preCondition>
    </preConditions>
</outboundRules>
```

**原因**：對非 SSE 請求恢復正常的壓縮支援

---

#### 4. 禁用 text/event-stream 壓縮

```xml
<httpCompression>
    <dynamicTypes>
        <add mimeType="text/event-stream" enabled="false" />
    </dynamicTypes>
</httpCompression>
```

**原因**：明確禁用 SSE 的壓縮

---

## 🔧 部署步驟

### 方法 1：最小修改（推薦）

如果你的原始 web.config 已經可以正常工作，只需要添加以下配置：

1. **在 `<system.webServer>` 開頭添加**：
```xml
<urlCompression doStaticCompression="false" doDynamicCompression="false" />
```

2. **在 `<rule name="API Proxy">` 的 `<action>` 後添加**：
```xml
<serverVariables>
    <set name="HTTP_X_ORIGINAL_ACCEPT_ENCODING" value="{HTTP_ACCEPT_ENCODING}" />
    <set name="HTTP_ACCEPT_ENCODING" value="" />
</serverVariables>
```

3. **在 `</rules>` 後、`</rewrite>` 前添加**：
```xml
<outboundRules>
    <rule name="RestoreAcceptEncoding" preCondition="NeedsRestoringAcceptEncoding">
        <match serverVariable="HTTP_ACCEPT_ENCODING" pattern="^(.*)" />
        <action type="Rewrite" value="{HTTP_X_ORIGINAL_ACCEPT_ENCODING}" />
    </rule>
    <preConditions>
        <preCondition name="NeedsRestoringAcceptEncoding">
            <add input="{HTTP_X_ORIGINAL_ACCEPT_ENCODING}" pattern=".+" />
        </preCondition>
    </preConditions>
</outboundRules>
```

4. **在 `<staticContent>` 前添加**：
```xml
<httpCompression>
    <dynamicTypes>
        <add mimeType="text/event-stream" enabled="false" />
    </dynamicTypes>
</httpCompression>
```

---

### 方法 2：使用完整的優化版本

直接使用 `web.config.sse-optimized`：

```bash
# 備份原始 web.config
copy web.config web.config.backup

# 使用優化版本
copy web.config.sse-optimized web.config

# 重啟 IIS 應用程式池
Restart-WebAppPool -Name "YourAppPoolName"
```

---

## ⚠️ 重要注意事項

### 1. serverVariables 需要解鎖

如果遇到錯誤：
```
This configuration section cannot be used at this path. This happens when the section is locked at a parent level.
```

**解決方法**：

在 IIS 管理員中解鎖 `serverVariables`：

```powershell
# 以管理員身份執行
%windir%\system32\inetsrv\appcmd.exe unlock config -section:system.webServer/rewrite/allowedServerVariables
```

或手動編輯 `applicationHost.config`：

1. 打開 `C:\Windows\System32\inetsrv\config\applicationHost.config`
2. 找到 `<section name="rewrite/allowedServerVariables"`
3. 將 `overrideModeDefault="Deny"` 改為 `overrideModeDefault="Allow"`

---

### 2. 確保安裝了 URL Rewrite 模組

如果 IIS 沒有安裝 URL Rewrite 模組，需要先安裝：

**下載**：https://www.iis.net/downloads/microsoft/url-rewrite

**檢查是否已安裝**：
- 打開 IIS 管理員
- 選擇網站
- 查看是否有「URL Rewrite」圖示

---

### 3. 測試配置

修改 web.config 後，測試配置是否正確：

```powershell
# 測試 IIS 配置
%windir%\system32\inetsrv\appcmd.exe list config "Default Web Site" -section:system.webServer/rewrite/rules
```

---

## 🔍 驗證 SSE 串流

### 1. 檢查 Response Headers

F12 → Network → `/chat/` 請求 → Headers

**應該看到**：
```
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
Transfer-Encoding: chunked
```

**不應該看到**：
```
Content-Encoding: gzip  ← 如果有這個，表示被壓縮了
```

---

### 2. 測試串流效果

1. 發送 chat 請求
2. 觀察文字是否逐字顯示
3. 檢查 Console 是否有錯誤

---

## 📊 配置對比

| 項目 | 原始配置 | SSE 優化配置 |
|------|---------|-------------|
| URL 壓縮 | 預設（啟用） | **禁用** |
| Accept-Encoding | 保留 | **移除（API 請求）** |
| text/event-stream 壓縮 | 預設（啟用） | **禁用** |
| 輸出規則 | 無 | **恢復 Accept-Encoding** |
| API 代理 | ✅ | ✅ |
| SPA Fallback | ✅ | ✅ |
| 靜態檔案 | ✅ | ✅ |

---

## 🎯 總結

### 核心修改

1. ✅ **禁用壓縮**（`urlCompression`）
2. ✅ **移除 Accept-Encoding**（`serverVariables`）
3. ✅ **禁用 SSE 壓縮**（`httpCompression`）
4. ✅ **恢復 Accept-Encoding**（`outboundRules`）

### 保持不變

- ✅ API 反向代理邏輯
- ✅ SPA Fallback 邏輯
- ✅ 靜態檔案配置
- ✅ CORS 設定（在 Flask 中處理）

### 部署建議

**如果原始 web.config 可用**：
- 使用**方法 1**（最小修改）
- 逐步添加 SSE 優化配置
- 每次修改後測試

**如果要完全重新配置**：
- 使用**方法 2**（完整版本）
- 使用 `web.config.sse-optimized`
- 記得備份原始檔案

---

## 🐛 常見問題

### Q: 修改後出現 CORS 錯誤？

**A**: CORS 是在 Flask 中配置的，與 web.config 無關。檢查：

```python
# app.py
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {"origins": "*"}
})
```

### Q: serverVariables 配置失敗？

**A**: 需要解鎖 serverVariables（見上方說明）

### Q: 還是一次全部顯示？

**A**: 檢查：
1. Waitress 是否使用新的參數重啟
2. Flask Response Headers 是否正確
3. IIS 應用程式池是否重啟
4. 瀏覽器快取是否清空

---

現在你可以選擇：
1. **最小修改**：在原始 web.config 上添加 SSE 優化
2. **使用優化版本**：直接使用 `web.config.sse-optimized`

建議先備份原始 web.config，然後嘗試最小修改！
