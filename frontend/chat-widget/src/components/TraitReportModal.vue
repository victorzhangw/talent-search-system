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
            <div class="meta-row">
                <span>測評日期: {{ assessmentDate }}</span>
            </div>
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
                        <td>{{ trait.name }}</td>
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
    candidateId: String,
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
    try {
        const res = await fetch(`http://localhost:5000/api/v2/candidates/${props.candidateId}/report`, {
            headers: { 'Authorization': `Bearer ${props.token}` }
        })
        if (!res.ok) throw new Error('Fetch failed')
        const data = await res.json()
        traits.value = data.traits
        assessmentDate.value = data.assessment_date
    } catch (e) {
        error.value = "無法載入報告數據"
    } finally {
        loading.value = false
    }
})
</script>

<style scoped>
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
}

.report-modal {
    background: white; /* Clean white for business look */
    width: 600px;
    max-width: 90%;
    max-height: 80vh;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: 'Segoe UI', sans-serif;
    color: #333;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #eee;
    background: #f8f9fa;
}

.modal-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #2c3e50;
    font-weight: 600;
}

.close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #999;
}

.modal-body {
    padding: 1.5rem;
    overflow-y: auto;
}

.loading-state, .error-text {
    text-align: center;
    padding: 2rem;
    color: #666;
}

.meta-row {
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: #666;
    text-align: right;
}

.trait-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.trait-table th {
    text-align: left;
    padding: 0.8rem;
    border-bottom: 2px solid #eee;
    color: #555;
    font-weight: 600;
}

.trait-table td {
    padding: 0.8rem;
    border-bottom: 1px solid #f5f5f5;
    vertical-align: middle;
}

.score-bar-container {
    display: flex;
    align-items: center;
    gap: 10px;
}

.score-bar-container span {
    width: 25px;
    text-align: right;
    font-weight: bold;
    color: #444;
}

.score-bar-bg {
    flex: 1;
    height: 8px;
    background: #eee;
    border-radius: 4px;
    overflow: hidden;
    min-width: 100px;
}

.score-bar-fill {
    height: 100%;
    background: #4f46e5; /* Professional Indigo */
    border-radius: 4px;
}

.badged-text {
    background: #f3f4f6;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
    color: #555;
}
</style>
