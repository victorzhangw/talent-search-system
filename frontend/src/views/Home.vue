<template>
  <div class="home-container">
    <!-- 頂部標題 -->
    <AppHeader />

    <div class="main-content">
      <!-- 左側聊天區域 -->
      <ChatArea />

      <!-- 右側結果區域 -->
      <ResultsArea />
    </div>

    <!-- 面試問題對話框 -->
    <InterviewDialog />
  </div>
</template>

<script setup>
import AppHeader from "@/components/AppHeader.vue";
import ChatArea from "@/components/ChatArea.vue";
import ResultsArea from "@/components/ResultsArea.vue";
import InterviewDialog from "@/components/InterviewDialog.vue";
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}
</style>
