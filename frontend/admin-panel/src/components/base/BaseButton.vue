
<template>
  <button :class="['btn', `btn-${variant}`, { 'is-loading': loading }]" :disabled="disabled || loading">
    <span v-if="loading" class="spinner"></span>
    <span v-else>
        <slot></slot>
    </span>
  </button>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'danger', 'outline'].includes(value)
  },
  loading: Boolean,
  disabled: Boolean
})
</script>

<style lang="scss" scoped>
.btn {
  padding: 0.75rem 1.5rem;
  border-radius: $border-radius-sm;
  font-weight: 500;
  border: none;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-primary {
  background-color: $primary-color;
  color: white;
  &:hover:not(:disabled) {
    background-color: $primary-hover;
  }
}

.btn-secondary {
  background-color: white;
  color: $text-main;
  border: 1px solid $border-color;
  &:hover:not(:disabled) {
    background-color: $bg-body;
  }
}

.btn-danger {
    background-color: $danger-color;
    color: white;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
