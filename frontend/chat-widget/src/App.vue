<template>
  <div id="talent-rag-widget">
    <!-- Hide Launcher when Open OR in Full Page Mode -->
    <transition name="fade">
      <ChatLauncher 
        v-if="!isOpen && !isFullPageMode" 
        :is-open="isOpen" 
        :has-active-session="hasActiveSession"
        @toggle="toggleChat" 
      />
    </transition>
    
    <transition name="fade">
      <ChatContainer 
        v-if="isOpen" 
        :is-full-page="isFullPageMode" 
        @close="handleClose" 
        @minimize="handleMinimize"
      />
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import ChatLauncher from './components/ChatLauncher.vue'
import ChatContainer from './components/ChatContainer.vue'

const isOpen = ref(false)
const isFullPageMode = ref(false)
const hasActiveSession = ref(false)

const toggleChat = () => {
  if (!isOpen.value) {
      // Opening the widget
      if (!hasActiveSession.value) {
          // Fresh start: Clear session state
          try {
              sessionStorage.removeItem('traitty_selected_candidates')
              sessionStorage.removeItem('traitty_batch_reports')
              sessionStorage.removeItem('traitty_session_active_ids')
          } catch (e) {
              console.error('Error clearing storage:', e)
          }
      }
      // If hasActiveSession is true, we simply open (restore) without clearing
  }
  isOpen.value = !isOpen.value
}

const handleClose = () => {
    isOpen.value = false
    hasActiveSession.value = false // Reset active state
}

const handleMinimize = () => {
    isOpen.value = false
    hasActiveSession.value = true // Keep active state
}

onMounted(() => {
    // Check URL params for mode
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('mode') === 'fullpage') {
        isFullPageMode.value = true
        isOpen.value = true
    }

    // Check if we are opening in a new tab with transferred state (applies to both modes)
    const transferredState = localStorage.getItem('traitty_new_tab_state')
    if (transferredState) {
        // If we have state but not fullpage param, we can optionally force open too
        // But usually Open New Tab logic adds the param now.
        if (!isFullPageMode.value) isOpen.value = true
    }
})
</script>

<style lang="scss">
/* Global Reset for Widget */
/* Font Import handled in main.js/global.scss or index.html usually */
#talent-rag-widget {
  font-family: 'Inter', system-ui, sans-serif;
  
  /* Reset box sizing for our widget subtree */
  *, *::before, *::after {
    box-sizing: border-box;
  }
}
</style>
