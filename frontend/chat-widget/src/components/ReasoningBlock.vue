<template>
  <div class="reasoning-block">
    <div class="reasoning-header">
      <span class="icon">🧠</span>
      <span class="title">
        Traitty 努力思考中，請稍待一會
        <span class="loading-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </span>
      </span>
    </div>
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
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  font-size: 0.9rem;
}

.reasoning-header {
  padding: 0.5rem 0.8rem;
  display: flex;
  align-items: center;
  color: #94a3b8;

  .icon { 
    margin-right: 0.5rem;
    font-size: 1.1rem;
  }
  
  .title { 
    flex: 1; 
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }
}

/* Loading Dots Animation */
.loading-dots {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: 0.4rem;
}

.dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: #94a3b8;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

.dot:nth-child(3) {
  animation-delay: 0s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.3;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
