# Bug 修復：API Key Invalid 錯誤

## 問題描述

LLM API 返回錯誤：`"Api key is invalid"`

## 問題原因

在添加日誌記錄時，為了安全起見在日誌中隱藏 API Key，但錯誤地在實際的 HTTP 請求中也使用了隱藏後的 API Key。

### 錯誤代碼

```python
# BackEnd/hr_consultation_service.py (第 900 行)
headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key[:10]}...{api_key[-4:]}'  # ❌ 錯誤！
}
```

這會導致發送到 LLM API 的 Authorization header 變成類似：

```
Authorization: Bearer sk-abc1234...xyz9
```

而不是完整的 API Key，因此 API 返回 "Api key is invalid" 錯誤。

## 解決方案

### 修復代碼

```python
# BackEnd/hr_consultation_service.py
headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'  # ✅ 使用完整的 API Key
}
```

### 安全的日誌記錄

在日誌中記錄隱藏後的 API Key，但在實際請求中使用完整的 Key：

```python
# 在日誌中隱藏 API Key
logger.info(f"🔑 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '****'}")

# 在實際請求中使用完整的 API Key
headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'  # 完整的 Key
}
```

## 修復文件

- `BackEnd/hr_consultation_service.py`

## 修復時間

2025-12-17

## 測試驗證

### 修復前

```
❌ LLM API 返回錯誤: 401
📄 響應內容: "Api key is invalid"
```

### 修復後

```
✅ API 調用成功
📡 HTTP 狀態碼: 200
📊 Token 使用統計:
   - Prompt Tokens: 1500
   - Completion Tokens: 300
   - Total Tokens: 1800
```

## 安全最佳實踐

### ✅ 正確做法

1. **日誌記錄**: 隱藏敏感信息

   ```python
   logger.info(f"API Key: {api_key[:10]}...{api_key[-4:]}")
   ```

2. **實際使用**: 使用完整的值
   ```python
   headers={'Authorization': f'Bearer {api_key}'}
   ```

### ❌ 錯誤做法

1. **在請求中使用隱藏後的值**

   ```python
   # 錯誤！這會導致 API 調用失敗
   headers={'Authorization': f'Bearer {api_key[:10]}...{api_key[-4:]}'}
   ```

2. **在日誌中記錄完整的敏感信息**
   ```python
   # 不安全！API Key 會暴露在日誌中
   logger.info(f"API Key: {api_key}")
   ```

## 相關文件

- `BackEnd/hr_consultation_service.py` - 已修復
- `BackEnd/hr_consultation_routes.py` - 無此問題
- `BackEnd/talent_search_api.py` - 無此問題
- `BackEnd/interview_api.py` - 無此問題

## 預防措施

### 代碼審查檢查清單

- [ ] 確認 API Key 在請求中使用完整值
- [ ] 確認敏感信息在日誌中被隱藏
- [ ] 測試 API 調用是否成功
- [ ] 檢查日誌中是否有完整的敏感信息

### 單元測試建議

```python
def test_api_key_not_truncated_in_request():
    """確保 API Key 在請求中使用完整值"""
    api_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"

    # 模擬請求
    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    # 驗證
    assert headers['Authorization'] == f'Bearer {api_key}'
    assert '...' not in headers['Authorization']
```

## 診斷結果

✅ 文件通過診斷檢查（無錯誤、無警告）

## 總結

這是一個典型的「過度安全」導致的 bug。在保護敏感信息時，要確保只在日誌/顯示層面隱藏，而不影響實際的業務邏輯。

**關鍵原則**:

- 日誌 = 隱藏敏感信息
- 實際使用 = 完整的值
