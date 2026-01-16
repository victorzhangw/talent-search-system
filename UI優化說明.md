# UI 優化說明 - 思考提示與動畫

## ✅ 已完成的修改

### 1. 立即顯示「思考中」提示

**修改檔案**：`MessageList.vue`

**變更內容**：
- ✅ 當使用者點擊發送按鈕後，AI 訊息立即顯示 ReasoningBlock
- ✅ 不需要等待後端回傳 intent 或 reasoning

**修改邏輯**：
```vue
<!-- 原本：只在有 reasoning 或 intent 時顯示 -->
<ReasoningBlock v-if="msg.reasoning || msg.intent" :intent="msg.intent">

<!-- 修改後：在 isTyping 時就立即顯示 -->
<ReasoningBlock v-if="msg.isTyping || msg.reasoning || msg.intent" :intent="msg.intent">
```

---

### 2. 移除「意圖識別」顯示

**修改檔案**：`ReasoningBlock.vue`

**變更內容**：
- ✅ 移除「意圖識別: UC-GENERAL」的顯示
- ✅ 簡化 UI，只保留「Traitty 努力思考中，請稍待一會」

**修改前**：
```vue
<div class="intent-tag" v-if="intent">
  <span class="label">意圖識別:</span> {{ intent }}
</div>
```

**修改後**：
```vue
<!-- 完全移除 intent-tag -->
```

---

### 3. 添加 Loading 動畫

**修改檔案**：`ReasoningBlock.vue`

**新增內容**：
- ✅ 添加三個跳動的點（...）作為 loading 動畫
- ✅ 使用 CSS animation 創建流暢的跳動效果

**HTML 結構**：
```vue
<span class="title">
  Traitty 努力思考中，請稍待一會
  <span class="loading-dots">
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
  </span>
</span>
```

**CSS 動畫**：
```scss
.loading-dots {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  margin-left: 0.3rem;
}

.dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: #94a3b8;
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
```

**動畫效果**：
- 三個點依序跳動
- 創造出「思考中」的視覺效果
- 循環播放，直到 AI 開始回應

---

## 📊 使用者體驗流程

### 修改前

```
使用者點擊發送
    ↓
（空白等待）
    ↓
後端回傳 intent
    ↓
顯示「意圖識別: UC-GENERAL」
    ↓
AI 開始回應
```

**問題**：
- ❌ 使用者不知道系統是否在處理
- ❌ 顯示技術性的「UC-GENERAL」對使用者沒有意義

### 修改後

```
使用者點擊發送
    ↓
立即顯示「Traitty 努力思考中，請稍待一會 ...」
（三個點跳動動畫）
    ↓
AI 開始回應
    ↓
思考提示自動消失（或可展開查看詳情）
```

**優勢**：
- ✅ 即時反饋，使用者知道系統正在處理
- ✅ 友善的提示文字
- ✅ 視覺化的 loading 動畫
- ✅ 移除技術性術語

---

## 🎨 視覺效果

### ReasoningBlock 外觀

```
┌─────────────────────────────────────────────┐
│ 🧠 Traitty 努力思考中，請稍待一會 ● ● ●  ▼ │
└─────────────────────────────────────────────┘
```

**特點**：
- 🧠 腦袋圖示表示「思考」
- ● ● ● 三個點跳動（動畫）
- ▼ 可展開查看詳細資訊（如果有 reasoning）
- 深色半透明背景，與 chat 介面融合

### 動畫效果

```
時間軸：
0.0s:  ● ○ ○
0.2s:  ○ ● ○
0.4s:  ○ ○ ●
0.6s:  ● ○ ○
...（循環）
```

---

## 🔧 技術細節

### 1. 顯示時機

**條件**：`msg.isTyping || msg.reasoning || msg.intent`

**說明**：
- `msg.isTyping`：AI 訊息正在生成中（立即顯示）
- `msg.reasoning`：有推理過程資訊（保留顯示）
- `msg.intent`：有意圖資訊（保留顯示，但不再顯示內容）

### 2. 動畫參數

| 參數 | 值 | 說明 |
|------|-----|------|
| 點的大小 | 4px | 小巧不突兀 |
| 點的間距 | 0.2rem | 適當的視覺間距 |
| 動畫時長 | 1.4s | 舒適的節奏 |
| 延遲時間 | 0.16s/0.32s | 創造波浪效果 |

### 3. 樣式整合

- 使用現有的 `#94a3b8` 顏色（與 header 文字一致）
- 保持與 chat 介面的視覺一致性
- 響應式設計，適配不同螢幕尺寸

---

## 📝 測試步驟

### 1. 基本測試

1. 重新整理頁面
2. 選擇候選人並開始提問
3. 輸入問題並點擊發送
4. **立即檢查**：應該看到「Traitty 努力思考中，請稍待一會 ...」
5. **檢查動畫**：三個點應該依序跳動
6. **等待回應**：AI 開始回應後，思考提示仍然保留（可展開）

### 2. 視覺檢查

- ✅ 文字清晰可讀
- ✅ 動畫流暢不卡頓
- ✅ 顏色與整體風格一致
- ✅ 沒有顯示「意圖識別: UC-GENERAL」

### 3. 互動測試

- ✅ 點擊 ReasoningBlock 可以展開/收起
- ✅ 展開後沒有顯示 intent 資訊
- ✅ 如果有 reasoning 資訊，會顯示在展開區域

---

## 🎯 總結

### 完成的功能

1. ✅ **立即反饋**：點擊發送後立即顯示思考提示
2. ✅ **移除技術術語**：不再顯示「意圖識別: UC-GENERAL」
3. ✅ **視覺化動畫**：三個跳動的點表示載入中
4. ✅ **友善提示**：使用自然語言「Traitty 努力思考中，請稍待一會」

### 使用者體驗提升

- 🎨 更直觀的視覺反饋
- ⚡ 即時的狀態提示
- 🎯 簡潔的介面設計
- 💫 流暢的動畫效果

### 技術實作

- 📝 修改 3 個檔案
- 🎨 新增 CSS 動畫
- 🔧 優化顯示邏輯
- ✨ 保持向後相容
