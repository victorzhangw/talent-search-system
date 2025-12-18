<template>
  <div class="hr-consultation-panel">
    <!-- 頂部工具欄 -->
    <div class="panel-header">
      <div class="header-left">
        <h3>💼 HR 專業諮詢</h3>
        <span class="subtitle">基於測評數據的專業人力資源建議</span>
      </div>
      <div class="header-right">
        <button
          class="btn-icon"
          @click="toggleHistoryPanel"
          :title="showHistoryPanel ? '隱藏歷史' : '顯示歷史'"
        >
          📜
        </button>
        <button class="btn-icon" @click="resetConsultation" title="重置">
          🔄
        </button>
      </div>
    </div>

    <!-- 候選人選擇區域 -->
    <div class="candidate-section">
      <div class="candidate-selector">
        <label>選擇候選人（可選）：</label>
        <div class="selector-wrapper">
          <button
            class="btn-select-candidate"
            @click="toggleCandidateSelector"
            :class="{ 'has-selection': hasSelectedCandidate }"
          >
            <span v-if="selectedCandidate">
              👤 {{ selectedCandidate.name }}
              <span class="clear-btn" @click.stop="clearCandidate">×</span>
            </span>
            <span v-else>點擊選擇候選人或在問題中提到姓名</span>
          </button>
        </div>
      </div>

      <!-- 使用新的候選人選擇器組件 -->
      <CandidateSelector
        :show="showCandidateSelector"
        @select="selectCandidate"
        @close="toggleCandidateSelector"
      />
    </div>

    <!-- 諮詢輸入區域 -->
    <div class="consultation-input">
      <div class="input-wrapper">
        <textarea
          v-model="consultQuery"
          placeholder="請輸入您的問題，例如：&#10;• 張三適合什麼職位？&#10;• 如何提升李四的領導能力？&#10;• 王五的優劣勢是什麼？"
          rows="4"
          @keydown.ctrl.enter="handleConsult"
          :disabled="consultationLoading"
        ></textarea>
        <div class="input-footer">
          <div class="input-hint">
            <span v-if="hasSelectedCandidate">
              💡 已選擇候選人：{{ selectedCandidateName }}
            </span>
            <span v-else> 💡 可選擇候選人或直接在問題中提到姓名 </span>
          </div>
          <button
            class="btn-consult"
            @click="handleConsult"
            :disabled="!consultQuery.trim() || consultationLoading"
          >
            <span v-if="consultationLoading">諮詢中...</span>
            <span v-else>🚀 開始諮詢</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 諮詢結果顯示 -->
    <div
      v-if="currentConsultation || consultationError"
      class="consultation-result"
    >
      <!-- 錯誤提示 -->
      <div v-if="consultationError" class="error-message">
        ❌ {{ consultationError }}
      </div>

      <!-- 成功結果 -->
      <div v-else-if="currentConsultation" class="result-card">
        <div class="result-header">
          <!-- 候選人特定諮詢 -->
          <div v-if="currentConsultation.candidate" class="candidate-info">
            <h4>👤 {{ currentConsultation.candidate.name }}</h4>
            <span class="timestamp">{{
              formatTimestamp(currentConsultation.timestamp)
            }}</span>
          </div>
          <!-- 通用 HR 諮詢 -->
          <div v-else class="general-info">
            <h4>💼 通用 HR 諮詢</h4>
            <span class="timestamp">{{
              formatTimestamp(currentConsultation.timestamp)
            }}</span>
          </div>
        </div>

        <div class="result-question">
          <strong>❓ 問題：</strong>
          <p>{{ currentConsultation.question }}</p>
        </div>

        <div class="result-consultation">
          <strong>💡 專業建議：</strong>
          <p class="consultation-text">
            {{ currentConsultation.consultation }}
          </p>
        </div>

        <!-- 通用諮詢提示 -->
        <div
          v-if="
            currentConsultation.mode === 'general' && currentConsultation.note
          "
          class="general-note"
        >
          ℹ️ {{ currentConsultation.note }}
        </div>

        <!-- 候選人特定數據概覽 -->
        <div v-if="currentConsultation.data_summary" class="result-summary">
          <div class="summary-item">
            <span class="label">優勢特質：</span>
            <span class="value success"
              >{{ currentConsultation.data_summary.strengths.length }} 項</span
            >
          </div>
          <div class="summary-item">
            <span class="label">待提升特質：</span>
            <span class="value warning"
              >{{ currentConsultation.data_summary.weaknesses.length }} 項</span
            >
          </div>
          <div class="summary-item">
            <span class="label">總特質數：</span>
            <span class="value"
              >{{ currentConsultation.data_summary.total_traits }} 項</span
            >
          </div>
        </div>

        <div
          v-if="currentConsultation.based_on_traits?.length"
          class="used-traits"
        >
          <strong>🎯 引用特質：</strong>
          <div class="traits-tags">
            <span
              v-for="trait in currentConsultation.based_on_traits"
              :key="trait"
              class="trait-tag"
            >
              {{ trait }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 諮詢歷史側邊欄 -->
    <transition name="slide">
      <div v-if="showHistoryPanel" class="history-panel">
        <div class="history-header">
          <h4>📜 諮詢歷史</h4>
          <div class="history-actions">
            <button
              class="btn-small"
              @click="loadHistory"
              :disabled="historyLoading"
            >
              刷新
            </button>
            <button
              class="btn-small btn-danger"
              @click="confirmClearHistory"
              :disabled="consultationHistory.length === 0"
            >
              清除
            </button>
          </div>
        </div>

        <div class="history-content">
          <div v-if="historyLoading" class="loading">載入中...</div>
          <div v-else-if="consultationHistory.length === 0" class="empty-state">
            暫無諮詢歷史
          </div>
          <div v-else class="history-list">
            <div
              v-for="(item, index) in consultationHistory"
              :key="item.id"
              class="history-item"
              @click="viewHistoryItem(item)"
            >
              <div class="history-index">{{ index + 1 }}</div>
              <div class="history-info">
                <div class="history-candidate">{{ item.candidate_name }}</div>
                <div class="history-query">{{ truncate(item.query, 50) }}</div>
                <div class="history-time">
                  {{ formatTimestamp(item.created_at) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useHRConsultationStore } from "@/stores/hrConsultation";
import { storeToRefs } from "pinia";
import CandidateSelector from "@/components/CandidateSelector.vue";

const hrStore = useHRConsultationStore();

// 從 store 獲取響應式狀態
const {
  selectedCandidate,
  candidates,
  candidatesLoading,
  consultationLoading,
  currentConsultation,
  consultationError,
  consultationHistory,
  historyLoading,
  showCandidateSelector,
  showHistoryPanel,
  hasSelectedCandidate,
  selectedCandidateName,
} = storeToRefs(hrStore);

// 本地狀態
const consultQuery = ref("");

// 組件掛載時加載候選人列表
onMounted(() => {
  hrStore.initSession();
  hrStore.loadCandidates({ hasTestData: true });
});

// 執行諮詢
const handleConsult = async () => {
  if (!consultQuery.value.trim() || consultationLoading.value) return;

  try {
    await hrStore.consult(consultQuery.value);
    consultQuery.value = ""; // 清空輸入
  } catch (error) {
    console.error("諮詢失敗:", error);
  }
};

// 選擇候選人
const selectCandidate = (candidate) => {
  hrStore.selectCandidate(candidate);
  hrStore.toggleCandidateSelector();
};

// 清除候選人選擇
const clearCandidate = () => {
  hrStore.clearSelectedCandidate();
};

// 切換候選人選擇器
const toggleCandidateSelector = () => {
  hrStore.toggleCandidateSelector();
};

// 切換歷史面板
const toggleHistoryPanel = () => {
  hrStore.toggleHistoryPanel();
  if (showHistoryPanel.value) {
    hrStore.loadHistory();
  }
};

// 加載歷史
const loadHistory = () => {
  hrStore.loadHistory();
};

// 確認清除歷史
const confirmClearHistory = () => {
  if (confirm("確定要清除所有諮詢歷史嗎？")) {
    hrStore.clearHistory();
  }
};

// 查看歷史項目
const viewHistoryItem = (item) => {
  // 可以實現查看歷史詳情的邏輯
  console.log("查看歷史:", item);
};

// 重置諮詢
const resetConsultation = () => {
  if (confirm("確定要重置嗎？這會清除當前會話的所有數據。")) {
    hrStore.reset();
    consultQuery.value = "";
  }
};

// 格式化時間戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return date.toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// 截斷文本
const truncate = (text, length) => {
  if (!text) return "";
  return text.length > length ? text.substring(0, length) + "..." : text;
};
</script>

<style scoped>
.hr-consultation-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
  position: relative;
}

/* 頂部工具欄 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: white;
  border-bottom: 2px solid #e1e8ed;
}

.header-left h3 {
  margin: 0;
  font-size: 20px;
  color: #2c3e50;
}

.subtitle {
  display: block;
  font-size: 12px;
  color: #7f8c8d;
  margin-top: 4px;
}

.general-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.general-info h4 {
  margin: 0;
  color: #3498db;
  font-size: 16px;
}

.general-note {
  margin-top: 16px;
  padding: 12px;
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  border-radius: 4px;
  font-size: 13px;
  color: #1565c0;
  line-height: 1.5;
}

.header-right {
  display: flex;
  gap: 8px;
}

.btn-icon {
  width: 36px;
  height: 36px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #f0f0f0;
  transform: scale(1.05);
}

/* 候選人選擇區域 */
.candidate-section {
  padding: 20px;
  background: white;
  border-bottom: 1px solid #e1e8ed;
}

.candidate-selector label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #2c3e50;
}

.btn-select-candidate {
  width: 100%;
  padding: 12px 16px;
  border: 2px dashed #cbd5e0;
  background: #f7fafc;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  font-size: 14px;
  color: #718096;
  transition: all 0.2s;
}

.btn-select-candidate:hover {
  border-color: #4299e1;
  background: #ebf8ff;
}

.btn-select-candidate.has-selection {
  border-color: #48bb78;
  background: #f0fff4;
  color: #2d3748;
  border-style: solid;
}

.clear-btn {
  float: right;
  font-size: 20px;
  color: #e53e3e;
  font-weight: bold;
  margin-left: 8px;
}

.clear-btn:hover {
  color: #c53030;
}

/* 諮詢輸入區域 */
.consultation-input {
  padding: 20px;
  background: white;
}

.input-wrapper textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  min-height: 100px;
}

.input-wrapper textarea:focus {
  outline: none;
  border-color: #4299e1;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.input-hint {
  font-size: 12px;
  color: #718096;
}

.btn-consult {
  padding: 10px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-consult:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-consult:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 諮詢結果 */
.consultation-result {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.error-message {
  padding: 16px;
  background: #fff5f5;
  border: 1px solid #fc8181;
  border-radius: 8px;
  color: #c53030;
}

.result-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.result-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e1e8ed;
}

.result-header h4 {
  margin: 0;
  font-size: 18px;
  color: #2c3e50;
}

.timestamp {
  font-size: 12px;
  color: #718096;
}

.result-question,
.result-consultation {
  margin-bottom: 20px;
}

.result-question strong,
.result-consultation strong {
  display: block;
  margin-bottom: 8px;
  color: #2c3e50;
}

.consultation-text {
  line-height: 1.8;
  color: #4a5568;
  background: #f7fafc;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.result-summary {
  display: flex;
  gap: 20px;
  padding: 16px;
  background: #f7fafc;
  border-radius: 8px;
  margin-bottom: 16px;
}

.summary-item {
  flex: 1;
}

.summary-item .label {
  display: block;
  font-size: 12px;
  color: #718096;
  margin-bottom: 4px;
}

.summary-item .value {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: #2c3e50;
}

.summary-item .value.success {
  color: #38a169;
}

.summary-item .value.warning {
  color: #dd6b20;
}

.used-traits {
  margin-top: 16px;
}

.used-traits strong {
  display: block;
  margin-bottom: 8px;
  color: #2c3e50;
}

.traits-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trait-tag {
  background: #ebf8ff;
  color: #2c5282;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  border: 1px solid #bee3f8;
}

/* 歷史側邊欄 */
.history-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 300px;
  background: white;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 900;
}

.history-header {
  padding: 20px;
  border-bottom: 1px solid #e1e8ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-header h4 {
  margin: 0;
  font-size: 16px;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.btn-small {
  padding: 6px 12px;
  border: 1px solid #cbd5e0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-small:hover {
  background: #f0f0f0;
}

.btn-danger {
  color: #e53e3e;
  border-color: #e53e3e;
}

.history-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e1e8ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #f7fafc;
  border-color: #4299e1;
}

.history-index {
  width: 24px;
  height: 24px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.history-candidate {
  font-weight: 500;
  font-size: 14px;
  color: #2c3e50;
}

.history-query {
  font-size: 12px;
  color: #718096;
  margin: 4px 0;
}

.history-time {
  font-size: 11px;
  color: #a0aec0;
}

.loading,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #718096;
}

/* 動畫 */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from {
  transform: translateX(100%);
}

.slide-leave-to {
  transform: translateX(100%);
}
</style>
