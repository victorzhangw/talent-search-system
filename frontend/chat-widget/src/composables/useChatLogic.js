
import { ref, computed, onMounted, watch } from 'vue'
import { getFeatures } from '../config/widgetFeatures.js'

export function useChatLogic(emit) {
    // --- 型別安全的 candidate_id 比對輔助函式 ---
    // 上游 API 回傳的 candidate_id 可能是 number 或 string，
    // 經 sessionStorage JSON 序列化/反序列化後型別可能不一致，
    // Array.includes() 使用嚴格相等（===）會導致匹配失敗。
    // 統一轉為字串比對以避免此問題。
    const idIncludes = (arr, id) => arr.map(String).includes(String(id))
    const idEquals = (a, b) => String(a) === String(b)

    // --- State ---
    const currentTab = ref('login') // 'login' or 'main' (split view)
    const isSelectionLocked = ref(false) // Controls the split view state

    const userToken = ref(null)
    const autoLoginError = ref('')

    // Quota and Init State
    const quotaSummary = ref({ total: 0, used: 0, remaining: 0 })
    const remainingDays = ref(null)
    const isWidgetEnabled = ref(true) // Default to true, updated by /v1/init/

    const showWelcomeMessage = ref(false);
    const messages = ref(showWelcomeMessage.value ? [{ role: 'ai', content: '您好！我是Traitty，將為您提供特質分析與建議。' }] : []);
    const inputQuery = ref('');
    const isTyping = ref(false);

    // Helper to show the welcome message when needed
    const toggleWelcomeMessage = (show = true) => {
        showWelcomeMessage.value = show;
        if (show && messages.value.length === 0) {
            messages.value = [{ role: 'ai', content: '您好！我是Traitty，將為您提供特質分析與建議。' }];
        }
    };

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

    // Preview Logic (Option A)
    const previewMessages = ref([])
    const showPreviewPanel = ref(false)
    const previewSessionData = ref(null)

    // Modal Logic
    const showReportModal = ref(false)
    const currentReportCandidate = ref({})

    // 快速提問模組：從後端 API 動態拉取（單一資料源）
    const quickQuestionCategories = ref({})
    // 當前快速提問模組 ID（僅在 sendQuickMessage 時設定，發送後重置）
    const currentModuleId = ref(null)

    const selectedQuickQuestionCategory = ref('')

    const quickQuestions = computed(() => {
        return quickQuestionCategories.value[selectedQuickQuestionCategory.value] || []
    })

    const toggleQuickQuestionCategory = () => {
        const keys = Object.keys(quickQuestionCategories.value)
        if (keys.length === 0) return
        const currentIndex = keys.indexOf(selectedQuickQuestionCategory.value)
        const nextIndex = (currentIndex + 1) % keys.length
        selectedQuickQuestionCategory.value = keys[nextIndex]
    }

    const selectQuickQuestionCategory = (catName) => {
        const keys = Object.keys(quickQuestionCategories.value)
        if (keys.includes(catName)) {
            selectedQuickQuestionCategory.value = catName
        }
    }

    /**
     * 從後端 API 拉取快速提問模組清單
     * 回應格式：{ categories: { "招募": [{id, label, mode}, ...], ... } }
     */
    const fetchQuickModules = async () => {
        const { apiBaseUrl } = getApiConfig()
        try {
            const res = await fetch(`${apiBaseUrl}/modules/`, {
                headers: { 'Authorization': `Bearer ${userToken.value}` }
            })
            if (res.ok) {
                const resp = await res.json()
                quickQuestionCategories.value = (resp.success ? resp.data?.categories : null) || {}
                const keys = Object.keys(quickQuestionCategories.value)
                if (keys.length > 0 && !keys.includes(selectedQuickQuestionCategory.value)) {
                    selectedQuickQuestionCategory.value = keys[0]
                }
                console.log(`[ChatLogic] ✅ Loaded ${keys.length} quick question categories from API`)
            }
        } catch (e) {
            console.error('[ChatLogic] Failed to fetch quick modules:', e)
        }
    }

    /**
     * 過濾後的快速提問（桌面側欄版）
     * 根據目前鎖定的候選人數量，依據每個提問項目的 mode 屬性動態過濾。
     */
    const filteredQuickQuestions = computed(() => {
        const features = getFeatures()
        const questions = quickQuestionCategories.value[selectedQuickQuestionCategory.value] || []

        if (!features.quickQuestions.enforceSingleCandidateLimit) return questions
        const activeCount = activeConversationCandidateIds.value.length

        return questions.filter(q => {
            // 純字串格式（fallback，相容舊資料）
            if (typeof q === 'string') return true
            // 物件格式：依 mode 過濾
            if (activeCount <= 1 && q.mode === 'multi_only') return false
            if (activeCount > 1 && q.mode === 'single_only') return false
            return true
        })
    })

    /**
     * 過濾後的快速提問分類物件（行動版彈出視窗用）
     * 依據每個提問項目的 mode 屬性動態過濾。
     */
    const filteredQuickQuestionCategories = computed(() => {
        const features = getFeatures()
        if (!features.quickQuestions.enforceSingleCandidateLimit) return quickQuestionCategories.value
        const activeCount = activeConversationCandidateIds.value.length

        const result = {}
        for (const [cat, questions] of Object.entries(quickQuestionCategories.value)) {
            const filtered = questions.filter(q => {
                if (typeof q === 'string') return true
                if (activeCount <= 1 && q.mode === 'multi_only') return false
                if (activeCount > 1 && q.mode === 'single_only') return false
                return true
            })
            if (filtered.length > 0) result[cat] = filtered
        }
        return result
    })

    const historySessions = ref({ today: [], past_30_days: [] })
    const historyPage = ref(1)
    const historyHasMore = ref(false)
    const historyIsLoading = ref(false)
    const showMobileHistoryDrawer = ref(false)

    // --- Computed ---
    const currentThemeLabel = computed(() => {
        switch (currentTheme.value) {
            case 'light': return '明亮 (白)'
            case 'midnight': return '深邃 (黑)'
            default: return '標準'
        }
    })

    const activeConversationCandidatesObjects = computed(() => {
        return candidates.value.filter(c => idIncludes(activeConversationCandidateIds.value, c.candidate_id))
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
            selectedCandidates: candidates.value.filter(c => idIncludes(activeConversationCandidateIds.value, c.candidate_id)),
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

            const resp = await res.json()
            const reports = resp.success ? (resp.data?.reports ?? []) : []

            const reportsMap = {}
            reports.forEach(report => {
                const candidate = selectedCandidates.find(
                    c => String(c.latest_assessment?.assessment_id) === String(report.assessment_id)
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

    // 增量模式：只抓新增候選人的報告，並合併到現有 sessionStorage
    const fetchBatchTraitReportsIncremental = async (newCandidates) => {
        const { apiBaseUrl } = getApiConfig()

        const assessmentIds = newCandidates
            .map(c => c.latest_assessment?.assessment_id)
            .filter(id => id != null)

        if (assessmentIds.length === 0) return

        try {
            const res = await fetch(`${apiBaseUrl}/reports/batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${userToken.value}`
                },
                body: JSON.stringify({ assessment_ids: assessmentIds })
            })

            if (!res.ok) throw new Error(`Incremental batch reports failed: ${res.status}`)

            const resp = await res.json()
            const reports = resp.success ? (resp.data?.reports ?? []) : []

            let existingReports = {}
            try {
                const cached = sessionStorage.getItem('traitty_batch_reports')
                if (cached) existingReports = JSON.parse(cached)
            } catch (e) { }

            reports.forEach(report => {
                const candidate = newCandidates.find(
                    c => String(c.latest_assessment?.assessment_id) === String(report.assessment_id)
                )
                if (candidate) {
                    existingReports[candidate.candidate_id] = report
                }
            })

            sessionStorage.setItem('traitty_batch_reports', JSON.stringify(existingReports))
            console.log('[ChatLogic] ✅ Incremental reports merged to Session Storage')
        } catch (e) {
            console.error('[ChatLogic] ❌ Failed to fetch incremental reports:', e)
        }
    }

    const openReport = (cand) => {
        currentReportCandidate.value = cand
        showReportModal.value = true
    }

    // History Logic
    const fetchHistory = async (page = 1, append = false) => {
        if (historyIsLoading.value) return;
        historyIsLoading.value = true;
        try {
            const { serverRoot } = getApiConfig()
            const userId = window.TRAITTY_WIDGET_CONFIG?.userEmail || 'anonymous'

            const res = await fetch(`${serverRoot}/chat/history?user_id=${userId}&page=${page}`, {
                headers: { 'Authorization': `Bearer ${userToken.value}` }
            })
            if (res.ok) {
                const resp = await res.json()
                const d = resp.success ? (resp.data || {}) : {}
                if (append) {
                    historySessions.value.today = [...(historySessions.value.today || []), ...(d.today || [])]
                    historySessions.value.past_30_days = [...(historySessions.value.past_30_days || []), ...(d.past_30_days || [])]
                } else {
                    historySessions.value = {
                        today: d.today || [],
                        past_30_days: d.past_30_days || []
                    }
                }
                historyPage.value = page
                historyHasMore.value = d.has_more ?? false
            }
        } catch (e) {
            console.error("[ChatContainer] Failed to load history", e)
        } finally {
            historyIsLoading.value = false;
        }
    }

    const loadMoreHistory = async () => {
        if (historyHasMore.value && !historyIsLoading.value) {
            await fetchHistory(historyPage.value + 1, true);
        }
    }

    const loadHistorySession = async (sessionData) => {
        const { serverRoot } = getApiConfig()

        // Option A: Load into Preview Panel instead of overriding main chat
        previewSessionData.value = sessionData
        showPreviewPanel.value = true
        previewMessages.value = [] // clear previous or set loading state
        showMobileHistoryDrawer.value = false // close drawer when previewing

        try {
            const res = await fetch(`${serverRoot}/chat/${sessionData.session_id}`, {
                headers: { 'Authorization': `Bearer ${userToken.value}` }
            })
            if (res.ok) {
                const resp = await res.json()
                const rawMessages = resp.success ? (resp.data?.messages ?? []) : []
                const msgs = rawMessages.map(m => ({
                    id: m.id,
                    role: m.role,
                    content: m.content,
                    rating: m.rating || 0
                }))
                previewMessages.value = msgs.length > 0 ? msgs : [{ role: 'ai', content: '（尚無對話紀錄）' }]
            }
        } catch (e) {
            console.error("[ChatContainer] Failed to load session details for preview", e)
        }
    }

    const switchContextToPreview = () => {
        if (!previewSessionData.value) return;

        // Draft preservation is implicitly handled as current session is just left behind
        // We override the active messages
        currentSessionId.value = previewSessionData.value.session_id;
        messages.value = [...previewMessages.value];
        showPreviewPanel.value = false;

        // Also update selection lock if possible
        if (!isSelectionLocked.value && messages.value.length > 0) {
            isSelectionLocked.value = true;
        }

        // Add small AI prompt confirming context switch
        messages.value.push({
            role: 'ai',
            content: '已為您切換至歷史對話，您可以繼續提問。'
        });

        saveSessionToStorage();
    }

    // Init Data Fetching
    const fetchInitData = async () => {
        if (!userToken.value) return;

        try {
            const { apiBaseUrl } = getApiConfig();
            // Call the local backend proxy map instead of upstream directly
            const initUrl = `${apiBaseUrl}/init/`;

            const res = await fetch(initUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${userToken.value}`
                }
            });

            if (res.ok) {
                const resp = await res.json()
                const data = resp.success ? (resp.data || {}) : {}

                if (data.quota_summary) {
                    quotaSummary.value = data.quota_summary
                }

                if (data.usable_plans && data.usable_plans.length > 0) {
                    try {
                        const endsAtDate = new Date(data.usable_plans[0].ends_at.replace(/-/g, '/'))
                        const diffTime = endsAtDate - new Date()
                        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
                        remainingDays.value = diffDays > 0 ? diffDays : 0
                    } catch (e) {
                        console.error("Failed to parse remaining days", e)
                    }
                }

                isWidgetEnabled.value = data.status === true &&
                    (data.quota_summary && data.quota_summary.remaining > 0)
            } else {
                console.warn(`[ChatLogic] /v1/init/ returned status ${res.status}`)
            }
        } catch (e) {
            console.error("[ChatLogic] Failed to fetch init data", e);
        }
    }

    // Login & Init
    const handleLoginSuccess = async (authData) => {
        userToken.value = authData.token
        // Fetch Init Data to check quota and widget status
        await fetchInitData()
        // Fetch candidates after login
        await fetchCandidates()
        // Fetch quick question modules from API
        await fetchQuickModules()
        // Fetch history
        await fetchHistory()
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
                    fetchInitData() // Fetch init data asynchronously
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
            const resp = await res.json()

            let rawList = []
            let total = 0

            if (resp.success) {
                rawList = Array.isArray(resp.data) ? resp.data : []
                total = resp.meta?.page?.total ?? rawList.length
            } else if (Array.isArray(resp)) {
                rawList = resp
                total = 9999
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
        const selectedCandidates = candidates.value.filter(c => idIncludes(ids, c.candidate_id))

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
        messages.value = showWelcomeMessage.value ? [{ role: 'ai', content: '您好！我是Traitty，將為您提供特質分析與建議。' }] : []
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

    const removeCandidate = (candidateIdToRemove) => {
        activeConversationCandidateIds.value = activeConversationCandidateIds.value.filter(id => !idEquals(id, candidateIdToRemove))

        if (activeConversationCandidateIds.value.length === 0) {
            resetAndReselect()
        } else {
            try {
                sessionStorage.setItem('traitty_session_active_ids', JSON.stringify(activeConversationCandidateIds.value))
                const activeCands = candidates.value.filter(c => idIncludes(activeConversationCandidateIds.value, c.candidate_id))
                sessionStorage.setItem('traitty_selected_candidates', JSON.stringify(activeCands))

                // 同步清除被移除候選人的報告資料，避免 sendMessage 時
                // trait_reports 中仍存在已移除候選人的報告，導致後端
                // rag_engine 找不到對應的 candidates_info 而使用 fallback 名稱
                try {
                    const cachedReports = sessionStorage.getItem('traitty_batch_reports')
                    if (cachedReports) {
                        const reports = JSON.parse(cachedReports)
                        // 清除可能的 number/string 兩種 key 格式
                        delete reports[candidateIdToRemove]
                        delete reports[String(candidateIdToRemove)]
                        sessionStorage.setItem('traitty_batch_reports', JSON.stringify(reports))
                    }
                } catch (reportErr) {
                    console.error('[ChatLogic] Failed to clean up batch reports on remove:', reportErr)
                }

                // Push Helper Message upon update
                messages.value.push({
                    role: 'ai',
                    content: `已更新分析對象。目前鎖定 ${activeConversationCandidateIds.value.length} 位候選人。您現在可以針對他們進行提問。`
                })
            } catch (e) {
                console.error('[ChatLogic] Failed to update Session Storage on remove:', e)
            }
        }
    }

    // 在對話中新增候選人（增量）
    const addCandidates = async (newIds) => {
        if (!newIds || newIds.length === 0) return

        // 過濾掉已在對話中的人
        const realNewIds = newIds.filter(id => !idIncludes(activeConversationCandidateIds.value, id))
        if (realNewIds.length === 0) return

        // 找出新增候選人的完整物件
        const newCandidateObjects = candidates.value.filter(c => idIncludes(realNewIds, c.candidate_id))

        // 將新 IDs 合併到現有對話
        const mergedIds = [...activeConversationCandidateIds.value, ...realNewIds]

        // 僅對新增候選人抓報告（增量）
        await fetchBatchTraitReportsIncremental(newCandidateObjects)

        // 更新 state
        activeConversationCandidateIds.value = mergedIds

        // 更新 sessionStorage
        try {
            sessionStorage.setItem('traitty_session_active_ids', JSON.stringify(mergedIds))
            const allActiveCands = candidates.value.filter(c => idIncludes(mergedIds, c.candidate_id))
            sessionStorage.setItem('traitty_selected_candidates', JSON.stringify(allActiveCands))
        } catch (e) {
            console.error('[ChatLogic] Failed to update session storage on add:', e)
        }

        // AI 提示訊息
        messages.value.push({
            role: 'ai',
            content: `已新增 ${realNewIds.length} 位候選人，目前共鎖定 ${mergedIds.length} 位。您可繼續針對他們發問。`
        })
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
                    const resp = await res.json()
                    if (resp.success && resp.data?.token) {
                        await handleLoginSuccess(resp.data)
                        return
                    } else {
                        const msg = resp.error?.message || 'Response OK but no token found'
                        throw new Error(msg)
                    }
                } else {
                    let msg = `Server returned ${res.status}`
                    try {
                        const body = await res.json()
                        if (body.error?.message) msg = body.error.message
                    } catch (_) { }
                    throw new Error(msg)
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

        // 使用唯一 ID 標記 AI 訊息，避免陣列索引在非同步過程中失效
        const aiMsgTempId = `ai_${Date.now()}`
        messages.value.push({
            role: 'ai',
            content: '',
            intent: '',
            isTyping: true,
            _tempId: aiMsgTempId
        })

        const { serverRoot } = getApiConfig()

        let traitReports = {}
        try {
            const cachedReports = sessionStorage.getItem('traitty_batch_reports')
            if (cachedReports) traitReports = JSON.parse(cachedReports)
        } catch (e) { }

        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 180000)

            // Using activeConversationCandidateIds here!
            const activeIds = activeConversationCandidateIds.value
            // Define activeCandidates for usage in body
            const activeCandidates = candidates.value.filter(c => idIncludes(activeIds, c.candidate_id))

            // Determine mode
            // 1. Quick Questions -> Force 'expert'
            // 2. Typed Input -> 'auto' (Let backend router decide)
            const mode = isQuick ? 'expert' : 'auto';
            // 快速提問時攜帶 module_id
            const moduleId = currentModuleId.value || null;

            const response = await fetch(`${serverRoot}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    module_id: moduleId,  // 快速提問模組 ID
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
                        try {
                            const event = JSON.parse(jsonStr)
                            if (event.type === 'done') continue
                            const aiMsgIndex = messages.value.findIndex(m => m._tempId === aiMsgTempId)
                            if (aiMsgIndex === -1) continue
                            if (event.type === 'error') {
                                messages.value[aiMsgIndex].content += `\n\n⚠️ ${event.message}`
                            } else if (event.type === 'meta') {
                                messages.value[aiMsgIndex].intent = event.intent
                            } else if (event.type === 'token') {
                                messages.value[aiMsgIndex].content += event.content
                            } else if (event.type === 'quota') {
                                if (event.quota_summary) {
                                    quotaSummary.value = event.quota_summary
                                    isWidgetEnabled.value = (event.quota_summary.remaining > 0)
                                }
                            } else if (event.type === 'message_id') {
                                messages.value[aiMsgIndex].id = event.id
                            }
                        } catch (e) { console.error(e) }
                    }
                }
            }
        } catch (e) {
            console.error(e)
            const aiMsgIndex = messages.value.findIndex(m => m._tempId === aiMsgTempId)
            if (aiMsgIndex !== -1) {
                messages.value[aiMsgIndex].content += "\n\n(發生錯誤，請重試)"
            }
        } finally {
            const aiMsgIndex = messages.value.findIndex(m => m._tempId === aiMsgTempId)
            if (aiMsgIndex !== -1) {
                messages.value[aiMsgIndex].isTyping = false
            }
            isTyping.value = false
            // 重置 module_id（確保下次自由提問不會攜帶舊值）
            currentModuleId.value = null

            // Save state to Session Storage
            try {
                sessionStorage.setItem('traitty_session_active_ids', JSON.stringify(activeConversationCandidateIds.value))
                sessionStorage.setItem('traitty_session_messages', JSON.stringify(messages.value))
                sessionStorage.setItem('traitty_session_id', currentSessionId.value)
            } catch (e) { }
        }
    }

    const rateMessage = async (messageId, rating) => {
        if (!messageId) return false

        try {
            const { serverRoot } = getApiConfig()
            const res = await fetch(`${serverRoot}/chat/message/${messageId}/rating`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${userToken.value}`
                },
                body: JSON.stringify({ rating })
            })

            if (res.ok) {
                return true
            } else {
                console.error("Failed to rate message:", await res.text())
                return false
            }
        } catch (e) {
            console.error("Error rating message:", e)
            return false
        }
    }

    const sendQuickMessage = (questionItem) => {
        // questionItem 可能是物件 {id, label, mode} 或純字串（相容舊版）
        if (typeof questionItem === 'string') {
            inputQuery.value = questionItem
            currentModuleId.value = null
        } else {
            inputQuery.value = questionItem.label
            currentModuleId.value = questionItem.id || null
        }
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
        quotaSummary,
        remainingDays,
        isWidgetEnabled,
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

        // Option A States
        previewMessages,
        showPreviewPanel,
        previewSessionData,

        // Quick Questions
        quickQuestionCategories,
        selectedQuickQuestionCategory,
        quickQuestions,
        // 過濾版（依候選人數量與 widgetFeatures 設定動態調整）
        filteredQuickQuestions,
        filteredQuickQuestionCategories,

        // History
        historySessions,
        historyPage,
        historyHasMore,
        historyIsLoading,
        showMobileHistoryDrawer,

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
        removeCandidate,
        addCandidates,
        sendMessage,
        sendQuickMessage,
        toggleQuickQuestionCategory,
        selectQuickQuestionCategory,
        fetchHistory,
        loadMoreHistory,
        loadHistorySession,
        switchContextToPreview,
        rateMessage
    }
}
