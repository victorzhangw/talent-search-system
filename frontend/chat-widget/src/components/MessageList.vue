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
           <img :src="traittyAvatar" class="avatar-img" alt="Traitty Avatar" />
        </div>
        <div class="content">
          <!-- Show ReasoningBlock when AI is typing (thinking) -->
          <ReasoningBlock v-if="msg.isTyping || msg.reasoning || msg.intent" :intent="msg.intent">
            {{ msg.reasoning }}
          </ReasoningBlock>
          
          <div class="text-content" v-html="renderMarkdown(msg.content)"></div>
          
          <span v-if="msg.isTyping" class="cursor">|</span>

          <!-- Message Actions (Copy, placeholder for Good/Bad) -->
          <div v-if="!msg.isTyping && index > 0" class="message-actions">
            <!-- Thumbs up placeholder -->
            <button class="action-btn" title="Good (功能開發中)">
              <img src="@/assets/images/chat-Good.svg" class="action-icon" alt="Good" />
            </button>
            <!-- Thumbs down placeholder -->
            <button class="action-btn" title="Bad (功能開發中)">
              <img src="@/assets/images/chat-Bad.svg" class="action-icon" alt="Bad" />
            </button>
            <!-- Copy button -->
            <button class="action-btn" @click="copyText(msg.content)" title="複製內容">
              <img src="@/assets/images/chat-copy.svg" class="action-icon" alt="Copy" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ReasoningBlock from './ReasoningBlock.vue'
import { marked } from 'marked' 
import traittyAvatar from '@/assets/images/traitty-avatar.svg'

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

const copyText = async (text) => {
  try {
    // Strip markdown formatting approximately or just copy raw. We'll copy raw for now, 
    // or we could create a temporary div to grab innerText if we want plain text.
    await navigator.clipboard.writeText(text)
    // Optional: show a small toast or change icon briefly
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}
</script>

<style lang="scss" scoped>
@use '../styles/components/message-list.scss';
</style>
