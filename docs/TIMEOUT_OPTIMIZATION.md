# API 超時優化 - 支持長 LLM 響應

## 問題描述

通過日誌分析發現，LLM API 響應時間約為 **54.37 秒**，這是因為：

1. **結構化 JSON 回應**：要求 LLM 返回完整的 JSON 格式（包含 summary、sections、key_points）
2. **詳細特質分析**：包含 27+ 個特質的完整說明和分析
3. **長文本生成**：max_tokens 設置為 5000，max_response_length 為 3000 字

原有的 60 秒超時設置過於接近實際響應時間，容易導致超時錯誤。

## 解決方案

將所有層級的超時設置從 **60 秒** 增加到 **90 秒**，提供充足的緩衝時間。

---

## 修改內容

### 1. 後端 LLM 調用超時

**文件**: `BackEnd/hr_consultation_service.py`

```python
# 修改前
with httpx.Client(timeout=60.0) as client:

# 修改後
with httpx.Client(timeout=90.0) as client:
```

**影響**: 後端調用 LLM API 的超時時間

---

### 2. 前端 API 請求超時

**文件**: `frontend/src/api/hrConsultation.js`

```javascript
// 修改前
const hrApiClient = axios.create({
  timeout: 60000, // 60 秒
});

// 修改後
const hrApiClient = axios.create({
  timeout: 90000, // 90 秒
});
```

**影響**: 前端調用後端 API 的超時時間

---

### 3. Uvicorn Keep-Alive 超時

**文件**: `BackEnd/main_api.py`

```python
# 修改前
timeout_keep_alive=75

# 修改後
timeout_keep_alive=120
```

**影響**: HTTP 連接保持活躍的時間

---

### 4. Render 部署配置

**文件**: `render.yaml`

```yaml
# 修改前
startCommand: cd BackEnd && uvicorn main_api:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75

# 修改後
startCommand: cd BackEnd && uvicorn main_api:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120
```

**影響**: 生產環境的 Keep-Alive 超時

---

### 5. 環境變數配置

**文件**: `BackEnd/.env.local`

```bash
# 新增
API_TIMEOUT=90
```

**說明**: 記錄 API 超時設置，方便未來調整

---

## 超時層級架構

```
用戶瀏覽器
    ↓ (90 秒超時)
前端 Axios 請求
    ↓ (90 秒超時)
後端 FastAPI
    ↓ (90 秒超時)
LLM API (DeepSeek)
    ↓ (實際響應: ~54 秒)
返回結構化 JSON
```

**時間分配：**

- LLM 實際響應: ~54 秒
- 網絡傳輸: ~2-3 秒
- 處理和解析: ~1-2 秒
- 緩衝時間: ~30 秒
- **總計設置: 90 秒**

---

## 性能數據

### LLM API 響應時間分析

根據 `BackEnd/logs/llm_api.log` 的實際數據：

```
⏱️ API 響應時間: 54.37 秒
📊 Token 使用統計:
   - Prompt Tokens: 2,847
   - Completion Tokens: 1,234
   - Total Tokens: 4,081
💬 原始回答長度: 2,456 字符
```

**影響因素：**

1. **Prompt 長度**: 2,847 tokens（包含完整候選人檔案和特質說明）
2. **回應長度**: 1,234 tokens（結構化 JSON 格式）
3. **模型**: DeepSeek-V3（較大模型，推理時間較長）
4. **溫度**: 0.7（較高創造性，生成時間較長）

---

## 優化建議

### 短期優化（已實施）

✅ **增加超時時間**: 60s → 90s  
✅ **統一所有層級**: 前端、後端、Keep-Alive 一致

### 中期優化（可選）

1. **減少 Prompt 長度**

   - 只包含相關特質（不是全部 27 個）
   - 簡化候選人檔案描述
   - 預期效果：減少 20-30% 響應時間

2. **調整 max_tokens**

   - 當前: 5000
   - 建議: 3000-4000
   - 預期效果：減少 10-15% 響應時間

3. **降低溫度**
   - 當前: 0.7
   - 建議: 0.5-0.6
   - 預期效果：減少 5-10% 響應時間

### 長期優化（未來考慮）

1. **流式響應 (Streaming)**

   ```python
   # 使用 SSE (Server-Sent Events) 流式返回
   response = client.post(..., stream=True)
   for chunk in response.iter_lines():
       yield chunk
   ```

   - 優點：用戶可以即時看到生成過程
   - 缺點：需要修改前端和後端架構

2. **快取常見問題**

   ```python
   # 快取相似問題的回答
   cache_key = f"{candidate_id}:{query_hash}"
   if cache_key in redis_cache:
       return cached_response
   ```

   - 優點：相同問題秒級響應
   - 缺點：需要 Redis 或類似快取系統

3. **使用更快的模型**
   - 當前: DeepSeek-V3（大模型）
   - 替代: DeepSeek-V2 或 GPT-3.5-turbo
   - 預期效果：減少 40-50% 響應時間
   - 缺點：可能降低回答質量

---

## 測試驗證

### 本地測試

```bash
# 1. 重啟後端服務
cd BackEnd
python main_api.py

# 2. 測試 HR 諮詢端點
curl -X POST http://localhost:8000/api/hr-consult/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "這個候選人適合什麼職位？",
    "candidate_id": 55
  }' \
  --max-time 95  # 設置 95 秒超時以驗證

# 3. 觀察日誌
tail -f BackEnd/logs/llm_api.log
```

### 生產環境測試

```bash
# 測試 Render 部署
curl -X POST https://talent-search-system.onrender.com/api/hr-consult/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "這個候選人適合什麼職位？",
    "candidate_id": 55
  }' \
  --max-time 95
```

---

## 監控指標

### 需要監控的指標

1. **LLM API 響應時間**

   - 目標: < 60 秒
   - 警告: > 70 秒
   - 錯誤: > 85 秒

2. **端到端響應時間**

   - 目標: < 65 秒
   - 警告: < 80 秒
   - 錯誤: > 90 秒

3. **超時錯誤率**
   - 目標: < 1%
   - 警告: 1-5%
   - 錯誤: > 5%

### 日誌查詢

```bash
# 查看最近的 LLM 響應時間
grep "API 響應時間" BackEnd/logs/llm_api.log | tail -20

# 統計平均響應時間
grep "API 響應時間" BackEnd/logs/llm_api.log | \
  awk '{print $5}' | \
  awk '{sum+=$1; count++} END {print "平均:", sum/count, "秒"}'

# 查找超時錯誤
grep -i "timeout\|timed out" BackEnd/logs/error.log
```

---

## 回滾計劃

如果新的超時設置導致問題，可以快速回滾：

```bash
# 1. 恢復到 60 秒設置
git revert <commit-hash>

# 2. 或手動修改
# - hr_consultation_service.py: timeout=60.0
# - hrConsultation.js: timeout: 60000
# - main_api.py: timeout_keep_alive=75
# - render.yaml: --timeout-keep-alive 75

# 3. 重新部署
git add -A
git commit -m "Revert: 恢復 60 秒超時設置"
git push
```

---

## 相關文件

- [API 超時修復](./BUGFIX_API_TIMEOUT.md) - 之前的 60 秒超時修復
- [結構化響應功能](./FEATURE_STRUCTURED_RESPONSE.md) - JSON 格式回應實現
- [Prompt 增強](./PROMPT_ENHANCEMENT_TRAIT_DESCRIPTIONS.md) - 特質說明增強

---

**修改日期**: 2025-12-19  
**修改原因**: LLM 響應時間 54 秒，接近 60 秒超時限制  
**修改內容**: 所有超時設置從 60 秒增加到 90 秒  
**預期效果**: 消除超時錯誤，提供 36 秒緩衝時間
