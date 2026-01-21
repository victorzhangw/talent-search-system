<template>
  <div class="candidate-selector">
    <div class="header-section">
      <h3>
        請選擇評估候選人
        <span class="subtitle"></span>
      </h3>
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

    <!-- Stats -->
    <div class="list-stats">
       <span v-if="searchQuery">搜尋結果: {{ filteredCandidates.length }} 筆</span>
       <span v-else>已顯示 {{ candidates.length }} / 共 {{ totalCount }} 筆</span>
    </div>

    <!-- List -->
    <div class="list-container" ref="listContainer">
      <div 
        v-for="cand in filteredCandidates" 
        :key="cand.id" 
        class="candidate-item"
        :class="{ active: selectedIds.includes(cand.id), disabled: disabled }"
        @click="!disabled && toggle(cand.id)"
      >
        <div class="checkbox">
          <!-- Icon: Check -->
          <svg v-if="selectedIds.includes(cand.id)" class="material-icon check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
        </div>
        
        <div class="info">
          <span class="name">
            {{ cand.name }}
            <span v-if="cand.position"> - {{ cand.position }}</span>
            <span v-if="cand.email" class="email">({{ cand.email }})</span>
          </span>
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

    <div class="selected-count">
      已選擇 {{ selectedIds.length }} 位
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
  }
})

const emit = defineEmits(['change', 'load-more'])
const selectedIds = ref([])
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

const toggle = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  } else {
    selectedIds.value.push(id)
  }
  emit('change', selectedIds.value)
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
  padding: 1.1rem;
  color: var(--glass-text-primary);
  overflow-x: hidden; /* Prevent horizontal scroll */
}

.header-section {
  flex-shrink: 0;
  margin-bottom: 1rem;
  
  h3 { 
      margin: 0; 
      font-size: 1.1rem; 
      color: var(--glass-text-primary);
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      flex-wrap: wrap; 
  }
  
  .subtitle { 
      font-size: 0.85rem; 
      color: var(--glass-text-secondary); 
      font-weight: normal;
  }
}

.search-toolbar {
    flex-shrink: 0;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
}

.search-box {
    position: relative;
    display: flex;
    align-items: center;
    background: rgba(127, 127, 127, 0.1);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    padding: 0 0.8rem;
    height: 40px;
    
    .icon { opacity: 0.6; margin-right: 0.5rem; width: 18px; height: 18px; }
    
    input {
        border: none;
        background: transparent;
        color: var(--glass-text-primary);
        flex: 1;
        height: 100%;
        outline: none;
        font-family: inherit;
        font-size: 0.95rem;
        
        &::placeholder { color: var(--glass-text-secondary); opacity: 0.7; }
    }
    
    .clear-btn {
        background: none;
        border: none;
        color: var(--glass-text-secondary);
        cursor: pointer;
        padding: 0.2rem;
        display: flex;
        align-items: center;
        &:hover { color: var(--glass-text-primary); }
        .material-icon { width: 16px; height: 16px; }
    }
    
    &:focus-within {
        border-color: var(--primary-color);
        background: rgba(127, 127, 127, 0.15);
    }
}

.batch-actions {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    font-size: 0.85rem;
    
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
    font-size: 0.8rem;
    color: var(--glass-text-secondary);
    margin-bottom: 0.5rem;
    padding-left: 0.2rem;
}

.list-container {
  flex: 1;
  /* Flex height hack: Force height to 0 so flex-grow controls the height entirely */
  height: 0; 
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-right: 0.5rem; 
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.6rem; 
  
  background: rgba(127, 127, 127, 0.05); 
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(127, 127, 127, 0.1);
  }

  &.active {
    background: rgba(79, 70, 229, 0.15); 
    border-color: var(--primary-color);
  }

  &.disabled {
    opacity: 0.6;
    cursor: not-allowed;
    background: rgba(127,127,127,0.05); /* Force non-hover look */
    &:hover { background: rgba(127,127,127,0.05); } 
  }

  &.active .checkbox {
      background: var(--primary-color);
      border-color: var(--primary-color);
      opacity: 1;
  }

  .checkbox {
    width: 20px; 
    height: 20px;
    border-radius: 5px;
    border: 2px solid var(--glass-text-secondary);
    opacity: 0.6;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white; /* White icon on Primary Color */
    font-size: 0.8rem;
    flex-shrink: 0;
    
    .check-icon { width: 16px; height: 16px; }
  }

  .info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    min-width: 0; /* Crucial for flex child truncation */
    flex: 1;
    
    .name { 
        font-weight: 500; 
        font-size: 0.95rem;
        color: var(--glass-text-primary); 
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1; 
        
        .email {
            font-size: 0.75rem;
            color: var(--glass-text-secondary);
            margin-left: 0.5rem;
            display: inline-block;
        }
    }
  }
}

.empty-state {
    text-align: center;
    padding: 2rem;
    color: var(--glass-text-secondary);
    font-style: italic;
}

.loading-more {
    padding: 1rem;
    text-align: center;
    color: var(--glass-text-secondary);
    font-size: 0.85rem;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;

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
    padding: 0.8rem;
    text-align: center;
    color: var(--glass-text-secondary);
    font-size: 0.8rem;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.3rem;
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
        animation: bounce 2s infinite;
    }
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
  40% {transform: translateY(5px);}
  60% {transform: translateY(3px);}
}

.selected-count {
    color: var(--glass-text-secondary);
    font-size: 0.9rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--glass-border);
    flex-shrink: 0;
}
</style>
