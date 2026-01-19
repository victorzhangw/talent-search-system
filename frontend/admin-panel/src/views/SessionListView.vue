
<template>
  <div class="session-list">
      <div class="header-section">
          <h2>Session Management</h2>
          <div class="filters">
              <BaseInput v-model="search" placeholder="Search Session ID..." />
          </div>
      </div>

      <BaseCard>
          <div class="table-container">
            <div v-if="loading" class="loading-state">Loading...</div>
            <table v-else class="data-table">
                <thead>
                    <tr>
                        <th>Session ID</th>
                        <th>User ID</th>
                        <th>Status</th>
                        <th>Messages</th>
                        <th>Tokens</th>
                        <th>Last Active</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="session in sessions" :key="session.session_id">
                        <td class="font-mono">{{ session.session_id.slice(0, 8) }}...</td>
                        <td>{{ session.user_id || 'Guest' }}</td>
                        <td>
                            <span :class="['status-badge', session.status]">
                                {{ session.status }}
                            </span>
                        </td>
                        <td>{{ session.message_count }}</td>
                        <td>{{ session.total_tokens }}</td>
                        <td>{{ formatDate(session.last_active_at) }}</td>
                        <td>
                            <router-link :to="`/sessions/${session.session_id}`">
                                <BaseButton variant="secondary" class="btn-sm">View</BaseButton>
                            </router-link>
                        </td>
                    </tr>
                </tbody>
            </table>
          </div>
      </BaseCard>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import { useDateFormat } from '@vueuse/core'

const sessions = ref([])
const loading = ref(false)
const search = ref('')

const fetchSessions = async () => {
    loading.value = true
    try {
        // In real app, pass search params
        const res = await axios.get('/api/admin/sessions', {
            params: { limit: 50 }
        })
        sessions.value = res.data
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const formatDate = (dateStr) => {
    return useDateFormat(dateStr, 'MM-DD HH:mm').value
}

onMounted(fetchSessions)
</script>

<style lang="scss" scoped>
.header-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.table-container {
    overflow-x: auto;
}

.data-table {
    width: 100%;
    border-collapse: collapse;

    th {
        text-align: left;
        padding: 1rem;
        background-color: #F8FAFC;
        border-bottom: 2px solid $border-color;
        color: $text-muted;
        font-weight: 600;
        font-size: 0.85rem;
    }

    td {
        padding: 1rem;
        border-bottom: 1px solid $border-color;
        color: $text-main;
        font-size: 0.95rem;
    }

    .font-mono {
        font-family: monospace;
        color: $primary-color;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        
        &.active { background: #DCFCE7; color: #166534; } // Green
        &.ended { background: #F1F5F9; color: #64748B; } // Gray
    }
    
    .btn-sm {
        padding: 0.25rem 0.75rem;
        font-size: 0.85rem;
    }
}
</style>
