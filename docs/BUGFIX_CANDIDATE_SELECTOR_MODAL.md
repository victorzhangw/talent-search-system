# Bug 修復：候選人選擇器 Modal 不顯示

## 問題描述

點擊 `btn-select-candidate-compact` 按鈕後，候選人選擇器 Modal 沒有出現。

## 問題原因

`CandidateSelector` 組件定義了一個 `show` prop 來控制顯示/隱藏：

```vue
<template>
  <div v-if="show" class="candidate-selector-modal">
    <!-- ... -->
  </div>
</template>

<script setup>
const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  // ...
});
</script>
```

但是在使用該組件時，沒有傳遞 `show` prop：

```vue
<!-- 錯誤的用法 -->
<CandidateSelector
  v-if="showCandidateModal"
  @select="selectCandidate"
  @close="toggleCandidateSelector"
/>
```

這導致組件內部的 `show` prop 始終為 `false`（默認值），因此 `v-if="show"` 條件不滿足，Modal 不會顯示。

## 解決方案

### 修改 1: `frontend/src/components/ChatArea.vue`

```vue
<!-- 修復後 -->
<CandidateSelector
  :show="showCandidateModal"
  @select="selectCandidate"
  @close="toggleCandidateSelector"
/>
```

### 修改 2: `frontend/src/components/HRConsultationPanel.vue`

```vue
<!-- 修復後 -->
<CandidateSelector
  :show="showCandidateSelector"
  @select="selectCandidate"
  @close="toggleCandidateSelector"
/>
```

## 技術說明

### Vue 3 組件通信

- `v-if` 指令：控制組件是否被創建/銷毀
- `:prop` 綁定：將父組件的數據傳遞給子組件的 prop

### 正確的模式

當子組件需要控制自己的顯示/隱藏時，有兩種常見模式：

**模式 1：使用 v-if（父組件控制）**

```vue
<!-- 父組件 -->
<ChildComponent v-if="showModal" />

<!-- 子組件 -->
<template>
  <div class="modal">...</div>
</template>
```

**模式 2：使用 prop（子組件控制）**

```vue
<!-- 父組件 -->
<ChildComponent :show="showModal" />

<!-- 子組件 -->
<template>
  <div v-if="show" class="modal">...</div>
</template>

<script setup>
defineProps({
  show: Boolean,
});
</script>
```

**模式 3：混合使用（本次修復採用）**

```vue
<!-- 父組件 -->
<ChildComponent :show="showModal" />

<!-- 子組件 -->
<template>
  <div v-if="show" class="modal">...</div>
</template>
```

這種模式的優點：

- 父組件通過 prop 控制顯示
- 子組件內部可以有額外的顯示邏輯
- 更靈活，易於擴展

## 測試驗證

### 測試步驟

1. 啟動前端應用
2. 切換到 HR 諮詢模式
3. 點擊「選擇候選人」按鈕
4. 確認 Modal 正確顯示
5. 測試搜索、排序、分頁功能
6. 選擇候選人並關閉 Modal

### 預期結果

- ✅ Modal 正確顯示
- ✅ 搜索功能正常
- ✅ 排序功能正常
- ✅ 分頁功能正常
- ✅ 候選人選擇正常
- ✅ 關閉 Modal 正常

## 相關文件

- `frontend/src/components/CandidateSelector.vue` - 候選人選擇器組件
- `frontend/src/components/ChatArea.vue` - 聊天區域（已修復）
- `frontend/src/components/HRConsultationPanel.vue` - HR 諮詢面板（已修復）

## 修復時間

2025-12-17

## 診斷結果

✅ 所有文件通過診斷檢查（無錯誤、無警告）
