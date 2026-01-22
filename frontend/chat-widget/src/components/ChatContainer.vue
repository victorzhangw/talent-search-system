<template>
  <!-- Apply theme to root -->
  <div class="chat-container" :class="{ 'full-page-mode': isFullPage, 'expanded-mode': isExpanded }" :data-theme="currentTheme">
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
        <button v-if="!isFullPage" class="icon-btn new-tab-btn" @click="openNewTab" title="在新分頁開啟">
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
        </button>

        <!-- Dynamic Expand/Collapse Button -->
        <button v-if="!isFullPage" class="icon-btn expand-btn" @click="toggleExpand" :title="isExpanded ? '恢復預設寬度' : '切換全寬模式'">
            <!-- Expand Icon -->
            <svg v-if="!isExpanded" class="material-icon" viewBox="0 0 24 24">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
            <!-- Collapse Icon -->
            <svg v-else class="material-icon" viewBox="0 0 24 24">
                <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-14v3h3v2h-5V5h2z"/>
            </svg>
        </button>

        <!-- Theme Switcher -->
        <div class="theme-selector">
            <button class="icon-btn theme-btn" @click="cycleTheme" :title="'切換主題: ' + currentThemeLabel">
                <!-- Dynamic Material Icons for Themes -->
                <svg v-if="currentTheme === 'light'" class="material-icon" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.8 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"/></svg>
                <svg v-else class="material-icon" viewBox="0 0 24 24"><path d="M11.1 12.08c-2.33-4.51-.5-8.48.53-10.07C6.27 2.2 1.98 6.59 1.98 12c0 .14.02.28.02.42.62-.27 1.29-.42 2-.42 1.66 0 3.18.83 4.1 2.15 1.67.48 2.9 2.02 2.9 3.85 0 1.52-.87 2.83-2.12 3.51.98.32 2.03.5 3.11.5 3.5 0 6.58-1.8 8.37-4.52-2.36.23-6.98-.97-9.26-5.41z"/><path d="M7 16h-.18C6.4 14.84 5.3 14 4 14c-1.66 0-3 1.34-3 3s1.34 3 3 3h3v-4z"/></svg>
            </button>
        </div>
        
        <!-- Minimize Button (Only in Chat Mode) -->
        <button v-if="isSelectionLocked" class="icon-btn minimize-btn" @click="$emit('minimize')" title="最小化至按鈕">
            <svg class="material-icon" viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
        </button>

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
        <div v-else class="split-view" :class="{ 'chat-mode': isSelectionLocked }">
            
            <!-- LEFT PANEL: Candidate List -->
            <div class="left-panel" :class="{ 'wide-sidebar': !isSelectionLocked }">
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
                        :total-count="totalCandidatesCount"
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
import { ref } from 'vue'
import MessageList from './MessageList.vue'
import CandidateSelector from './CandidateSelector.vue'
import LoginView from './LoginView.vue'
import TraitReportModal from './TraitReportModal.vue'
import { useChatLogic } from '../composables/useChatLogic.js'

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
    lockSelectionAndStart: logicLockSelection, // Rename to wrap
    resetAndReselect: logicResetAndReselect,
    sendMessage,
    sendQuickMessage
} = useChatLogic(emit)

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
        width: 70% !important;
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
</style>
