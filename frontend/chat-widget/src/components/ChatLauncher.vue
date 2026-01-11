<template>
  <div class="chat-launcher" :class="{ 'is-open': isOpen }" @click="$emit('toggle')">
    <div class="content-wrapper">
      <div class="icon-container">
        <transition name="fade" mode="out-in">
          <!-- Close Icon (Material: close) -->
          <svg v-if="isOpen" class="material-icon" viewBox="0 0 24 24">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
          </svg>
          
          <!-- Chat Icon (Material: chat_bubble) -->
          <svg v-else class="material-icon" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
          </svg>
        </transition>
      </div>
      <span class="label" v-if="!isOpen">AI 助手</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: Boolean
})
</script>

<style lang="scss" scoped>
@import '../styles/glass.scss';

.chat-launcher {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  min-width: 3.5rem;
  height: 3.5rem;
  padding: 0 1rem; 
  border-radius: 2rem; 
  
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  
  background: var(--primary-color);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4); /* Cleaner shadow */
  color: white; 
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

  .content-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  /* Material Icon Sizing */
  .material-icon {
      width: 24px;
      height: 24px;
      fill: currentColor;
  }

  .label {
    font-weight: 500; /* More professional weight */
    font-size: 0.95rem;
    white-space: nowrap;
    letter-spacing: 0.02em;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(99, 102, 241, 0.5);
  }

  &.is-open {
    background: #4b5563; /* Gray-600 for close state (Commercial neutral) */
    transform: rotate(90deg);
    width: 3.5rem; 
    padding: 0;
    
    .label {
      display: none;
    }
  }
}
</style>
