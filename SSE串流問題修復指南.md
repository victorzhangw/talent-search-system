# SSE 串流問題修復指南

## 🐛 問題描述

**症狀**：
- 本地開發環境（Flask dev server）：✅ 文字逐字顯示（打字機效果）
- 正式環境（IIS + Waitress）：❌ 文字一次全部顯示

**根本原因**：
IIS 和 Waitress 預設會緩衝 HTTP 回應，導致 Server-Sent Events (SSE) 串流失效。

---

## ✅ 解決方案

### 1. Flask Response Headers（後端修改）

**檔案**：`BackEnd/api_v2/routes/chat.py`

**修改內容**：添加關鍵 HTTP headers 來禁用緩衝

```python
# Create response with proper headers to prevent buffering
response = Response(stream_with_context(generate()), mimetype='text/event-stream')

# Critical headers to disable buffering in production (IIS, Nginx, Waitress)
response.headers['Cache-Control'] = 'no-cache, no-transform'
response.headers['X-Accel-Buffering'] = 'no'  # Nginx
response.headers['Content-Encoding'] = 'none'  # Prevent compression

return response
```

**說明**：
- `Cache-Control: no-cache, no-transform` - 禁止快取和轉換
- `X-Accel-Buffering: no` - 禁用 Nginx 緩衝（IIS 也會參考）
- `Content-Encoding: none` - 防止壓縮（壓縮會破壞串流）

---

### 2. Waitress 配置優化

**檔案**：`BackEnd/api_v2/run_waitress.py`

**修改內容**：優化 Waitress 參數以支援 SSE 串流

```python
serve(
    app, 
    host=host, 
    port=port, 
    threads=6,
    _quiet=False,
    # SSE Streaming optimization (only valid Waitress parameters)
    channel_timeout=300,      # 5 minutes for long SSE connections
    outbuf_overflow=1048576,  # 1MB overflow buffer
    send_bytes=8192,          # 8KB per send (enable chunked streaming)
    recv_bytes=8192,          # 8KB receive buffer
    asyncore_use_poll=True    # Use poll() instead of select()
)
```

**參數說明**：

| 參數 | 值 | 說明 |
|------|-----|------|
| `channel_timeout` | 300 | 延長超時到 5 分鐘，支援長時間 SSE 連線 |
| `outbuf_overflow` | 1048576 | 增大輸出緩衝溢出限制到 1MB |
| `send_bytes` | 8192 | 減少每次發送的字節數到 8KB，啟用分塊串流 |
| `recv_bytes` | 8192 | 接收緩衝大小 8KB |
| `asyncore_use_poll` | True | 使用 poll() 而非 select()，更好的效能 |

---

### 3. IIS 配置（web.config）

**檔案**：IIS 網站根目錄的 `web.config`

**添加以下配置**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <!-- 禁用 IIS 的輸出緩衝 -->
    <httpProtocol>
      <customHeaders>
        <add name="X-Content-Type-Options" value="nosniff" />
      </customHeaders>
    </httpProtocol>
    
    <!-- 禁用壓縮（對 SSE 很重要） -->
    <urlCompression doStaticCompression="false" doDynamicCompression="false" />
    
    <!-- 反向代理設定 -->
    <rewrite>
      <rules>
        <rule name="ReverseProxyInboundRule1" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="http://localhost:5000/{R:1}" />
          <serverVariables>
            <!-- 禁用 IIS 緩衝 -->
            <set name="HTTP_X_ORIGINAL_ACCEPT_ENCODING" value="{HTTP_ACCEPT_ENCODING}" />
            <set name="HTTP_ACCEPT_ENCODING" value="" />
          </serverVariables>
        </rule>
      </rules>
      <outboundRules>
        <!-- 確保 SSE 回應不被修改 -->
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
    </rewrite>
    
    <!-- 禁用 IIS 的回應緩衝 -->
    <httpCompression>
      <scheme name="gzip" dll="%Windir%\system32\inetsrv\gzip.dll" />
      <dynamicTypes>
        <add mimeType="text/event-stream" enabled="false" />
      </dynamicTypes>
      <staticTypes>
        <add mimeType="text/event-stream" enabled="false" />
      </staticTypes>
    </httpCompression>
  </system.webServer>
</configuration>
```

**關鍵配置說明**：
1. **禁用壓縮**：`urlCompression` 和 `httpCompression` 都設為 false
2. **移除 Accept-Encoding**：防止 IIS 嘗試壓縮回應
3. **禁用 text/event-stream 壓縮**：明確禁用 SSE 的壓縮

---

### 4. IIS Application Initialization（可選）

如果使用 IIS Application Initialization，需要確保不會預載入 SSE 端點。

**web.config 添加**：

```xml
<system.webServer>
  <applicationInitialization doAppInitAfterRestart="true">
    <!-- 不要預載入 /chat/ 端點 -->
    <add initializationPage="/api/v2/candidates/" />
  </applicationInitialization>
</system.webServer>
```

---

## 🔍 診斷方法

### 1. 檢查 Response Headers

在瀏覽器開發者工具中：

1. F12 → Network 標籤
2. 發送 chat 請求
3. 點擊 `/chat/` 請求
4. 查看 Response Headers

**應該看到**：
```
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
X-Accel-Buffering: no
Content-Encoding: none
Transfer-Encoding: chunked  ← 重要！表示分塊傳輸
```

**如果沒有 `Transfer-Encoding: chunked`**：
- 表示回應被緩衝了
- 檢查 IIS 和 Waitress 配置

---

### 2. 檢查 SSE 事件流

在瀏覽器 Console 中：

```javascript
// 檢查 EventSource 連線狀態
console.log('EventSource readyState:', eventSource.readyState)
// 0: CONNECTING
// 1: OPEN
// 2: CLOSED

// 監聽 SSE 事件
eventSource.onmessage = (event) => {
  console.log('Received:', event.data)
  console.log('Timestamp:', new Date().toISOString())
}
```

**正常串流**：
```
Received: {"type":"meta","intent":"UC-GENERAL"}
Timestamp: 2026-01-15T14:15:30.123Z
Received: {"type":"token","content":"根據"}
Timestamp: 2026-01-15T14:15:30.234Z  ← 時間差很小
Received: {"type":"token","content":"特質"}
Timestamp: 2026-01-15T14:15:30.345Z  ← 逐字接收
```

**被緩衝**：
```
Received: {"type":"meta","intent":"UC-GENERAL"}
Timestamp: 2026-01-15T14:15:30.123Z
（等待 5-10 秒）
Received: {"type":"token","content":"根據特質分析...（完整內容）"}
Timestamp: 2026-01-15T14:15:35.456Z  ← 一次全部接收
```

---

### 3. 測試 Waitress 直接連線

**繞過 IIS，直接測試 Waitress**：

```bash
# 在瀏覽器中直接訪問
http://localhost:5000/api/v2/chat/

# 或使用 curl 測試
curl -N -X POST http://localhost:5000/api/v2/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query":"測試","candidate_ids":[58],"session_id":"test"}'
```

**如果直接連 Waitress 可以串流**：
- 問題在 IIS 配置
- 檢查 web.config

**如果直接連 Waitress 也不能串流**：
- 問題在 Waitress 配置
- 檢查 run_waitress.py 參數

---

## 📊 效能對比

### 修改前

```
使用者發送問題
    ↓
等待 5-10 秒
    ↓
完整回應一次顯示（500+ 字）
```

**問題**：
- ❌ 使用者體驗差（長時間等待）
- ❌ 看起來像系統卡住
- ❌ 無法提前看到部分結果

### 修改後

```
使用者發送問題
    ↓
立即顯示「思考中」
    ↓
0.5 秒後開始逐字顯示
    ↓
打字機效果（每 0.1 秒顯示 1-2 個字）
```

**優勢**：
- ✅ 即時反饋
- ✅ 流暢的使用者體驗
- ✅ 可以提前閱讀部分結果

---

## 🎯 完整部署檢查清單

### 後端修改

- [x] `chat.py` - 添加 Response headers
- [x] `run_waitress.py` - 優化 Waitress 參數

### IIS 配置

- [ ] `web.config` - 禁用壓縮
- [ ] `web.config` - 禁用緩衝
- [ ] `web.config` - 設定反向代理
- [ ] 重啟 IIS 應用程式池

### 測試驗證

- [ ] 檢查 Response Headers（Transfer-Encoding: chunked）
- [ ] 測試 SSE 串流（逐字顯示）
- [ ] 檢查 Console 無錯誤
- [ ] 測試長時間連線（不超時）

---

## 🔧 常見問題

### Q1: 修改後還是一次全部顯示？

**A**: 檢查以下項目：
1. 確認後端已重啟（Waitress）
2. 確認 IIS 應用程式池已重啟
3. 清空瀏覽器快取（Ctrl+F5）
4. 檢查 web.config 是否正確
5. 使用 curl 直接測試 Waitress

### Q2: 連線超時（502 Bad Gateway）？

**A**: 增加超時設定：
```python
# run_waitress.py
channel_timeout=600  # 增加到 10 分鐘
```

```xml
<!-- web.config -->
<system.webServer>
  <aspNetCore requestTimeout="00:10:00" />
</system.webServer>
```

### Q3: 前端收不到任何回應？

**A**: 檢查 CORS 設定：
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

## 📝 總結

### 關鍵修改

1. **Flask Response Headers** - 禁用快取和壓縮
2. **Waitress 參數** - 優化緩衝和超時
3. **IIS web.config** - 禁用壓縮和緩衝

### 核心原理

SSE 串流需要：
- ✅ `Transfer-Encoding: chunked`（分塊傳輸）
- ✅ 禁用壓縮（gzip 會破壞串流）
- ✅ 禁用緩衝（立即發送每個 chunk）
- ✅ 延長超時（支援長時間連線）

### 測試方法

1. 檢查 Response Headers
2. 觀察 Console 時間戳記
3. 直接測試 Waitress
4. 使用 curl 驗證

修改完成後，重啟服務並測試！🚀
