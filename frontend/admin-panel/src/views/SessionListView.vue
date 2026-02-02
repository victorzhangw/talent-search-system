
<template>
  <div class="session-list">
      <div class="header-section">
          <h2>對話紀錄管理 (Session Management)</h2>
          <div class="filters">
              <div class="date-group">
                  <input type="date" v-model="startDate" class="date-input" placeholder="Start Date">
                  <span class="sep">至</span>
                  <input type="date" v-model="endDate" class="date-input" placeholder="End Date">
              </div>
              <BaseInput v-model="search" placeholder="輸入使用者 ID..." />
              <BaseButton @click="fetchSessions">搜尋</BaseButton>
          </div>
      </div>

      <BaseCard>
          <div class="table-container">
            <div v-if="loading" class="loading-state">讀取中...</div>
            <table v-else class="data-table">
                <thead>
                    <tr>
                        <th>對話 ID</th>
                        <th>使用者 ID</th>
                        <th>狀態</th>
                        <th>訊息數</th>
                        <th>Tokens (消耗)</th>
                        <th>最後活動時間</th>
                        <th>操作</th>
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
                                <BaseButton variant="secondary" class="btn-sm">查看內容</BaseButton>
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
import { useRoute } from 'vue-router'
import axios from 'axios'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import { useDateFormat } from '@vueuse/core'

const route = useRoute()
const sessions = ref([])
const loading = ref(false)
const search = ref('')
// Default to Taiwan/Local today (YYYY-MM-DD)
const today = new Date().toLocaleDateString('en-CA')
const startDate = ref(today)
const endDate = ref(today)

const fetchSessions = async () => {
    loading.value = true
    try {
        const params = { limit: 50 }
        if (search.value) params.user_id = search.value
        if (startDate.value) params.start_date = startDate.value
        if (endDate.value) params.end_date = endDate.value
        
        const res = await axios.get('/api/admin/sessions', { params })
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

onMounted(() => {
    // Initialize from query params if present
    if (route.query.user_id) search.value = route.query.user_id
    if (route.query.start_date) startDate.value = route.query.start_date
    if (route.query.end_date) endDate.value = route.query.end_date
    
    fetchSessions()
})
</script>

<style lang="scss" scoped>
.header-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.filters {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.date-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: white;
    padding: 0.25rem;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

.date-input {
    border: none;
    padding: 0.5rem;
    border-radius: 4px;
    font-family: inherit;
    outline: none;
    color: #475569;
}

.sep {
    color: #94a3b8;
    font-size: 0.9rem;
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
