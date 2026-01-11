<template>
  <div class="candidate-selector">
    <div class="header-section">
      <h3>
        請選擇評估候選人
        <span class="subtitle">（您可以選擇一位或多位候選人進行分析）</span>
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
                placeholder="搜尋姓名或職位..."
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
            <button class="action-link" v-if="selectedIds.length > 0" @click="selectedIds = []">
                清除已選
            </button>
        </div>
    </div>

    <!-- Stats -->
    <div class="list-stats" v-if="searchQuery">
       搜尋結果: {{ filteredCandidates.length }} 筆
    </div>

    <!-- List -->
    <div class="list-container">
      <div 
        v-for="cand in filteredCandidates" 
        :key="cand.id" 
        class="candidate-item"
        :class="{ active: selectedIds.includes(cand.id) }"
        @click="toggle(cand.id)"
      >
        <div class="checkbox">
          <!-- Icon: Check -->
          <svg v-if="selectedIds.includes(cand.id)" class="material-icon check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
        </div>
        
        <div class="info">
          <span class="role">{{ cand.position || '候選人' }}</span>
          <span class="separator">-</span>
          <span class="name">{{ cand.name }}</span>
        </div>
      </div>
      
      <div v-if="filteredCandidates.length === 0" class="empty-state">
          沒有找到匹配的候選人
      </div>
    </div>

    <div class="action-footer">
      <div class="selected-count">
        已選擇 {{ selectedIds.length }} 位
      </div>
      <button 
        class="start-btn" 
        :disabled="selectedIds.length === 0"
        @click="$emit('confirm', selectedIds)"
      >
        開始分析
        <!-- Icon: Arrow Forward -->
        <svg class="material-icon" viewBox="0 0 24 24"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  candidates: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['confirm'])
const selectedIds = ref([])
const searchQuery = ref('')

// Filter Logic
const filteredCandidates = computed(() => {
    const query = searchQuery.value.toLowerCase().trim()
    if (!query) return props.candidates
    
    return props.candidates.filter(c => {
        const nameMatch = (c.name || '').toLowerCase().includes(query)
        const posMatch = (c.position || '').toLowerCase().includes(query)
        return nameMatch || posMatch
    })
})

const toggle = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  } else {
    selectedIds.value.push(id)
  }
}

// Batch Actions
const selectAllFiltered = () => {
    const idsToAdd = filteredCandidates.value.map(c => c.id)
    const newSelection = [...new Set([...selectedIds.value, ...idsToAdd])]
    selectedIds.value = newSelection
}
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
  padding: 1.5rem;
  color: var(--glass-text-primary);
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
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-right: 0.5rem; 
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem; 
  
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

  /* Fixed Nesting Logic */
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
    
    .role { 
        font-weight: 700; 
        color: var(--glass-text-primary); 
    }
    
    .separator {
        color: var(--glass-text-secondary);
        opacity: 0.6;
    }
    
    .name { 
        font-weight: 400; 
        color: var(--glass-text-secondary); 
    }
  }
}

.empty-state {
    text-align: center;
    padding: 2rem;
    color: var(--glass-text-secondary);
    font-style: italic;
}

.action-footer {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px solid var(--glass-border);
  flex-shrink: 0;

  .selected-count {
      color: var(--glass-text-secondary);
      font-size: 0.9rem;
  }

  .start-btn {
    background: var(--primary-color);
    color: white;
    border: none;
    padding: 0.6rem 1.2rem;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      background: gray;
    }
    
    &:hover:not(:disabled) {
      background: var(--primary-hover);
    }
  }
}
</style>
