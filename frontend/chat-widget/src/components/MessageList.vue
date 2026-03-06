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
            <!-- Thumbs up -->
            <button class="action-btn" :class="{ 'active': msg.rating === 1 }" @click="handleRate(msg, 1)" title="Good">
              <img src="@/assets/images/chat-Good.svg" class="action-icon" alt="Good" />
            </button>
            <!-- Thumbs down -->
            <button class="action-btn" :class="{ 'active': msg.rating === -1 }" @click="handleRate(msg, -1)" title="Bad">
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
  messages: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['rateMessage'])

const listRef = ref(null)

const handleRate = async (msg, rating) => {
  // If already rated to the same, maybe un-rate (0)
  const newRating = msg.rating === rating ? 0 : rating
  
  // Optimistic update
  msg.rating = newRating
  
  // Call API
  if (msg.id) {
    emit('rateMessage', msg.id, newRating)
  }
}

// Auto-scroll to bottom
watch(() => props.messages?.length, () => scrollToBottom())
watch(() => props.messages?.[props.messages?.length - 1]?.content, () => scrollToBottom())

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
