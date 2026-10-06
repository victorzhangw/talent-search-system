<template>
  <div>
    <!-- Mobile History Overlay -->
    <transition name="fade">
      <div v-if="modelValue" class="mobile-history-overlay" @click="closeDrawer"></div>
    </transition>

    <!-- Mobile History Drawer (Slide from Left)
         用 v-show 不用 v-if：關掉抽屜時保留 DOM，捲動位置跟著保留。清單拉到 180 天後要捲很多
         頁，v-if 每次重開都回到最上面。 -->
    <transition name="slide-in-left">
      <div v-show="modelValue" class="mobile-history-drawer">
        <div class="drawer-inner">
          <div class="drawer-header">
            <!-- 點標題回到頂端（iOS 習慣），和右下角的箭頭按鈕同一個動作 -->
            <h3 class="drawer-title" @click="scrollToTop">歷史紀錄</h3>
            <button class="close-btn" @click="closeDrawer">
              <svg viewBox="0 0 24 24" class="material-icon"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>
            </button>
          </div>

          <div ref="content" class="drawer-content" @scroll.passive="onContentScroll">
            <!-- New Analysis Action -->
            <div class="history-actions">
              <button class="primary-btn full-width new-analysis-btn" @click="onNewAnalysis">
                <img src="../assets/images/AI star.svg" class="material-icon new-analysis-icon" alt="AI Star" />
                開啟新人才解析
              </button>
            </div>

            <HistoryList
              variant="drawer"
              :items="items"
              :currentSessionId="currentSessionId"
              :isLoading="isLoading"
              :hasMore="hasMore"
              :error="error"
              :historyDays="historyDays"
              @select="onSelectSession"
              @load-more="$emit('load-more')"
              @retry="$emit('retry')"
            />
          </div>

          <!-- 第一次打開、清單又長到要捲時，提示「往下還有」。只用符號不用文字；一捲就收起並記住，
               之後不再出現。點它等於幫忙往下捲一屏。 -->
          <transition name="fade">
            <button
              v-if="showScrollHint"
              class="scroll-hint"
              aria-label="往下捲動查看更早的對話"
              @click="onScrollHintClick"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
            </button>
          </transition>

          <!-- 捲深了才出現的回到頂端；180 天的清單往回找要能一鍵回來。同樣只用符號。 -->
          <transition name="fade">
            <button
              v-if="showBackToTop"
              class="back-to-top"
              aria-label="回到最新的對話"
              @click="scrollToTop"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7.41 15.41 12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg>
            </button>
          </transition>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import HistoryList from './HistoryList.vue'

const props = defineProps({
  modelValue: Boolean, // controls drawer open/close
  items: { type: Array, default: () => [] },
  currentSessionId: String,
  isLoading: Boolean,
  hasMore: Boolean,
  error: { type: String, default: '' },
  historyDays: { type: Number, default: null }
})

const emit = defineEmits(['update:modelValue', 'select-session', 'new-analysis', 'load-more', 'retry'])

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

// ---- 往下捲提示（只出現到使用者第一次自己捲過為止）----
// 讀不到 storage（無痕、被擋）就當作看過：寧可不提示，也不要每次打開都跳出來。
const HINT_SEEN_KEY = 'traitty_history_scroll_hint_seen'
const readHintSeen = () => {
  try { return localStorage.getItem(HINT_SEEN_KEY) === '1' } catch (e) { return true }
}

const content = ref(null)
const hintSeen = ref(readHintSeen())
const showScrollHint = ref(false)

const markHintSeen = () => {
  showScrollHint.value = false
  if (hintSeen.value) return
  hintSeen.value = true
  try { localStorage.setItem(HINT_SEEN_KEY, '1') } catch (e) { }
}

// 抽屜是 v-show，關著的時候量不到高度；所以在打開、清單變長時各量一次。
const updateScrollHint = async () => {
  if (hintSeen.value || !props.modelValue) {
    showScrollHint.value = false
    return
  }
  await nextTick()
  const el = content.value
  showScrollHint.value = !!el && el.scrollTop === 0 && el.scrollHeight > el.clientHeight
}

watch(() => props.modelValue, updateScrollHint, { immediate: true })
watch(() => props.items.length, updateScrollHint)

// ---- 回到頂端 ----
// 捲過一屏半才出現：只捲一點點時自己滑回去就好，按鈕反而礙眼。
const showBackToTop = ref(false)

const onContentScroll = () => {
  const el = content.value
  if (!el) return
  if (el.scrollTop > 0) markHintSeen()
  showBackToTop.value = el.scrollTop > el.clientHeight * 1.5
}

const scrollToTop = () => {
  if (content.value) content.value.scrollTo({ top: 0, behavior: 'smooth' })
}

const onScrollHintClick = () => {
  const el = content.value
  if (el) el.scrollBy({ top: el.clientHeight * 0.8, behavior: 'smooth' })
  markHintSeen()
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
    /* 底部不留 padding：sticky 的底部漸層會停在 padding 內緣，下面多出一條沒淡出、被硬切的項目。
       底部留白改由清單自己的 padding-bottom（HistoryList .variant-drawer）提供。 */
    padding: 1rem 0 0;
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
      padding: 0.5rem 0.7rem;
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

  /* 清單（分組標題、項目、載入中、空狀態）的樣式在 HistoryList.vue，與桌機側欄共用。 */

  .scroll-hint {
    position: absolute;
    left: 50%;
    bottom: 20px;
    z-index: 2;                 /* 疊在清單底部漸層之上 */
    width: 40px;
    height: 40px;
    margin-left: -20px;         /* 用 margin 置中，transform 留給跳動動畫 */
    padding: 0;
    border: none;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    background: #6A25F4;
    box-shadow: 0 4px 12px rgba(106, 37, 244, 0.35);
    animation: scroll-hint-bounce 1.6s ease-in-out infinite;

    svg {
      width: 24px;
      height: 24px;
      fill: #fff;
    }

    @media (prefers-reduced-motion: reduce) {
      animation: none;
    }
  }

  .back-to-top {
    position: absolute;
    right: 16px;
    bottom: 20px;
    z-index: 2;
    width: 40px;
    height: 40px;
    padding: 0;
    border: 1px solid rgba(106, 37, 244, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    background: #fff;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);

    svg {
      width: 24px;
      height: 24px;
      fill: #6A25F4;
    }

    [data-theme="midnight"] & {
      background: #2d2640;
      border-color: rgba(167, 139, 250, 0.3);
      svg { fill: #a78bfa; }
    }
  }

  .drawer-title { cursor: pointer; }
}

@keyframes scroll-hint-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(5px); }
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
