# 人才搜索系統 - LLM 整合技術文檔

## 概述

本系統整合 **DeepSeek-V3** 大語言模型，實現資料庫驅動的 AI 人才搜索。

### 核心原則

1. ✅ **特質來自資料庫** - 所有特質從 `trait` 表載入
2. ✅ **LLM 生成 SQL** - 將自然語言轉換為精確的 SQL 查詢
3. ✅ **真實分數匹配** - 基於候選人的實際測評分數計算匹配度

## 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (Vue.js)                            │
│              talent-chat-frontend.html                       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/WebSocket
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI 後端 (Python)                           │
│           BackEnd/talent_search_api.py                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           LLMService (DeepSeek-V3)                   │  │
│  │  • 查詢解析 (parse_query)                            │  │
│  │  • 推薦理由生成 (generate_match_reason)              │  │
│  └──────────────────────────────────────────────────────┘  │
│                     │                                        │
│  ┌──────────────────┴──────────────────────────────────┐  │
│  │        TalentSearchEngine                            │  │
│  │  • 資料庫查詢                                         │  │
│  │  • 匹配分數計算                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────┬────────────────────────┘
             │                        │
             ↓                        ↓
    ┌────────────────┐      ┌────────────────────┐
    │  DeepSeek API  │      │  PostgreSQL DB     │
    │  (SiliconFlow) │      │  (via SSH Tunnel)  │
    └────────────────┘      └────────────────────┘
```

## LLM 功能

### 1. 自然語言查詢解析

**輸入**: "我需要一個善於溝通的銷售人員"

**LLM 分析輸出**:

```json
{
  "traits": ["溝通能力", "說服力"],
  "role": "銷售人員",
  "keywords": ["溝通", "銷售", "客戶"],
  "requirements": {
    "personality": ["外向", "親和力"],
    "skills": ["客戶關係管理", "商務談判"]
  },
  "summary": "尋找具備優秀溝通能力的銷售人員"
}
```

### 2. 個性化推薦理由生成

**輸入**:

- 候選人資訊
- 用戶查詢
- 匹配分數

**LLM 生成輸出**:

```
"王小明在溝通能力方面表現優異（92分），已完成3項測評，具備豐富的銷售經驗，高度符合您的需求"
```

### 3. 澄清問題生成

當用戶查詢模糊時，LLM 會生成澄清問題：

**輸入**: "找一個好的人"

**LLM 輸出**:

```json
{
  "clarification": "請問您需要什麼職位的人才？需要具備哪些特質或技能？",
  "questions": [
    "您需要什麼職位的人才？",
    "需要具備哪些特質？",
    "有經驗要求嗎？"
  ]
}
```

## 技術細節

### LLM 配置

```python
LLM_CONFIG = {
    'api_key': 'sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff',
    'api_host': 'https://api.siliconflow.cn',
    'model': 'deepseek-ai/DeepSeek-V3',
    'endpoint': 'https://api.siliconflow.cn/v1/chat/completions'
}
```

### 系統 Prompt

```python
def get_system_prompt():
    return """你是一個專業的人才搜索助手，專門幫助 HR 和招聘人員理解和分析人才需求。

你的任務是：
1. 理解用戶用自然語言描述的人才需求
2. 提取關鍵的特質、技能和職位要求
3. 將需求轉換為結構化的搜索參數

請以 JSON 格式輸出分析結果..."""
```

### API 調用流程

1. **接收用戶查詢** → 前端發送到後端
2. **LLM 分析** → 調用 DeepSeek API 解析查詢
3. **資料庫搜索** → 根據分析結果查詢候選人
4. **匹配計算** → 計算每個候選人的匹配分數
5. **LLM 生成理由** → 為每個候選人生成推薦理由
6. **返回結果** → 發送到前端顯示

## 降級策略

系統實作了完善的降級機制，當 LLM API 不可用時：

1. **查詢解析降級** → 使用關鍵字匹配
2. **理由生成降級** → 使用模板化理由
3. **錯誤處理** → 友好的錯誤提示

```python
async def parse_query(self, query: str):
    # 嘗試使用 LLM
    llm_result = await self.llm_service.analyze_query(query)

    if llm_result['success']:
        return llm_result['analysis']

    # LLM 失敗，降級到關鍵字匹配
    return self._parse_query_simple(query)
```

## 效能優化

### 1. 非同步處理

使用 `async/await` 處理 LLM API 調用，避免阻塞：

```python
async def analyze_query(self, query: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(...)
```

### 2. 超時控制

設定合理的超時時間（30 秒），避免長時間等待：

```python
async with httpx.AsyncClient(timeout=30.0) as client:
```

### 3. 批次處理限制

限制同時處理的候選人數量，避免過多 API 調用：

```python
for candidate in raw_candidates[:20]:  # 限制處理數量
```

## 測試

### 測試 LLM 連接

```cmd
cd BackEnd
venv\Scripts\activate
python test_llm.py
```

### 測試完整流程

1. 啟動 API 服務：

```cmd
cd BackEnd
start_api.bat
```

2. 開啟前端：

```
talent-chat-frontend.html
```

3. 輸入測試查詢：

- "我需要一個善於溝通的銷售人員"
- "找一個有創造力的設計師"
- "尋找分析能力強的數據分析師"

## API 端點

### POST /api/search

使用 LLM 增強的搜索端點。

**請求**:

```json
{
  "query": "我需要一個善於溝通的銷售人員",
  "filters": null
}
```

**回應**:

```json
{
  "candidates": [
    {
      "id": 1,
      "name": "王小明",
      "email": "wang@example.com",
      "test_results": [...],
      "match_score": 0.85,
      "match_reason": "王小明在溝通能力方面表現優異（92分）..."
    }
  ],
  "total": 10,
  "query_understanding": "尋找具備優秀溝通能力的銷售人員",
  "suggestions": ["嘗試添加更多具體要求"]
}
```

### WebSocket /ws

支援即時對話的 WebSocket 端點，同樣使用 LLM 增強。

## 成本考量

### DeepSeek-V3 定價

- 輸入：約 $0.14 / 1M tokens
- 輸出：約 $0.28 / 1M tokens

### 預估成本

假設每次搜索：

- 查詢解析：~500 tokens
- 推薦理由生成（5 個候選人）：~1000 tokens
- 總計：~1500 tokens/次

**每月成本預估**（1000 次搜索）：

- 1000 次 × 1500 tokens = 1.5M tokens
- 成本：約 $0.21 - $0.42

非常經濟實惠！

## 優勢

✅ **準確理解** - LLM 深度理解自然語言需求
✅ **個性化** - 為每個候選人生成獨特的推薦理由
✅ **智能澄清** - 自動識別模糊需求並提出問題
✅ **可擴展** - 易於添加新功能和優化
✅ **成本低** - DeepSeek-V3 性價比極高
✅ **穩定性** - 完善的降級機制確保服務可用

## 未來擴展

### 1. 向量搜索

整合向量資料庫實現語義搜索：

```python
# 使用 Embedding 模型
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
query_embedding = model.encode(query)
```

### 2. RAG 架構

檢索增強生成，提升推薦準確性：

```python
# 1. 檢索相關候選人
candidates = vector_search(query_embedding)

# 2. 增強 Prompt
prompt = f"""
基於以下候選人資料：
{candidates_data}

用戶需求：{query}

請生成推薦理由...
"""
```

### 3. 多輪對話

實作對話狀態管理：

```python
class ConversationManager:
    def __init__(self):
        self.sessions = {}

    def update_context(self, session_id, message):
        # 維護對話歷史
        pass
```

### 4. 用戶偏好學習

基於歷史搜索學習用戶偏好：

```python
def learn_preferences(user_id, search_history):
    # 分析用戶的搜索模式
    # 調整推薦權重
    pass
```

## 疑難排解

### LLM API 調用失敗

**症狀**: 搜索時顯示 "LLM 分析失敗"

**解決方案**:

1. 檢查網路連接
2. 確認 API Key 正確
3. 查看 API 服務狀態
4. 系統會自動降級到關鍵字匹配

### 回應速度慢

**症狀**: 搜索需要很長時間

**解決方案**:

1. 減少處理的候選人數量
2. 調整 LLM 的 max_tokens 參數
3. 使用快取機制
4. 考慮批次處理

### JSON 解析錯誤

**症狀**: "JSON 解析失敗"

**解決方案**:

1. 檢查 LLM 回應格式
2. 添加更嚴格的 Prompt 指示
3. 實作 JSON 修復邏輯
4. 降級到簡單匹配

## 總結

本系統成功整合了 DeepSeek-V3 大語言模型，實現了：

1. ✅ **智能查詢理解** - 深度理解自然語言需求
2. ✅ **個性化推薦** - AI 生成的匹配理由
3. ✅ **穩定可靠** - 完善的降級機制
4. ✅ **成本效益** - 極低的 API 調用成本
5. ✅ **易於擴展** - 清晰的架構設計

這是一個真正的 AI 驅動人才搜索系統！🎉
