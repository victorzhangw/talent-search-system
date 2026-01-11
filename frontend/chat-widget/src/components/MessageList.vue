<template>
  <div class="message-list" ref="listRef">
    <div 
      v-for="(msg, index) in messages" 
      :key="index" 
      class="message-row"
      :class="msg.role"
    >
      <!-- User Message -->
      <div v-if="msg.role === 'user'" class="message-bubble user">
        {{ msg.content }}
      </div>

      <!-- AI Message -->
      <div v-else class="message-bubble ai">
        <div class="avatar">
           <!-- Icon: Smart Toy (Robot) -->
           <svg class="material-icon" viewBox="0 0 24 24"><path d="M20 9V7c0-1.1-.9-2-2-2h-3c0-1.66-1.34-3-3-3S9 3.34 9 5H6c-1.1 0-2 .9-2 2v2c-1.66 0-3 1.34-3 3s1.34 3 3 3v4c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-4c1.66 0 3-1.34 3-3s-1.34-3-3-3zM8 10.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5S10.33 12 9.5 12 8 11.33 8 10.5zm9 0c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5-1.5-.67-1.5-1.5zM12 18c-1.66 0-3-1.5-3-3.6h6c0 2.1-1.34 3.6-3 3.6z"/></svg>
        </div>
        <div class="content">
          <ReasoningBlock v-if="msg.reasoning || msg.intent" :intent="msg.intent">
            {{ msg.reasoning }}
          </ReasoningBlock>
          
          <div class="text-content" v-html="renderMarkdown(msg.content)"></div>
          
          <span v-if="msg.isTyping" class="cursor">|</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ReasoningBlock from './ReasoningBlock.vue'
import { marked } from 'marked' 

const props = defineProps({
  messages: Array
})

const listRef = ref(null)

// Auto-scroll to bottom
watch(() => props.messages.length, () => scrollToBottom())
watch(() => props.messages[props.messages.length - 1]?.content, () => scrollToBottom())

const scrollToBottom = async () => {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text)
}
</script>

<style lang="scss" scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.2rem; 
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.material-icon {
    width: 28px; /* Slightly larger avatar */
    height: 28px;
    fill: var(--primary-color); /* Commercial Brand Color */
}

.message-row {
  display: flex;
  &.user { justify-content: flex-end; }
  &.ai { justify-content: flex-start; }
}

.message-bubble {
  max-width: 90%;
  padding: 0.8rem 1rem;
  border-radius: 12px;
  
  &.user {
    background: var(--primary-color);
    color: white;
    border-bottom-right-radius: 4px;
    font-size: 0.95rem;
    line-height: 1.5;
  }
  
  &.ai {
    background: var(--bubble-ai-bg); 
    border: 1px solid var(--bubble-ai-border); 
    border-bottom-left-radius: 4px;
    color: var(--glass-text-primary);
    
    display: flex;
    gap: 0.6rem; 
    padding: 0.6rem 0.8rem; 
    
    width: 100%;
    
    .avatar {
      margin-top: 0.1rem; 
    }
    
    .content {
      flex: 1;
      min-width: 0;
      
      font-size: 0.95rem;
      line-height: 1.6; 
      
      :deep(p) { margin: 0.4rem 0 0.8rem 0; }
      :deep(p:last-child) { margin-bottom: 0; }
      
      :deep(ul), :deep(ol) {
        margin: 0.4rem 0 0.8rem 1.2rem;
        padding-left: 0;
      }
      
      :deep(li) {
        margin-bottom: 0.3rem;
        padding-left: 0.2rem;
      }
      
      :deep(h1), :deep(h2), :deep(h3) {
        margin: 1rem 0 0.5rem 0;
        font-weight: 600;
        color: var(--glass-text-primary);
        line-height: 1.3;
      }
      
      :deep(strong) {
        color: var(--glass-text-primary);
        font-weight: 600;
      }
      
      :deep(code) {
        background: rgba(127, 127, 127, 0.15);
        padding: 0.1rem 0.3rem;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.9em;
      }
    }
  }
}

.cursor {
  display: inline-block;
  animation: blink 1s step-end infinite;
  margin-left: 2px;
}

@keyframes blink {
  50% { opacity: 0; }
}
</style>
