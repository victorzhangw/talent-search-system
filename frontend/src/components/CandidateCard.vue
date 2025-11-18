<template>
  <div class="candidate-card" :class="{ selected: isSelected }">
    <!-- Checkbox -->
    <input
      type="checkbox"
      class="candidate-checkbox"
      :checked="isSelected"
      @click.stop="handleToggle"
    />

    <!-- 卡片內容 -->
    <div class="candidate-card-content">
      <div class="candidate-header" @click="viewCandidate">
        <div class="candidate-avatar">
          {{ getInitials(candidate.name) }}
        </div>
        <div class="candidate-info">
          <h3>{{ candidate.name }}</h3>
          <div class="candidate-email">{{ candidate.email }}</div>
        </div>
      </div>
      <div class="match-score" @click="viewCandidate">
        <div class="score-bar">
          <div
            class="score-fill"
            :style="{ width: candidate.match_score * 100 + '%' }"
          ></div>
        </div>
        <div class="score-text">
          {{ Math.round(candidate.match_score * 100) }}%
        </div>
      </div>
      <div class="match-reason" @click="viewCandidate">
        <i
          class="fas fa-lightbulb"
          style="margin-right: 8px; color: #93bfc7"
        ></i>
        <span v-html="formatMatchReason(candidate.match_reason)"></span>
      </div>

      <!-- AI 分析按鈕 -->
      <button
        class="ai-analysis-btn"
        @click.stop="toggleAIAnalysis"
        :disabled="isAnalyzing"
      >
        <i class="fas fa-brain"></i>
        {{
          showAnalysis
            ? "隱藏 AI 分析"
            : aiAnalysis
            ? "查看 AI 分析"
            : "生成 AI 分析"
        }}
      </button>

      <!-- AI 分析結果 -->
      <div v-if="showAnalysis" class="ai-analysis-section">
        <!-- 載入中 -->
        <div v-if="isAnalyzing" class="ai-analysis-loading">
          <i class="fas fa-spinner fa-spin"></i>
          <span>AI 正在分析中...</span>
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>

        <!-- 錯誤訊息 -->
        <div v-else-if="analysisError" class="ai-analysis-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>{{ analysisError }}</span>
        </div>

        <!-- 分析結果 -->
        <div v-else-if="aiAnalysis" class="ai-analysis-content">
          <!-- 一句話總結 -->
          <div v-if="aiAnalysis.summary" class="ai-analysis-summary">
            💡 {{ aiAnalysis.summary }}
          </div>

          <!-- 性格特徵 -->
          <div v-if="aiAnalysis.personality_traits" class="ai-analysis-item">
            <div class="ai-analysis-item-title">
              <i class="fas fa-user-circle"></i>
              性格特徵
            </div>
            <div class="ai-analysis-tags">
              <span
                v-for="(trait, index) in aiAnalysis.personality_traits"
                :key="index"
                class="ai-analysis-tag"
              >
                {{ trait }}
              </span>
            </div>
          </div>

          <!-- 核心優勢 -->
          <div v-if="aiAnalysis.core_strengths" class="ai-analysis-item">
            <div class="ai-analysis-item-title">
              <i class="fas fa-star"></i>
              核心優勢
            </div>
            <ul class="ai-analysis-list">
              <li
                v-for="(strength, index) in aiAnalysis.core_strengths"
                :key="index"
              >
                <strong>{{ strength.strength }}</strong
                >: {{ strength.description }}
              </li>
            </ul>
          </div>

          <!-- 適合職位 -->
          <div v-if="aiAnalysis.suitable_positions" class="ai-analysis-item">
            <div class="ai-analysis-item-title">
              <i class="fas fa-briefcase"></i>
              適合職位
            </div>
            <ul class="ai-analysis-list">
              <li
                v-for="(pos, index) in aiAnalysis.suitable_positions"
                :key="index"
              >
                <strong>{{ pos.position }}</strong
                >: {{ pos.reason }}
              </li>
            </ul>
          </div>

          <!-- 工作風格 -->
          <div v-if="aiAnalysis.work_style" class="ai-analysis-item">
            <div class="ai-analysis-item-title">
              <i class="fas fa-laptop-code"></i>
              工作風格
            </div>
            <div class="ai-analysis-item-content">
              {{ aiAnalysis.work_style }}
            </div>
          </div>

          <!-- 團隊角色 -->
          <div v-if="aiAnalysis.team_role" class="ai-analysis-item">
            <div class="ai-analysis-item-title">
              <i class="fas fa-users"></i>
              團隊角色
            </div>
            <div class="ai-analysis-item-content">
              {{ aiAnalysis.team_role }}
            </div>
          </div>

          <!-- 發展建議 -->
          <div
            v-if="aiAnalysis.development_suggestions"
            class="ai-analysis-item"
          >
            <div class="ai-analysis-item-title">
              <i class="fas fa-chart-line"></i>
              發展建議
            </div>
            <ul class="ai-analysis-list">
              <li
                v-for="(
                  suggestion, index
                ) in aiAnalysis.development_suggestions"
                :key="index"
              >
                <strong>{{ suggestion.area }}</strong
                >: {{ suggestion.suggestion }}
              </li>
            </ul>
          </div>

          <!-- 面試重點 -->
          <div v-if="aiAnalysis.interview_focus" class="ai-analysis-item">
            <div class="ai-analysis-item-title">
              <i class="fas fa-clipboard-check"></i>
              面試重點
            </div>
            <ul class="ai-analysis-list">
              <li
                v-for="(focus, index) in aiAnalysis.interview_focus"
                :key="index"
              >
                {{ focus }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useTalentStore } from "@/stores/talent";
import axios from "axios";

const props = defineProps({
  candidate: {
    type: Object,
    required: true,
  },
});

const talentStore = useTalentStore();

const isSelected = computed(() => talentStore.isSelected(props.candidate.id));
const showAnalysis = ref(false);
const aiAnalysis = ref(null);
const isAnalyzing = ref(false);
const analysisError = ref(null);

function handleToggle() {
  talentStore.toggleSelection(props.candidate);
}

function getInitials(name) {
  return name.substring(0, 2).toUpperCase();
}

function viewCandidate() {
  alert(
    `查看候選人詳情：\n\n姓名：${props.candidate.name}\nEmail：${
      props.candidate.email
    }\n匹配度：${Math.round(props.candidate.match_score * 100)}%\n\n${
      props.candidate.match_reason
    }`
  );
}

function formatMatchReason(reason) {
  // 簡單的格式化，可以根據需要擴展
  return reason;
}

async function toggleAIAnalysis() {
  if (showAnalysis.value) {
    // 如果已經顯示，則隱藏
    showAnalysis.value = false;
  } else {
    // 如果還沒有分析結果，則調用 API
    if (!aiAnalysis.value) {
      await fetchAIAnalysis();
    }
    showAnalysis.value = true;
  }
}

async function fetchAIAnalysis() {
  isAnalyzing.value = true;
  analysisError.value = null;

  try {
    const response = await axios.post(
      `http://localhost:8000/api/candidates/${props.candidate.id}/analyze`
    );

    if (response.data && response.data.analysis) {
      aiAnalysis.value = response.data.analysis;
      console.log("AI 分析結果:", aiAnalysis.value);
    } else {
      analysisError.value = "分析結果格式錯誤";
    }
  } catch (error) {
    console.error("AI 分析錯誤:", error);
    analysisError.value =
      error.response?.data?.detail || "分析失敗，請稍後再試";
  } finally {
    isAnalyzing.value = false;
  }
}
</script>
