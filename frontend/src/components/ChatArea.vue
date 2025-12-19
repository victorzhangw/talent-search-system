<template>
  <div class="chat-area">
    <!-- 模式切換標籤 -->
    <div class="mode-tabs">
      <button
        :class="['mode-tab', { active: currentMode === 'search' }]"
        @click="switchMode('search')"
      >
        <i class="fas fa-search"></i> 人才搜索
      </button>
      <button
        :class="['mode-tab', { active: currentMode === 'hr-consult' }]"
        @click="switchMode('hr-consult')"
      >
        <i class="fas fa-user-tie"></i> HR 諮詢
      </button>
    </div>

    <!-- HR 諮詢模式 - 候選人選擇 -->
    <div v-if="currentMode === 'hr-consult'" class="hr-candidate-section">
      <div class="candidate-selector-compact">
        <label>
          <i class="fas fa-user-check"></i>
          選擇候選人（可選）：
        </label>
        <button
          class="btn-select-candidate-compact"
          @click="toggleCandidateSelector"
          :class="{ 'has-selection': hrStore.hasSelectedCandidate }"
        >
          <span v-if="hrStore.selectedCandidate">
            {{ hrStore.selectedCandidate.name }}
            <span class="clear-btn" @click.stop="clearCandidate">×</span>
          </span>
          <span v-else>點擊選擇或在問題中提到姓名</span>
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="messages" ref="messagesContainer">
      <div
        v-for="message in currentMessages"
        :key="message.id"
        :class="['message', message.type]"
      >
        <div class="message-avatar">
          <i
            :class="
              message.type === 'user'
                ? 'fas fa-user'
                : currentMode === 'hr-consult'
                ? 'fas fa-user-tie'
                : 'fas fa-robot'
            "
          ></i>
        </div>
        <div class="message-content">
          <!-- 普通消息 -->
          <div v-if="!message.isHRConsult">{{ message.content }}</div>

          <!-- HR 諮詢結果 -->
          <div v-else class="hr-consult-message">
            <div class="hr-consult-header">
              <strong>👤 {{ message.candidateName }}</strong>
              <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
            </div>
            <div class="hr-consult-question">
              <strong>❓ 問題：</strong> {{ message.question }}
            </div>
            <div class="hr-consult-answer">
              <strong>💡 專業建議：</strong>

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
                  <p
                    class="section-content"
                    v-html="formatContent(section.content)"
                  ></p>
                </div>

                <!-- 要點 -->
                <div
                  v-if="
                    message.parsedAnswer.key_points &&
                    message.parsedAnswer.key_points.length
                  "
                  class="answer-keypoints"
                >
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
            </div>
            <div v-if="message.dataSummary" class="hr-consult-summary">
              <span class="summary-badge success">
                優勢 {{ message.dataSummary.strengths.length }} 項
              </span>
              <span class="summary-badge warning">
                待提升 {{ message.dataSummary.weaknesses.length }} 項
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="currentIsTyping" class="message system">
        <div class="message-avatar">
          <i
            :class="
              currentMode === 'hr-consult' ? 'fas fa-user-tie' : 'fas fa-robot'
            "
          ></i>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
          <div class="loading-text">{{ currentLoadingMessage }}</div>
        </div>
      </div>
    </div>

    <!-- 輸入區域 -->
    <div class="input-area">
      <div class="mode-hint">
        <i
          :class="
            currentMode === 'hr-consult'
              ? 'fas fa-info-circle'
              : 'fas fa-lightbulb'
          "
        ></i>
        <span v-if="currentMode === 'search'">
          {{ currentModePlaceholder }}
        </span>
        <span v-else>
          {{
            hrStore.hasSelectedCandidate
              ? `已選擇：${hrStore.selectedCandidateName}`
              : "可選擇候選人或在問題中提到姓名"
          }}
        </span>
      </div>
      <div class="input-container">
        <input
          v-model="userInput"
          @keyup.enter="handleSendMessage"
          :placeholder="currentModePlaceholder"
          :disabled="currentIsTyping"
        />
        <button
          @click="handleSendMessage"
          :disabled="!userInput.trim() || currentIsTyping"
          :class="{ 'hr-mode': currentMode === 'hr-consult' }"
        >
          <i class="fas fa-paper-plane"></i>
          {{ currentMode === "hr-consult" ? "諮詢" : "搜索" }}
        </button>
      </div>
      <div class="suggestions" v-if="currentSuggestions.length > 0">
        <span
          v-for="(suggestion, index) in currentSuggestions"
          :key="index"
          class="suggestion-chip"
          @click="useSuggestion(suggestion)"
        >
          {{ suggestion }}
        </span>
      </div>
    </div>

    <!-- 使用新的候選人選擇器組件 -->
    <CandidateSelector
      :show="showCandidateModal"
      @select="selectCandidate"
      @close="toggleCandidateSelector"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from "vue";
import { useTalentStore } from "@/stores/talent";
import { useHRConsultationStore } from "@/stores/hrConsultation";
import CandidateSelector from "@/components/CandidateSelector.vue";

const talentStore = useTalentStore();
const hrStore = useHRConsultationStore();

const userInput = ref("");
const messagesContainer = ref(null);
const currentMode = ref("search"); // 'search' or 'hr-consult'
const showCandidateModal = ref(false);

// HR 諮詢消息列表
const hrMessages = ref([]);

// 計算屬性
const currentMessages = computed(() => {
  if (currentMode.value === "hr-consult") {
    return hrMessages.value;
  }
  return talentStore.messages;
});

const currentIsTyping = computed(() => {
  if (currentMode.value === "hr-consult") {
    return hrStore.consultationLoading;
  }
  return talentStore.isTyping;
});

const currentLoadingMessage = computed(() => {
  if (currentMode.value === "hr-consult") {
    return "正在分析測評數據，生成專業建議...";
  }
  return talentStore.loadingMessage;
});

const currentModePlaceholder = computed(() => {
  if (currentMode.value === "hr-consult") {
    return "例如：張三適合什麼職位？如何提升李四的領導力？";
  }
  return "描述您需要的人才特質或直接提問...";
});

const currentSuggestions = computed(() => {
  if (currentMode.value === "hr-consult") {
    return [
      "適合什麼職位？",
      "優勢和劣勢是什麼？",
      "如何提升領導能力？",
      "適合團隊合作嗎？",
    ];
  }
  return talentStore.suggestions;
});

// 模式切換
function switchMode(mode) {
  currentMode.value = mode;

  if (mode === "hr-consult") {
    // 初始化 HR 諮詢
    hrStore.initSession();
    hrStore.loadCandidates({ hasTestData: true });
  }
}

// 發送消息
async function handleSendMessage() {
  if (!userInput.value.trim() || currentIsTyping.value) return;

  const message = userInput.value;

  if (currentMode.value === "hr-consult") {
    // HR 諮詢模式
    await handleHRConsult(message);
  } else {
    // 人才搜索模式
    await talentStore.sendMessage(message);
  }

  userInput.value = "";
  scrollToBottom();
}

// HR 諮詢處理
async function handleHRConsult(query) {
  // 添加用戶消息
  hrMessages.value.push({
    id: Date.now(),
    type: "user",
    content: query,
    timestamp: new Date(),
  });

  try {
    // 調用 HR 諮詢，會自動使用已選擇的候選人
    const result = await hrStore.consult(query);

    console.log("[ChatArea] 收到 HR 諮詢結果:", result);
    console.log("[ChatArea] parsed_answer:", result.parsed_answer);
    console.log("[ChatArea] parsed_answer 類型:", typeof result.parsed_answer);

    // 添加 AI 回答
    const message = {
      id: Date.now() + 1,
      type: "system",
      isHRConsult: true,
      candidateName: result.candidate.name,
      question: result.question,
      consultation: result.consultation,
      parsedAnswer: result.parsed_answer || null, // 結構化回應
      dataSummary: result.data_summary,
      timestamp: result.timestamp,
    };

    console.log("[ChatArea] 添加消息:", message);
    console.log("[ChatArea] message.parsedAnswer:", message.parsedAnswer);

    hrMessages.value.push(message);
  } catch (error) {
    // 顯示錯誤，但保持候選人選擇狀態
    hrMessages.value.push({
      id: Date.now() + 1,
      type: "system",
      content: `❌ ${error.message}`,
      timestamp: new Date(),
    });
  }
}

// 候選人選擇
function toggleCandidateSelector() {
  showCandidateModal.value = !showCandidateModal.value;
}

function selectCandidate(candidate) {
  hrStore.selectCandidate(candidate);
  toggleCandidateSelector();
}

function clearCandidate() {
  hrStore.clearSelectedCandidate();
}

// 使用建議
function useSuggestion(suggestion) {
  if (currentMode.value === "hr-consult" && hrStore.selectedCandidate) {
    userInput.value = `${hrStore.selectedCandidate.name}${suggestion}`;
  } else {
    userInput.value = suggestion;
  }
}

// 滾動到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}

// 格式化時間
function formatTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return date.toLocaleTimeString("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// 格式化內容（將 \n 轉換為 <br>）
function formatContent(content) {
  if (!content) return "";
  return content.replace(/\n/g, "<br>");
}

// 監聽消息變化
watch(
  currentMessages,
  () => {
    scrollToBottom();
  },
  { deep: true }
);
</script>

<style scoped>
/* 結構化回應樣式 */
.structured-answer {
  margin-top: 12px;
}

.answer-summary {
  background: #f0f7ff;
  border-left: 4px solid #1890ff;
  padding: 12px 16px;
  margin-bottom: 16px;
  font-weight: 500;
  color: #1890ff;
  border-radius: 4px;
}

.answer-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 2px solid #e8e8e8;
}

.section-content {
  line-height: 1.8;
  color: #595959;
  margin: 0;
  white-space: pre-wrap;
}

.answer-keypoints {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}

.answer-keypoints h4 {
  font-size: 15px;
  font-weight: 600;
  color: #262626;
  margin: 0 0 12px 0;
}

.answer-keypoints ul {
  margin: 0;
  padding-left: 20px;
}

.answer-keypoints li {
  line-height: 1.8;
  color: #595959;
  margin-bottom: 8px;
}

.answer-keypoints li:last-child {
  margin-bottom: 0;
}

.plain-answer {
  line-height: 1.8;
  color: #595959;
  white-space: pre-wrap;
}
</style>
