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
    
    <!-- Backdrop Overlay to block parent page clicks -->
    <Teleport to="body">
      <div class="talent-widget-portal-reset">
        <transition name="fade">
          <div 
            v-if="isOpen && !isFullPageMode" 
            class="widget-modal-backdrop"
            @click="isOpen = true" 
          ></div>
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
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import ChatLauncher from './components/ChatLauncher.vue'
import ChatContainer from './components/ChatContainer.vue'

// sessionStorage 旗標 key：跨頁面跳轉保留「是否有活躍對話」
const ACTIVE_SESSION_KEY = 'traitty_widget_has_active_session'

const isOpen = ref(false)
const isFullPageMode = ref(false)
const hasActiveSession = ref(false)

const toggleChat = () => {
  if (!isOpen.value) {
      // 同時檢查記憶體狀態 與 sessionStorage 持久化旗標
      // 頁面跳轉後記憶體清空，但 sessionStorage 仍保留，
      // 因此必須以兩者 OR 做判斷，避免誤判為全新開始而清除對話狀態
      const persistedActive = !!sessionStorage.getItem(ACTIVE_SESSION_KEY)
      const actuallyHasSession = hasActiveSession.value || persistedActive

      if (!actuallyHasSession) {
          // 確認是全新開始才清除 sessionStorage
          try {
              sessionStorage.removeItem('traitty_selected_candidates')
              sessionStorage.removeItem('traitty_batch_reports')
              sessionStorage.removeItem('traitty_session_active_ids')
              sessionStorage.removeItem('traitty_session_messages')
              sessionStorage.removeItem('traitty_session_id')
          } catch (e) {
              console.error('Error clearing storage:', e)
          }
      }

      // 同步記憶體狀態（確保後續邏輯一致）
      hasActiveSession.value = actuallyHasSession
  }
  isOpen.value = !isOpen.value
}

const handleClose = () => {
    isOpen.value = false
    hasActiveSession.value = false
    // 用戶主動關閉：清除持久化旗標，下次開啟視為全新開始
    try { sessionStorage.removeItem(ACTIVE_SESSION_KEY) } catch (e) {}
}

const handleMinimize = () => {
    isOpen.value = false
    hasActiveSession.value = true
    // 最小化：寫入持久化旗標，頁面跳轉後仍能正確還原對話
    try { sessionStorage.setItem(ACTIVE_SESSION_KEY, '1') } catch (e) {}
}

onMounted(() => {
    // 從 sessionStorage 恢復 hasActiveSession 狀態
    // 解決：最小化 → 點擊頁面連結（頁面跳轉）→ 重開 widget 回到初始狀態的問題
    try {
        if (sessionStorage.getItem(ACTIVE_SESSION_KEY)) {
            hasActiveSession.value = true
        }
    } catch (e) {}

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
  all: initial ;
  font-family: 'Inter', system-ui, sans-serif;
  
  /* Reset box sizing for our widget subtree */
  *, *::before, *::after {
    box-sizing: border-box;
  }
}

.widget-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 9998; /* Just below the chat container's 9999 */
}

/* Teleport to body -> the subtree won't be affected by #talent-rag-widget's reset.
   Provide a local reset wrapper to resist host page inherited/default styles. */
.talent-widget-portal-reset {
  all: initial;
  display: contents;
  font-family: 'Inter', system-ui, sans-serif;

  line-height: 1.6;

  /* Reset box sizing inside the teleported subtree */
  *, *::before, *::after {
    box-sizing: border-box;
  }
}

/* Base fade transition for both the launcher, overlay, and container if needed */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
