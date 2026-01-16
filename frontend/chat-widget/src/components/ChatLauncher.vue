<template>
  <div 
    class="chat-launcher" 
    :class="{ 'is-open': isOpen }" 
    @click="$emit('toggle')"
  >
    <!-- Closed State: Pill Design -->
    <div class="launcher-content" v-if="!isOpen">
      <!-- Icon Section -->
      <div class="icon-wrapper">
        <svg class="chat-icon" viewBox="0 0 24 24">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
        </svg>
      </div>

      <!-- Text Section -->
      <div class="text-wrapper">
        <span class="title">Traitty</span>
      </div>

     
    </div>

    <!-- Open State: Simple Close Button -->
    <div class="close-content" v-else>
       <svg class="material-icon" viewBox="0 0 24 24">
        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
      </svg>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: Boolean
})
</script>

<style lang="scss" scoped>
@use '../styles/glass.scss' as *;

.chat-launcher {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 10000;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Default State (Closed): Pill Shape */
  &:not(.is-open) {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.6);
    box-shadow: 
      0 4px 6px -1px rgba(0, 0, 0, 0.1), 
      0 2px 4px -1px rgba(0, 0, 0, 0.06),
      0 10px 15px -3px rgba(0, 0, 0, 0.1);
    
    border-radius: 999px; /* Pill shape */
    padding: 0.5rem;
    padding-right: 1rem;
    min-width: 100px;
    height: 3rem;
    
    display: flex;
    align-items: center;
    justify-content: space-between;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }
  }

  /* Open State: Circle Button */
  &.is-open {
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 50%;
    background: #4b5563; /* Gray-600 */
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    transform: rotate(90deg);

    .material-icon {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
  }

  .launcher-content {
    display: flex;
    align-items: center;
    width: 100%;
    gap: 0.65rem;
  }

  /* Left Icon Wrapper */
  .icon-wrapper {
    width: 2.5rem;
    height: 2.5rem;
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); /* Orange Gradient */
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
    
    .chat-icon {
      width: 1.25rem;
      height: 1.25rem;
      fill: currentColor;
    }
  }

  /* Center Text */
  .text-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    
    .title {
      color: #1f2937; /* Gray-800 */
      font-weight: 700;
      font-size: 0.95rem;
      letter-spacing: 0.01em;
    }
  }

  /* Right Close Decoration */
  .close-decoration {
    color: #9ca3af; /* Gray-400 */
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    transition: background-color 0.2s;

    &:hover {
        background-color: rgba(0,0,0,0.05);
        color: #4b5563;
    }

    .close-icon {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }
  }
}
</style>
