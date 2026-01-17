<template>
  <!-- Apply theme to root -->
  <div class="chat-container" :class="{ 'full-page-mode': isFullPage }" :data-theme="currentTheme">
    <!-- Header -->
    <div class="header">
      <div class="title">
        <!-- Icon: psychology (Brain/AI) -->
        <svg class="material-icon title-icon" viewBox="0 0 24 24">
            <path d="M6 5.5v13h12v-13H6zm12-1.5c.83 0 1.5.67 1.5 1.5v13c0 .83-.67 1.5-1.5 1.5H6c-.83 0-1.5-.67-1.5-1.5v-13c0-.83.67-1.5 1.5-1.5h12z M13 8.5h-2v2H9v2h2v2h2v-2h2v-2h-2v-2z" fill-rule="evenodd"/>
            <path d="M0 0h24v24H0z" fill="none"/>
            <circle cx="14.5" cy="18.5" r="1"/> <circle cx="9.5" cy="5.5" r="1"/> <circle cx="5.5" cy="13.5" r="1"/> <circle cx="18.5" cy="10.5" r="1"/>
        </svg>
        Traitty Beta
      </div>
      <div class="actions">
        <!-- New Tab Button (Hidden if already in full page mode) -->
        <button v-if="!isFullPage" class="icon-btn new-tab-btn" @click="openNewTab" title="在新分頁開啟">
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
        </button>

        <!-- Theme Switcher -->
        <div class="theme-selector">
            <button class="icon-btn theme-btn" @click="cycleTheme" :title="'切換主題: ' + currentThemeLabel">
                <!-- Dynamic Material Icons for Themes -->
                <svg v-if="currentTheme === 'light'" class="material-icon" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.8 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"/></svg>
                <svg v-else class="material-icon" viewBox="0 0 24 24"><path d="M11.1 12.08c-2.33-4.51-.5-8.48.53-10.07C6.27 2.2 1.98 6.59 1.98 12c0 .14.02.28.02.42.62-.27 1.29-.42 2-.42 1.66 0 3.18.83 4.1 2.15 1.67.48 2.9 2.02 2.9 3.85 0 1.52-.87 2.83-2.12 3.51.98.32 2.03.5 3.11.5 3.5 0 6.58-1.8 8.37-4.52-2.36.23-6.98-.97-9.26-5.41z"/><path d="M7 16h-.18C6.4 14.84 5.3 14 4 14c-1.66 0-3 1.34-3 3s1.34 3 3 3h3v-4z"/></svg>
            </button>
        </div>
        
        <!-- Icon: Close -->
        <button class="icon-btn close-btn" @click="$emit('close')">
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>
    </div>

    <!-- Main Flex Container -->
    <div class="main-layout">
        
        <!-- Login View (Intercepts everything if not logged in) -->
        <div v-if="currentTab === 'login'" class="content-body">
            <!-- Loading State -->
            <div v-if="isInitializing" class="loading-view">
                <div class="spinner"></div>
                <p>驗證身分中...</p>
            </div>
            
            <LoginView
                v-else
                :serverRoot="computedServerRoot"
                :initialError="autoLoginError"
                @login-success="handleLoginSuccess"
            />
        </div>

        <!-- Split View (Selection Left + Chat Right) -->
        <div v-else class="split-view">
            
            <!-- LEFT PANEL: Candidate List -->
            <div class="left-panel">
                <div class="panel-header" v-if="!isSelectionLocked">
                     <button 
                        class="primary-btn full-width"
                        :disabled="selectedCandidateIds.length === 0"
                        @click="lockSelectionAndStart"
                     >
                        開始分析 ({{ selectedCandidateIds.length }})
                     </button>
                </div>
                <div class="panel-header" v-else>
                     <button class="secondary-btn full-width" @click="resetAndReselect">
                        重選候選人
                     </button>
                </div>
                
                <!-- Selector Wrapper -->
                <div class="selector-wrapper">
                    <CandidateSelector 
                        ref="candidateSelectorRef"
                        :candidates="candidates"
                        :is-loading="isLoadingCandidates"
                        :has-more="hasMoreCandidates"
                        :disabled="isSelectionLocked"
                        @change="handleSelectionChange"
                        @load-more="loadMoreCandidates"
                    />

                    <!-- Locked Overlay -->
                    <div v-if="isSelectionLocked" class="locked-overlay">
                        <div class="overlay-content">
                            <!-- Icon: Lock -->
                            <svg class="material-icon large" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>
                            <h3>已進入分析模式</h3>
                            <p>下方列表已暫時鎖定。</p>
                            <p style="font-size: 0.8rem; margin-top: 0.5rem;">如需切換候選人，請點擊上方的「重選」按鈕。</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- RIGHT PANEL: Chat Area -->
            <div class="right-panel">
                
                <!-- Chat View -->
                <div v-if="isSelectionLocked" class="chat-view">
                    <div class="selected-summary">
                        已鎖定: 
                        <span 
                            v-for="(cand, idx) in activeConversationCandidatesObjects" 
                            :key="cand.id"
                            class="candidate-link"
                            @click="openReport(cand)"
                        >
                            {{ cand.name }}<span v-if="idx < activeConversationCandidatesObjects.length - 1">, </span>
                        </span>
                    </div>
                    
                    <MessageList :messages="messages" />

                    <div class="input-area">
                        <textarea 
                            v-model="inputQuery" 
                            @keydown.enter.prevent="sendMessage"
                            placeholder="請提問... (Shift+Enter 換行)"
                            :disabled="isTyping"
                        ></textarea>
                        <button class="send-btn" @click="sendMessage" :disabled="!inputQuery.trim() || isTyping">
                            <!-- Icon: Send -->
                            <svg class="material-icon" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                        </button>
                    </div>
                </div>

                <!-- Empty State Placeholder -->
                <div v-else class="empty-layout-placeholder">
                     <div class="placeholder-content">
                        <!-- Icon: Touch App / Click -->
                        <svg class="material-icon large" viewBox="0 0 24 24"><path d="M9 11.24V7.5C9 6.12 10.12 5 11.5 5S14 6.12 14 7.5v3.74c1.21-.81 2-2.18 2-3.74C16 5.01 13.99 3 11.5 3S7 5.01 7 7.5c0 1.56.79 2.93 2 3.74zm9.84 4.63l-4.54-2.26c-.17-.07-.35-.11-.54-.11H13v-6c0-.83-.67-1.5-1.5-1.5S10 6.67 10 7.5v10.74l-3.43-.72c-.08-.01-.15-.03-.24-.03-.31 0-.59.13-.79.33l-.79.8 4.94 4.94c.27.27.65.44 1.06.44h6.79c.75 0 1.33-.55 1.44-1.28l.75-5.27c.01-.07.02-.14.02-.2 0-.62-.38-1.16-.91-1.38z"/></svg>
                        <h3>準備開始</h3>
                        <p>請從左側列表勾選候選人，然後點擊「開始分析」。</p>
                     </div>
                </div>

            </div>

            <!-- Right Sidebar -->
            <div v-if="isSelectionLocked" class="quick-sidebar">
                <div class="sidebar-title">
                    <svg class="material-icon small" viewBox="0 0 24 24"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg>
                    快速提問
                </div>
                <div class="quick-btn-list">
                    <button 
                        v-for="(q, idx) in quickQuestions" 
                        :key="idx" 
                        class="quick-btn"
                        @click="sendQuickMessage(q)"
                        :disabled="isTyping"
                    >
                        {{ q }}
                    </button>
                </div>
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
import { ref, computed, onMounted } from 'vue'
import MessageList from './MessageList.vue'
import CandidateSelector from './CandidateSelector.vue'
import LoginView from './LoginView.vue'
import TraitReportModal from './TraitReportModal.vue'

const emit = defineEmits(['close'])
const props = defineProps({
    isFullPage: {
        type: Boolean,
        default: false
    }
})

const currentTab = ref('login') // 'login' or 'main' (split view)
const isSelectionLocked = ref(false) // Controls the split view state

const userToken = ref(null)
const autoLoginError = ref('')

const messages = ref([
  { role: 'ai', content: '您好！我是Traitty，將為您提供特質分析與建議。' }
])
const inputQuery = ref('')
const isTyping = ref(false)

const candidates = ref([])
// UI Selection State
const selectedCandidateIds = ref([]) 
// Active Conversation Logic State
const activeConversationCandidateIds = ref([])

const isLoadingCandidates = ref(false)
const hasMoreCandidates = ref(true)
const candidateOffset = ref(0)
const PAGE_LIMIT = 20
const candidateSelectorRef = ref(null)

// Theme Logic
const themes = ['light', 'midnight']
const themeIndex = ref(0)
const currentTheme = computed(() => themes[themeIndex.value])

const currentThemeLabel = computed(() => {
     switch(currentTheme.value) {
        case 'light': return '明亮 (白)'
        case 'midnight': return '深邃 (黑)'
        default: return '標準'
    }
})

const cycleTheme = () => {
    themeIndex.value = (themeIndex.value + 1) % themes.length
}

const openNewTab = () => {
    // Save state to LOCAL STORAGE for cross-tab sharing
    const state = {
        token: userToken.value,
        activeIds: activeConversationCandidateIds.value,
        selectedCandidates: candidates.value.filter(c => activeConversationCandidateIds.value.includes(c.candidate_id)),
        messages: messages.value,
        sessionId: currentSessionId.value,
        theme: themeIndex.value
    }
    
    try {
        localStorage.setItem('traitty_new_tab_state', JSON.stringify(state))
    } catch (e) {
        console.error("Failed to save state for new tab", e)
    }

    // Open New Tab with 'mode=fullpage' param
    const url = new URL(window.location.href)
    url.searchParams.set('mode', 'fullpage')
    window.open(url.toString(), '_blank')
    
    // Reset Current Window State (Pop-out behavior)
    resetAndReselect()
    
    // Close the widget in current window
    emit('close')
}

const currentSessionId = ref(crypto.randomUUID())

// Used for "Locked: XXX, YYY" display
const activeConversationCandidatesObjects = computed(() => {
  return candidates.value.filter(c => activeConversationCandidateIds.value.includes(c.candidate_id))
})


// --- API Configuration Helper ---
const getApiConfig = () => {
    const config = window.TRAITTY_WIDGET_CONFIG || {}
    // Default to localhost for dev fallback
    const rawBaseUrl = config.apiBaseUrl || 'http://localhost:5000/api/v2'
    
    // Deduce Server Root (remove /api/v2 if present)
    let serverRoot = rawBaseUrl
    if (serverRoot.includes('/api/v2')) {
        serverRoot = serverRoot.split('/api/v2')[0]
    }
    // Remove trailing slash
    if (serverRoot.endsWith('/')) serverRoot = serverRoot.slice(0, -1)
    
    // Ensure rawBaseUrl has no trailing slash also for consistency
    let apiBaseUrl = rawBaseUrl
    if (apiBaseUrl.endsWith('/')) apiBaseUrl = apiBaseUrl.slice(0, -1)

    return { serverRoot, apiBaseUrl }
}

const computedServerRoot = computed(() => getApiConfig().serverRoot)

// Modal Logic
const showReportModal = ref(false)
const currentReportCandidate = ref({})

const quickQuestions = ref([
    "候選人的主要優勢是什麼？",
    "他/她適合擔任什麼角色？",
    "有什麼潛在風險或缺點嗎？",
    "與團隊合作的適配性如何？",
    "請比較所選候選人的領導風格。",
    "如何提升這位候選人的績效？"
])

const sendQuickMessage = (text) => {
    inputQuery.value = text
    sendMessage()
}

// NEW: Batch fetch trait reports for all selected candidates
const fetchBatchTraitReports = async (selectedCandidates) => {
    const { apiBaseUrl } = getApiConfig()
    
    // Extract assessment IDs from selected candidates
    const assessmentIds = selectedCandidates
        .map(c => c.latest_assessment?.assessment_id)
        .filter(id => id != null)
    
    if (assessmentIds.length === 0) {
        return
    }
    
    const apiUrl = `${apiBaseUrl}/reports/batch`
    const payload = { assessment_ids: assessmentIds }
    
    try {
        const res = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken.value}`
            },
            body: JSON.stringify(payload)
        })
        
        if (!res.ok) {
            throw new Error(`Batch reports fetch failed: ${res.status}`)
        }
        
        const data = await res.json()
        
        // Store reports in Session Storage, keyed by candidate_id
        const reportsMap = {}
        data.reports.forEach(report => {
            const candidate = selectedCandidates.find(
                c => c.latest_assessment?.assessment_id === report.assessment_id
            )
            if (candidate) {
                reportsMap[candidate.candidate_id] = report
            }
        })
        
        sessionStorage.setItem('traitty_batch_reports', JSON.stringify(reportsMap))
        console.log('[ChatContainer] ✅ Saved to Session Storage')
        
    } catch (e) {
        console.error('[ChatContainer] ❌ Failed to fetch batch reports:', e)
    }
}

const openReport = (cand) => {
    currentReportCandidate.value = cand
    showReportModal.value = true
}

const handleLoginSuccess = async (authData) => {
    userToken.value = authData.token
    // Fetch candidates after login
    await fetchCandidates()
    currentTab.value = 'main' // Switch to split view
    
    // After login and candidates load, check if we need to restore state (New Tab scenario)
    restoreSessionState()
}

const restoreSessionState = () => {
    try {
        // Priority 1: Check Local Storage (from New Tab action)
        const newTabStateRaw = localStorage.getItem('traitty_new_tab_state')
        if (newTabStateRaw) {
            const state = JSON.parse(newTabStateRaw)
            console.log('[ChatContainer] Hydrating from Local Storage (New Tab)...')
            
            // Restore Token if not already set (this bypasses auto-login wait)
            if (state.token && !userToken.value) {
                userToken.value = state.token
                // We might need to fetch candidates now if not done yet
                if (candidates.value.length === 0) fetchCandidates()
                currentTab.value = 'main'
            }
            
            if (state.activeIds && state.activeIds.length > 0) {
                activeConversationCandidateIds.value = state.activeIds
                isSelectionLocked.value = true
                selectedCandidateIds.value = [] // Keep UI clean
            }
            
            if (state.messages) messages.value = state.messages
            if (state.sessionId) currentSessionId.value = state.sessionId
            if (state.theme !== undefined) themeIndex.value = state.theme
            
            // Clear it so it doesn't persist forever
            localStorage.removeItem('traitty_new_tab_state')
            return 
        }

        // Priority 2: Check Session Storage (Same tab reload)
        const rawIds = sessionStorage.getItem('traitty_session_active_ids')
        if (rawIds) {
            const ids = JSON.parse(rawIds)
            if (Array.isArray(ids) && ids.length > 0) {
                console.log('[ChatContainer] Restoring session state for IDs:', ids)
                activeConversationCandidateIds.value = ids
                isSelectionLocked.value = true
                selectedCandidateIds.value = [] 
            }
        }
    } catch (e) {
        console.error("Failed to restore session state", e)
    }
}

const loadMoreCandidates = () => {
    if (isLoadingCandidates.value || !hasMoreCandidates.value) return
    fetchCandidates(true)
}

const fetchCandidates = async (isLoadMore = false) => {
  if (isLoadMore) {
      isLoadingCandidates.value = true
  }

  try {
    const { apiBaseUrl } = getApiConfig()
    
    // Using LIMIT and OFFSET
    const offset = isLoadMore ? candidateOffset.value : 0
    // Corrected to use query params
    const res = await fetch(`${apiBaseUrl}/candidates/?limit=${PAGE_LIMIT}&offset=${offset}`, {
        headers: {
            'Authorization': `Bearer ${userToken.value}`
        }
    })
    const data = await res.json()
    
    // API v2 returns { data: [], page: { total, limit, offset } }
    let rawList = []
    let total = 0
    
    if (data.data) {
        rawList = data.data
        total = data.page ? data.page.total : rawList.length
    } else if (Array.isArray(data)) {
        // Fallback for Mock which returned partial array or other APIs
        rawList = data
        total = 9999 // Unknown
    }

    const newCandidates = rawList.map(c => ({
        ...c, 
        id: c.candidate_id,
        position: c.position || '' 
    }))

    if (isLoadMore) {
        // Append
        // Filter duplicates just in case
        const existingIds = new Set(candidates.value.map(c => c.id))
        const uniqueNew = newCandidates.filter(c => !existingIds.has(c.id))
        candidates.value = [...candidates.value, ...uniqueNew]
    } else {
        // Replace
        candidates.value = newCandidates
    }

    // Update Offset
    candidateOffset.value = offset + newCandidates.length
    
    // Update HasMore
    // If we received fewer than limit, or total reached
    if (newCandidates.length < PAGE_LIMIT || candidates.value.length >= total) {
        hasMoreCandidates.value = false
    } else {
        hasMoreCandidates.value = true
    }

  } catch (e) {
    console.error("Failed to load candidates", e)
    if (!isLoadMore) candidates.value = []
    hasMoreCandidates.value = false
  } finally {
      isLoadingCandidates.value = false
  }
}

const handleSelectionChange = (ids) => {
    selectedCandidateIds.value = ids
}

const lockSelectionAndStart = async () => {
    if (selectedCandidateIds.value.length === 0) return

    const ids = selectedCandidateIds.value
    // Logic: Promote UI selection to Active Conversation
    activeConversationCandidateIds.value = [...ids]
    
    // Identify objects for report fetching
    const selectedCandidates = candidates.value.filter(c => ids.includes(c.candidate_id))
    
    // Save to Session Storage for New Tab Restoration
    try {
        sessionStorage.setItem('traitty_session_active_ids', JSON.stringify(ids))
        sessionStorage.setItem('traitty_selected_candidates', JSON.stringify(selectedCandidates))
    } catch (e) {
        console.error('[ChatContainer] Failed to save to Session Storage:', e)
    }
    
    // Batch fetch trait reports
    await fetchBatchTraitReports(selectedCandidates)
    
    // Update State: Lock Selection and Show AI Message
    isSelectionLocked.value = true
    
    // UI Cleanup: Clear checkboxes in the underlying list as requested
    selectedCandidateIds.value = []
    if (candidateSelectorRef.value && candidateSelectorRef.value.clearSelection) {
        candidateSelectorRef.value.clearSelection() 
    }
    
    // Push Helper Message
    messages.value.push({ 
        role: 'ai', 
        content: `已鎖定 ${ids.length} 位候選人。您現在可以針對他們進行提問。` 
    })
}

// Reset Logic: Clears history and generates new session
const resetAndReselect = () => {
    // Reset Chat
    messages.value = [{ role: 'ai', content: '您好！我是您的人才評鑑助手。請先選擇候選人，我將為您提供特質分析與建議。' }]
    currentSessionId.value = crypto.randomUUID() 
    inputQuery.value = ''
    
    // Clear Session Storage
    try {
        sessionStorage.removeItem('traitty_selected_candidates')
        sessionStorage.removeItem('traitty_batch_reports') 
        sessionStorage.removeItem('traitty_session_active_ids')
    } catch (e) {
        console.error('[ChatContainer] Failed to clear Session Storage:', e)
    }
    
    // Unlock Selection
    isSelectionLocked.value = false
    activeConversationCandidateIds.value = []
    selectedCandidateIds.value = [] // Should be empty already
}

// Initial loading state to prevent login form flash
const isInitializing = ref(true)

// Auto-login Logic with Retry
const performAutoLogin = async (email) => {
    const { serverRoot } = getApiConfig()
    const maxRetries = 3
    let attempt = 0
    let lastError = null

    console.log(`[AutoLogin] Starting auto-login for: ${email}`)

    while (attempt < maxRetries) {
        attempt++
        try {
            const res = await fetch(`${serverRoot}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            })

            if (res.ok) {
                const data = await res.json()
                if (data.token) {
                    await handleLoginSuccess(data)
                    return // Success
                } else {
                    throw new Error("Response OK but no token found")
                }
            } else {
                const text = await res.text()
                throw new Error(`Server returned ${res.status}: ${text}`)
            }
        } catch (e) {
            console.warn(`[AutoLogin] Attempt ${attempt}/${maxRetries} failed:`, e.message)
            lastError = e
            if (attempt < maxRetries) await new Promise(resolve => setTimeout(resolve, 1000))
        }
    }
    autoLoginError.value = `自動登入失敗 (重試 ${maxRetries} 次): ${lastError?.message || '未知錯誤'}`
}

onMounted(async () => {
    // First, check if we have a state transfer incoming
    // If we do, we can skip the standard auto-login wait because we have the token
    const newTabStateRaw = localStorage.getItem('traitty_new_tab_state')
    if (newTabStateRaw) {
        restoreSessionState()
        // Ensure candidates are loaded
        if (userToken.value) {
             await fetchCandidates()
        }
    } 
    
    // Normal Flow: Auto Login if needed
    if (!userToken.value && window.TRAITTY_WIDGET_CONFIG && window.TRAITTY_WIDGET_CONFIG.userEmail) {
        await performAutoLogin(window.TRAITTY_WIDGET_CONFIG.userEmail)
    }
    
    isInitializing.value = false
})

const sendMessage = async (e) => {
  if (e && e.shiftKey) return; 
  
  const query = inputQuery.value.trim()
  if (!query || isTyping.value) return
  
  // ... (rest of sendMessage)

  messages.value.push({ role: 'user', content: query })
  inputQuery.value = ''
  isTyping.value = true

  const aiMsgIndex = messages.value.push({ 
    role: 'ai', 
    content: '', 
    intent: '', 
    isTyping: true 
  }) - 1

  const { serverRoot } = getApiConfig()
  
  let traitReports = {}
  try {
    const cachedReports = sessionStorage.getItem('traitty_batch_reports')
    if (cachedReports) traitReports = JSON.parse(cachedReports)
  } catch (e) {}

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 90000)

    // Using activeConversationCandidateIds here!
    const activeIds = activeConversationCandidateIds.value
    // Find objects for active IDs
    const activeCandidates = candidates.value.filter(c => activeIds.includes(c.candidate_id))


    const response = await fetch(`${serverRoot}/chat/`, { 
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken.value}`
      },
      body: JSON.stringify({
        query: query,
        candidate_ids: activeIds,
        candidates_info: activeCandidates.map(c => ({
          candidate_id: c.candidate_id,
          name: c.name,
          email: c.email || '',
          phone: c.phone || '',
          enterprise_name: c.enterprise_name || '',
          position: c.position || '',
          status: c.status || '',
          created_at: c.created_at || '',
          last_assessment_date: c.last_assessment_date || '',
          latest_assessment: c.latest_assessment || null
        })),
        trait_reports: traitReports,
        session_id: currentSessionId.value
      }),
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
        if (response.status === 504 || response.status === 503 || response.status === 524) {
            throw new Error("TIMEOUT_RESPONSE")
        }
        throw new Error(`API Error: ${response.status}`)
    }

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
          if (jsonStr === '[DONE]') continue
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
    if (error.name === 'AbortError' || error.message === 'TIMEOUT_RESPONSE') {
         messages.value[aiMsgIndex].content = "Traitty暫時沒回應，請稍等一下"
    } else {
         messages.value[aiMsgIndex].content = "系統錯誤。"
    }
  } finally {
    isTyping.value = false
    messages.value[aiMsgIndex].isTyping = false
  }
}
</script>

<style lang="scss" scoped>
@use '../styles/chat-container.scss';
</style>
