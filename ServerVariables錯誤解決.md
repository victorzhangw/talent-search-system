# serverVariables 錯誤解決方案

## ❌ 錯誤訊息

```
This configuration section cannot be used at this path. 
This happens when the section is locked at a parent level.
```

或

```
Cannot add duplicate collection entry of type 'add' with unique key attribute 'name' set to 'HTTP_X_ORIGINAL_ACCEPT_ENCODING'
```

---

## ✅ 解決方案

### 方案 1：解鎖 serverVariables（完整功能）

#### 步驟 1：以管理員身份開啟 PowerShell

右鍵點擊「開始」→「Windows PowerShell (系統管理員)」

#### 步驟 2：執行解鎖命令

```powershell
# 解鎖 serverVariables
C:\Windows\System32\inetsrv\appcmd.exe unlock config -section:system.webServer/rewrite/allowedServerVariables
```

**預期輸出**：
```
Unlocked section "system.webServer/rewrite/allowedServerVariables" at configuration path "MACHINE/WEBROOT/APPHOST".
```

#### 步驟 3：重啟 IIS

```powershell
# 重啟 IIS
iisreset
```

或重啟應用程式池：
```powershell
Restart-WebAppPool -Name "YourAppPoolName"
```

#### 步驟 4：測試

重新載入網站，檢查是否正常。

---

### 方案 2：使用簡化版 web.config（無需解鎖）

如果無法解鎖 serverVariables（例如沒有管理員權限），使用簡化版配置。

**檔案**：`web.config.simple`

**特點**：
- ✅ 不需要 serverVariables
- ✅ 不需要 outboundRules
- ✅ 只使用基本的壓縮禁用
- ⚠️ 功能略少，但足以支援 SSE 串流

**使用方法**：
```powershell
# 備份原始檔案
copy web.config web.config.backup

# 使用簡化版
copy web.config.simple web.config

# 重啟應用程式池
Restart-WebAppPool -Name "YourAppPoolName"
```

---

## 📊 兩種方案對比

| 項目 | 完整版（需解鎖） | 簡化版（無需解鎖） |
|------|----------------|------------------|
| serverVariables | ✅ 使用 | ❌ 不使用 |
| outboundRules | ✅ 使用 | ❌ 不使用 |
| urlCompression | ✅ 禁用 | ✅ 禁用 |
| httpCompression | ✅ 禁用 SSE | ✅ 禁用 SSE |
| SSE 串流支援 | ✅ 完整 | ✅ 基本 |
| 需要管理員權限 | ✅ 需要 | ❌ 不需要 |

---

## 🔍 驗證解鎖是否成功

### 方法 1：檢查配置

```powershell
# 查看 serverVariables 的鎖定狀態
C:\Windows\System32\inetsrv\appcmd.exe list config -section:system.webServer/rewrite/allowedServerVariables
```

**如果已解鎖**，應該看到：
```xml
<system.webServer>
  <rewrite>
    <allowedServerVariables>
      ...
    </allowedServerVariables>
  </rewrite>
</system.webServer>
```

### 方法 2：測試 web.config

使用完整版 web.config，如果沒有錯誤，表示解鎖成功。

---

## 🐛 常見問題

### Q1: appcmd.exe 找不到？

**A**: 確認路徑是否正確：
```powershell
# 完整路徑
C:\Windows\System32\inetsrv\appcmd.exe

# 或添加到 PATH
$env:Path += ";C:\Windows\System32\inetsrv"
appcmd.exe unlock config -section:system.webServer/rewrite/allowedServerVariables
```

### Q2: 解鎖後還是錯誤？

**A**: 可能需要編輯 applicationHost.config：

1. 打開檔案（需要管理員權限）：
   ```
   C:\Windows\System32\inetsrv\config\applicationHost.config
   ```

2. 找到這一行：
   ```xml
   <section name="allowedServerVariables" overrideModeDefault="Deny" />
   ```

3. 改為：
   ```xml
   <section name="allowedServerVariables" overrideModeDefault="Allow" />
   ```

4. 儲存並重啟 IIS

### Q3: 簡化版效果如何？

**A**: 簡化版已經足夠支援 SSE 串流：

**關鍵配置**：
- ✅ `urlCompression` 禁用（防止整體壓縮）
- ✅ `httpCompression` 禁用 SSE（防止 SSE 壓縮）
- ✅ Flask Response Headers（在後端已設定）
- ✅ Waitress 參數優化（已完成）

**缺少的功能**：
- ❌ 移除 Accept-Encoding（影響較小）
- ❌ 恢復 Accept-Encoding（影響較小）

**結論**：簡化版對 SSE 串流的影響很小，應該可以正常工作。

---

## 🎯 推薦方案

### 如果你有管理員權限

**使用方案 1**（完整版）：
1. 解鎖 serverVariables
2. 使用完整的 web.config
3. 獲得最佳的 SSE 串流支援

### 如果你沒有管理員權限

**使用方案 2**（簡化版）：
1. 使用 `web.config.simple`
2. 不需要解鎖
3. 基本的 SSE 串流支援（足夠使用）

---

## 📝 簡化版 web.config 內容

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <!-- 禁用 IIS 壓縮 -->
        <urlCompression doStaticCompression="false" doDynamicCompression="false" />
        
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
        
        <!-- 禁用 text/event-stream 壓縮 -->
        <httpCompression>
            <dynamicTypes>
                <add mimeType="text/event-stream" enabled="false" />
            </dynamicTypes>
        </httpCompression>
        
        <!-- 靜態檔案 -->
        <staticContent>
            <mimeMap fileExtension=".vue" mimeType="text/plain" />
            <mimeMap fileExtension=".json" mimeType="application/json" />
        </staticContent>
    </system.webServer>
</configuration>
```

**特點**：
- ✅ 保持原有的 API Proxy 和 SPA Fallback
- ✅ 禁用壓縮（`urlCompression`）
- ✅ 禁用 SSE 壓縮（`httpCompression`）
- ✅ 不使用 serverVariables（無需解鎖）
- ✅ 不使用 outboundRules（無需解鎖）

---

## 🔧 部署步驟（簡化版）

### 1. 備份原始 web.config

```powershell
copy web.config web.config.backup
```

### 2. 使用簡化版

```powershell
copy web.config.simple web.config
```

### 3. 重啟 IIS 應用程式池

```powershell
Restart-WebAppPool -Name "YourAppPoolName"
```

或在 IIS 管理員中手動重啟。

### 4. 測試

1. 清空瀏覽器快取（Ctrl+F5）
2. 發送 chat 請求
3. 檢查是否逐字顯示

---

## ✅ 總結

### 兩種解決方案

1. **完整版**（需要管理員權限）
   - 解鎖 serverVariables
   - 使用完整的 web.config
   - 最佳的 SSE 支援

2. **簡化版**（無需管理員權限）
   - 使用 `web.config.simple`
   - 不需要解鎖
   - 足夠的 SSE 支援

### 核心配置（兩種方案都有）

- ✅ 禁用壓縮（`urlCompression`）
- ✅ 禁用 SSE 壓縮（`httpCompression`）
- ✅ API 反向代理
- ✅ SPA Fallback

### 建議

**先嘗試簡化版**（`web.config.simple`）：
- 更簡單
- 不需要管理員權限
- 應該足以支援 SSE 串流

**如果簡化版不夠**，再嘗試解鎖 serverVariables。

現在請使用 `web.config.simple` 並測試！🚀
