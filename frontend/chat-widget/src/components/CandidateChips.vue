<template>
  <div class="candidate-bar">
    <div 
      v-for="cand in candidates" 
      :key="cand.id" 
      class="chip"
      :class="{ active: selectedIds.includes(cand.id) }"
      @click="$emit('toggle', cand.id)"
    >
      <div class="avatar">{{ cand.name[0] }}</div>
      <span class="name">{{ cand.name }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  candidates: {
    type: Array,
    default: () => []
  },
  selectedIds: {
    type: Array,
    default: () => []
  }
})

defineEmits(['toggle'])
</script>

<style lang="scss" scoped>
.candidate-bar {
  padding: 0.8rem 1rem;
  display: flex;
  gap: 0.8rem;
  overflow-x: auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);

  /* Horizontal Scrollbar Config */
  &::-webkit-scrollbar { height: 4px; }
  &::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 2px; }

  .chip {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.8rem 0.3rem 0.3rem; // extra padding right
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s;
    user-select: none;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
    }

    &.active {
      background: rgba(99, 102, 241, 0.2);
      border-color: var(--primary-color);
      
      .avatar {
        background: var(--primary-color);
        color: white;
      }
    }

    .avatar {
      width: 24px;
      height: 24px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: bold;
      color: #cbd5e1;
    }

    .name {
      font-size: 0.85rem;
      color: #e2e8f0;
    }
  }
}
</style>
