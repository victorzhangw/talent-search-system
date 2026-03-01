<template>
  <!-- Apply theme to root -->
  <div class="chat-container" :class="{ 'full-page-mode': isFullPage, 'expanded-mode': isExpanded }" :data-theme="currentTheme">
    <!-- Header -->
    <div class="header new-layout">
      
      <!-- Left: Sidebar Toggle -->
      <div class="header-left">
        <button v-if="!isFullPage" class="icon-btn border-box" @click="toggleSidebar" :title="isSidebarOpen ? '隱藏側邊欄' : '顯示側邊欄'">
            <img v-if="isSidebarOpen" src="../assets/images/sidebar_close.svg" class="material-icon" alt="隱藏側邊欄" />
            <img v-else src="../assets/images/sidebar_open.svg" class="material-icon" alt="顯示側邊欄" />
        </button>
      </div>

      <!-- Center: Title -->
      <div class="header-center title">
        <img src="../assets/images/AI DIA.svg" class="title-img-icon" alt="Traitty AI" />
        Traitty AI
      </div>

      <!-- Right: Actions -->
      <div class="header-right">
        <div class="action-pill">
            <!-- Expand -->
            <button v-if="!isFullPage" class="icon-btn" @click="toggleExpand" :title="isExpanded ? '恢復預設寬度' : '切換全寬模式'">
                <img v-if="!isExpanded" src="../assets/images/展開箭頭.svg" class="material-icon" alt="展開" />
                <img v-else src="../assets/images/收起箭頭.svg" class="material-icon" alt="收起" />
            </button>
            <div class="pill-divider" v-if="!isFullPage"></div>
            <!-- Theme -->
            <button class="icon-btn theme-btn" @click="cycleTheme" :title="'切換主題: ' + currentThemeLabel">
                <svg v-if="currentTheme === 'light'" class="material-icon" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.8 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"/></svg>
                <svg v-else class="material-icon" viewBox="0 0 24 24"><path d="M11.1 12.08c-2.33-4.51-.5-8.48.53-10.07C6.27 2.2 1.98 6.59 1.98 12c0 .14.02.28.02.42.62-.27 1.29-.42 2-.42 1.66 0 3.18.83 4.1 2.15 1.67.48 2.9 2.02 2.9 3.85 0 1.52-.87 2.83-2.12 3.51.98.32 2.03.5 3.11.5 3.5 0 6.58-1.8 8.37-4.52-2.36.23-6.98-.97-9.26-5.41z"/><path d="M7 16h-.18C6.4 14.84 5.3 14 4 14c-1.66 0-3 1.34-3 3s1.34 3 3 3h3v-4z"/></svg>
            </button>
        </div>
        
        <!-- Minimize & Close -->
        <button v-if="isSelectionLocked" class="icon-btn styled-circle" @click="$emit('minimize')" title="最小化至按鈕">
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
        </button>
        <button class="icon-btn styled-circle close-btn" @click="$emit('close')">
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

        <!-- Split View (3-Column Layout) -->
        <div v-else class="split-view" :class="{ 'chat-mode': isSelectionLocked }">
            
            <!-- Widget Disabled Overlay -->
            <div class="disabled-overlay" v-if="!isWidgetEnabled">
                <div class="disabled-message">
                    <svg class="material-icon disabled-icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                    目前方案額度已用盡或無權限使用
                </div>
            </div>

            <!-- LEFT PANEL: History Sidebar -->
            <div class="left-panel history-sidebar" v-show="isSidebarOpen">
                <div class="history-actions">
                    <button class="primary-btn full-width new-analysis-btn" @click="resetAndReselect">
                        <img src="../assets/images/AI star.svg" class="material-icon new-analysis-icon" alt="AI Star" />
                        開啟新人才解析
                    </button>
                </div>

                <div class="history-lists" v-if="historySessions">
                    <!-- Today -->
                    <div class="history-group" v-if="historySessions.today && historySessions.today.length > 0">
                        <div class="group-title">今天</div>
                        <div 
                            class="history-item" 
                            v-for="s in historySessions.today" 
                            :key="s.session_id" 
                            @click="loadHistorySession(s)"
                            :class="{ active: currentSessionId === s.session_id }"
                        >
                            {{ s.title }}
                        </div>
                    </div>
                    <!-- Past 30 Days -->
                    <div class="history-group" v-if="historySessions.past_30_days && historySessions.past_30_days.length > 0">
                        <div class="group-title">過去30天</div>
                        <div 
                            class="history-item" 
                            v-for="s in historySessions.past_30_days" 
                            :key="s.session_id" 
                            @click="loadHistorySession(s)"
                            :class="{ active: currentSessionId === s.session_id }"
                        >
                            {{ s.title }}
                        </div>
                    </div>
                </div>
                
                <div class="quota-info" v-if="quotaSummary">
                    <div class="quota-count">
                        <svg class="material-icon small" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/></svg>
                        剩餘額度 <span class="highlight">{{ quotaSummary.remaining }}</span> 次
                    </div>
                    <div class="quota-expire">總計 {{ quotaSummary.total }} 次</div>
                </div>
            </div>

            <!-- MIDDLE PANEL: Main Area -->
            <div class="right-panel main-area">
                
                <!-- If Not Locked: Welcome & Candidate Selection -->
                <div v-if="!isSelectionLocked" class="welcome-container">
                    <div class="welcome-header">
                        <div class="magic-icon-wrapper">
                            <img src="@/assets/images/TAI star icon.png" alt="AI Icon" class="magic-icon" />
                        </div>
                        <h2><span class="gradient">Traitty Ai</span> 人才解析</h2>
                        <p class="subtitle">討論履歷、面試結果，或從填答者找尋符合文化的人選。</p>
                    </div>

                    <div class="instructions">
                        <ol>
                            <li>先在下方「選取人才」勾選想了解的人選</li>
                            <li>點「開始分析」後直接發問，或</li>
                            <li>從快速提問按鈕選取 Traitty AI 為您規劃的提問</li>
                        </ol>
                    </div>

                    <!-- Hidden floating Candidate Selector -->
                    <transition name="slide-up">
                        <div class="candidate-dropdown-overlay" v-if="showCandidateDropdown" @click.self="showCandidateDropdown = false">
                            <div class="candidate-dropdown-modal">
                                <div class="modal-body">
                                    <CandidateSelector 
                                        ref="candidateSelectorRef"
                                        :candidates="candidates"
                                        :is-loading="isLoadingCandidates"
                                        :has-more="hasMoreCandidates"
                                        :disabled="false"
                                        :total-count="totalCandidatesCount"
                                        :initial-selected-ids="selectedCandidateIds"
                                        @change="handleSelectionChange"
                                        @load-more="loadMoreCandidates"
                                    />
                                </div>
                                <div class="modal-footer">
                                    <button 
                                        class="secondary-btn clear-btn" 
                                        v-if="selectedCandidateIds.length > 0" 
                                        @click="clearCandidates"
                                    >
                                        清除選取
                                    </button>
                                    <button class="secondary-btn cancel-btn" @click="showCandidateDropdown = false">
                                        取消
                                    </button>
                                    <button class="primary-btn confirm-btn" @click="confirmSelection">
                                        確認選取 {{ selectedCandidateIds.length > 0 ? `(${selectedCandidateIds.length})` : '' }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </transition>

                    <!-- Large Input Box for Welcome Screen -->
                    <div class="big-input-box">
                        <textarea 
                            v-model="inputQuery" 
                            placeholder="向 Traitty 詢問任何人才相關問題..."
                        ></textarea>
                        <div class="input-actions-row">
                            <button class="select-candidate-btn" @click="showCandidateDropdown = true">
                                <svg class="material-icon small" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                                選取人才 {{ selectedCandidateIds.length > 0 ? `(${selectedCandidateIds.length})` : '' }}
                            </button>
                            <button class="send-btn" @click="handleInitialSend" :disabled="!canSendInitial">
                                <svg class="material-icon" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Chat View -->
                <div v-else class="chat-view">
                    <div class="selected-summary">
                        已鎖定: 
                        <span 
                            v-for="(cand, idx) in activeConversationCandidatesObjects" 
                            :key="cand.id"
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
                            <svg class="material-icon" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                        </button>
                    </div>
                </div>

            </div>

            <!-- Right Sidebar -->
            <div v-if="isSelectionLocked" class="quick-sidebar">
               
                <div class="sidebar-header">
                    <div class="custom-select-wrapper category-toggle" @click="toggleQuickQuestionCategory">
                        <!-- 燈泡 Icon -->
                        <svg class="material-icon select-icon" viewBox="0 0 24 24">
                            <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6C7.8 12.16 7 10.63 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/>
                        </svg>
                        
                        <div class="category-name-display">
                            {{ selectedQuickQuestionCategory }}
                        </div>
                        
                        <!-- 循環切換 Icon (上下箭頭) -->
                        <svg class="material-icon select-caret" viewBox="0 0 24 24" title="點擊切換類別">
                            <path fill="currentColor" d="M12 5.83L15.17 9l1.41-1.41L12 3 7.41 7.59 8.83 9 12 5.83zm0 12.34L8.83 15l-1.41 1.41L12 21l4.59-4.59L15.17 15 12 18.17z"/>
                        </svg>
                    </div>
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
import { ref, computed } from 'vue'
import MessageList from './MessageList.vue'
import CandidateSelector from './CandidateSelector.vue'
import LoginView from './LoginView.vue'
import TraitReportModal from './TraitReportModal.vue'
import { useChatLogic } from '../composables/useChatLogic.js'

const isSidebarOpen = ref(true)

const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value
}

const emit = defineEmits(['close'])
const props = defineProps({
    isFullPage: {
        type: Boolean,
        default: false
    }
})

// Initialize Logic Composable
const {
    // State
    currentTab,
    isSelectionLocked,
    userToken,
    autoLoginError,
    quotaSummary,
    isWidgetEnabled,
    messages,
    inputQuery,
    isTyping,
    candidates,
    selectedCandidateIds,
    activeConversationCandidateIds, // Not directly used in template but good to have if extending
    isLoadingCandidates,
    hasMoreCandidates,
    candidateOffset,
    totalCandidatesCount,
    currentTheme,
    currentSessionId,
    isInitializing,
    showReportModal,
    currentReportCandidate,
    quickQuestionCategories,
    selectedQuickQuestionCategory,
    quickQuestions,
    historySessions,

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
    lockSelectionAndStart: logicLockSelection,
    resetAndReselect: logicResetAndReselect,
    sendMessage,
    sendQuickMessage,
    toggleQuickQuestionCategory,
    loadHistorySession
} = useChatLogic(emit)

const showCandidateDropdown = ref(false)

const confirmSelection = () => {
    showCandidateDropdown.value = false
    if (selectedCandidateIds.value.length > 0) {
        handleInitialSend()
    }
}

const clearCandidates = () => {
    if (candidateSelectorRef.value && candidateSelectorRef.value.clearSelection) {
        candidateSelectorRef.value.clearSelection() 
    }
}

const canSendInitial = computed(() => {
    return selectedCandidateIds.value.length > 0
})

const handleInitialSend = async () => {
    if (selectedCandidateIds.value.length > 0) {
        lockSelectionAndStart()
        // wait for state update
        await new Promise(r => setTimeout(r, 100))
        if (inputQuery.value.trim()) {
            sendMessage()
        }
    }
}

// Template Ref for CandidateSelector (needed for clearing selection)
const candidateSelectorRef = ref(null)

// Wrapper for lockSelectionAndStart to handle Template Ref side-effect
const lockSelectionAndStart = () => {
    logicLockSelection(() => {
        if (candidateSelectorRef.value && candidateSelectorRef.value.clearSelection) {
            candidateSelectorRef.value.clearSelection() 
        }
    })
}

// Wrapper for resetAndReselect to handle Template Ref side-effect
const resetAndReselect = () => {
    logicResetAndReselect()
    if (candidateSelectorRef.value && candidateSelectorRef.value.clearSelection) {
        candidateSelectorRef.value.clearSelection() 
    }
}

// Full Width Toggle Logic
const isExpanded = ref(false)
const toggleExpand = () => {
    isExpanded.value = !isExpanded.value
}

</script>

<style lang="scss" scoped>
@use '../styles/chat-container.scss';

.new-tab-btn {
    display: none !important;
}

.chat-container.expanded-mode {
    width: 98vw;
    max-width: none;
    right: 1vw;
    /* Optional: Ensure header doesn't stretch weirdly if needed, but flex handles it */
}

/* Wide Sidebar Logic for Selection Mode (Not Locked) */
.left-panel.wide-sidebar {
    width: 60%;
    max-width: 800px;
    
    @media (max-width: 768px) {
        width: 100%;
    }
}
/* Chat Mode Layout (15% - 70% - 15%) */
.split-view.chat-mode {
    .left-panel {
        width: 15% !important;
        min-width: 200px;
    }

    .right-panel {
        width: 90% !important;
        flex: unset !important;
        display: flex;
        flex-direction: column;
    }

    .quick-sidebar {
        width: 15% !important;
        min-width: 150px;
        border-left: 1px solid var(--glass-border);
        background: rgba(0, 0, 0, 0.02);
    }
}

/* Widget Disabled Overlay */
.disabled-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: inherit;

    .disabled-message {
        background: var(--surface-color, #ffffff);
        color: var(--text-color, #333333);
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        font-weight: 500;
        font-size: 1.1rem;

        .disabled-icon {
            width: 48px;
            height: 48px;
            fill: #ef4444; /* Red color for error/alert */
        }
    }
}

/* Ensure split-view handles absolute overlay correctly */
.split-view {
    position: relative;
}
</style>
