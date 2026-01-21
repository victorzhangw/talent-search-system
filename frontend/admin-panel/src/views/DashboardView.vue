
<template>
  <div class="dashboard">
     <div class="header-section">
         <h2>數據總覽</h2>
         <div class="controls">
             <BaseButton variant="secondary">下載報表</BaseButton>
         </div>
     </div>

     <div class="stats-grid">
         <BaseCard title="本月對話數">
            <div class="stat-content">
                 <div class="stat-value">{{ stats.total_sessions }}</div>
                 <div class="stat-trend text-primary">
                    <TrendingUp :size="16" /> +12%
                 </div>
            </div>
         </BaseCard>
         <BaseCard title="本月 Token 消耗">
             <div class="stat-content">
                 <div class="stat-value">{{ (stats.total_tokens / 1000).toFixed(1) }}k</div>
                 <div class="stat-label">已消耗</div>
            </div>
         </BaseCard>
         <BaseCard title="昨日活躍人數">
             <div class="stat-content">
                 <div class="stat-value">{{ stats.active_users_yesterday }}</div>
                 <div class="stat-label">人數</div>
            </div>
         </BaseCard>
         <BaseCard title="本月訊息數">
             <div class="stat-content">
                 <div class="stat-value">{{ stats.total_messages }}</div>
            </div>
         </BaseCard>
     </div>

     <div class="charts-section">
         <BaseCard title="Token 消耗趨勢">
             <TokenChart :data="stats.token_trend || []" />
         </BaseCard>
     </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import TokenChart from '@/components/charts/TokenChart.vue'
import { TrendingUp } from 'lucide-vue-next'

const stats = ref({
    total_sessions: 0,
    total_tokens: 0,
    active_users_yesterday: 0,
    total_messages: 0,
    token_trend: []
})



onMounted(async () => {
    try {
        const res = await axios.get('/api/admin/stats')
        stats.value = res.data
    } catch (e) {
        console.error("Failed to fetch stats", e)
    }
})
</script>

<style lang="scss" scoped>
.dashboard {
    .header-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;

        h2 { margin: 0; font-size: 1.5rem; }
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;

        .stat-content {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            
            .stat-value {
                font-size: 2rem;
                font-weight: 700;
                color: $text-main;
            }

            .stat-trend {
                font-size: 0.9rem;
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }
            
            .stat-label {
                color: $text-muted;
                font-size: 0.9rem;
            }
        }
    }

    .charts-section {
        margin-bottom: 2rem;
    }
}
</style>
