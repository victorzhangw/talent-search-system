# Bug 修復：API 超時問題

## 問題描述

前端顯示「無法連接到 HR 諮詢服務，請檢查網絡連接」，但後端日誌顯示 LLM API 已正常返回數據。

## 根本原因

生成 2000 字的結構化 JSON 回應需要較長時間（20-40 秒），超過了原有的超時設置：

1. **前端超時**：30 秒
2. **後端 LLM API 超時**：30 秒
3. **實際處理時間**：可能需要 30-40 秒

當處理時間接近或超過 30 秒時，前端會先超時並顯示錯誤，即使後端最終成功返回了數據。

## 超時層級

```
用戶請求
    ↓
前端 axios (30秒) ← 超時！
    ↓
FastAPI/uvicorn (默認無限制)
    ↓
後端 httpx (30秒) ← 可能超時！
    ↓
LLM API (處理中...)
    ↓
返回結果 (但前端已超時)
```

## 修復方案

### 1. 增加前端超時

**文件**: `frontend/src/api/hrConsultation.js`

```javascript
const hrApiClient = axios.create({
  baseURL: import.meta.env.VITE_HR_API_BASE_URL || "http://localhost:8000",
  timeout: 60000, // 30秒 → 60秒
  ...
});
```

### 2. 增加後端 LLM API 超時

**文件**: `BackEnd/hr_consultation_service.py`

```python
# 增加超時時間以支持長回應生成（60 秒）
with httpx.Client(timeout=60.0) as client:  # 30秒 → 60秒
    response = client.post(...)
```

### 3. 配置 uvicorn 超時

**文件**: `BackEnd/main_api.py`

```python
uvicorn.run(
    "main_api:app",
    host=host,
    port=port,
    reload=True,
    log_level="info",
    timeout_keep_alive=75,  # Keep-alive 超時（秒）
    timeout_graceful_shutdown=10  # 優雅關閉超時（秒）
)
```

## 超時設置總結

| 層級               | 原設置 | 新設置 | 說明              |
| ------------------ | ------ | ------ | ----------------- |
| 前端 axios         | 30 秒  | 60 秒  | 等待後端回應      |
| 後端 httpx         | 30 秒  | 60 秒  | 等待 LLM API      |
| uvicorn keep-alive | 默認   | 75 秒  | 保持連接          |
| LLM API            | N/A    | N/A    | 由 LLM 服務商控制 |

## 為什麼選擇 60 秒？

1. **LLM 處理時間**：

   - 2000 字結構化回應
   - 包含多個章節和要點
   - 需要解析特質說明
   - 預估：20-40 秒

2. **網絡延遲**：

   - API 往返時間：1-3 秒
   - 資料庫查詢：1-2 秒
   - 總計：5-10 秒

3. **安全邊際**：

   - 60 秒 = 40 秒處理 + 10 秒網絡 + 10 秒緩衝

4. **用戶體驗**：
   - 60 秒是可接受的等待時間
   - 超過 60 秒應該優化 Prompt 或減少字數

## 優化建議

### 短期優化（已實施）

✅ 增加超時時間到 60 秒

### 中期優化（建議）

1. **添加進度提示**

   ```javascript
   // 前端顯示處理進度
   "正在分析測評數據...";
   "正在生成專業建議...";
   "即將完成...";
   ```

2. **流式回應**

   ```python
   # 使用 Server-Sent Events (SSE) 流式返回
   # 讓用戶看到逐步生成的內容
   ```

3. **緩存機制**
   ```python
   # 相同問題的回答緩存 5 分鐘
   # 減少重複的 LLM 調用
   ```

### 長期優化（建議）

1. **異步處理**

   ```
   用戶提交問題 → 返回任務 ID → 輪詢結果
   ```

2. **預生成常見問題**

   ```
   候選人上傳後，預生成常見問題的回答
   ```

3. **LLM 優化**
   ```
   - 使用更快的模型
   - 減少 Prompt 長度
   - 優化 temperature 和 max_tokens
   ```

## 測試驗證

### 測試步驟

1. 重啟服務

   ```bash
   stop.bat
   start.bat
   ```

2. 測試長回應

   - 選擇候選人
   - 提問複雜問題
   - 觀察等待時間

3. 檢查日誌
   ```bash
   # 查看 API 響應時間
   tail -f BackEnd/logs/llm_api.log | grep "API 響應時間"
   ```

### 預期結果

✅ 前端不再顯示超時錯誤  
✅ 能夠等待 LLM 完成處理  
✅ 成功顯示結構化回應  
✅ 日誌顯示完整的處理流程

### 如果仍然超時

1. **檢查實際處理時間**

   ```
   查看日誌中的 "API 響應時間"
   如果超過 50 秒，考慮：
   - 減少 LLM_MAX_RESPONSE_LENGTH
   - 簡化 Prompt
   - 使用更快的模型
   ```

2. **檢查網絡連接**

   ```
   測試到 LLM API 的連接速度
   ```

3. **檢查 LLM API 狀態**
   ```
   確認 LLM 服務商沒有限流或故障
   ```

## 監控建議

添加超時監控：

```python
# 記錄超時事件
if elapsed_time > 45:
    logger.warning(f"⚠️ LLM 回應時間較長: {elapsed_time:.2f} 秒")

if elapsed_time > 55:
    logger.error(f"❌ LLM 回應時間過長: {elapsed_time:.2f} 秒，接近超時")
```

## 相關配置

- 前端超時：`frontend/src/api/hrConsultation.js`
- 後端超時：`BackEnd/hr_consultation_service.py`
- 服務器配置：`BackEnd/main_api.py`
- 字數限制：`BackEnd/.env.local` (LLM_MAX_RESPONSE_LENGTH)

## 修復日期

2025-12-18
