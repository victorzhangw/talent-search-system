
<template>
  <header class="header">
    <div class="header-left">
      <div class="breadcrumbs">
        <span class="text-muted">Dashboard</span>
        <ChevronRight :size="16" class="separator" />
        <span class="current">{{ pageTitle }}</span>
      </div>
    </div>

    <div class="header-right">
      <div class="actions">
        <button class="icon-btn" @click="handleLogout" title="登出">
            <LogOut :size="20" />
        </button>
        <div class="user-profile">
            <div class="avatar">AD</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, LogOut } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const pageTitle = computed(() => route.meta.title || 'Overview')

const handleLogout = () => {
    if (confirm('確定要登出系統嗎？')) {
        auth.logout()
        router.push('/login')
    }
}
</script>

<style lang="scss" scoped>
.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  background-color: $bg-body; // Transparent/Body bg
  // border-bottom: 1px solid $border-color;
  
  &-left {
    .breadcrumbs {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.9rem;
      
      .separator { color: $text-muted; }
      .current { font-weight: 600; color: $text-main; }
    }
  }

  &-right {
    display: flex;
    align-items: center;
    gap: 1.5rem;

    .actions {
        display: flex;
        align-items: center;
        gap: 1rem;

        .icon-btn {
            background: none;
            border: none;
            color: $text-muted;
            position: relative;
            padding: 0.25rem;
            cursor: pointer;
            
            &:hover { color: $primary-color; }
        }

        .user-profile {
            .avatar {
                width: 36px;
                height: 36px;
                background: $text-main;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
            }
        }
    }
  }
}
</style>
