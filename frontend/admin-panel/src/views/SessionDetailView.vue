
<template>
  <div class="session-detail">
    <div class="header-section">
      <div class="title-group">
        <router-link to="/sessions" class="back-link">
          <ArrowLeft :size="20" />
        </router-link>
        <h2>Session Details</h2>
      </div>
      <div class="actions">
         <span :class="['status-badge', session?.session?.status]">
            {{ session?.session?.status || 'Unknown' }}
         </span>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading session data...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-else class="content-grid">
      <!-- Chat History -->
      <div class="chat-column">
        <BaseCard title="Conversation History" class="chat-card">
          <div class="messages-list">
            <div 
              v-for="msg in session.messages" 
              :key="msg.id"
              :class="['message-item', msg.role]"
            >
              <div class="message-header">
                <span class="role">{{ msg.role === 'user' ? 'User' : 'Associate' }}</span>
                <span class="tokens" v-if="msg.token_usage">
                  {{ msg.token_usage }} tokens
                </span>
              </div>
              <div class="message-content">
                {{ msg.content }}
              </div>
              <div class="message-time">
                {{ formatTime(msg.created_at) }}
              </div>
            </div>
          </div>
        </BaseCard>
      </div>

      <!-- Metadata Side Panel -->
      <div class="meta-column">
        <BaseCard title="Metadata">
          <div class="meta-list">
             <div class="meta-item">
               <span class="label">Session ID</span>
               <span class="value font-mono">{{ session.session.session_id }}</span>
             </div>
             <div class="meta-item">
               <span class="label">User/Candidate</span>
               <span class="value">{{ session.session.user_id || 'Guest' }}</span>
             </div>
             <div class="meta-item">
               <span class="label">Started At</span>
               <span class="value">{{ formatDate(session.session.started_at) }}</span>
             </div>
             <div class="meta-item">
               <span class="label">Total Tokens</span>
               <span class="value text-primary font-bold">
                 {{ session.messages.reduce((acc, m) => acc + (m.token_usage || 0), 0) }}
               </span>
             </div>
          </div>
        </BaseCard>

        <!-- Debug JSON -->
        <!-- <BaseCard title="Raw Metadata" class="mt-4">
           <pre class="json-dump">{{ JSON.stringify(session.session.metadata, null, 2) }}</pre>
        </BaseCard> -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import BaseCard from '@/components/base/BaseCard.vue'
import { ArrowLeft } from 'lucide-vue-next'
import { useDateFormat } from '@vueuse/core'

const route = useRoute()
const session = ref(null)
const loading = ref(true)
const error = ref(null)

const fetchDetail = async () => {
  try {
    const res = await axios.get(`/api/admin/sessions/${route.params.id}`)
    session.value = res.data
  } catch (e) {
    error.value = "Failed to load session details."
    console.error(e)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr) => useDateFormat(dateStr, 'YYYY-MM-DD HH:mm:ss').value
const formatTime = (dateStr) => useDateFormat(dateStr, 'HH:mm:ss').value

onMounted(fetchDetail)
</script>

<style lang="scss" scoped>
.header-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;

  .title-group {
    display: flex;
    align-items: center;
    gap: 1rem;

    .back-link {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: white;
      border: 1px solid $border-color;
      color: $text-muted;
      &:hover { color: $primary-color; border-color: $primary-color; }
    }
  }

  .status-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 12px;
      font-weight: 600;
      font-size: 0.9rem;
      background: $bg-body;
      color: $text-muted;
      &.active { background: #DCFCE7; color: #166534; }
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 2rem;
  align-items: start;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  
  .message-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid $border-color;
    
    &:last-child { border-bottom: none; }

    .message-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      
      .role { font-weight: 700; text-transform: uppercase; }
      .tokens { color: $text-muted; font-size: 0.8rem; background: $bg-body; padding: 2px 6px; border-radius: 4px; }
    }

    &.user .role { color: $secondary-color; }
    &.assistant .role { color: $primary-color; }

    .message-content {
      line-height: 1.6;
      color: $text-main;
      white-space: pre-wrap;
    }
    
    .message-time {
      font-size: 0.75rem;
      color: $text-muted;
      align-self: flex-end;
    }
  }
}

.meta-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;

  .meta-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    
    .label { font-size: 0.75rem; color: $text-muted; text-transform: uppercase; font-weight: 600; }
    .value { font-size: 0.95rem; color: $text-main; word-break: break-all; }
  }
}

.font-mono { font-family: monospace; }
.mt-4 { margin-top: 1rem; }
.json-dump { font-size: 0.8rem; overflow-x: auto; background: $bg-body; padding: 0.5rem; border-radius: 4px; }
</style>
