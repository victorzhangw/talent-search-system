
<template>
  <div class="chart-container">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  data: {
    type: Array, // Array of { date: 'YYYY-MM-DD', tokens: 123 }
    default: () => []
  }
})

const chartData = computed(() => ({
  labels: props.data.map(d => d.date),
  datasets: [
    {
      label: 'Token Usage',
      backgroundColor: (ctx) => {
        const canvas = ctx.chart.ctx;
        const gradient = canvas.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(0, 220, 130, 0.4)'); // Primary Color
        gradient.addColorStop(1, 'rgba(0, 220, 130, 0.0)');
        return gradient;
      },
      borderColor: '#00DC82',
      pointBackgroundColor: '#00DC82',
      borderWidth: 2,
      fill: true,
      data: props.data.map(d => d.tokens),
      tension: 0.4
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { 
        mode: 'index', 
        intersect: false,
        backgroundColor: '#1E293B',
        titleColor: '#F8FAFC',
        bodyColor: '#F8FAFC',
        padding: 10,
        cornerRadius: 8
    }
  },
  scales: {
    x: { 
        grid: { display: false },
        ticks: { color: '#94A3B8' }
    },
    y: { 
        grid: { borderDash: [4, 4], color: '#E2E8F0' },
        ticks: { color: '#94A3B8' }
    }
  }
}
</script>

<style scoped>
.chart-container {
  height: 300px;
  width: 100%;
}
</style>
