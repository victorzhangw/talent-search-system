# 完整的 Chat 流程說明 - 使用批次特質報告

## 🎯 優化後的完整流程

```
1. 使用者勾選候選人（例如：2 位）
   ↓
2. 點擊「開始提問」
   ↓
3. 【批次獲取特質報告】
   - 前端提取 assessment_ids: [62, 63]
   - POST /api/v2/reports/batch
   - 後端呼叫 POST /v1/assessments/latest:batch
   - 一次獲取所有候選人的報告
   ↓
4. 【儲存到 Session Storage】
   - Key: traitty_batch_reports
   - Value: {
       "58": { assessment_id: 62, traits: [...], assessment_date: "..." },
       "59": { assessment_id: 63, traits: [...], assessment_date: "..." }
     }
   ↓
5. 進入 Chat 模式
   ↓
6. 使用者輸入問題並點擊發送
   ↓
7. 【從 Session Storage 讀取報告】
   - 前端讀取 traitty_batch_reports
   - 準備完整的 payload
   ↓
8. 【發送 Chat 請求】
   - POST /chat/
   - Payload 包含:
     * query: "與團隊合作的適配性如何？"
     * candidate_ids: [58, 59]
     * candidates_info: [完整候選人資料]
     * trait_reports: {完整特質報告}  ← 新增！
     * session_id: "uuid"
   ↓
9. 【後端處理】
   - 接收 trait_reports
   - 優先使用前端提供的報告
   - 跳過呼叫上游 API 獲取評估
   - 直接合併資料並建立 RAG Context
   ↓
10. 【LLM 生成回應】
    - 使用完整的特質資料
    - 串流回傳給前端
```

---

## 📡 完整的 Chat Payload

### Request

```json
POST /chat/
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "與團隊合作的適配性如何？",
  "candidate_ids": [58, 59],
  "candidates_info": [
    {
      "candidate_id": 58,
      "name": "吳至平",
      "email": "peterwuzhp@outlook.com",
      "phone": "",
      "enterprise_name": "WePredict",
      "position": "",
      "status": "employed",
      "created_at": "2025-12-01T14:18:37.437348Z",
      "last_assessment_date": "2025-12-03T09:30:48.315395Z",
      "latest_assessment": {
        "assessment_id": 62,
        "project_code": 3,
        "project_name": "CIA綜合人才洞察評鑑",
        "score_value": 56
      }
    },
    {
      "candidate_id": 59,
      "name": "阮暐捷",
      ...
    }
  ],
  "trait_reports": {
    "58": {
      "assessment_id": 62,
      "traits": [
        {
          "name": "同理心",
          "score": 56,
          "band": "Mid"
        },
        {
          "name": "洞察力",
          "score": 72,
          "band": "High"
        },
        ...
      ],
      "assessment_date": "2025-12-03T09:30:48.315395Z"
    },
    "59": {
      "assessment_id": 63,
      "traits": [...],
      "assessment_date": "2025-12-03T09:30:44.494004Z"
    }
  },
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## 💻 前端實作

### 1. 發送訊息時讀取報告

**檔案**: `ChatContainer.vue`  
**函數**: `sendMessage()`

```javascript
const sendMessage = async (e) => {
  // ... 基本驗證 ...
  
  // Load trait reports from Session Storage
  let traitReports = {}
  try {
    const cachedReports = sessionStorage.getItem('traitty_batch_reports')
    if (cachedReports) {
      traitReports = JSON.parse(cachedReports)
      console.log('[ChatContainer] Loaded trait reports:', Object.keys(traitReports).length, 'reports')
    } else {
      console.warn('[ChatContainer] No trait reports found in Session Storage')
    }
  } catch (e) {
    console.error('[ChatContainer] Failed to load trait reports:', e)
  }
  
  // Send chat request
  const response = await fetch(`${serverRoot}/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${userToken.value}`
    },
    body: JSON.stringify({
      query: query,
      candidate_ids: selectedCandidateIds.value,
      candidates_info: selectedCandidatesObjects.value.map(c => ({...})),
      trait_reports: traitReports,  // NEW: Include trait reports
      session_id: currentSessionId.value
    })
  })
}
```

---

## 🔧 後端實作

### 1. Chat 路由接收報告

**檔案**: `routes/chat.py`

```python
@bp.route('/', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query')
    candidate_ids = data.get('candidate_ids', [])
    candidates_info = data.get('candidates_info', [])
    trait_reports = data.get('trait_reports', {})  # NEW
    session_id = data.get('session_id', 'default_session')
    
    print(f"[Chat] Received trait_reports for {len(trait_reports)} candidates")
    
    # ... 生成回應 ...
    response_stream, use_case_id = rag_service.generate_response(
        query, candidate_ids, session_id,
        candidates_info=candidates_info,
        trait_reports=trait_reports  # NEW: Pass to RAG
    )
```

### 2. RAG Engine 使用報告

**檔案**: `services/rag_engine.py`

```python
def generate_response(self, query: str, candidate_ids: List[str], session_id: str,
                     candidates_info: List[Dict] = None, trait_reports: Dict = None):
    # ... 快取檢查 ...
    
    # Check if trait_reports are provided from frontend
    if trait_reports:
        print(f"[RAG] ✅ Using trait reports from frontend for {len(trait_reports)} candidates")
        
        # Merge trait reports with candidate basic info
        final_candidates_data = []
        for cand in target_candidates_basic:
            cand_id = str(cand.get('candidate_id'))
            merged = cand.copy()
            
            # Get trait report from frontend data
            if cand_id in trait_reports:
                report = trait_reports[cand_id]
                print(f"[RAG] Found trait report for candidate {cand_id}: {len(report.get('traits', []))} traits")
                
                # Convert frontend report format to expected format
                trait_results = {}
                for trait in report.get('traits', []):
                    trait_name = trait.get('name', 'Unknown')
                    trait_results[trait_name] = {
                        'score': trait.get('score', 0),
                        'band': trait.get('band', ''),
                        'chinese_name': trait_name
                    }
                
                merged['assessment'] = {
                    'assessment_id': report.get('assessment_id'),
                    'trait_results': trait_results,
                    'completion_time': report.get('assessment_date', 'N/A')
                }
            
            final_candidates_data.append(merged)
        
        print(f"[RAG] Merged {len(final_candidates_data)} candidates with trait reports")
    
    else:
        # Fallback: Fetch from upstream API (original logic)
        print(f"[RAG] No trait reports from frontend. Fetching from upstream API...")
        # ... 原有的 API 呼叫邏輯 ...
```

---

## 📊 效能提升

### API 呼叫次數對比

| 操作 | 原有流程 | 優化後流程 | 減少比例 |
|------|---------|-----------|---------|
| 點擊「開始提問」 | 0 次 | 1 次批次呼叫 | - |
| 第 1 次 Chat 提問 | 1 次 (獲取評估) | 0 次 | **100%** |
| 第 2 次 Chat 提問 | 0 次 (快取) | 0 次 | - |
| 第 3 次 Chat 提問 | 0 次 (快取) | 0 次 | - |
| **總計（3 次提問）** | **1 次** | **1 次** | **相同** |

### 但是...

**優化後的優勢**：
1. ✅ **第一次 Chat 提問更快**（不需要等待 API 呼叫）
2. ✅ **資料一致性更好**（前端和後端使用相同的報告）
3. ✅ **減少後端負載**（不需要每次 Chat 都處理 API 呼叫）
4. ✅ **更好的錯誤處理**（批次獲取失敗時，Chat 仍可使用快取）

---

## 🔍 Debug 日誌

### 前端 Console

```
[ChatContainer] Loaded trait reports from Session Storage: 2 reports
```

### 後端 Console

```
[Chat] Received trait_reports for 2 candidates
[RAG] ✅ Using trait reports from frontend for 2 candidates
[RAG] Found trait report for candidate 58: 35 traits
[RAG] Found trait report for candidate 59: 35 traits
[RAG] Merged 2 candidates with trait reports
```

**如果沒有報告**：
```
[Chat] Received trait_reports for 0 candidates
[RAG] No trait reports from frontend. Fetching from upstream API...
[RAG] Prepared Assessment IDs: [62, 63]
[RealService] Batch Fetch Assessments URL: https://uat.traitty.com/v1/assessments/latest:batch
```

---

## ✅ 測試步驟

### 1. 完整流程測試

1. 重新啟動前後端服務
2. 清空 Session Storage
3. 選擇 2 位候選人
4. 點擊「開始提問」
   - 檢查：Session Storage 應該有 `traitty_batch_reports`
5. 輸入問題並發送
   - 檢查前端 Console：應該看到 "Loaded trait reports: 2 reports"
   - 檢查後端 Console：應該看到 "Using trait reports from frontend"
6. AI 應該正確回應，並使用候選人的真實姓名

### 2. Fallback 測試

1. 手動清空 Session Storage 中的 `traitty_batch_reports`
2. 輸入問題並發送
3. 後端應該回退到從 API 獲取評估
4. 檢查後端 Console：應該看到 "Fetching from upstream API"

---

## 🎯 總結

### 完整的資料流程

```
點擊「開始提問」
    ↓
批次獲取報告 → 儲存到 Session Storage
    ↓
使用者輸入問題
    ↓
從 Session Storage 讀取報告
    ↓
發送 Chat 請求（包含報告）
    ↓
後端直接使用報告（不呼叫 API）
    ↓
建立 RAG Context
    ↓
LLM 生成回應
```

### 關鍵優勢

1. ✅ **減少 API 呼叫**：第一次 Chat 提問不需要呼叫上游 API
2. ✅ **提升回應速度**：減少資料獲取時間
3. ✅ **資料一致性**：前後端使用相同的報告資料
4. ✅ **更好的錯誤處理**：批次獲取失敗時，仍可正常 Chat
5. ✅ **向後相容**：沒有報告時，自動回退到原有邏輯
