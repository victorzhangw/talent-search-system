# 候選人列表分頁與排序功能更新

## 更新日期

2025-12-17

## 更新概述

為 HR 諮詢模組的候選人選擇功能添加了分頁和排序支持，提升了大量候選人數據的瀏覽體驗。

## 主要變更

### 1. 前端 Store 更新 (`frontend/src/stores/hrConsultation.js`)

#### 新增狀態

- `candidatesPage`: 當前頁碼（從 1 開始）
- `candidatesPageSize`: 每頁顯示數量（默認 10）
- `candidatesSortBy`: 排序欄位（默認 'last_test_date'）
- `candidatesSortOrder`: 排序順序（默認 'desc'）
- `candidatesSearchQuery`: 搜索關鍵字
- `candidatesTotalCount`: 候選人總數

#### 新增 Getters

- `candidatesTotalPages`: 總頁數
- `candidatesHasPrevPage`: 是否有上一頁
- `candidatesHasNextPage`: 是否有下一頁

#### 新增 Actions

- `setCandidatesPage(page)`: 設置頁碼
- `candidatesPrevPage()`: 上一頁
- `candidatesNextPage()`: 下一頁
- `setCandidatesSort(sortBy, sortOrder)`: 設置排序
- `searchCandidates(query)`: 搜索候選人
- `resetCandidatesState()`: 重置分頁狀態

#### 更新的 Actions

- `loadCandidates()`: 支持分頁和排序參數

### 2. 新增候選人選擇器組件 (`frontend/src/components/CandidateSelector.vue`)

#### 功能特性

- **搜索功能**: 支持按姓名、郵箱搜索，帶防抖處理（300ms）
- **排序功能**:
  - 支持按最後測驗日期、姓名、創建日期排序
  - 支持升序/降序切換
- **分頁功能**:
  - 每頁顯示 10 筆資料
  - 上一頁/下一頁按鈕
  - 顯示當前頁碼和總頁數
  - 顯示候選人總數
- **候選人資訊顯示**:
  - 姓名、郵箱
  - 最後測驗日期
  - 測驗完成數量
  - 是否有測評數據標記
- **響應式設計**: 適配不同螢幕尺寸
- **載入狀態**: 顯示載入動畫和空狀態提示

### 3. 後端 API 更新 (`BackEnd/hr_consultation_routes.py`)

#### `/api/hr-consult/candidates` 端點更新

新增查詢參數：

- `sort_by`: 排序欄位（可選值：last_test_date, name, created_at）
- `sort_order`: 排序順序（可選值：asc, desc）

#### 排序邏輯

```python
valid_sort_fields = {
    'last_test_date': 'ti.last_test_date',
    'name': 'ti.name',
    'created_at': 'ti.created_at'
}

# 對於 last_test_date，NULL 值排在最後
if sort_by == 'last_test_date':
    order_clause = f"ORDER BY {sort_field} {sort_direction} NULLS LAST, ti.created_at DESC"
else:
    order_clause = f"ORDER BY {sort_field} {sort_direction}, ti.created_at DESC"
```

#### 響應格式更新

```json
{
  "success": true,
  "candidates": [...],
  "total": 100,
  "limit": 10,
  "offset": 0,
  "sort_by": "last_test_date",
  "sort_order": "desc",
  "enterprise_id": null
}
```

### 4. API 客戶端更新 (`frontend/src/api/hrConsultation.js`)

#### `getCandidates()` 函數更新

```javascript
export const getCandidates = async (params = {}) => {
  const response = await hrApiClient.get("/api/hr-consult/candidates", {
    params: {
      search: params.search || undefined,
      has_test_data:
        params.hasTestData !== undefined ? params.hasTestData : undefined,
      sort_by: params.sortBy || "last_test_date",
      sort_order: params.sortOrder || "desc",
      limit: params.limit || 20,
      offset: params.offset || 0,
    },
  });
  return response.data;
};
```

### 5. 組件整合更新

#### `HRConsultationPanel.vue`

- 移除內聯的候選人列表彈窗
- 使用新的 `CandidateSelector` 組件
- 移除本地搜索和防抖邏輯（由組件內部處理）

#### `ChatArea.vue`

- 移除內聯的候選人列表彈窗
- 使用新的 `CandidateSelector` 組件
- 簡化候選人選擇邏輯

## 使用方式

### 前端使用示例

```vue
<template>
  <!-- 使用候選人選擇器 -->
  <CandidateSelector
    v-if="showSelector"
    @select="handleSelect"
    @close="handleClose"
  />
</template>

<script setup>
import CandidateSelector from "@/components/CandidateSelector.vue";
import { useHRConsultationStore } from "@/stores/hrConsultation";

const hrStore = useHRConsultationStore();

function handleSelect(candidate) {
  hrStore.selectCandidate(candidate);
}

function handleClose() {
  // 關閉選擇器
}
</script>
```

### Store 使用示例

```javascript
import { useHRConsultationStore } from "@/stores/hrConsultation";

const hrStore = useHRConsultationStore();

// 載入候選人（第一頁，按最後測驗日期降序）
await hrStore.loadCandidates({ hasTestData: true });

// 切換到第 2 頁
hrStore.setCandidatesPage(2);

// 按姓名升序排序
hrStore.setCandidatesSort("name", "asc");

// 搜索候選人
hrStore.searchCandidates("張三");

// 下一頁
hrStore.candidatesNextPage();

// 上一頁
hrStore.candidatesPrevPage();
```

## 技術細節

### 分頁計算

- 總頁數 = Math.ceil(總數 / 每頁數量)
- 偏移量 = (當前頁 - 1) × 每頁數量

### 防抖處理

搜索輸入使用 300ms 防抖，避免頻繁 API 請求：

```javascript
let searchTimeout = null;

const handleSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    hrStore.searchCandidates(searchQuery.value);
  }, 300);
};
```

### 排序欄位映射

| 前端欄位       | 資料庫欄位        | 說明         |
| -------------- | ----------------- | ------------ |
| last_test_date | ti.last_test_date | 最後測驗日期 |
| name           | ti.name           | 候選人姓名   |
| created_at     | ti.created_at     | 創建日期     |

## 測試建議

### 功能測試

1. ✅ 分頁功能

   - 驗證頁碼切換
   - 驗證上一頁/下一頁按鈕狀態
   - 驗證總頁數計算

2. ✅ 排序功能

   - 測試按不同欄位排序
   - 測試升序/降序切換
   - 驗證 NULL 值處理

3. ✅ 搜索功能

   - 測試姓名搜索
   - 測試郵箱搜索
   - 驗證防抖效果

4. ✅ 整合測試
   - 搜索 + 排序
   - 搜索 + 分頁
   - 排序 + 分頁

### 性能測試

- 大量候選人數據（1000+）的載入速度
- 搜索響應時間
- 分頁切換流暢度

## 已知限制

1. 每頁固定顯示 10 筆資料（未來可考慮讓用戶自定義）
2. 搜索僅支持姓名和郵箱（未來可擴展到其他欄位）
3. 排序欄位有限（未來可添加更多排序選項）

## 未來改進方向

1. **用戶自定義每頁數量**: 允許用戶選擇 10/20/50 筆
2. **高級搜索**: 支持多條件組合搜索
3. **排序記憶**: 記住用戶的排序偏好
4. **快速跳轉**: 直接輸入頁碼跳轉
5. **批量操作**: 支持多選候選人
6. **導出功能**: 導出候選人列表

## 相關文件

- `frontend/src/stores/hrConsultation.js` - Store 狀態管理
- `frontend/src/components/CandidateSelector.vue` - 候選人選擇器組件
- `frontend/src/api/hrConsultation.js` - API 客戶端
- `BackEnd/hr_consultation_routes.py` - 後端路由
- `frontend/src/components/HRConsultationPanel.vue` - HR 諮詢面板
- `frontend/src/components/ChatArea.vue` - 聊天區域

## 版本資訊

- **版本**: 2.1.0
- **更新日期**: 2025-12-17
- **相容性**: 需要後端 API v2.0.0+
