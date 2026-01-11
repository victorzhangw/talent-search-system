<template>
  <div id="talent-rag-widget">
    <!-- Hide Launcher when Open -->
    <transition name="fade">
      <ChatLauncher v-if="!isOpen" :is-open="isOpen" @toggle="toggleChat" />
    </transition>
    
    <transition name="fade">
      <ChatContainer v-if="isOpen" @close="isOpen = false" />
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatLauncher from './components/ChatLauncher.vue'
import ChatContainer from './components/ChatContainer.vue'

const isOpen = ref(false)

const toggleChat = () => {
  isOpen.value = !isOpen.value
}
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
