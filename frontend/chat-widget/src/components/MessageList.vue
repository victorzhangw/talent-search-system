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
</script>

<style lang="scss" scoped>
@use '../styles/components/message-list.scss';
</style>
