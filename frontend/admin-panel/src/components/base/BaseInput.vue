
<template>
  <div class="form-group">
    <label v-if="label" :for="id">{{ label }}</label>
    <div class="input-wrapper">
      <input
        :id="id"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        @input="$emit('update:modelValue', $event.target.value)"
        class="form-control"
      />
      <span v-if="icon" class="icon-slot">
         <component :is="icon" size="18" />
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: String,
  modelValue: [String, Number],
  type: { type: String, default: 'text' },
  placeholder: String,
  icon: Object // Component
})

const id = computed(() => `input-${Math.random().toString(36).substr(2, 9)}`)
</script>

<style lang="scss" scoped>
.form-group {
  margin-bottom: 1rem;
  
  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: $text-main;
    font-size: 0.9rem;
  }
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.form-control {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  font-family: inherit;
  font-size: 1rem;
  transition: border-color 0.2s;

  &:focus {
    outline: none;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px $primary-light;
  }
}

.icon-slot {
  position: absolute;
  right: 1rem;
  color: $text-muted;
  pointer-events: none;
}
</style>
