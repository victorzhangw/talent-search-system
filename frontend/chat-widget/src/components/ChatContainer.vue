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
        Traitty Beta
      </div>
      <div class="actions">
        <!-- Theme Switcher -->
        <div class="theme-selector">
            <button class="icon-btn theme-btn" @click="cycleTheme" :title="'切換主題: ' + currentThemeLabel">
                <!-- Dynamic Material Icons for Themes -->
                <svg v-if="currentTheme === 'light'" class="material-icon" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.8 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"/></svg>
                <svg v-else class="material-icon" viewBox="0 0 24 24"><path d="M11.1 12.08c-2.33-4.51-.5-8.48.53-10.07C6.27 2.2 1.98 6.59 1.98 12c0 .14.02.28.02.42.62-.27 1.29-.42 2-.42 1.66 0 3.18.83 4.1 2.15 1.67.48 2.9 2.02 2.9 3.85 0 1.52-.87 2.83-2.12 3.51.98.32 2.03.5 3.11.5 3.5 0 6.58-1.8 8.37-4.52-2.36.23-6.98-.97-9.26-5.41z"/><path d="M7 16h-.18C6.4 14.84 5.3 14 4 14c-1.66 0-3 1.34-3 3s1.34 3 3 3h3v-4z"/></svg>
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

    <!-- Main Flex Container -->
    <div class="main-layout">
        <!-- Left/Main Content Area -->
        <div class="content-body">
          

          <!-- Loading State -->
          <div v-if="isInitializing" class="loading-view">
             <div class="spinner"></div>
             <p>驗證身分中...</p>
          </div>

          <!-- Tab 0: Login (Only show if not initializing and failed to auto-login) -->
          <LoginView
            v-else-if="currentTab === 'login'"
            :serverRoot="computedServerRoot"
            :initialError="autoLoginError"
            @login-success="handleLoginSuccess"
           />

          <!-- Tab 1: Selection -->
          <CandidateSelector 
            v-else-if="currentTab === 'selection'"
            :candidates="candidates"
            :is-loading="isLoadingCandidates"
            :has-more="hasMoreCandidates"
            @confirm="handleSelectionConfirmed"
            @load-more="loadMoreCandidates"
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
                placeholder="請提問... (Shift+Enter 換行)"
                :disabled="isTyping"
              ></textarea>
              <button class="send-btn" @click="sendMessage" :disabled="!inputQuery.trim() || isTyping">
                <!-- Icon: Send -->
                <svg class="material-icon" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Right Sidebar (Only in Chat Mode) -->
        <div v-if="currentTab === 'chat'" class="quick-sidebar">
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

const currentTab = ref('login') // Defaut to login
const userToken = ref(null)
const autoLoginError = ref('')

const messages = ref([
  { role: 'ai', content: '您好！我是Traitty，將為您提供特質分析與建議。' }
])
const inputQuery = ref('')
const isTyping = ref(false)

const candidates = ref([])
const selectedCandidateIds = ref([])
const isLoadingCandidates = ref(false)
const hasMoreCandidates = ref(true)
const candidateOffset = ref(0)
const PAGE_LIMIT = 20

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

const currentSessionId = ref(crypto.randomUUID())

const selectedCandidatesObjects = computed(() => {
  return candidates.value.filter(c => selectedCandidateIds.value.includes(c.candidate_id))
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
    
    console.log('[ChatContainer] ========== Batch Report Fetch Debug ==========')
    console.log('[ChatContainer] Selected candidates:', selectedCandidates)
    
    // Extract assessment IDs from selected candidates
    const assessmentIds = selectedCandidates
        .map(c => c.latest_assessment?.assessment_id)
        .filter(id => id != null)
    
    console.log('[ChatContainer] Extracted assessment IDs:', assessmentIds)
    
    if (assessmentIds.length === 0) {
        console.warn('[ChatContainer] No assessment IDs found for selected candidates')
        return
    }
    
    const apiUrl = `${apiBaseUrl}/reports/batch`
    const payload = { assessment_ids: assessmentIds }
    
    console.log('[ChatContainer] API URL:', apiUrl)
    console.log('[ChatContainer] Request Payload:', JSON.stringify(payload, null, 2))
    console.log('[ChatContainer] Authorization:', userToken.value ? 'Token present' : 'No token')
    
    try {
        const res = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken.value}`
            },
            body: JSON.stringify(payload)
        })
        
        console.log('[ChatContainer] Response status:', res.status, res.statusText)
        
        if (!res.ok) {
            const errorText = await res.text()
            console.error('[ChatContainer] Error response body:', errorText)
            throw new Error(`Batch reports fetch failed: ${res.status} - ${errorText}`)
        }
        
        const data = await res.json()
        console.log('[ChatContainer] Response data:', data)
        console.log('[ChatContainer] Number of reports received:', data.reports?.length || 0)
        
        // Store reports in Session Storage, keyed by candidate_id
        const reportsMap = {}
        data.reports.forEach(report => {
            console.log('[ChatContainer] Processing report for assessment_id:', report.assessment_id)
            
            // Find matching candidate by assessment_id
            const candidate = selectedCandidates.find(
                c => c.latest_assessment?.assessment_id === report.assessment_id
            )
            
            if (candidate) {
                console.log('[ChatContainer] Matched to candidate_id:', candidate.candidate_id)
                reportsMap[candidate.candidate_id] = report
            } else {
                console.warn('[ChatContainer] No candidate found for assessment_id:', report.assessment_id)
            }
        })
        
        console.log('[ChatContainer] Final reportsMap:', reportsMap)
        console.log('[ChatContainer] Number of reports to save:', Object.keys(reportsMap).length)
        
        sessionStorage.setItem('traitty_batch_reports', JSON.stringify(reportsMap))
        console.log('[ChatContainer] ✅ Saved to Session Storage')
        console.log('[ChatContainer] ========== End Debug ==========')
        
    } catch (e) {
        console.error('[ChatContainer] ❌ Failed to fetch batch reports:', e)
        console.error('[ChatContainer] Error details:', e.message)
        console.error('[ChatContainer] ========== End Debug (Error) ==========')
        // Non-blocking: Continue even if batch fetch fails
    }
}

const openReport = (cand) => {
    console.log("openReport called with:", cand)
    currentReportCandidate.value = cand
    showReportModal.value = true
}

const handleLoginSuccess = async (authData) => {
    userToken.value = authData.token
    // Fetch candidates after login
    await fetchCandidates()
    currentTab.value = 'selection'
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

const handleSelectionConfirmed = async (ids) => {
    selectedCandidateIds.value = ids
    
    // Save selected candidates to Session Storage for reuse
    const selectedCandidates = candidates.value.filter(c => ids.includes(c.candidate_id))
    try {
        sessionStorage.setItem('traitty_selected_candidates', JSON.stringify(selectedCandidates))
        console.log('[ChatContainer] Saved selected candidates to Session Storage:', selectedCandidates.length)
    } catch (e) {
        console.error('[ChatContainer] Failed to save to Session Storage:', e)
    }
    
    // NEW: Batch fetch trait reports for all selected candidates
    console.log('[ChatContainer] Fetching batch trait reports for', ids.length, 'candidates...')
    await fetchBatchTraitReports(selectedCandidates)
    
    currentTab.value = 'chat'
    messages.value.push({ 
        role: 'ai', 
        content: `已勾選 ${ids.length} 位候選人。您現在可以針對他們進行提問。` 
    })
}

// Reset Logic: Clears history and generates new session
const resetAndReselect = () => {
    messages.value = [{ role: 'ai', content: '您好！我是您的人才評鑑助手。請先選擇候選人，我將為您提供特質分析與建議。' }]
    selectedCandidateIds.value = []
    currentSessionId.value = crypto.randomUUID() // New Session -> New Context
    inputQuery.value = ''
    
    // Clear Session Storage (candidates and reports)
    try {
        sessionStorage.removeItem('traitty_selected_candidates')
        sessionStorage.removeItem('traitty_batch_reports')  // NEW: Clear reports cache
        console.log('[ChatContainer] Cleared Session Storage')
    } catch (e) {
        console.error('[ChatContainer] Failed to clear Session Storage:', e)
    }
    
    // Reset Candidates List (Reload fresh)
    candidateOffset.value = 0
    hasMoreCandidates.value = true
    candidates.value = []
    fetchCandidates(false)
    
    currentTab.value = 'selection'
}

// Initial loading state to prevent login form flash
const isInitializing = ref(true)

// Auto-login Logic with Retry
const performAutoLogin = async (email) => {
    const { serverRoot } = getApiConfig()
    const maxRetries = 3
    let attempt = 0
    let lastError = null

    // Store for UI display if failed
    // autoLoginEmailAttempt removed per user request

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
                    console.log("[AutoLogin] Success!")
                    await handleLoginSuccess(data)
                    return // Success, exit function
                } else {
                    throw new Error("Response OK but no token found")
                }
            } else {
                // If 4xx/5xx, capture status text
                const text = await res.text()
                throw new Error(`Server returned ${res.status}: ${text}`)
            }
        } catch (e) {
            console.warn(`[AutoLogin] Attempt ${attempt}/${maxRetries} failed:`, e.message)
            lastError = e
            
            // Wait 1 second before retrying, unless it's the last attempt
            if (attempt < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, 1000))
            }
        }
    }

    // If we get here, all retries failed
    console.error("[AutoLogin] All attempts failed.")
    autoLoginError.value = `自動登入失敗 (重試 ${maxRetries} 次): ${lastError?.message || '未知錯誤'}`
}

onMounted(async () => {
    // Check global config for user email
    if (window.TRAITTY_WIDGET_CONFIG && window.TRAITTY_WIDGET_CONFIG.userEmail) {
        await performAutoLogin(window.TRAITTY_WIDGET_CONFIG.userEmail)
    }
    // Done checking, stop loading
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
  
  // Load trait reports from Session Storage
  let traitReports = {}
  try {
    const cachedReports = sessionStorage.getItem('traitty_batch_reports')
    if (cachedReports) {
      traitReports = JSON.parse(cachedReports)
      console.log('[ChatContainer] Loaded trait reports from Session Storage:', Object.keys(traitReports).length, 'reports')
    } else {
      console.warn('[ChatContainer] No trait reports found in Session Storage')
    }
  } catch (e) {
    console.error('[ChatContainer] Failed to load trait reports from Session Storage:', e)
  }

  try {
    // CORRECTED: Ensure trailing slash to match Flask strict routing
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 90000) // 90 seconds timeout

    const response = await fetch(`${serverRoot}/chat/`, { 
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken.value}`
      },
      body: JSON.stringify({
        query: query,
        candidate_ids: selectedCandidateIds.value,
        // Include full candidate info to avoid backend re-fetching
        // This matches the structure from /v1/candidates/ API
        candidates_info: selectedCandidatesObjects.value.map(c => ({
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
        // NEW: Include trait reports from Session Storage
        trait_reports: traitReports,
        session_id: currentSessionId.value // Dynamic Session ID
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
    if (error.name === 'AbortError' || error.message === 'TIMEOUT_RESPONSE') {
         messages.value[aiMsgIndex].content = "Traitty暫時沒回應，請稍等一下"
    } else {
         console.error(error)
         messages.value[aiMsgIndex].content = "系統錯誤。"
    }
  } finally {
    isTyping.value = false
    messages.value[aiMsgIndex].isTyping = false
  }
}
</script>

<style lang="scss" scoped>
@use '../styles/glass.scss' as *;

.material-icon {
    width: 24px;
    height: 24px;
    fill: currentColor;
    flex-shrink: 0;
    
    &.small {
        width: 18px;
        height: 18px;
    }
}

.chat-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  width: 65vw; /* Expanded from 50vw */
  min-width: 800px; /* Expanded from 600px */
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
  background: rgba(var(--glass-text-primary), 0.05);
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
        color: #ef4444; 
        background: rgba(239, 68, 68, 0.1);
    }
  }
}

/* Layout for Content + Sidebar */
.main-layout {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.content-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0; 
    min-width: 0; /* Important for flex child truncation */
}

/* Quick Question Sidebar */
.quick-sidebar {
    width: 220px;
    background: rgba(0, 0, 0, 0.02); /* Very subtle background */
    border-left: 1px solid var(--glass-border);
    display: flex;
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
    
    .sidebar-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--primary-color);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .quick-btn-list {
        display: flex;
        flex-direction: column;
        gap: 0.8rem;
        overflow-y: auto;
    }
    
    .quick-btn {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        color: var(--glass-text-primary);
        padding: 0.8rem;
        border-radius: 8px;
        text-align: left;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        
        &:hover:not(:disabled) {
            border-color: var(--primary-color);
            transform: translateX(2px);
            background: rgba(var(--primary-color), 0.05);
        }
        
        &:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
    }
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
    position: relative;
    z-index: 100;

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

.loading-view {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    color: var(--glass-text-secondary);
    
    .spinner {
        width: 30px;
        height: 30px;
        border: 3px solid rgba(127,127,127,0.2);
        border-top-color: var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
</style>
