<template>
  <div class="interview-dialog" v-if="showDialog" @click.self="handleClose">
    <div class="interview-dialog-content">
      <div class="interview-dialog-header">
        <h2>
          <i
            class="fas fa-clipboard-question"
            style="margin-right: 8px; color: #93bfc7"
          ></i>
          面試問題建議
        </h2>
        <button class="close-btn" @click="handleClose">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="interview-dialog-body">
        <div class="interview-messages">
          <div
            v-for="(message, index) in messages"
            :key="index"
            class="interview-message"
            :class="message.role"
            v-html="formatMessage(message.content)"
          ></div>
          <div v-if="isGenerating" class="loading-indicator">
            <div class="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            正在生成面試問題...
          </div>
        </div>
      </div>
      <div class="interview-dialog-footer">
        <div class="interview-footer-actions">
          <button
            class="download-btn"
            @click="handleDownload"
            :disabled="messages.length === 0"
          >
            <i class="fas fa-file-excel"></i>
            下載為 CSV
          </button>
        </div>
        <input
          v-model="userInput"
          @keyup.enter="handleSendMessage"
          class="interview-input"
          placeholder="輸入您的修改建議，例如：請增加關於團隊合作的問題..."
          :disabled="isGenerating"
        />
        <button
          class="send-btn"
          @click="handleSendMessage"
          :disabled="!userInput.trim() || isGenerating"
        >
          <i class="fas fa-paper-plane"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useInterviewStore } from "@/stores/interview";

const interviewStore = useInterviewStore();

const userInput = ref("");

const showDialog = computed(() => interviewStore.showDialog);
const messages = computed(() => interviewStore.messages);
const isGenerating = computed(() => interviewStore.isGenerating);

function handleClose() {
  interviewStore.closeDialog();
}

async function handleSendMessage() {
  if (!userInput.value.trim() || isGenerating.value) return;

  await interviewStore.sendMessage(userInput.value);
  userInput.value = "";
}

function handleDownload() {
  interviewStore.downloadAsCSV();
}

function formatMessage(content) {
  let formatted = content;
  const lines = formatted.split("\n");
  let inList = false;
  let result = [];

  for (let line of lines) {
    if (
      line.match(/^(#+\s*)?(.*(問題|建議|評估|技能|能力|特質|候選人|面試).*)$/)
    ) {
      if (inList) {
        result.push("</ul>");
        inList = false;
      }
      const title = line.replace(/^#+\s*/, "");
      result.push(
        `<div class="interview-section-title"><i class="fas fa-chevron-right"></i>${title}</div>`
      );
    } else if (line.match(/^\d+\.\s+(.+)$/)) {
      if (!inList) {
        result.push('<ul class="interview-question-list">');
        inList = true;
      }
      const content = line.replace(/^\d+\.\s+/, "");
      result.push(
        `<li class="interview-question-item"><i class="fas fa-circle-question"></i><span>${content}</span></li>`
      );
    } else if (line.match(/^[•\-\*]\s+(.+)$/)) {
      if (!inList) {
        result.push('<ul class="interview-question-list">');
        inList = true;
      }
      const content = line.replace(/^[•\-\*]\s+/, "");
      result.push(
        `<li class="interview-question-item"><i class="fas fa-check-circle"></i><span>${content}</span></li>`
      );
    } else if (line.trim()) {
      if (inList) {
        result.push("</ul>");
        inList = false;
      }
      result.push(line);
    } else {
      if (inList) {
        result.push("</ul>");
        inList = false;
      }
      result.push("<br/>");
    }
  }

  if (inList) {
    result.push("</ul>");
  }

  return result.join("\n");
}
</script>
