<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { useTalentStore } from "@/stores/talent";

const talentStore = useTalentStore();

onMounted(() => {
  talentStore.checkApiConnection();
  talentStore.loadTraitDefinitions();
});
</script>

<style>
/* 全局樣式已在 style.css 中 */
</style>
