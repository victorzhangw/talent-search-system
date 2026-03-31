<template>
  <!-- Apply theme to root -->
  <div class="chat-container" :class="{ 'full-page-mode': isFullPage, 'expanded-mode': isExpanded }" :data-theme="currentTheme">
    <!-- Header -->
    <div class="header new-layout">
      
      <!-- Left: Sidebar Toggle -->
      <div class="header-left mobile-visible">
        <button v-if="!isFullPage" class="icon-btn border-box" @click="toggleSidebar" :title="isSidebarOpen ? '隱藏側邊欄' : '顯示側邊欄'">
            <img v-if="isSidebarOpen" src="../assets/images/sidebar_close.svg" class="material-icon" alt="隱藏側邊欄" />
            <img v-else src="../assets/images/sidebar_open.svg" class="material-icon" alt="顯示側邊欄" />
        </button>
      </div>

      <!-- Center: Title -->
      <div class="header-center title">
        <img src="../assets/images/TraittyAIIcon-S.svg" class="title-img-icon" alt="Traitty AI" />
        Traitty AI
      </div>

      <!-- Right: Actions -->
      <div class="header-right">
        <div class="action-pill">
            <!-- Expand -->
            <button v-if="!isFullPage" class="icon-btn desktop-only" @click="toggleExpand" :title="isExpanded ? '恢復緊湊視窗' : '展開完整視窗'">
                <img v-if="!isExpanded" src="../assets/images/展開箭頭.svg" class="material-icon" alt="展開" />
                <img v-else src="../assets/images/收起箭頭.svg" class="material-icon" alt="收起" />
            </button>
            <div class="pill-divider" v-if="!isFullPage"></div>
            <!-- Theme -->
            <button class="icon-btn theme-btn" @click="cycleTheme" :title="currentTheme === 'light' ? '切換為深邃 (黑)' : '切換為明亮 (白)'">
                <svg v-if="currentTheme === 'midnight'" class="material-icon" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.8 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"/></svg>
                <svg v-else class="material-icon" viewBox="0 0 24 24"><path d="M11.1 12.08c-2.33-4.51-.5-8.48.53-10.07C6.27 2.2 1.98 6.59 1.98 12c0 .14.02.28.02.42.62-.27 1.29-.42 2-.42 1.66 0 3.18.83 4.1 2.15 1.67.48 2.9 2.02 2.9 3.85 0 1.52-.87 2.83-2.12 3.51.98.32 2.03.5 3.11.5 3.5 0 6.58-1.8 8.37-4.52-2.36.23-6.98-.97-9.26-5.41z"/><path d="M7 16h-.18C6.4 14.84 5.3 14 4 14c-1.66 0-3 1.34-3 3s1.34 3 3 3h3v-4z"/></svg>
            </button>
        </div>
        
        <!-- Minimize & Close -->
        <button v-if="isSelectionLocked" class="icon-btn styled-circle" @click="$emit('minimize')" title="最小化至按鈕">
            <img src="../assets/images/header-minimize.svg" class="material-icon" alt="最小化" />
        </button>
        <button class="icon-btn styled-circle close-btn" @click="$emit('close')" title="關閉">
            <img src="../assets/images/header-close.svg" class="material-icon" alt="關閉" />
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
                        <svg width="18" height="12" viewBox="0 0 18 12" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M6.93221 10.4067C6.61492 10.4679 6.28666 10.5 5.95056 10.5C3.21645 10.5 1 8.37335 1 5.75C1 3.12665 3.21645 1 5.95056 1C6.28666 1 6.61492 1.03213 6.93221 1.09338M16.8333 5.75C16.8333 8.37335 14.6169 10.5 11.8828 10.5C9.14863 10.5 6.93221 8.37335 6.93221 5.75C6.93221 3.12665 9.14863 1 11.8828 1C14.6169 1 16.8333 3.12665 16.8333 5.75Z" stroke="#6A25F4" stroke-opacity="0.7" stroke-width="2" stroke-linecap="round"/>
</svg>
                        <span class="label">剩餘額度</span>
                        <span class="highlight">{{ quotaSummary.remaining }}</span>
                        <span class="unit">次</span>
                    </div>
                    <div class="quota-divider"></div>
                    <div class="quota-expire" v-if="remainingDays !== null">{{ remainingDays }}天後到期</div>
                </div>
            </div>

            <!-- MIDDLE PANEL: Main Area -->
            <div class="right-panel main-area">
                
                <!-- HISTORY PREVIEW DRAWER (Option A) moved here so it can be seen in both welcome screen and chat screen -->
                <transition name="fade">
                    <div v-if="showPreviewPanel" class="history-preview-overlay" @click="showPreviewPanel = false"></div>
                </transition>

                <transition name="slide-in-left">
                    <div v-show="showPreviewPanel" class="history-preview-drawer">
                        <div class="drawer-header">
                            <div class="drawer-title">
                                <svg class="material-icon" viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
                                歷史紀錄預覽 <span class="preview-badge">唯讀</span>
                            </div>
                            <button class="close-drawer-btn" @click="showPreviewPanel = false">✕</button>
                        </div>
                        <div class="drawer-content">
                            <MessageList :messages="previewMessages" />
                        </div>
                        <div class="preview-footer">
                            <button class="secondary-btn" @click="showPreviewPanel = false">🔙 返回當前對話</button>
                            
                        </div>
                    </div>
                </transition>

                <!-- If Not Locked: Welcome & Candidate Selection -->
                <div v-if="!isSelectionLocked" class="welcome-container">
                    <div class="welcome-header">
                        <div class="magic-icon-wrapper">
                            <img src="@/assets/images/TAI star icon.png" alt="AI Icon" class="magic-icon" />
                        </div>
                        <h2><img src="@/assets/images/TraittyAI.svg" alt="Traitty AI" class="traitty-logo" /> 人才解析</h2>
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
                                   
                                   
                                    <button class="primary-btn confirm-btn" @click="confirmSelection">
                                        <img src="../assets/images/AI star.svg" class="material-icon small" alt="AI Star" />
                                        <span class="desktop-only">開始分析</span><span class="mobile-only">開始分析</span> {{ selectedCandidateIds.length > 0 ? `(${selectedCandidateIds.length})` : '' }}
                                    </button>
                                     <button class="secondary-btn cancel-btn" @click="showCandidateDropdown = false">
                                        關閉視窗
                                    </button>
                                </div>
                            </div>
                        </div>
                    </transition>

                    <!-- Large Input Box for Welcome Screen -->
                    <div class="big-input-box">
                        <textarea 
                            v-model="inputQuery" 
                            :placeholder="selectedCandidateIds.length > 0 ? '問問Traitty' : '問問Traitty AI'"
                            :disabled="selectedCandidateIds.length === 0"
                        ></textarea>
                        <div class="input-actions-row">
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <button class="select-candidate-btn" @click="showCandidateDropdown = true">
                                    選取人才 {{ selectedCandidateIds.length > 0 ? `(${selectedCandidateIds.length})` : '' }}
                                    <svg class="material-icon small" viewBox="0 0 18 17" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M6.66667 6.66667C5.75 6.66667 4.96528 6.34028 4.3125 5.6875C3.65972 5.03472 3.33333 4.25 3.33333 3.33333C3.33333 2.41667 3.65972 1.63194 4.3125 0.979167C4.96528 0.326389 5.75 0 6.66667 0C7.58333 0 8.36806 0.326389 9.02083 0.979167C9.67361 1.63194 10 2.41667 10 3.33333C10 4.25 9.67361 5.03472 9.02083 5.6875C8.36806 6.34028 7.58333 6.66667 6.66667 6.66667ZM6.66667 5C7.125 5 7.51736 4.83681 7.84375 4.51042C8.17014 4.18403 8.33333 3.79167 8.33333 3.33333C8.33333 2.875 8.17014 2.48264 7.84375 2.15625C7.51736 1.82986 7.125 1.66667 6.66667 1.66667C6.20833 1.66667 5.81597 1.82986 5.48958 2.15625C5.16319 2.48264 5 2.875 5 3.33333C5 3.79167 5.16319 4.18403 5.48958 4.51042C5.81597 4.83681 6.20833 5 6.66667 5ZM15.9167 16.25L13.25 13.5833C12.9583 13.75 12.6458 13.8889 12.3125 14C11.9792 14.1111 11.625 14.1667 11.25 14.1667C10.2083 14.1667 9.32292 13.8021 8.59375 13.0729C7.86458 12.3438 7.5 11.4583 7.5 10.4167C7.5 9.375 7.86458 8.48958 8.59375 7.76042C9.32292 7.03125 10.2083 6.66667 11.25 6.66667C12.2917 6.66667 13.1771 7.03125 13.9062 7.76042C14.6354 8.48958 15 9.375 15 10.4167C15 10.7917 14.9444 11.1458 14.8333 11.4792C14.7222 11.8125 14.5833 12.125 14.4167 12.4167L17.0833 15.0833L15.9167 16.25ZM11.25 12.5C11.8333 12.5 12.3264 12.2986 12.7292 11.8958C13.1319 11.4931 13.3333 11 13.3333 10.4167C13.3333 9.83333 13.1319 9.34028 12.7292 8.9375C12.3264 8.53472 11.8333 8.33333 11.25 8.33333C10.6667 8.33333 10.1736 8.53472 9.77083 8.9375C9.36806 9.34028 9.16667 9.83333 9.16667 10.4167C9.16667 11 9.36806 11.4931 9.77083 11.8958C10.1736 12.2986 10.6667 12.5 11.25 12.5ZM0 13.3333V11.0208C0 10.5486 0.118056 10.1111 0.354167 9.70833C0.590278 9.30556 0.916667 9 1.33333 8.79167C2.04167 8.43056 2.84028 8.125 3.72917 7.875C4.61806 7.625 5.60417 7.5 6.6875 7.5C6.52083 7.75 6.37847 8.01736 6.26042 8.30208C6.14236 8.58681 6.04861 8.88194 5.97917 9.1875C5.14583 9.25694 4.40278 9.39931 3.75 9.61458C3.09722 9.82986 2.54861 10.0556 2.10417 10.2917C1.96528 10.3611 1.85764 10.4618 1.78125 10.5938C1.70486 10.7257 1.66667 10.8681 1.66667 11.0208V11.6667H5.97917C6.04861 11.9722 6.14236 12.2639 6.26042 12.5417C6.37847 12.8194 6.52083 13.0833 6.6875 13.3333H0Z" fill="currentColor"/>
                                    </svg>
                                </button>
                                <button class="welcome-quick-btn" 
                                    @click="toggleMobileQuickQuestions" 
                                    :class="{ 'active': showMobileQuickQuestions }" 
                                    :disabled="selectedCandidateIds.length === 0"
                                    title="需先選取人才才能提問">
                                    快速提問
                                    <svg class="material-icon small" viewBox="0 0 24 24"><path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6C7.8 12.16 7 10.63 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/></svg>
                                </button>
                            </div>
                            <button class="send-btn" @click="handleInitialSend" :disabled="!canSendInitial">
                                <svg class="material-icon" viewBox="0 0 15 15">
                                  <path d="M6.0625 14.75V5.04167L1.85417 9.25L0 7.375L7.375 0L14.75 7.375L12.8958 9.25L8.6875 5.04167V14.75H6.0625Z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Chat View -->
                <div v-else class="chat-view">
                    <!-- Selected summary removed per request -->
                    <MessageList :messages="messages" @rate-message="rateMessage" />

                    <div class="chat-input-container">
                        <textarea 
                            v-model="inputQuery" 
                            @keydown.enter.prevent="sendMessage"
                            placeholder="新增問題......"
                            :disabled="isTyping"
                            class="multi-line-input"
                        ></textarea>
                        
                        <div class="chat-input-footer">
                            <div class="left-actions">
                                <div class="locked-status-wrapper">
                                    <button class="locked-status-btn" @click="toggleLockedCandidates" :class="{ 'active': showLockedCandidates }">
                                        
                                        選定 {{ activeConversationCandidatesObjects.length }} 位人選
                                        <svg class="material-icon small dropdown-icon" viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
                                    </button>
                                    
                                    <transition name="fade">
                                        <div v-if="showLockedCandidates" class="locked-candidates-dropdown">
                                            <div class="dropdown-info-header">
                                                <div class="info-content">
                                                   
                                                    <span>增刪人選或開啟新解析</span>
                                                </div>
                                                <button class="close-dropdown-btn" @click.stop="showLockedCandidates = false">✕</button>
                                            </div>
                                            <div class="dropdown-list">
                                                <div class="candidate-row" v-for="cand in activeConversationCandidatesObjects" :key="cand.id">
                                                    <div class="list-avatar-initial" :class="'bg-' + (cand.name ? cand.name.length % 5 : 0)">
                                                        {{ cand.name ? cand.name.charAt(0).toUpperCase() : '?' }}
                                                    </div>
                                                    <div class="candidate-info">
                                                        <span class="name">{{ cand.name }} <span v-if="cand.position" class="position">{{ cand.position }}</span></span>
                                                    </div>
                                                    <button class="remove-btn" @click.stop="removeCandidate(cand.id)" title="移除">
                                                        <svg width="14" height="2" viewBox="0 0 14 2" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            <rect width="14" height="2" rx="1" fill="#EF4444"/>
                                                        </svg>
                                                    </button>
                                                </div>
                                                
                                                <!-- 增加候選人按鈕 -->
                                                <button class="add-candidate-btn" @click.stop="showAddCandidateModal = true; showLockedCandidates = false">
                                                    <svg class="material-icon small" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                                                    增加候選人
                                                </button>
                                            </div>
                                            <div class="dropdown-footer">
                                                <button class="primary-btn new-analysis-btn" @click="resetAndReselect">
                                                    <img src="../assets/images/reopen-circle.svg" class="material-icon new-analysis-icon" alt="Reopen" />
                                                    開啟新人才解析
                                                </button>
                                            </div>
                                        </div>
                                    </transition>
                                </div>

                                <button class="locked-status-btn mobile-quick-btn" @click="toggleMobileQuickQuestions" :class="{ 'active': showMobileQuickQuestions }">
                                    快速提問
                                    <svg class="material-icon small" viewBox="0 0 24 24"><path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6C7.8 12.16 7 10.63 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/></svg>
                                </button>
                            </div>
                            
                            <button class="send-btn primary" @click="sendMessage" :disabled="!inputQuery.trim() || isTyping">
                                <svg class="material-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M11 21V5.83l-4.59 4.58L5 9l7-7 7 7-1.41 1.41L13 5.83V21h-2z"/></svg>
                            </button>
                        </div>
                    </div>
                </div>

            </div>

            <!-- Right Sidebar / Mobile Popover -->
            <QuickQuestionPanel
  :isSelectionLocked="isSelectionLocked"
  :showMobileQuickQuestions="showMobileQuickQuestions"
  :quickQuestionCategories="filteredQuickQuestionCategories"
  :selectedQuickQuestionCategory="selectedQuickQuestionCategory"
  :quickQuestions="filteredQuickQuestions"
  :isTyping="isTyping"
  @update:showMobileQuickQuestions="showMobileQuickQuestions = $event"
  @toggleCategory="toggleQuickQuestionCategory"
  @sendQuick="handleSendQuick"
/>

                <!-- 增加候選人 Modal -->
                <transition name="slide-up">
                    <div class="candidate-dropdown-overlay" v-if="showAddCandidateModal" @click.self="showAddCandidateModal = false">
                        <div class="candidate-dropdown-modal">
                            
                            <div class="modal-body">
                                <CandidateSelector
                                    ref="addCandidateSelectorRef"
                                    :candidates="candidates"
                                    :is-loading="isLoadingCandidates"
                                    :has-more="hasMoreCandidates"
                                    :disabled="false"
                                    :total-count="totalCandidatesCount"
                                    :initial-selected-ids="addModalInitialIds"
                                    :locked-ids="activeConversationCandidateIds"
                                    @change="handleAddCandidateChange"
                                    @load-more="loadMoreCandidates"
                                />
                            </div>
                            <div class="modal-footer">
                                <button 
                                    class="primary-btn confirm-btn" 
                                    @click="confirmAddCandidates"
                                    :disabled="newSelectedCandidateIds.length === 0 || isAddingCandidates"
                                >
                                    <svg v-if="!isAddingCandidates" class="material-icon small" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                                    <div v-else class="btn-spinner"></div>
                                    {{ isAddingCandidates ? '獲取報告中...' : `確認新增 (${newSelectedCandidateIds.length})` }}
                                </button>
                                <button class="secondary-btn cancel-btn" @click="showAddCandidateModal = false">關閉</button>
                            </div>
                        </div>
                    </div>
                </transition>


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

    <!-- Mobile History Drawer -->
    <HistoryDrawer 
        v-model="showMobileHistoryDrawer"
        :historySessions="historySessions"
        :currentSessionId="currentSessionId"
        :isLoading="historyIsLoading"
        :hasMore="historyHasMore"
        @load-more="loadMoreHistory"
        @select-session="loadHistorySession"
        @new-analysis="resetAndReselect"
    />

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import MessageList from './MessageList.vue'
import CandidateSelector from './CandidateSelector.vue'
import QuickQuestionPanel from './QuickQuestionPanel.vue'
import HistoryDrawer from './HistoryDrawer.vue'

import LoginView from './LoginView.vue'
import TraitReportModal from './TraitReportModal.vue'
import { useChatLogic } from '../composables/useChatLogic.js'

const isSidebarOpen = ref(true)

const toggleSidebar = () => {
    if (window.innerWidth <= 768) {
        showMobileHistoryDrawer.value = true
    } else {
        isSidebarOpen.value = !isSidebarOpen.value
    }
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
    remainingDays,
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
    previewMessages,
    showPreviewPanel,
    quickQuestionCategories,
    selectedQuickQuestionCategory,
    quickQuestions,
    filteredQuickQuestions,
    filteredQuickQuestionCategories,
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
    lockSelectionAndStart: logicLockSelection,
    resetAndReselect: logicResetAndReselect,
    removeCandidate,
    addCandidates: logicAddCandidates,
    sendMessage,
    sendQuickMessage,
    toggleQuickQuestionCategory,
    loadHistorySession,
    switchContextToPreview,
    loadMoreHistory,
    rateMessage
} = useChatLogic(emit)

const showCandidateDropdown = ref(false)
const showMobileQuickQuestions = ref(false)
const showLockedCandidates = ref(false)

const toggleLockedCandidates = () => {
    showLockedCandidates.value = !showLockedCandidates.value
    if (showLockedCandidates.value) {
        showMobileQuickQuestions.value = false
    }
}

const toggleMobileQuickQuestions = () => {
    showMobileQuickQuestions.value = !showMobileQuickQuestions.value
    if (showMobileQuickQuestions.value) {
        showLockedCandidates.value = false
    }
}

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

const handleSendQuick = async (q) => {
    if (!isSelectionLocked.value) {
        if (selectedCandidateIds.value.length === 0) return;
        lockSelectionAndStart();
        await new Promise(r => setTimeout(r, 100)); // wait for lock
    }
    sendQuickMessage(q);
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
    showLockedCandidates.value = false
    showMobileQuickQuestions.value = false
}

// Full Width Toggle Logic
const isExpanded = ref(true)
const toggleExpand = () => {
    isExpanded.value = !isExpanded.value
    if (isExpanded.value) {
        showMobileQuickQuestions.value = false
        showLockedCandidates.value = false
    }
}

// 增加候選人 Modal 狀態
const showAddCandidateModal = ref(false)
const newSelectedCandidateIds = ref([])
const addCandidateSelectorRef = ref(null)
const isAddingCandidates = ref(false)
// 固定空陣列 ref，避免字面量 [] 導致子元件 watch 重複觸發重置
const addModalInitialIds = ref([])

const handleAddCandidateChange = (ids) => {
    newSelectedCandidateIds.value = ids
}

const confirmAddCandidates = async () => {
    if (newSelectedCandidateIds.value.length === 0) return
    isAddingCandidates.value = true
    try {
        await logicAddCandidates(newSelectedCandidateIds.value)
        showAddCandidateModal.value = false
        newSelectedCandidateIds.value = []
        if (addCandidateSelectorRef.value?.clearSelection) {
            addCandidateSelectorRef.value.clearSelection()
        }
    } finally {
        isAddingCandidates.value = false
    }
}

</script>

<style lang="scss" scoped>
@use '../styles/chat-container.scss';

.new-tab-btn {
    display: none !important;
}

.desktop-only {
    @media (max-width: 768px) {
        display: none !important;
    }
}

.mobile-only {
    display: none !important;
    @media (max-width: 768px) {
        display: inline-block !important;
    }
}

.chat-container.expanded-mode {
    width: 98vw;
    height: 90vh;
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
/* Chat Mode Layout — left 15% / chat 93% / quick 12% */
.split-view.chat-mode {
    .left-panel {
        width: 15% !important;    /* ← 原 20%，縮小歷史側欄 */
        min-width: 300px;          /* ← 原 200px */
        @media (max-width: 768px) {
            width: 100% !important;
        }
    }

    .right-panel {
        /* 緊湊模式下預設寬度 100% */
        width: 100% !important;
        flex: unset !important;
        display: flex;
        flex-direction: column;

        /* 只有在展開模式下才縮小寬度以適應側邊欄佈局 */
        .chat-container.expanded-mode & {
            width: 94% !important;
        }

        @media (max-width: 768px) {
            width: 100% !important;
            flex: 1 !important;
        }
    }

    .quick-sidebar {
        width: 12% !important;     /* ← 原 15%，縮小快速提問側欄 */
        min-width: 200px;          /* ← 原 240px */
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

        [data-theme="midnight"] & {
            background: rgba(30, 30, 40, 0.98);
            color: var(--glass-text-primary);
        }

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

.header-left.mobile-visible {
    @media (max-width: 768px) {
        display: flex !important;
    }
}

.preview-footer {
    padding: 1rem;
    border-top: 1px solid var(--glass-border);
    display: flex;
    gap: 0.8rem;
    justify-content: flex-end;
    background: var(--glass-bg);
    border-bottom-left-radius: inherit;
    border-bottom-right-radius: inherit;
    
    @media (max-width: 768px) {
        flex-direction: column;
        padding: 0.8rem;
        gap: 0.5rem;
    }
    
    .secondary-btn, .confirm-btn {
        padding: 0.6rem 1rem;
        font-size: 0.95rem;
        
        @media (max-width: 768px) {
            width: 100%;
            justify-content: center;
            font-size: 0.9rem;
        }
    }
}
</style>
