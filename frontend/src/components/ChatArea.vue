<template>
  <div class="chat-area">
    <div class="messages" ref="messagesContainer">
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message', message.type]"
      >
        <div class="message-avatar">
          <i
            :class="message.type === 'user' ? 'fas fa-user' : 'fas fa-robot'"
          ></i>
        </div>
        <div class="message-content">{{ message.content }}</div>
      </div>

      <div v-if="isTyping" class="message system">
        <div class="message-avatar">
          <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="input-container">
        <input
          v-model="userInput"
          @keyup.enter="handleSendMessage"
          placeholder="描述您需要的人才特質或直接提問..."
          :disabled="isTyping"
        />
        <button
          @click="handleSendMessage"
          :disabled="!userInput.trim() || isTyping"
        >
          <i class="fas fa-paper-plane"></i> 發送
        </button>
      </div>
      <div class="suggestions" v-if="suggestions.length > 0">
        <span
          v-for="(suggestion, index) in suggestions"
          :key="index"
          class="suggestion-chip"
          @click="useSuggestion(suggestion)"
        >
          {{ suggestion }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from "vue";
import { useTalentStore } from "@/stores/talent";

const talentStore = useTalentStore();

const userInput = ref("");
const messagesContainer = ref(null);

const messages = computed(() => talentStore.messages);
const isTyping = computed(() => talentStore.isTyping);
const suggestions = computed(() => talentStore.suggestions);

async function handleSendMessage() {
  if (!userInput.value.trim() || isTyping.value) return;

  await talentStore.sendMessage(userInput.value);
  userInput.value = "";
  scrollToBottom();
}

function useSuggestion(suggestion) {
  userInput.value = suggestion;
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}

watch(
  messages,
  () => {
    scrollToBottom();
  },
  { deep: true }
);
</script>
