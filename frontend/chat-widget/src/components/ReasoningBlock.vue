<template>
  <div class="reasoning-block">
    <div class="reasoning-header">
      <span class="icon">🧠</span>
      <span class="title">
        
        <span class="loading-dots">
          <span class="bouncing-dot"></span>
          <span class="bouncing-dot"></span>
          <span class="bouncing-dot"></span>
          <span class="bouncing-dot"></span>
          <span class="bouncing-dot"></span>
          <span class="bouncing-dot"></span>
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


</style>
