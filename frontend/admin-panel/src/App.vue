
<template>
  <component :is="layout">
    <router-view />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const route = useRoute()

// Default to MainLayout, switch if meta.layout is defined (e.g. 'auth')
const layout = computed(() => {
  if (route.meta.layout === 'auth') {
    return 'div' // Simple wrapper for auth pages, or dedicated AuthLayout
  }
  return MainLayout
})
</script>
