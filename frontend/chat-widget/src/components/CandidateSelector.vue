<template>
  <div class="candidate-selector">
    

    <!-- Mobile Selected Tags Block (Hidden on Desktop) -->
    <div class="mobile-selected-tags" v-if="selectedIds.length > 0">
       
        <div class="tags-list">
            <span class="selected-tag" v-for="id in selectedIds" :key="id" @click="toggle(id)">
                {{ getCandidateName(id) }} <svg class="tag-close-icon" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </span>
        </div>
    </div>

    <!-- Search & Toolbar -->
    <div class="search-toolbar">
        <div class="search-box">
            <!-- Icon: Search -->
            <svg class="material-icon icon" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
            <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="輸入姓名或Email..."
            />
            <!-- Icon: Close -->
            <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">
                <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
        </div>
        <div class="toolbar-actions">
            <!-- Stats -->
            <div class="list-stats">
               <span v-if="searchQuery">搜尋結果: {{ filteredCandidates.length }} 筆</span>
               <span v-else>已顯示 {{ candidates.length }} / 共 {{ totalCount }} 筆</span>
               
               <span class="centered-selected-text">選取人才 ({{ selectedIds.length }})</span>
            </div>

            <!-- Batch Actions -->
            <div class="batch-actions" v-if="filteredCandidates.length > 0">
                <button class="action-link" @click="selectAllFiltered">
                    全選 ({{ filteredCandidates.length }})
                </button>
                <span class="divider" v-if="selectedIds.length > 0">|</span>
                <button class="action-link" v-if="selectedIds.length > 0 && !disabled" @click="clearSelection">
                    清除已選
                </button>
            </div>
        </div>
    </div>

    <!-- List -->
    <div class="list-container" ref="listContainer">
      <div 
        v-for="cand in filteredCandidates" 
        :key="cand.id" 
        class="candidate-item"
        :class="{ 
          active: selectedIds.includes(cand.id) || lockedIds.includes(cand.id), 
          locked: lockedIds.includes(cand.id),
          disabled: disabled 
        }"
        @click="!disabled && !lockedIds.includes(cand.id) && toggle(cand.id)"
      >
        <div class="avatar-initial" :class="'bg-' + (cand.name ? cand.name.length % 5 : 0)">
            {{ cand.name ? cand.name.charAt(0).toUpperCase() : '?' }}
        </div>
        
        <div class="info">
          <span class="name">
            {{ cand.name }}
            <span v-if="cand.position" class="position"> {{ cand.position }}</span>
            <span v-if="cand.email" class="email">({{ cand.email }})</span>
          </span>
        </div>

        <div class="checkbox">
          <!-- 已鎖定狀态：顯示鎖頭圖示 -->
          <svg v-if="lockedIds.includes(cand.id)" class="material-icon lock-icon" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>
          <!-- 已選取狀态：顯示勾選圖示 -->
          <svg v-else-if="selectedIds.includes(cand.id)" class="material-icon check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
        </div>
      </div>
      
      <div v-if="filteredCandidates.length === 0 && !isLoading" class="empty-state">
          沒有找到匹配的候選人
      </div>

      <!-- Loading Indicator -->
      <div v-if="isLoading" class="loading-more">
          <div class="spinner-small"></div> 載入中...
      </div>
      
      <!-- Scroll Hint / Manual Load -->
      <div 
        v-else-if="hasMore && !searchQuery" 
        class="scroll-hint clickable" 
        @click="emit('load-more')"
        title="點擊載入更多"
      >
          <span>載入更多...</span>
          <svg class="material-icon small arrow" viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'

const props = defineProps({
  candidates: {
    type: Array,
    default: () => []
  },
  isLoading: {
      type: Boolean,
      default: false
  },
  hasMore: {
      type: Boolean,
      default: false
  },
  disabled: {
      type: Boolean,
      default: false
  },
  totalCount: {
      type: Number,
      default: 0
  },
  initialSelectedIds: {
      type: Array,
      default: () => []
  },
  lockedIds: {
      type: Array,
      default: () => []  // 已鎖定（已在對話中）的候選人 ID，顯示為鎖定且不可再選
  }
})

const emit = defineEmits(['change', 'load-more'])
const selectedIds = ref([...props.initialSelectedIds])
const searchQuery = ref('')

// Filter Logic
const filteredCandidates = computed(() => {
    const query = searchQuery.value.toLowerCase().trim()
    if (!query) return props.candidates
    
    return props.candidates.filter(c => {
        const nameMatch = (c.name || '').toLowerCase().includes(query)
        const posMatch = (c.position || '').toLowerCase().includes(query)
        const emailMatch = (c.email || '').toLowerCase().includes(query)
        return nameMatch || posMatch || emailMatch
    })
})

const getCandidateName = (id) => {
    const cand = props.candidates.find(c => c.id === id);
    return cand ? cand.name : 'Unknown';
}

const toggle = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]  // 不可變方式，確保 Vue 可偵測變化
  }
  emit('change', [...selectedIds.value])  // 傳出副本避免外部共用引用
}

// Batch Actions
const selectAllFiltered = () => {
    const idsToAdd = filteredCandidates.value.map(c => c.id)
    const newSelection = [...new Set([...selectedIds.value, ...idsToAdd])]
    selectedIds.value = newSelection
    emit('change', selectedIds.value)
}

const clearSelection = () => {
    selectedIds.value = []
    emit('change', [])
}

// Ensure syncing if parent changes it
watch(() => props.initialSelectedIds, (newVal, oldVal) => {
    // 防止當 newVal 是空陣列（畫面重渲染產生的新引用）但使用者已有選取時，被重置
    if (newVal.length === 0 && selectedIds.value.length > 0) {
        // 父元件傳入空 ref/字面量 []，不應清除使用者已選取的項目
        return
    }
    // 使用內容比較，避免不必要的同步
    const isSame = newVal.length === selectedIds.value.length &&
                   newVal.every(id => selectedIds.value.includes(id))
    if (!isSame) {
        selectedIds.value = [...newVal]
    }
}, { deep: true })

// Scroll Detection
const listContainer = ref(null)

const onScroll = (e) => {
    const el = e.target
    // Trigger when within 50px of bottom
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 50) {
        if (!props.isLoading && props.hasMore) {
            emit('load-more')
        }
    }
}

// Auto-fill container if content doesn't scrolling (e.g. large screen)
const checkAndFillContainer = async () => {
    await nextTick()
    if (!listContainer.value) return
    
    // If not loading, has more data, and NO scrollbar (scrollHeight <= clientHeight)
    // We fetch more to fill the space
    const { scrollHeight, clientHeight } = listContainer.value
    if (!props.isLoading && props.hasMore && scrollHeight <= clientHeight + 50) {
        emit('load-more')
    }
}

// Watch candidates change to re-check if we need to fill more
watch(() => props.candidates, () => {
    checkAndFillContainer()
}, { deep: true }) // Deep watch just in case

onMounted(() => {
    if(listContainer.value) {
        listContainer.value.addEventListener('scroll', onScroll)
        // Initial check
        checkAndFillContainer()
    }
})

defineExpose({
    clearSelection
})
</script>

<style lang="scss" scoped>
.material-icon {
    width: 20px;
    height: 20px;
    fill: currentColor;
    flex-shrink: 0;
}

.candidate-selector {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.4em;
  color: var(--glass-text-primary);
  overflow-x: hidden; /* Prevent horizontal scroll */
}

.header-section {
  flex-shrink: 0;
  margin-bottom: 0.5em;
  
  h3 { 
      margin: 0; 
      font-size: 1.1em; 
      color: var(--glass-text-primary);
      display: flex;
      align-items: baseline;
      gap: 0.5em;
      flex-wrap: wrap; 
  }
  
  .subtitle { 
      font-size: 0.85em; 
      color: var(--glass-text-secondary); 
      font-weight: normal;
  }
}

.mobile-selected-tags {
    display: none;
    @media (max-width: 768px) {
        display: flex;
        flex-direction: column;
        gap: 0.5em;
        padding: 0 0.5em 0.5em;
        border-bottom: 1px dashed rgba(0, 0, 0, 0.1);
        margin-bottom: 0.5em;
    }
    
    .tags-header {
        font-size: 0.85em;
        color: var(--glass-text-secondary);
        font-weight: 500;
    }
    
    .tags-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5em;
    }
    
    .selected-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.1em;
        background: rgba(106, 37, 244, 0.1);
        border: 1px solid rgba(106, 37, 244, 0.2);
        color: var(--primary-color);
        padding: 0.2em 0.2em;
        border-radius: 16px;
        font-size: 0.6em;
        cursor: pointer;
        
        .tag-close-icon {
            width: 14px;
            height: 14px;
            fill: currentColor;
            opacity: 0.7;
        }
    }
}

.search-toolbar {
    flex-shrink: 0;
    margin-bottom: 0.5em;
    display: flex;
    flex-direction: column;
    gap: 0.5em;
}

.search-box {
    position: relative;
    display: flex;
    align-items: center;
    background: rgba(127, 127, 127, 0.1);
    border: 1px solid var(--glass-border);
    border-radius: 32px;
    padding: 0 0.8em;
    height: 40px;
    
    @media (max-width: 768px) {
        height: 30px;
    }
    
    .icon { opacity: 0.6; margin-right: 0.5em; width: 18px; height: 18px; }
    
    input {
        border: none;
        background: transparent;
        color: var(--glass-text-primary);
        flex: 1;
        height: 100%;
        outline: none;
        font-family: inherit;
        font-size: 0.9em;

        @media (max-width: 768px) {
            font-size: 0.65em;
        }
        
        &::placeholder { color: var(--glass-text-secondary); opacity: 0.7; }
    }
    
    .clear-btn {
        background: transparent;
        border: 1px solid rgba(127, 127, 127, 0.2);
        color: var(--glass-text-secondary);
        cursor: pointer;
        padding: 0.2em;
        border-radius: 50%; /* 改為圓形 */
        display: flex;
        align-items: center;
        transition: all 0.2s;
        &:hover { 
            color: var(--glass-text-primary); 
            background: rgba(127, 127, 127, 0.1);
        }
        .material-icon { width: 16px; height: 16px; }
    }
    
    &:focus-within {
        border-color: var(--primary-color);
        background: rgba(127, 127, 127, 0.15);
    }
}

.toolbar-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 0.2em;
    gap: 0.2em;
    
    @media (max-width: 768px) {
        flex-direction: column;
        gap: 0.5em;
        align-items: flex-start;
        position: relative;
    }
}

.batch-actions {
    display: flex;
    align-items: center;
    gap: 0.4em;
    font-size: 0.75em;
    
    @media (max-width: 768px) {
        display: none !important; /* Hide select all / clear on mobile */
    }
    
    .action-link {
        background: none;
        border: none;
        padding: 0;
        color: var(--primary-color);
        cursor: pointer;
        font-weight: 500;
        
        &:hover { text-decoration: underline; filter: brightness(1.2); }
    }
    
    .divider { color: var(--glass-text-secondary); opacity: 0.5; }
}

.list-stats {
    font-size: 0.75em;
    color: var(--glass-text-secondary);
    display: flex;
    align-items: center;
    gap: 0.5em; /* 給予間距 */
    
    @media (max-width: 768px) {
        display: none !important;
    }
}

.centered-selected-text {
    font-size: 0.8em;
    font-weight: 600;
    color: var(--glass-text-primary);
    flex: 1;
    text-align: center;
    white-space: nowrap;
    
    @media (max-width: 768px) {
        position: static;
        transform: none;
        width: 100%;
        text-align: center;
        margin-top: 0.5em;
        font-size: 1em;
        padding-bottom: 0.5em;
        border-bottom: 1px solid rgba(0,0,0,0.05);
    }
}

.list-container {
  flex: 1;
  /* Flex height hack: Force height to 0 so flex-grow controls the height entirely */
  height: 0; 
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6em;
  padding-right: 0.5em; 
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 0.3em;
  padding: 0.4em 0.8em; 
  
  @media (max-width: 768px) {
      padding: 0.2em 0.3em;
  }
  
  background: white; 
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 5px rgba(0,0,0,0.02);

  [data-theme="midnight"] & {
    background: rgba(255, 255, 255, 0.05);
  }

  &:hover {
    background: rgba(127, 127, 127, 0.03);
    border-color: rgba(127, 127, 127, 0.2);
  }

  &.active {
    background: rgba(106, 37, 244, 0.03); 
    border-color: rgba(106, 37, 244, 0.15);

    [data-theme="midnight"] & {
      background: rgba(63, 42, 107, 1);
    }
  }

  &.locked {
    opacity: 0.85;
    cursor: not-allowed;
    background: rgba(106, 37, 244, 0.04);
    border-color: rgba(106, 37, 244, 0.2);
    &:hover { background: rgba(106, 37, 244, 0.04); }

    .lock-icon {
      width: 14px;
      height: 14px;
      fill: #6A25F4;
      opacity: 0.7;
    }
  }

  &.disabled {
    opacity: 0.6;
    cursor: not-allowed;
    background: rgba(127,127,127,0.05);
    &:hover { background: rgba(127,127,127,0.05); } 
  }

  .avatar-initial {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 13px;
      flex-shrink: 0;
      
      @media (max-width: 768px) {
          display: none !important;
      }
      
      &.bg-0 { background: #E0E7FF; color: #4F46E5; }
      &.bg-1 { background: #FFEDD5; color: #C2410C; }
      &.bg-2 { background: #DCFCE7; color: #15803D; }
      &.bg-3 { background: #ECE9FE; color: #6A25F4; }
      &.bg-4 { background: #E0F2FE; color: #0369A1; }
  }

  &.active .checkbox {
      background: var(--primary-color);
      border-color: var(--primary-color);
      opacity: 1;
  }

  .checkbox {
    width: 22px; 
    height: 22px;
    border-radius: 50%;
    border: 2px solid var(--glass-border);
    margin-left: auto; /* Push to right by default on desktop */
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.8em;
    flex-shrink: 0;
    transition: all 0.2s;
    
    @media (max-width: 768px) {
        width: 18px;
        height: 18px;
        order: -1;          /* Force to the left side */
        margin-left: 0;     /* emove desktop push-right */
        margin-right: 0.5em;
    }
    
    .check-icon { width: 14px; height: 14px; }
  }

  .info {
    display: flex;
    align-items: center;
    gap: 0.5em;
    font-size: 0.9em;
    min-width: 0;
    flex: 1;
    
    @media (max-width: 768px) {
        font-size: 0.85em;
        flex-direction: column;
        align-items: flex-start;
        gap: 0.1em;
    }
    
    .name { 
        font-weight: 500; 
        font-size: 0.9em;
        color: var(--glass-text-primary); 
        
        @media (max-width: 768px) {
            font-size: 0.95em;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 0.1em;
        }
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1; 

        .position {
            font-size: 0.8em;
            color: var(--glass-text-secondary);
            font-weight: normal;
            margin-left: 0.3em;
            
            @media (max-width: 768px) {
                margin-left: 0;
                font-size: 0.4em;
            }
        }
        
        .email {
            font-size: 0.6em;
            color: var(--glass-text-secondary);
            margin-left: 0.5em;
            display: none; 
            
            @media (max-width: 768px) {
                display: block;
                margin-left: 0;
            }
        }
    }
  }
}

.empty-state {
    text-align: center;
    padding: 2em;
    color: var(--glass-text-secondary);
    font-style: italic;
}

.loading-more {
    padding: 1em;
    text-align: center;
    color: var(--glass-text-secondary);
    font-size: 0.85em;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5em;

    .spinner-small {
        width: 16px; 
        height: 16px; 
        border: 2px solid rgba(127,127,127, 0.2); 
        border-top-color: var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
}

.scroll-hint {
    padding: 0.8em;
    text-align: center;
    color: var(--glass-text-secondary);
    font-size: 0.8em;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.3em;
    opacity: 0.7;
    transition: opacity 0.2s;
    
    &.clickable {
        cursor: pointer;
        &:hover {
            opacity: 1;
            background: rgba(127, 127, 127, 0.05);
            border-radius: 8px;
        }
    }
    
    .arrow {
        animation: scroll-hint-bounce 2s infinite;
    }
}

@keyframes scroll-hint-bounce {
  0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
  40% {transform: translateY(5px);}
  60% {transform: translateY(3px);}
}

</style>
