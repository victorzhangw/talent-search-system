<template>
  <div class="user-reports">
      <div class="header-section">
          <h2>使用者用量報告 (User Reports)</h2>
          <div class="filters">
              <div class="date-group">
                  <input type="date" v-model="startDate" class="date-input" placeholder="Start Date">
                  <span class="sep">to</span>
                  <input type="date" v-model="endDate" class="date-input" placeholder="End Date">
              </div>
              <BaseButton @click="fetchReport" :disabled="loading">Search</BaseButton>
          </div>
      </div>

      <div class="stats-grid" v-if="stats">
          <div class="stat-card">
              <h3>Total Users</h3>
              <div class="value">{{ stats.length }}</div>
          </div>
          <div class="stat-card">
              <h3>Total Tokens</h3>
              <div class="value">{{ totalTokens.toLocaleString() }}</div>
          </div>
      </div>

      <BaseCard class="mt-4">
          <div class="table-container">
            <div v-if="loading" class="loading-state">Loading...</div>
            <table v-else class="data-table">
                <thead>
                    <tr>
                        <th>User ID (Email)</th>
                        <th>Sessions</th>
                        <th>Total Tokens</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in stats" :key="row.user_id">
                        <td>{{ row.user_id }}</td>
                        <td>{{ row.session_count }}</td>
                        <td>{{ row.total_tokens.toLocaleString() }}</td>
                        <td>
                            <BaseButton 
                                variant="secondary" 
                                class="btn-sm" 
                                @click="viewSessions(row.user_id)"
                            >
                                View Sessions
                            </BaseButton>
                        </td>
                    </tr>
                    <tr v-if="stats.length === 0">
                        <td colspan="4" class="text-center">No data found for selected period.</td>
                    </tr>
                </tbody>
            </table>
          </div>
      </BaseCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseButton from '@/components/base/BaseButton.vue'

const router = useRouter()
const loading = ref(false)
const stats = ref([])
// Default to Taiwan/Local today (YYYY-MM-DD)
const today = new Date().toLocaleDateString('en-CA')
const startDate = ref(today)
const endDate = ref(today)

const totalTokens = computed(() => {
    return stats.value.reduce((acc, curr) => acc + curr.total_tokens, 0)
})

const fetchReport = async () => {
    loading.value = true
    try {
        const params = {}
        if (startDate.value) params.start_date = startDate.value
        if (endDate.value) params.end_date = endDate.value
        
        const res = await axios.get('/api/admin/reports/users-usage', { params })
        stats.value = res.data
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const viewSessions = (userId) => {
    // Navigate to Session List with filters
    router.push({
        path: '/sessions',
        query: {
            user_id: userId,
            start_date: startDate.value,
            end_date: endDate.value
        }
    })
}

onMounted(() => {
    // Default to this month? Or just fetch all.
    fetchReport()
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

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.stat-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    
    h3 {
        font-size: 0.9rem;
        color: #64748B;
        margin: 0 0 0.5rem 0;
    }
    
    .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: $primary-color;
    }
}

.mt-4 {
    margin-top: 1rem;
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
        border-bottom: 2px solid #e2e8f0; // fallback
        color: #64748B; // fallback
        font-weight: 600;
        font-size: 0.85rem;
    }

    td {
        padding: 1rem;
        border-bottom: 1px solid #e2e8f0;
        color: #1e293b;
        font-size: 0.95rem;
    }
    
    .text-center { text-align: center; color: #94a3b8; }
    
    .btn-sm {
        padding: 0.25rem 0.75rem;
        font-size: 0.85rem;
    }
}
</style>
