
<template>
  <div class="main-layout">
    <TheSidebar />
    <div class="main-content">
      <TheHeader />
      <main class="page-container">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import TheSidebar from './TheSidebar.vue'
import TheHeader from './TheHeader.vue'
</script>

<style lang="scss" scoped>
.main-layout {
  display: flex;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  margin-left: 260px; // Sidebar width
  display: flex;
  flex-direction: column;
  width: calc(100% - 260px);
}

.page-container {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
