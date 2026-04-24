<template>
  <transition name="fade">
    <div 
      class="quick-question-overlay" 
      v-if="showMobileQuickQuestions" 
      @click="closeMobile"
    ></div>
  </transition>

  <div class="quick-sidebar" :class="{ 'show-mobile-popover': showMobileQuickQuestions }">
    <!-- Mobile only Header -->
    <div class="mobile-popover-header" v-if="showMobileQuickQuestions">
      <div class="header-left-content">
        <svg class="material-icon" viewBox="0 0 24 24"><path d="M3.06822 9.4092L1.85005 10.6075M1.72276 6.21345H0M1.85005 1.82022L3.06822 3.01848M6.31708 0V1.6946M10.7833 1.82022L9.5651 3.01848M12.9786 12.7458L17.365 11.2396C18.1872 10.9573 18.219 9.8248 17.4136 9.5104L7.3781 6.07269C6.62375 5.7782 5.86518 6.50613 6.1456 7.2554L9.4317 17.4017C9.7309 18.2013 10.8816 18.1988 11.1896 17.3979L12.9786 12.7458Z" stroke="#101010" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <span>點擊取得專業解析</span>
      </div>
      <button class="close-popover-btn" @click="closeMobile">✕</button>
    </div>

    <!-- Desktop Category Dropdown -->
    <div class="sidebar-header" v-show="!showMobileQuickQuestions">
      <div class="custom-select-wrapper" :class="{ 'is-open': isCategoryDropdownOpen }">
        <div class="category-toggle" @click="toggleDropdown">
          <img src="../assets/images/bulb.svg" class="material-icon select-icon" alt="提問類別" />
          <div class="category-name-display">{{ selectedQuickQuestionCategory }}</div>
          <img src="../assets/images/swithquicks.svg" class="material-icon select-caret" :class="{ 'caret-flipped': isCategoryDropdownOpen }" alt="切換類別" />
        </div>
        <transition name="dropdown-fade">
          <div class="category-dropdown-list" v-if="isCategoryDropdownOpen">
            <button
              v-for="catName in categoryNames"
              :key="'cat-opt-'+catName"
              class="category-dropdown-item"
              :class="{ 'is-active': catName === selectedQuickQuestionCategory }"
              @click="selectCategory(catName)"
            >
              <svg class="material-icon cat-icon" viewBox="0 0 24 24">
                <path v-if="catName === '招募'" d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"/>
                <path v-else-if="catName === '管理'" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                <path v-else d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"/>
              </svg>
              {{ catName }}
            </button>
          </div>
        </transition>
      </div>
    </div>

    <!-- Desktop Quick Questions List -->
    <div class="quick-btn-list" v-show="!showMobileQuickQuestions">
      <button
        v-for="(q, idx) in quickQuestions"
        :key="'desktop-'+idx"
        class="quick-btn"
        @click="sendQuick(q)"
        :disabled="isTyping"
      >
        {{ q.label || q }}
      </button>
    </div>

    <!-- Mobile All Categories List -->
    <div class="mobile-all-categories-list" v-if="showMobileQuickQuestions">
      <div class="category-group" v-for="(qs, catName) in quickQuestionCategories" :key="'cat-'+catName">
        <div class="category-group-title">
          <svg class="material-icon cat-icon" viewBox="0 0 24 24">
            <path v-if="catName === '招募'" d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"/>
            <path v-else-if="catName === '管理'" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
            <path v-else d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"/>
          </svg>
          {{ catName }}
        </div>
        <button
          v-for="(q, idx) in qs"
          :key="'mobile-'+catName+'-'+idx"
          class="quick-btn rounded-pill"
          @click="sendQuick(q); closeMobile()"
          :disabled="isTyping"
        >
          {{ q.label || q }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  isSelectionLocked: Boolean,
  showMobileQuickQuestions: Boolean,
  quickQuestionCategories: Object,
  selectedQuickQuestionCategory: String,
  quickQuestions: Array,
  isTyping: Boolean
});

const emit = defineEmits(['update:showMobileQuickQuestions', 'toggleCategory', 'selectCategory', 'sendQuick']);

// Dropdown state for desktop category selector
const isCategoryDropdownOpen = ref(false);

const categoryNames = computed(() => {
  return Object.keys(props.quickQuestionCategories || {});
});

function toggleDropdown() {
  isCategoryDropdownOpen.value = !isCategoryDropdownOpen.value;
}

function selectCategory(catName) {
  emit('selectCategory', catName);
  isCategoryDropdownOpen.value = false;
}

function closeMobile() {
  emit('update:showMobileQuickQuestions', false);
}

function sendQuick(q) {
  emit('sendQuick', q);
}

// Close dropdown when clicking outside
function handleClickOutside(e) {
  if (isCategoryDropdownOpen.value) {
    const wrapper = e.target.closest('.custom-select-wrapper');
    if (!wrapper) {
      isCategoryDropdownOpen.value = false;
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside, true);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside, true);
});
</script>

<style lang="scss" scoped>
@use '../styles/chat-container.scss';
</style>
