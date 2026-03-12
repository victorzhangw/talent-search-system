<template>
  <div>
    <!-- Mobile History Overlay -->
    <transition name="fade">
      <div v-if="modelValue" class="mobile-history-overlay" @click="closeDrawer"></div>
    </transition>

    <!-- Mobile History Drawer (Slide from Left) -->
    <transition name="slide-in-left">
      <div v-if="modelValue" class="mobile-history-drawer">
        <div class="drawer-inner">
          <div class="drawer-header">
            <h3>歷史紀錄</h3>
            <button class="close-btn" @click="closeDrawer">
              <svg viewBox="0 0 24 24" class="material-icon"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>
            </button>
          </div>

          <div class="drawer-content history-lists" @scroll="handleScroll">
            <!-- New Analysis Action -->
            <div class="history-actions">
              <button class="primary-btn full-width new-analysis-btn" @click="onNewAnalysis">
                <img src="../assets/images/AI star.svg" class="material-icon new-analysis-icon" alt="AI Star" />
                開啟新人才解析
              </button>
            </div>

            <template v-if="historySessions">
              <!-- Today -->
              <div class="history-group" v-if="historySessions.today && historySessions.today.length > 0">
                <div class="group-title">今天</div>
                <div 
                  class="history-item" 
                  v-for="s in historySessions.today" 
                  :key="s.session_id" 
                  @click="onSelectSession(s)"
                  :class="{ active: currentSessionId === s.session_id }"
                >
                  {{ s.title }}
                </div>
              </div>
              
              <!-- Past 30 Days -->
              <div class="history-group" v-if="historySessions.past_30_days && historySessions.past_30_days.length > 0">
                <div class="group-title">過去30天</div>
                <div 
                  class="history-item" 
                  v-for="s in historySessions.past_30_days" 
                  :key="s.session_id" 
                  @click="onSelectSession(s)"
                  :class="{ active: currentSessionId === s.session_id }"
                >
                  {{ s.title }}
                </div>
              </div>

              <!-- Loading Indicator -->
              <div v-if="isLoading" class="history-loading">
                <div class="spinner"></div>載入中...
              </div>
            </template>
            <div v-else class="empty-state">
              無歷史紀錄
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: Boolean, // controls drawer open/close
  historySessions: Object,
  currentSessionId: String,
  isLoading: Boolean,
  hasMore: Boolean
})

const emit = defineEmits(['update:modelValue', 'select-session', 'new-analysis', 'load-more'])

const closeDrawer = () => {
  emit('update:modelValue', false)
}

const onSelectSession = (session) => {
  emit('select-session', session)
}

const onNewAnalysis = () => {
  emit('new-analysis')
  closeDrawer()
}

const handleScroll = (e) => {
  const { scrollTop, scrollHeight, clientHeight } = e.target
  if (scrollTop + clientHeight >= scrollHeight - 50) {
    if (!props.isLoading && props.hasMore) {
      emit('load-more')
    }
  }
}
</script>

<style lang="scss" scoped>
.mobile-history-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  z-index: 10000;
}

.mobile-history-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 80%;
  max-width: 360px;
  background: var(--glass-bg);
  z-index: 10001;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  
  [data-theme="midnight"] & {
    background: #1e1e2d;
  }

  .drawer-inner {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.8rem 1rem;
    border-bottom: 1px solid var(--glass-border);
    
    h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
      color: var(--glass-text-primary);
    }
    
    .close-btn {
      background: none;
      border: none;
      color: var(--glass-text-secondary);
      padding: 0.5rem;
      border-radius: 50%;
      display: flex;
      cursor: pointer;
      margin-right: -0.5rem;
      
      &:active {
        background: rgba(127, 127, 127, 0.1);
      }
      
      .material-icon {
        width: 18px;
        height: 18px;
        fill: currentColor;
      }
    }
  }

  .drawer-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 0;
    -webkit-overflow-scrolling: touch;
  }

  /* History list styles matched with original */
  .history-actions {
    padding: 0 1rem 1rem;
    
    .new-analysis-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.4rem;
      border-radius: 16px;
      padding: 0.5rem 0.8rem;
      background: linear-gradient(90deg, #692ff3 0%, #517BE6 100%);
      border: none;
      color: white;
      font-size: 0.9rem;
      font-weight: 500;
      width: 100%;

      .new-analysis-icon {
        width: 16px;
        height: 16px;
      }
    }
  }

  .history-lists {
    padding-bottom: 2rem;
  }

  .history-group {
    margin-bottom: 1rem;
    padding: 0 1rem;
  }

  .group-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--glass-text-secondary);
    margin-bottom: 0.3rem;
    padding-left: 0.5rem;
  }

  .history-item {
    min-height: 40px; /* Adjusted touch target size for compactness */
    padding: 8px 12px;
    margin-bottom: 2px;
    border-radius: 8px;
    font-size: 0.85rem;
    cursor: pointer;
    color: var(--glass-text-primary);
    transition: background-color 0.2s;
    display: flex;
    align-items: center;

    &:active {
      background: rgba(106, 37, 244, 0.08);
    }

    &.active {
      background: rgba(106, 37, 244, 0.1);
      color: #6A25F4;
      font-weight: 600;
    }
  }

  .history-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 1rem;
    color: var(--glass-text-secondary);
    font-size: 0.9rem;
    
    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(127,127,127,0.3);
      border-top-color: var(--primary-color);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.slide-in-left-enter-active, .slide-in-left-leave-active {
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.slide-in-left-enter-from, .slide-in-left-leave-to {
  transform: translateX(-100%);
}
</style>
