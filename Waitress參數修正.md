# Waitress 參數錯誤修正

## ❌ 錯誤

```
ValueError: Unknown adjustment 'outbuf_high_water_mark'
```

## ✅ 原因

`outbuf_high_water_mark` 不是 Waitress 的有效參數。

## ✅ 修正後的參數

### 有效的 Waitress 參數（用於 SSE 串流優化）

```python
serve(
    app, 
    host=host, 
    port=port, 
    threads=6,
    _quiet=False,
    # 以下是有效的 Waitress 參數
    channel_timeout=300,      # ✅ 延長超時
    outbuf_overflow=1048576,  # ✅ 增大輸出緩衝
    send_bytes=8192,          # ✅ 減少每次發送字節數
    recv_bytes=8192,          # ✅ 接收緩衝大小
    asyncore_use_poll=True    # ✅ 使用 poll() 提升效能
)
```

## 📋 Waitress 常用參數列表

### 網路相關

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `host` | '0.0.0.0' | 綁定的 IP 地址 |
| `port` | 8080 | 監聽的端口 |
| `ipv4` | True | 啟用 IPv4 |
| `ipv6` | False | 啟用 IPv6 |

### 效能相關

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `threads` | 4 | 工作線程數 |
| `asyncore_use_poll` | False | 使用 poll() 而非 select() |
| `channel_timeout` | 120 | 通道超時（秒） |

### 緩衝相關

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `recv_bytes` | 8192 | 接收緩衝大小 |
| `send_bytes` | 18000 | 發送緩衝大小 |
| `outbuf_overflow` | 1048576 | 輸出緩衝溢出限制 |
| `inbuf_overflow` | 512000 | 輸入緩衝溢出限制 |

### 連線相關

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `backlog` | 1024 | 連線佇列大小 |
| `connection_limit` | 100 | 最大同時連線數 |
| `cleanup_interval` | 30 | 清理間隔（秒） |

### 其他

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `_quiet` | False | 是否靜默模式 |
| `ident` | 'waitress' | Server 識別字串 |
| `expose_tracebacks` | False | 是否暴露錯誤堆疊 |

## ⚠️ 無效的參數（不要使用）

以下參數**不存在**於 Waitress：
- ❌ `outbuf_high_water_mark`
- ❌ `outbuf_low_water_mark`
- ❌ `buffer_size`
- ❌ `max_request_body_size`（正確的是 `max_request_body_size` 但在不同版本可能不同）

## 🔍 如何查看所有可用參數

```python
from waitress.adjustments import Adjustments
import inspect

# 查看 Adjustments 類別的所有參數
sig = inspect.signature(Adjustments.__init__)
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        print(f"{param_name}: {param.default}")
```

## 📝 SSE 串流優化建議

### 最小配置（推薦）

```python
serve(
    app,
    host='0.0.0.0',
    port=5000,
    threads=6,
    channel_timeout=300,  # 延長超時
    send_bytes=8192       # 啟用分塊傳輸
)
```

### 完整配置（最佳化）

```python
serve(
    app,
    host='0.0.0.0',
    port=5000,
    threads=6,
    _quiet=False,
    # SSE 優化
    channel_timeout=300,
    outbuf_overflow=1048576,
    send_bytes=8192,
    recv_bytes=8192,
    asyncore_use_poll=True,
    # 效能優化
    backlog=2048,
    connection_limit=200,
    cleanup_interval=60
)
```

## 🎯 總結

### 修正步驟

1. ✅ 移除 `outbuf_high_water_mark` 參數
2. ✅ 使用有效的參數：`channel_timeout`, `outbuf_overflow`, `send_bytes`
3. ✅ 添加 `recv_bytes` 和 `asyncore_use_poll` 提升效能
4. ✅ 重新啟動 Waitress

### 核心參數（SSE 串流）

- `channel_timeout=300` - 延長超時
- `send_bytes=8192` - 啟用分塊傳輸
- `outbuf_overflow=1048576` - 增大緩衝

這些參數足以支援 SSE 串流！
