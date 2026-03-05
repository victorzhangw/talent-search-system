<template>
  <div v-if="show" class="candidate-selector-modal" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h4>選擇候選人</h4>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 搜索和排序工具欄 -->
        <div class="toolbar">
          <!-- 搜索框 -->
          <div class="search-box">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索候選人姓名或郵箱..."
              @input="handleSearch"
            />
          </div>

          <!-- 排序選擇 -->
          <div class="sort-box">
            <select v-model="sortBy" @change="handleSortChange">
              <option value="last_test_date">最後測驗時間</option>
              <option value="name">姓名</option>
              <option value="created_at">創建時間</option>
            </select>
            <button
              class="btn-sort-order"
              @click="toggleSortOrder"
              :title="sortOrder === 'desc' ? '降序' : '升序'"
            >
              {{ sortOrder === "desc" ? "↓" : "↑" }}
            </button>
          </div>
        </div>

        <!-- 候選人列表 -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <p>載入中...</p>
        </div>
        <div v-else-if="candidates.length === 0" class="empty-state">
          <p>沒有找到符合條件的候選人</p>
        </div>
        <div v-else class="candidates-list">
          <div
            v-for="candidate in candidates"
            :key="candidate.id"
            class="candidate-item"
            @click="$emit('select', candidate)"
            :class="{ selected: selectedId === candidate.id }"
          >
            <div class="candidate-info">
              <div class="candidate-name">{{ candidate.name }}</div>
              <div class="candidate-details">
                <span class="candidate-email">{{ candidate.email }}</span>
                <span v-if="candidate.position" class="candidate-position">
                  {{ candidate.position }}
                </span>
              </div>
              <div v-if="candidate.last_test_date" class="candidate-meta">
                最後測驗：{{ formatDate(candidate.last_test_date) }}
              </div>
            </div>
            <div class="candidate-badge">
              <span v-if="candidate.has_test_data" class="badge-success">
                ✓ 有測評
              </span>
              <span v-else class="badge-warning"> 無測評 </span>
            </div>
          </div>
        </div>

        <!-- 分頁控制 -->
        <div v-if="totalPages > 1" class="pagination">
          <button class="btn-page" @click="prevPage" :disabled="!hasPrevPage">
            ← 上一頁
          </button>

          <div class="page-info">
            <span class="page-numbers">
              第 {{ currentPage }} / {{ totalPages }} 頁
            </span>
            <span class="total-count"> 共 {{ total }} 筆 </span>
          </div>

          <button class="btn-page" @click="nextPage" :disabled="!hasNextPage">
            下一頁 →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useHRConsultationStore } from "@/stores/hrConsultation";
import { storeToRefs } from "pinia";

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  selectedId: {
    type: Number,
    default: null,
  },
});

const emit = defineEmits(["close", "select"]);

const hrStore = useHRConsultationStore();
const {
  candidates,
  candidatesTotal: total,
  candidatesLoading: loading,
  candidatesPage: currentPage,
  candidatesTotalPages: totalPages,
  candidatesHasPrevPage: hasPrevPage,
  candidatesHasNextPage: hasNextPage,
  candidatesSortBy,
  candidatesSortOrder,
} = storeToRefs(hrStore);

const searchQuery = ref("");
const sortBy = ref(candidatesSortBy.value);
const sortOrder = ref(candidatesSortOrder.value);

// 防抖搜索
let searchTimeout = null;
const handleSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    hrStore.searchCandidates(searchQuery.value);
  }, 500);
};

// 排序變更
const handleSortChange = () => {
  hrStore.setCandidatesSort(sortBy.value, sortOrder.value);
};

// 切換排序順序
const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === "desc" ? "asc" : "desc";
  handleSortChange();
};

// 分頁控制
const prevPage = () => {
  hrStore.candidatesPrevPage();
};

const nextPage = () => {
  hrStore.candidatesNextPage();
};

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
};

// 監聽 show 變化，打開時重置並加載
watch(
  () => props.show,
  (newVal) => {
    if (newVal) {
      searchQuery.value = "";
      sortBy.value = "last_test_date";
      sortOrder.value = "desc";
    }
  }
);
</script>

<style scoped>
.candidate-selector-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 700px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a202c;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #718096;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f7fafc;
  color: #2d3748;
}

.modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-box {
  flex: 1;
}

.search-box input {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 32px;
  font-size: 14px;
  transition: all 0.2s;
}

.search-box input:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.sort-box {
  display: flex;
  gap: 8px;
}

.sort-box select {
  padding: 10px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.sort-box select:focus {
  outline: none;
  border-color: #4299e1;
}

.btn-sort-order {
  padding: 10px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
  min-width: 48px;
}

.btn-sort-order:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
}

.loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #718096;
  gap: 12px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #4299e1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a0aec0;
  font-size: 14px;
}

.candidates-list {
  flex: 1;
  overflow-y: auto;
  margin: 0 -24px;
  padding: 0 24px;
}

.candidate-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.candidate-item:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
  transform: translateX(4px);
}

.candidate-item.selected {
  background: #ebf8ff;
  border-color: #4299e1;
}

.candidate-info {
  flex: 1;
}

.candidate-name {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 4px;
}

.candidate-details {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.candidate-email {
  font-size: 13px;
  color: #718096;
}

.candidate-position {
  font-size: 13px;
  color: #4299e1;
}

.candidate-meta {
  font-size: 12px;
  color: #a0aec0;
}

.candidate-badge {
  margin-left: 12px;
}

.badge-success,
.badge-warning {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.badge-success {
  background: #c6f6d5;
  color: #22543d;
}

.badge-warning {
  background: #feebc8;
  color: #7c2d12;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.btn-page {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #4299e1;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-page:hover:not(:disabled) {
  background: #ebf8ff;
  border-color: #4299e1;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.page-numbers {
  font-size: 14px;
  font-weight: 600;
  color: #2d3748;
}

.total-count {
  font-size: 12px;
  color: #718096;
}
</style>
