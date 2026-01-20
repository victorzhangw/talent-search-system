
<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">P</span>
        <span class="logo-text">Prometheus</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <div class="nav-label">儀表板</div>
        <router-link to="/dashboard" class="nav-item" active-class="active">
          <LayoutDashboard :size="20" />
          <span>數據分析</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-label">報表中心</div>
        <router-link to="/reports" class="nav-item" active-class="active">
          <BarChart2 :size="20" />
          <span>用量報表</span>
        </router-link>
      </div>

      <div class="nav-section">
        <div class="nav-label">管理功能</div>
        <router-link to="/sessions" class="nav-item" active-class="active">
          <MessageSquare :size="20" />
          <span>對話紀錄</span>
        </router-link>
        <router-link to="/users" class="nav-item" active-class="active">
          <Users :size="20" />
          <span>使用者管理</span>
        </router-link>
      </div>
    </nav>
  </aside>
</template>

<script setup>
import { LayoutDashboard, MessageSquare, Users, BarChart2 } from 'lucide-vue-next'
</script>

<style lang="scss" scoped>
.sidebar {
  width: 260px;
  height: 100vh;
  background-color: $bg-sidebar;
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;

  &-header {
    height: 64px;
    display: flex;
    align-items: center;
    padding: 0 1.5rem;
    border-bottom: 1px solid transparent; // Optional: Add separator if needed

    .logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      color: $text-main;
      
      &-icon {
        width: 32px;
        height: 32px;
        background: $primary-color;
        color: white;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
      }
    }
  }

  &-nav {
    padding: 1.5rem;
    flex: 1;
    overflow-y: auto;

    .nav-section {
      margin-bottom: 2rem;

      .nav-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: $text-muted;
        font-weight: 600;
        margin-bottom: 0.75rem;
        padding-left: 0.75rem;
      }

      .nav-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        border-radius: $border-radius-sm;
        color: $text-muted;
        font-weight: 500;
        margin-bottom: 0.25rem;
        transition: all 0.2s;

        &:hover {
          color: $text-main;
          background-color: $bg-body;
        }

        &.active {
          background-color: $primary-light;
          color: $primary-color;
        }
      }
    }
  }
}
</style>
