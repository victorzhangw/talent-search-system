<template>
  <div class="header">
    <div class="logo-area">
      <div class="logo">AI</div>
      <div class="header-content">
        <h1>AI人才搜索系統</h1>
        <p>智能人才匹配與分析平台</p>
      </div>
    </div>
    <div class="status-indicator">
      {{ connectionStatus }}
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useTalentStore } from "@/stores/talent";

const talentStore = useTalentStore();
const connectionStatus = computed(() => talentStore.connectionStatus);
</script>
