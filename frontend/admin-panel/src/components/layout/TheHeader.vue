
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
      <div class="search-bar">
        <Search :size="18" class="search-icon" />
        <input type="text" placeholder="Search (Ctrl + K)" />
      </div>

      <div class="actions">
        <button class="icon-btn">
            <Bell :size="20" />
            <span class="badge"></span>
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
import { useRoute } from 'vue-router'
import { Search, Bell, ChevronRight } from 'lucide-vue-next'

const route = useRoute()
const pageTitle = computed(() => route.meta.title || 'Overview')
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

    .search-bar {
      position: relative;
      
      .search-icon {
        position: absolute;
        left: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        color: $text-muted;
      }

      input {
        padding: 0.5rem 1rem 0.5rem 2.5rem;
        border: none;
        background-color: white; // Or input bg
        border-radius: 20px;
        width: 240px;
        font-size: 0.9rem;
        box-shadow: $shadow-sm;
        
        &:focus {
          outline: none;
          box-shadow: $shadow-md;
        }
      }
    }

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
            
            &:hover { color: $text-main; }

            .badge {
                position: absolute;
                top: 0;
                right: 0;
                width: 8px;
                height: 8px;
                background: $primary-color;
                border-radius: 50%;
                border: 1px solid white;
            }
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
