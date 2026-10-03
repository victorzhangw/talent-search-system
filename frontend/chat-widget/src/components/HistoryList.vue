<template>
  <div class="history-list" :class="`variant-${variant}`">
    <div v-for="group in groups" :key="group.key" class="history-group">
      <div class="group-title">{{ group.label }}</div>
      <div
        v-for="s in group.items"
        :key="s.session_id"
        class="history-item"
        :class="{ active: currentSessionId === s.session_id }"
        @click="$emit('select', s)"
      >
        {{ s.title }}
      </div>
    </div>

    <div v-if="error" class="history-status history-error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="$emit('retry')">重試</button>
    </div>
    <div v-else-if="isLoading" class="history-status">
      <div class="spinner"></div>載入中...
    </div>
    <div v-else-if="items.length === 0" class="history-status">無歷史紀錄</div>
    <div v-else-if="!hasMore && historyDays" class="history-status history-end">
      僅顯示近 {{ historyDays }} 天的對話
    </div>

    <!-- 捲到這裡就載下一頁。root 用 null（視窗）：外層捲動容器的裁切本來就會算進可見範圍，
         所以桌機側欄與手機抽屜不必各自傳入自己的捲動容器。 -->
    <div ref="sentinel" class="history-sentinel" aria-hidden="true"></div>
  </div>
</template>

<script setup>
/**
 * 左側歷史清單，桌機側欄與手機抽屜共用（原本是兩份重複的模板，標題還寫死「過去30天」）。
 *
 * 只負責畫：資料、分頁、刷新都在 useChatLogic。分組依後端給的 `bucket` 連續切段——後端
 * 已用台北時間算好並依新到舊排序，同一組必然相鄰，前端不重算時間。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  currentSessionId: { type: String, default: '' },
  isLoading: Boolean,
  hasMore: Boolean,
  error: { type: String, default: '' },
  historyDays: { type: Number, default: null },
  variant: { type: String, default: 'sidebar' }   // 'sidebar' | 'drawer'
})

const emit = defineEmits(['select', 'load-more', 'retry'])

const groups = computed(() => {
  const out = []
  for (const s of props.items) {
    const last = out[out.length - 1]
    if (last && last.key === s.bucket) {
      last.items.push(s)
    } else {
      out.push({ key: s.bucket, label: s.bucket_label, items: [s] })
    }
  }
  return out
})

const sentinel = ref(null)
let observer = null

const maybeLoadMore = (entries) => {
  const visible = entries.some(e => e.isIntersecting)
  if (visible && props.hasMore && !props.isLoading && !props.error) {
    emit('load-more')
  }
}

// IntersectionObserver 只在可見狀態「改變」時通知。載完一頁之後若哨兵仍在畫面內（清單
// 還不夠長），不會再收到通知，就會停在那裡；所以每次載完都重新 observe 一次，讓它依目前
// 狀態再判斷一遍。
const reobserve = async () => {
  if (!observer || !sentinel.value) return
  await nextTick()
  observer.unobserve(sentinel.value)
  observer.observe(sentinel.value)
}

onMounted(() => {
  observer = new IntersectionObserver(maybeLoadMore, { root: null, rootMargin: '0px 0px 120px 0px' })
  if (sentinel.value) observer.observe(sentinel.value)
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  observer = null
})

watch(() => props.isLoading, (loading, was) => {
  if (was && !loading) reobserve()
})
</script>

<style lang="scss" scoped>
/* 數值沿用原本兩處各自的樣式（chat-container.scss 的 .history-sidebar 與 HistoryDrawer.vue），
   只有抽屜的觸控高度由 40px 提高到 44px（iOS 建議值；清單拉長後誤觸機率變高）。 */

.history-item {
  border-radius: 8px;
  cursor: pointer;
  color: var(--glass-text-primary);
}

.group-title {
  /* 長清單捲動時仍看得出自己在哪一段 */
  position: sticky;
  top: 0;
  z-index: 1;
  color: var(--glass-text-secondary);
}

.history-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  color: var(--glass-text-secondary);
  font-size: 0.85rem;
  text-align: center;

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(127, 127, 127, 0.3);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: history-spin 1s linear infinite;
  }
}

.history-end {
  font-size: 0.78rem;
}

.retry-btn {
  border: 1px solid var(--glass-border, rgba(127, 127, 127, 0.3));
  background: transparent;
  color: #6A25F4;
  border-radius: 8px;
  padding: 0.2rem 0.7rem;
  cursor: pointer;
  font-size: 0.85rem;
}

.history-sentinel {
  height: 1px;
}

/* ---- 桌機側欄 ---- */
.variant-sidebar {
  .history-group { margin-bottom: 1.5em; }

  .group-title {
    font-size: 1em;
    font-weight: 800;
    /* 用 padding 不用 margin：固定在頂端時 margin 是透明的，捲上去的項目文字會從標題下方
       那條空隙露出來（實測看得到半個字）。 */
    padding: 0.2em 0 0.6em 0.4em;
    background: #F9FAFF;

    [data-theme="midnight"] & { background: var(--sidebar-bg, #262033); }
  }

  .history-item {
    padding: 0.45em 0.35em;
    font-size: 0.92em;
    transition: all 0.2s;

    &:hover {
      background: rgba(106, 37, 244, 0.05);
      [data-theme="midnight"] & { background: var(--btn-hover-bg, #3F3356); }
    }

    &.active {
      background: rgba(106, 37, 244, 0.1);
      color: #6A25F4;
      font-weight: 600;

      [data-theme="midnight"] & {
        background: rgba(106, 37, 244, 0.15);
        color: #a78bfa;
      }
    }
  }
}

/* ---- 手機抽屜 ---- */
.variant-drawer {
  padding-bottom: 2rem;

  .history-group {
    margin-bottom: 1rem;
    padding: 0 1rem;
  }

  .group-title {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0 0.55rem 0.5rem;   /* 同上：padding 而非 margin */
    background: var(--glass-bg);
  }

  .history-item {
    min-height: 44px;
    padding: 8px 12px;
    margin-bottom: 2px;
    font-size: 0.85rem;
    transition: background-color 0.2s;
    display: flex;
    align-items: center;

    &:active { background: rgba(106, 37, 244, 0.08); }

    &.active {
      background: rgba(106, 37, 244, 0.1);
      color: #6A25F4;
      font-weight: 600;
    }
  }
}

@keyframes history-spin {
  to { transform: rotate(360deg); }
}
</style>
