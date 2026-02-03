<template>
  <div class="feature-radar-chart" ref="chartRef"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue';
import * as echarts from 'echarts';

// Props
const props = defineProps({
  modelScores: {
    type: Array,
    default: () => [],
    // Expected format: [{ model_name, display_name, language_score, domain_score, multimodal_score }]
  },
  showLegend: {
    type: Boolean,
    default: true,
  },
  height: {
    type: String,
    default: '300px',
  },
});

// Refs
const chartRef = ref(null);
let chartInstance = null;

// Dimension labels
const dimensions = [
  { key: 'language_score', label: '语言匹配' },
  { key: 'domain_score', label: '领域专长' },
  { key: 'multimodal_score', label: '多模态支持' },
];

// Color palette for models
const colors = [
  '#0052D9', // Primary blue
  '#2BA471', // Green
  '#E37318', // Orange
  '#D54941', // Red
  '#8C50D9', // Purple
];

// Initialize chart
const initChart = () => {
  if (!chartRef.value) return;
  
  // Destroy existing instance
  if (chartInstance) {
    chartInstance.dispose();
  }
  
  chartInstance = echarts.init(chartRef.value);
  updateChart();
};

// Update chart with data
const updateChart = () => {
  if (!chartInstance || !props.modelScores.length) return;
  
  const indicator = dimensions.map(d => ({
    name: d.label,
    max: 1,
  }));
  
  const series = props.modelScores.map((model, index) => ({
    value: dimensions.map(d => model[d.key] || 0),
    name: model.display_name || model.model_name,
    lineStyle: {
      width: 2,
    },
    areaStyle: {
      opacity: 0.1,
    },
    itemStyle: {
      color: colors[index % colors.length],
    },
  }));
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (!params.data) return '';
        const values = params.data.value;
        let html = `<strong>${params.name}</strong><br/>`;
        dimensions.forEach((d, i) => {
          html += `${d.label}: ${(values[i] * 100).toFixed(0)}%<br/>`;
        });
        return html;
      },
    },
    legend: props.showLegend ? {
      type: 'scroll',
      bottom: 0,
      data: props.modelScores.map(m => m.display_name || m.model_name),
      textStyle: {
        fontSize: 12,
      },
    } : undefined,
    radar: {
      indicator,
      shape: 'polygon',
      splitNumber: 4,
      radius: props.showLegend ? '65%' : '75%',
      center: props.showLegend ? ['50%', '45%'] : ['50%', '50%'],
      axisName: {
        color: '#666',
        fontSize: 12,
      },
      splitLine: {
        lineStyle: {
          color: '#ddd',
        },
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(0, 82, 217, 0.02)', 'rgba(0, 82, 217, 0.04)'],
        },
      },
      axisLine: {
        lineStyle: {
          color: '#ddd',
        },
      },
    },
    series: [{
      type: 'radar',
      data: series,
      symbol: 'circle',
      symbolSize: 6,
    }],
  };
  
  chartInstance.setOption(option);
};

// Handle resize
const handleResize = () => {
  chartInstance?.resize();
};

// Lifecycle
onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
});

// Watch for data changes
watch(() => props.modelScores, () => {
  updateChart();
}, { deep: true });

// Expose refresh method
defineExpose({
  refresh: updateChart,
  resize: handleResize,
});
</script>

<style scoped>
.feature-radar-chart {
  width: 100%;
  height: v-bind(height);
}
</style>
