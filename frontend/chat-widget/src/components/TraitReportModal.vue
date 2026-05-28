<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="report-modal">
      <div class="modal-header">
        <h3>{{ candidateName }} - 特質報告</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>
      
      <div class="modal-body">
        <div v-if="loading" class="loading-state">
            讀取中...
        </div>
        <div v-else-if="error" class="error-text">
            {{ error }}
        </div>
        <div v-else class="trait-table-container">
           
            <table class="trait-table">
                <thead>
                    <tr>
                        <th>特質名稱 (Trait)</th>
                        <th>分數 (Score)</th>
                        <th>強度 (Level)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="trait in traits" :key="trait.name">
                        <!-- Use Chinese Name if available, otherwise fallback (handled in fetch) -->
                        <td class="trait-name">{{ trait.name }}</td>
                        <td>
                            <div class="score-bar-container">
                                <span>{{ trait.score }}</span>
                                <div class="score-bar-bg">
                                    <div class="score-bar-fill" :style="{ width: trait.score + '%' }"></div>
                                </div>
                            </div>
                        </td>
                        <td>
                            <span class="badged-text">{{ getBandLabel(trait.score) }}</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const props = defineProps({
    candidateId: [String, Number],
    candidateName: String,
    token: String
})

const emit = defineEmits(['close'])

const traits = ref([])
const assessmentDate = ref('')
const loading = ref(true)
const error = ref('')

// Utility to approximate band if missing
const getBandLabel = (score) => {
    if (score >= 75) return 'High';
    if (score <= 25) return 'Low';
    return 'Mid';
}

onMounted(async () => {
    console.log("TraitReportModal Mounted. ID:", props.candidateId, "Token:", props.token ? "Yes" : "No")
    
    // Try to load from Session Storage first
    try {
        const cachedReports = sessionStorage.getItem('traitty_batch_reports')
        if (cachedReports) {
            const reportsMap = JSON.parse(cachedReports)
            const cachedReport = reportsMap[props.candidateId]
            
            if (cachedReport) {
                console.log('[TraitReportModal] Using cached report for candidate', props.candidateId)
                traits.value = cachedReport.traits || []
                assessmentDate.value = cachedReport.assessment_date || ''
                loading.value = false
                return  // Exit early, no need to fetch from API
            }
        }
    } catch (e) {
        console.warn('[TraitReportModal] Failed to load from cache:', e)
    }
    
    // Fallback: Fetch from API if not in cache
    console.log('[TraitReportModal] Cache miss, fetching from API...')
    try {
        const res = await fetch(`http://localhost:5000/api/v2/candidates/${props.candidateId}/report`, {
            headers: { 'Authorization': `Bearer ${props.token}` }
        })
        if (!res.ok) throw new Error('Fetch failed')
        const resp = await res.json()
        if (!resp.success) throw new Error(resp.error?.message || 'Fetch failed')
        traits.value = resp.data.traits
        assessmentDate.value = resp.data.assessment_date
    } catch (e) {
        error.value = "無法載入報告數據"
    } finally {
        loading.value = false
    }
})
</script>

<style scoped>
.modal-backdrop {
    position: absolute; /* Changed from fixed to absolute to stay within ChatContainer */
    top: 0;
    left: 0;
    width: 100%; /* Changed from 100vw to 100% of parent */
    height: 100%; /* Changed from 100vh to 100% of parent */
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
}

.report-modal {
    background: var(--surface-color, #ffffff);
    [data-theme="midnight"] & {
        background: rgba(30, 30, 40, 0.98);
    }
    width: 600px;
    max-width: 90%;
    max-height: 80vh;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: inherit;
    color: var(--glass-text-primary, #333);
    border: 1px solid var(--glass-border);
}


.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.8rem 1rem; /* Reduced padding */
    border-bottom: 1px solid var(--glass-border, #eee);
    background: rgba(127, 127, 127, 0.05);
}

.modal-header h3 {
    margin: 0;
    font-size: 1rem; /* Smaller font */
    color: var(--glass-text-primary, #2c3e50);
    font-weight: 600;
}

.close-btn {
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    color: #999;
}

.modal-body {
    padding: 1rem;
    overflow-y: auto;
}

.loading-state, .error-text {
    text-align: center;
    padding: 2rem;
    color: var(--glass-text-secondary, #666);
}

.meta-row {
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    color: #666;
    text-align: right;
}

.trait-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}

.trait-table th {
    text-align: left;
    padding: 0.4rem 0.5rem; /* Compact padding */
    border-bottom: 2px solid var(--glass-border, #eee);
    color: var(--glass-text-secondary, #555);
    font-weight: 600;
    font-size: 12px; /* Smaller font */
}

.trait-table td {
    padding: 0.25rem 0.5rem; /* Very compact padding */
    border-bottom: 1px dashed var(--glass-border, #f5f5f5);
    vertical-align: middle;
}

.trait-table td.trait-name {
    font-size: 12px;
    font-weight: 500;
}

.score-bar-container {
    display: flex;
    align-items: center;
    gap: 8px;
}

.score-bar-container span {
    width: 25px;
    text-align: right;
    font-weight: bold;
    color: #f97316;
    font-size: 12px;
}

.score-bar-bg {
    flex: 1;
    height: 6px; /* Thinner bar */
    background: #ffe4d6; /* Light orange bg */
    border-radius: 3px;
    overflow: hidden;
    min-width: 80px;
}

.score-bar-fill {
    height: 100%;
    background: #f97316; /* Match score color */
    border-radius: 3px;
}

.badged-text {
    background: rgba(127, 127, 127, 0.1);
    padding: 1px 12px;
    border-radius: 10px;
    font-size: 0.75rem;
    color: var(--glass-text-secondary, #555);
}
</style>
