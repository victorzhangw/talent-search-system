<template>
  <div 
    class="chat-launcher" 
    :class="{ 'is-open': isOpen }" 
    @click="$emit('toggle')"
    :title="hasActiveSession ? '回到對話' : '開啟 Traitty'"
  >
    <!-- Closed State: Transparent Button with Dynamic SVG Image -->
    <div class="launcher-content" v-if="!isOpen">
      <div class="logo-wrapper">
        <img 
          :src="logoSrc" 
          alt="Traitty AI" 
          class="logo-img" 
          :class="{ 'in-use-pulse': hasActiveSession }"
        />
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
import { computed } from 'vue';

const props = defineProps({
  isOpen: Boolean,
  hasActiveSession: {
    type: Boolean,
    default: false
  }
})

// Dynamic Logo Source Logic
const getBaseUrl = () => {
  // 1. Try explicit configuration from window config
  if (typeof window !== 'undefined' && window.TRAITTY_WIDGET_CONFIG?.assetBaseUrl) {
    return window.TRAITTY_WIDGET_CONFIG.assetBaseUrl.replace(/\/$/, '');
  }

  // 2. In production (IIFE), try to auto-detect based on script tag
  // We look for the script named 'loader.iife.js' or 'loader.js'
  if (!import.meta.env.DEV && typeof document !== 'undefined') {
    const scripts = document.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
      const src = scripts[i].src;
      if (src && (src.includes('loader.iife.js') || src.includes('loader.js'))) {
        // Return the path up to the last slash (directory of the script)
        return src.substring(0, src.lastIndexOf('/'));
      }
    }
  }

  // 3. Fallback to local relative path (works in Dev or same-origin)
  return '';
};

const logoSrc = computed(() => {
  const baseUrl = getBaseUrl();
  const path = props.hasActiveSession 
    ? '/images/inuse.svg' 
    : '/images/suspend.svg';
    
  return baseUrl ? `${baseUrl}${path}` : path;
});
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

  /* Default State (Closed): Transparent Button with Image */
  &:not(.is-open) {
    background: transparent; /* No background */
    box-shadow: none; /* No shadow */
    border: none;
    
    padding: 0;
    min-width: unset; 
    width: auto;
    height: auto;
    
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      transform: scale(1.05); /* Slight grow effect instead of lift */
      filter: drop-shadow(0 4px 6px rgba(0,0,0,0.2)); /* Shadow on the image itself */
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
      width: 28px;
      height: 28px;
      fill: currentColor;
    }
  }

  .launcher-content {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }

  /* Logo Wrapper */
  .logo-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    overflow: hidden; /* Clip potential edge artifacts */
    
    .logo-img {
      height: 8rem; /* Standalone floating image size */
      width: auto;
      object-fit: contain;
      display: block; /* Remove inline spacing */
      /* Fixes for rendering artifacts/flickering */
      transform: translate3d(0, 0, 0); 
      backface-visibility: hidden;
      -webkit-font-smoothing: antialiased;
    @media (max-width: 768px) {
        height: 6rem;
        }
      /* Heartbeat/Breathing Animation when active */
      &.in-use-pulse {
        animation: heartbeat 2s infinite ease-in-out;
      }
    }
  }
}

@keyframes heartbeat {
  0%, 100% {
    transform: scale(1) translate3d(0, 0, 0);
  }
  50% {
    transform: scale(0.92) translate3d(0, 0, 0); /* Shrink inwards */
  }
}
</style>
