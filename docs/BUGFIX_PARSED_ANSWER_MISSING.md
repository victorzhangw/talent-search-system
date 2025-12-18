# Bug 修復：parsed_answer 未傳遞到前端

## 問題描述

前端顯示的是原始 JSON 字符串，而不是解析後的結構化內容：

````
專業建議：```json { "summary": "...", "sections": [...], ... }
````

## 根本原因

後端的 `consult()` 方法返回結果時，沒有包含 `parsed_answer` 欄位，導致前端無法獲取解析後的結構化數據。

## 修復內容

### 1. 後端修復

**文件**: `BackEnd/hr_consultation_service.py`

**修改前**:

```python
return {
    "success": True,
    "candidate": {...},
    "question": query,
    "consultation": consultation_result['answer'],
    "data_summary": consultation_result['data_summary'],
    ...
}
```

**修改後**:

```python
return {
    "success": True,
    "candidate": {...},
    "question": query,
    "consultation": consultation_result['answer'],
    "parsed_answer": consultation_result.get('parsed_answer'),  # ✅ 添加
    "data_summary": consultation_result['data_summary'],
    ...
}
```

### 2. 環境變數更新

**文件**: `BackEnd/.env.local`

```bash
LLM_MAX_RESPONSE_LENGTH=2000  # 從 500 增加到 2000
LLM_MAX_TOKENS=3000           # 從 1500 增加到 3000
```

## 數據流程

```
LLM 回應
    ↓
_parse_llm_response()  # 解析 JSON
    ↓
parsed_answer (Dict)
    ↓
consultation_result['parsed_answer']
    ↓
return {..., "parsed_answer": ...}  # ✅ 現在有了
    ↓
前端接收 result.parsed_answer
    ↓
顯示結構化內容
```

## 測試驗證

### 測試步驟

1. 重啟服務

   ```bash
   stop.bat
   start.bat
   ```

2. 測試 HR 諮詢
   - 選擇候選人
   - 提問
   - 檢查回應格式

### 預期結果

✅ **不再顯示**：

````
專業建議：```json { "summary": "...", ...
````

✅ **應該顯示**：

```
┌─────────────────────────────────────────┐
│ Amy是具有高度成就動機與韌性的執行者...    │  ← 摘要
└─────────────────────────────────────────┘

核心優勢分析
────────────────────────────────────────
1. Achievement Motivation(89分)：高度目標導向...
2. Resilience(81分)：在壓力下保持穩定表現...
...
```

## 相關修改

- ✅ 後端返回 `parsed_answer`
- ✅ 字數限制增加到 2000
- ✅ Token 限制增加到 3000

## 修復日期

2025-12-18
