<template>
  <div class="results-area">
    <div class="results-header">
      <div class="results-title">搜索結果</div>
      <div class="results-count">
        {{
          candidatesCount > 0
            ? `找到 ${candidatesCount} 位候選人`
            : "等待搜索..."
        }}
      </div>
      <button
        class="reset-session-btn"
        @click="handleResetSession"
        title="開始新的對話"
      >
        <i class="fas fa-redo"></i>
      </button>
    </div>

    <!-- 功能列 -->
    <div class="action-bar" v-if="candidatesCount > 0">
      <div class="action-bar-title">已選擇 {{ selectedCount }} 位候選人</div>
      <button
        class="action-btn"
        @click="handleGenerateQuestions"
        :disabled="selectedCount === 0"
      >
        <i class="fas fa-clipboard-question"></i>
        生成面試問題
      </button>
    </div>

    <div class="results-content">
      <div v-if="candidatesCount === 0" class="empty-state">
        <i class="fas fa-search"></i>
        <h3>開始搜索</h3>
        <p>在左側輸入您的需求，<br />我會為您找到合適的人才</p>
      </div>

      <CandidateCard
        v-for="candidate in candidates"
        :key="candidate.id"
        :candidate="candidate"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTalentStore } from "@/stores/talent";
import { useInterviewStore } from "@/stores/interview";
import CandidateCard from "./CandidateCard.vue";

const talentStore = useTalentStore();
const interviewStore = useInterviewStore();

const candidates = computed(() => talentStore.candidates);
const candidatesCount = computed(() => talentStore.candidatesCount);
const selectedCount = computed(() => talentStore.selectedCount);

function handleGenerateQuestions() {
  interviewStore.generateQuestions(talentStore.selectedCandidates);
}

function handleResetSession() {
  if (confirm("確定要開始新的對話嗎？這將清除當前的搜索結果和對話歷史。")) {
    talentStore.resetSession();
  }
}
</script>
