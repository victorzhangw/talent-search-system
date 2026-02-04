
import { ref, computed, onMounted, watch } from 'vue'

export function useChatLogic(emit) {
    // --- State ---
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
    const totalCandidatesCount = ref(0)
    const PAGE_LIMIT = 20

    // Theme Logic
    const themes = ['light', 'midnight']
    const themeIndex = ref(0)
    const currentTheme = computed(() => themes[themeIndex.value])

    const currentSessionId = ref(crypto.randomUUID())
    const isInitializing = ref(true)

    // Modal Logic
    const showReportModal = ref(false)
    const currentReportCandidate = ref({})

    const quickQuestions = ref([
        "快速面試提問指南",
        "工作中主要的優勢與潛力",
        "在團隊合作中適合的角色",
        "需注意的管理問題或潛在風險",
        "如何面對困難、壓力、挑戰",
        "合適的管理方式與風格",
        "有效的溝通方法/模式",
        "展現何種領導風格",
    ])


    // --- Computed ---
    const currentThemeLabel = computed(() => {
        switch (currentTheme.value) {
            case 'light': return '明亮 (白)'
            case 'midnight': return '深邃 (黑)'
            default: return '標準'
        }
    })

    const activeConversationCandidatesObjects = computed(() => {
        return candidates.value.filter(c => activeConversationCandidateIds.value.includes(c.candidate_id))
    })

    // --- API & Config Helpers ---
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

    // --- Methods ---
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

        // Close the widget in current window if emit is provided
        if (emit) emit('close')
    }

    // Reports
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

    // Login & Init
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

                // Immediately save to Session Storage so it survives a refresh/minimize
                saveSessionToStorage()
                return
            }

            // Priority 2: Check Session Storage (Same tab reload or Restore from Minimize)
            const rawIds = sessionStorage.getItem('traitty_session_active_ids')
            if (rawIds) {
                const ids = JSON.parse(rawIds)
                if (Array.isArray(ids) && ids.length > 0) {
                    console.log('[ChatContainer] Restoring session state for IDs:', ids)
                    activeConversationCandidateIds.value = ids
                    isSelectionLocked.value = true
                    selectedCandidateIds.value = []

                    // Restore Messages & SessionID
                    const storedMsgs = sessionStorage.getItem('traitty_session_messages')
                    if (storedMsgs) messages.value = JSON.parse(storedMsgs)

                    const storedSessionId = sessionStorage.getItem('traitty_session_id')
                    if (storedSessionId) currentSessionId.value = storedSessionId
                }
            }
        } catch (e) {
            console.error("Failed to restore session state", e)
        }
    }

    // Persist State Helper
    const saveSessionToStorage = () => {
        if (activeConversationCandidateIds.value.length > 0) {
            sessionStorage.setItem('traitty_session_active_ids', JSON.stringify(activeConversationCandidateIds.value))
            sessionStorage.setItem('traitty_session_messages', JSON.stringify(messages.value))
            sessionStorage.setItem('traitty_session_id', currentSessionId.value)
        }
    }

    // Watch for message usage to persist
    watch(messages, () => {
        saveSessionToStorage()
    }, { deep: true })

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

            totalCandidatesCount.value = total

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

    // Accepts an optional callback to clear UI selection (e.g. template ref method)
    const lockSelectionAndStart = async (clearSelectionCallback) => {
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

        if (clearSelectionCallback && typeof clearSelectionCallback === 'function') {
            clearSelectionCallback()
        }

        // Push Helper Message
        messages.value.push({
            role: 'ai',
            content: `已鎖定 ${ids.length} 位候選人。您現在可以針對他們進行提問。`
        })
    }

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
            sessionStorage.removeItem('traitty_session_messages')
            sessionStorage.removeItem('traitty_session_id')
        } catch (e) {
            console.error('[ChatContainer] Failed to clear Session Storage:', e)
        }

        // Unlock Selection
        isSelectionLocked.value = false
        activeConversationCandidateIds.value = []
        selectedCandidateIds.value = [] // Should be empty already
    }

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
                        // Success!
                        await handleLoginSuccess(data)
                        return
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

    const sendMessage = async (e, isQuick = false) => {
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

        const { serverRoot } = getApiConfig()

        let traitReports = {}
        try {
            const cachedReports = sessionStorage.getItem('traitty_batch_reports')
            if (cachedReports) traitReports = JSON.parse(cachedReports)
        } catch (e) { }

        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 90000)

            // Using activeConversationCandidateIds here!
            const activeIds = activeConversationCandidateIds.value
            // Determine mode
            // 1. Quick Questions -> Force 'expert'
            // 2. Typed Input -> 'auto' (Let backend router decide)
            const mode = isQuick ? 'expert' : 'auto';

            const response = await fetch(`${serverRoot}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
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
                    session_id: currentSessionId.value,
                    user_id: window.TRAITTY_WIDGET_CONFIG?.userEmail || 'anonymous',
                    mode: mode // Pass mode to backend
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

    const sendQuickMessage = (text) => {
        inputQuery.value = text
        sendMessage(null, true) // Pass true for isQuick
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

    return {
        // State
        currentTab,
        isSelectionLocked,
        userToken,
        autoLoginError,
        messages,
        inputQuery,
        isTyping,
        candidates,
        selectedCandidateIds,
        activeConversationCandidateIds,
        isLoadingCandidates,
        hasMoreCandidates,
        candidateOffset, // Might not need to expose
        totalCandidatesCount,
        currentTheme,
        currentSessionId,
        isInitializing,
        showReportModal,
        currentReportCandidate,
        quickQuestions,

        // Computed
        currentThemeLabel,
        activeConversationCandidatesObjects,
        computedServerRoot,

        // Methods
        cycleTheme,
        openNewTab,
        openReport,
        handleLoginSuccess,
        loadMoreCandidates,
        handleSelectionChange,
        lockSelectionAndStart,
        resetAndReselect,
        sendMessage,
        sendQuickMessage
    }
}
