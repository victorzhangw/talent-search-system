<template>
  <div class="reasoning-block">
    <div class="reasoning-header" @click="isExpanded = !isExpanded">
      <span class="icon">🧠</span>
      <span class="title">思考過程 (Reasoning)</span>
      <span class="toggle-icon">{{ isExpanded ? '▲' : '▼' }}</span>
    </div>
    <transition name="slide-fade">
      <div v-if="isExpanded" class="reasoning-content">
        <div class="intent-tag" v-if="intent">
          <span class="label">意圖識別:</span> {{ intent }}
        </div>
        <div class="content-text">
            <slot></slot>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  intent: String
})

const isExpanded = ref(false)
</script>

<style lang="scss" scoped>
.reasoning-block {
  margin: 0.5rem 0;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2); // Darker background for contrast
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  font-size: 0.9rem;
}

.reasoning-header {
  padding: 0.5rem 0.8rem;
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #94a3b8;
  
  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #e2e8f0;
  }

  .icon { margin-right: 0.5rem; }
  .title { flex: 1; font-weight: 500; }
  .toggle-icon { font-size: 0.8rem; }
}

.reasoning-content {
  padding: 0.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.1);
  color: #cbd5e1;
  font-family: monospace;
  white-space: pre-wrap;
}

.intent-tag {
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  color: #6366f1;
  .label { color: #64748b; margin-right: 0.3rem;}
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease-out;
  max-height: 500px;
  opacity: 1;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
