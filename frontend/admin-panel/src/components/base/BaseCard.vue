
<template>
  <div class="card">
    <div v-if="$slots.header || title" class="card-header">
      <h3 v-if="title">{{ title }}</h3>
      <slot name="header"></slot>
    </div>
    <div class="card-body">
      <slot></slot>
    </div>
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String
})
</script>

<style lang="scss" scoped>
.card {
  @extend .card; // Use global utility
  display: flex;
  flex-direction: column;
  padding: 0; // Reset for sub-sections

  &-header {
    padding: 1.5rem;
    border-bottom: 1px solid $border-color;
    h3 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 600;
      color: $text-main;
    }
  }

  &-body {
    padding: 1.5rem;
    flex: 1;
  }

  &-footer {
    padding: 1rem 1.5rem;
    background-color: $bg-body;
    border-top: 1px solid $border-color;
    border-bottom-left-radius: $border-radius;
    border-bottom-right-radius: $border-radius;
  }
}
</style>
