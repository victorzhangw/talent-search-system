<template>
  <!-- Apply theme to root -->
  <div class="chat-container" :data-theme="currentTheme">
    <!-- Header -->
    <div class="header">
      <div class="title">
        <!-- Icon: psychology (Brain/AI) -->
        <svg class="material-icon title-icon" viewBox="0 0 24 24">
            <path d="M6 5.5v13h12v-13H6zm12-1.5c.83 0 1.5.67 1.5 1.5v13c0 .83-.67 1.5-1.5 1.5H6c-.83 0-1.5-.67-1.5-1.5v-13c0-.83.67-1.5 1.5-1.5h12z M13 8.5h-2v2H9v2h2v2h2v-2h2v-2h-2v-2z" fill-rule="evenodd"/>
            <path d="M0 0h24v24H0z" fill="none"/>
            <circle cx="14.5" cy="18.5" r="1"/> <circle cx="9.5" cy="5.5" r="1"/> <circle cx="5.5" cy="13.5" r="1"/> <circle cx="18.5" cy="10.5" r="1"/>
        </svg>
        人才智庫助手
      </div>
      <div class="actions">
        <!-- Theme Switcher -->
        <div class="theme-selector">
            <button class="icon-btn theme-btn" @click="cycleTheme" :title="'切換主題: ' + currentThemeLabel">
                <!-- Dynamic Material Icons for Themes -->
                <svg v-if="currentTheme === 'light'" class="material-icon" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.79 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"/></svg>
                <svg v-else-if="currentTheme === 'midnight'" class="material-icon" viewBox="0 0 24 24"><path d="M11.1 12.08c-2.33-4.51-.5-8.48.53-10.07C6.27 2.2 1.98 6.59 1.98 12c0 .14.02.28.02.42.62-.27 1.29-.42 2-.42 1.66 0 3.18.83 4.1 2.15 1.67.48 2.9 2.02 2.9 3.85 0 1.52-.87 2.83-2.12 3.51.98.32 2.03.5 3.11.5 3.5 0 6.58-1.8 8.37-4.52-2.36.23-6.98-.97-9.26-5.41z"/><path d="M7 16h-.18C6.4 14.84 5.3 14 4 14c-1.66 0-3 1.34-3 3s1.34 3 3 3h3v-4z"/></svg>
                <svg v-else-if="currentTheme === 'sepia'" class="material-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/></svg>
                <svg v-else class="material-icon" viewBox="0 0 24 24"><path d="M9.37 5.51c-.18.64-.27 1.31-.27 1.99 0 4.08 3.32 7.4 7.4 7.4.68 0 1.35-.09 1.99-.27C17.45 18.5 14.47 21 11 21c-4.97 0-9-4.03-9-9 0-3.47 2.5-6.45 5.96-7.49zC7.2 4.08 7.37 3.54 7.58 3c-2.8.19-5.26 1.63-6.84 3.7C2 5.66 3.66 5 5.5 5c1.43 0 2.75.4 3.87 1.11.0-.2.0-.4.0-.6z"/></svg>
            </button>
        </div>
        
        <button 
          v-if="currentTab === 'chat'" 
          class="text-btn" 
          @click="resetAndReselect"
        >
          重選
        </button>
        <!-- Icon: Close -->
        <button class="icon-btn close-btn" @click="$emit('close')">
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>
    </div>

    <!-- Content Area -->
    <div class="content-body">
      
      <!-- Tab 0: Login -->
      <LoginView
        v-if="currentTab === 'login'"
        @login-success="handleLoginSuccess"
       />

      <!-- Tab 1: Selection -->
      <CandidateSelector 
        v-else-if="currentTab === 'selection'"
        :candidates="candidates"
        @confirm="handleSelectionConfirmed"
      />

      <!-- Tab 2: Chat -->
      <div v-else-if="currentTab === 'chat'" class="chat-view">
        <div class="selected-summary">
            已鎖定: 
            <span 
                v-for="(cand, idx) in selectedCandidatesObjects" 
                :key="cand.id"
                class="candidate-link"
                @click="openReport(cand)"
            >
                {{ cand.name }}<span v-if="idx < selectedCandidatesObjects.length - 1">, </span>
            </span>
        </div>
        
        <MessageList :messages="messages" />

        <div class="input-area">
          <textarea 
            v-model="inputQuery" 
            @keydown.enter.prevent="sendMessage"
            placeholder="請輸入關於候選人的問題... (Shift+Enter 換行)"
            :disabled="isTyping"
          ></textarea>
          <button class="send-btn" @click="sendMessage" :disabled="!inputQuery.trim() || isTyping">
            <!-- Icon: Send -->
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <TraitReportModal 
        v-if="showReportModal"
        :candidateId="currentReportCandidate.id"
        :candidateName="currentReportCandidate.name"
        :token="userToken"
        @close="showReportModal = false"
    />

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import MessageList from './MessageList.vue'
import CandidateSelector from './CandidateSelector.vue'
import LoginView from './LoginView.vue'
import TraitReportModal from './TraitReportModal.vue'

const emit = defineEmits(['close'])

const currentTab = ref('login') // Defaut to login
const userToken = ref(null)

const messages = ref([
  { role: 'ai', content: '您好！我是您的人才評鑑助手。請先選擇候選人，我將為您提供特質分析與建議。' }
])
const inputQuery = ref('')
const isTyping = ref(false)

const candidates = ref([])
const selectedCandidateIds = ref([])

// Theme Logic
const themes = ['default', 'light', 'midnight', 'sepia']
const themeIndex = ref(0)
const currentTheme = computed(() => themes[themeIndex.value])

const currentThemeLabel = computed(() => {
     switch(currentTheme.value) {
        case 'light': return '明亮'
        case 'midnight': return '深邃'
        case 'sepia': return '閱讀'
        default: return '標準'
    }
})

const cycleTheme = () => {
    themeIndex.value = (themeIndex.value + 1) % themes.length
}

const currentSessionId = ref(crypto.randomUUID())

const selectedCandidatesObjects = computed(() => {
  return candidates.value.filter(c => selectedCandidateIds.value.includes(c.candidate_id))
})

// Modal Logic
const showReportModal = ref(false)
const currentReportCandidate = ref({})

const openReport = (cand) => {
    currentReportCandidate.value = cand
    showReportModal.value = true
}

const handleLoginSuccess = async (authData) => {
    userToken.value = authData.token
    // Fetch candidates after login
    await fetchCandidates()
    currentTab.value = 'selection'
}

const fetchCandidates = async () => {
  try {
    // CORRECTED: Ensure trailing slash to match Flask strict routing
    const res = await fetch('http://localhost:5000/api/v2/candidates/', {
        headers: {
            'Authorization': `Bearer ${userToken.value}`
        }
    })
    const data = await res.json()
    // Handle both mock format and real format (from Traitty API)
    // Traitty API returns { data: [...] }
    const rawList = data.data || data.candidates || data || []
    
    candidates.value = rawList.map(c => ({
        ...c, 
        id: c.candidate_id,
        // Ensure position exists if API returns null
        position: c.position || 'Unknown' 
    }))
  } catch (e) {
    console.error("Failed to load candidates", e)
    candidates.value = []
  }
}

const handleSelectionConfirmed = (ids) => {
    selectedCandidateIds.value = ids
    currentTab.value = 'chat'
    messages.value.push({ 
        role: 'ai', 
        content: `已鎖定 ${ids.length} 位候選人。您現在可以針對他們進行提問。` 
    })
}

// Reset Logic: Clears history and generates new session
const resetAndReselect = () => {
    messages.value = [{ role: 'ai', content: '您好！我是您的人才評鑑助手。請先選擇候選人，我將為您提供特質分析與建議。' }]
    selectedCandidateIds.value = []
    currentSessionId.value = crypto.randomUUID() // New Session -> New Context
    inputQuery.value = ''
    currentTab.value = 'selection'
}

const sendMessage = async (e) => {
  if (e && e.shiftKey) return; 
  
  const query = inputQuery.value.trim()
  if (!query || isTyping.value) return

  messages.value.push({ role: 'user', content: query })
  inputQuery.value = ''
  isTyping.value = true

  const aiMsgIndex = messages.value.push({ 
    role: 'ai', 
    content: '', 
    intent: '', 
    isTyping: true 
  }) - 1

  try {
    // CORRECTED: Ensure trailing slash to match Flask strict routing
    const response = await fetch('http://localhost:5000/chat/', { 
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken.value}`
      },
      body: JSON.stringify({
        query: query,
        candidate_ids: selectedCandidateIds.value, 
        session_id: currentSessionId.value // Dynamic Session ID
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk
      
      const lines = buffer.split('\n\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6)
          if (jsonStr === '[DONE]') {
            continue
          }
          try {
            const data = JSON.parse(jsonStr)
            if (data.type === 'meta') {
              messages.value[aiMsgIndex].intent = data.intent
            } else if (data.type === 'token') {
              messages.value[aiMsgIndex].content += data.content
            }
          } catch (e) { console.error(e) }
        }
      }
    }
  } catch (error) {
    messages.value[aiMsgIndex].content = "系統錯誤。"
  } finally {
    isTyping.value = false
    messages.value[aiMsgIndex].isTyping = false
  }
}
</script>

<style lang="scss" scoped>
@import '../styles/glass.scss';

.material-icon {
    width: 24px;
    height: 24px;
    fill: currentColor;
    flex-shrink: 0;
}

.chat-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  width: 50vw; /* User Request: 1/2 Screen Width */
  min-width: 600px;
  height: 800px;
  max-height: 92vh;
  max-width: 95vw;
  z-index: 9999;
  
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);

  @include glass-effect(true); 
  
  background: var(--glass-bg);
  border-color: var(--glass-border);
  color: var(--glass-text-primary);
}

.header {
  padding: 0.8rem 1.2rem;
  border-bottom: 1px solid var(--glass-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(var(--glass-text-primary), 0.05); /* Adaptive header bg */
  flex-shrink: 0;
  
  .title { 
    font-weight: 700; 
    font-size: 1rem; 
    display: flex; 
    align-items: center; 
    gap: 0.5rem; 
    color: var(--glass-text-primary);
    
    .title-icon {
        width: 20px; 
        height: 20px;
        color: var(--primary-color); 
    }
  }
  
  .actions {
    display: flex;
    gap: 0.8rem;
    align-items: center;
  }
  
  .text-btn {
    background: rgba(127,127,127,0.1);
    border: 1px solid var(--glass-border);
    color: var(--glass-text-secondary);
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-size: 0.8rem;
    cursor: pointer;
    &:hover { background: rgba(127,127,127,0.2); color: var(--glass-text-primary); }
  }

  .icon-btn { 
    background: none; 
    border: none; 
    color: var(--glass-text-secondary); 
    cursor: pointer; 
    font-size: 1.1rem; 
    padding: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    
    &:hover { 
        color: var(--glass-text-primary); 
        background: rgba(127,127,127,0.1); 
    }
    
    &.close-btn:hover {
        color: #ef4444; /* Standard Red for Close */
        background: rgba(239, 68, 68, 0.1);
    }
  }
}

.content-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0; 
}

.chat-view {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.selected-summary {
    padding: 0.4rem 1rem;
    background: rgba(79, 70, 229, 0.1); 
    border-bottom: 1px solid var(--glass-border);
    font-size: 0.8rem;
    color: var(--primary-color); /* Matches theme */
    flex-shrink: 0;

    /* Clickable Link Style */
    .candidate-link {
        cursor: pointer;
        text-decoration: underline;
        font-weight: 600;
        &:hover {
            color: var(--glass-text-primary);
        }
    }
}

.input-area {
  padding: 0.8rem 1rem;
  border-top: 1px solid var(--glass-border);
  display: flex;
  gap: 0.8rem;
  background: rgba(127, 127, 127, 0.05);
  flex-shrink: 0;

  textarea {
    flex: 1;
    background: rgba(127, 127, 127, 0.1);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    color: var(--glass-text-primary);
    resize: none;
    height: 48px;
    font-family: inherit;
    font-size: 0.95rem;
    line-height: 1.4;
    transition: all 0.2s;
    
    &:focus { 
      outline: none; 
      border-color: var(--primary-color); 
      background: rgba(127, 127, 127, 0.15); 
    }
    &::placeholder { color: var(--glass-text-secondary); opacity: 0.7; }
  }

  .send-btn {
    background: var(--primary-color);
    border: none;
    border-radius: 8px;
    width: 48px;
    height: 48px;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
    
    .material-icon { width: 20px; height: 20px; }
    
    &:hover:not(:disabled) { background: var(--primary-hover); }
    &:disabled { opacity: 0.5; cursor: not-allowed; background: #6b7280; }
  }
}
</style>
