# 功能：結構化回應顯示

## 更新日期

2025-12-18

## 問題描述

LLM 返回的文字全部擠在一起，沒有斷行和段落，閱讀體驗很差。

## 解決方案

### 方案 1：要求 LLM 輸出 JSON 格式

修改 Prompt 要求 LLM 以結構化的 JSON 格式輸出，包含：

- `summary`: 一句話總結
- `sections`: 多個章節，每個章節有標題和內容
- `key_points`: 關鍵要點列表

### 方案 2：後端解析 JSON

添加 `_parse_llm_response()` 方法來解析 LLM 的 JSON 回應，支持：

- 從 `json ` 代碼塊中提取
- 從 { } 之間提取
- 容錯處理，失敗時返回原始文本

### 方案 3：前端結構化顯示

修改 `ChatArea.vue` 來顯示結構化內容：

- 摘要區塊（藍色背景）
- 章節標題和內容
- 關鍵要點列表
- 自動將 `\n` 轉換為換行

## 技術實現

### 1. Prompt 更新

**文件**: `BackEnd/prompts/hr_consultation_prompts.json`

````json
{
  "user_prompt_template": "...請以 JSON 格式輸出，結構如下：\n```json\n{\n  \"summary\": \"一句話總結（30字內）\",\n  \"sections\": [\n    {\n      \"title\": \"章節標題\",\n      \"content\": \"章節內容（可使用\\n換行）\"\n    }\n  ],\n  \"key_points\": [\"要點1\", \"要點2\", \"要點3\"]\n}\n```"
}
````

### 2. 後端解析

**文件**: `BackEnd/hr_consultation_service.py`

新增方法：

````python
def _parse_llm_response(self, response: str) -> Dict:
    """解析 LLM 的 JSON 回應"""
    # 1. 嘗試從 ```json ``` 代碼塊提取
    # 2. 嘗試從 { } 之間提取
    # 3. 解析 JSON
    # 4. 驗證必要欄位
    # 5. 失敗時返回原始文本
````

修改返回值：

```python
return {
    'answer': llm_response,  # 原始回應
    'parsed_answer': parsed_response,  # 結構化數據
    'data_summary': {...}
}
```

### 3. 前端顯示

**文件**: `frontend/src/components/ChatArea.vue`

```vue
<template>
  <!-- 結構化回應 -->
  <div
    v-if="message.parsedAnswer && message.parsedAnswer.sections"
    class="structured-answer"
  >
    <!-- 摘要 -->
    <div v-if="message.parsedAnswer.summary" class="answer-summary">
      {{ message.parsedAnswer.summary }}
    </div>

    <!-- 章節 -->
    <div
      v-for="(section, index) in message.parsedAnswer.sections"
      :key="index"
      class="answer-section"
    >
      <h4 class="section-title">{{ section.title }}</h4>
      <p class="section-content" v-html="formatContent(section.content)"></p>
    </div>

    <!-- 要點 -->
    <div v-if="message.parsedAnswer.key_points" class="answer-keypoints">
      <h4>關鍵要點</h4>
      <ul>
        <li
          v-for="(point, index) in message.parsedAnswer.key_points"
          :key="index"
        >
          {{ point }}
        </li>
      </ul>
    </div>
  </div>

  <!-- 純文本回應（後備） -->
  <p
    v-else
    class="plain-answer"
    v-html="formatContent(message.consultation)"
  ></p>
</template>

<script>
function formatContent(content) {
  if (!content) return "";
  return content.replace(/\n/g, "<br>");
}
</script>
```

## JSON 格式範例

### LLM 輸出

```json
{
  "summary": "候選人具備專案經理的核心能力，但需要加強決策和系統思考能力",
  "sections": [
    {
      "title": "優勢分析",
      "content": "候選人的「成就追求」分數高達 89 分，表示他對工作極為認真。\n「韌性」81 分，面對挫折時具備良好的恢復能力。"
    },
    {
      "title": "需要關注的方面",
      "content": "「決策能力」48 分，在複雜情境下快速判斷的能力較弱。\n建議在初期提供決策框架和指引。"
    },
    {
      "title": "職位適配建議",
      "content": "適合擔任中小型專案的經理，或在大型專案中擔任執行層面的角色。"
    }
  ],
  "key_points": [
    "高成就追求和韌性是核心優勢",
    "決策能力需要加強和支持",
    "適合中小型專案管理"
  ]
}
```

### 前端顯示效果

```
┌─────────────────────────────────────────┐
│ 候選人具備專案經理的核心能力，但需要加強決策和系統思考能力 │  ← 摘要（藍色背景）
└─────────────────────────────────────────┘

優勢分析                                    ← 章節標題（粗體，下劃線）
候選人的「成就追求」分數高達 89 分，表示他對工作極為認真。
「韌性」81 分，面對挫折時具備良好的恢復能力。

需要關注的方面
「決策能力」48 分，在複雜情境下快速判斷的能力較弱。
建議在初期提供決策框架和指引。

職位適配建議
適合擔任中小型專案的經理，或在大型專案中擔任執行層面的角色。

┌─────────────────────────────────────────┐
│ 關鍵要點                                  │  ← 要點區塊（灰色背景）
│ • 高成就追求和韌性是核心優勢                │
│ • 決策能力需要加強和支持                    │
│ • 適合中小型專案管理                        │
└─────────────────────────────────────────┘
```

## 容錯機制

1. **JSON 解析失敗** → 顯示原始文本（使用 `formatContent` 轉換換行）
2. **JSON 格式不完整** → 顯示原始文本
3. **LLM 未返回 JSON** → 顯示原始文本

## 樣式設計

### 摘要區塊

- 背景：淡藍色 (#f0f7ff)
- 左邊框：藍色 (#1890ff)
- 字體：粗體，藍色

### 章節標題

- 字體：16px，粗體
- 下劃線：灰色
- 間距：上下留白

### 章節內容

- 行高：1.8（易讀）
- 顏色：深灰色 (#595959)
- 保留換行（white-space: pre-wrap）

### 要點區塊

- 背景：淺灰色 (#fafafa)
- 圓角：8px
- 列表樣式：圓點
- 行高：1.8

## 測試驗證

### 測試步驟

1. 重啟服務
2. 選擇一位候選人
3. 提問：「這位候選人適合擔任專案經理嗎？」
4. 檢查回應格式

### 預期結果

✅ 回應有清晰的摘要  
✅ 內容分為多個章節  
✅ 每個章節有標題  
✅ 內容有適當的換行  
✅ 有關鍵要點列表  
✅ 整體排版美觀易讀

### 如果 LLM 未返回 JSON

✅ 仍然能顯示內容  
✅ 自動將 `\n` 轉換為換行  
✅ 不會出現錯誤

## 後續優化

1. **Markdown 支持**：支持粗體、斜體等格式
2. **表格支持**：顯示特質對比表格
3. **圖表支持**：顯示特質雷達圖
4. **可折疊章節**：長內容可折疊
5. **複製功能**：一鍵複製整個回應
6. **導出功能**：導出為 PDF 或 Word

## 相關文件

- Prompt 模板：`BackEnd/prompts/hr_consultation_prompts.json`
- 後端服務：`BackEnd/hr_consultation_service.py`
- 前端組件：`frontend/src/components/ChatArea.vue`
