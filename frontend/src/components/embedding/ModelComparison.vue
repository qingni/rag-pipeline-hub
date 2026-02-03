<template>
  <div class="model-comparison">
    <!-- 标题 -->
    <div class="comparison-header">
      <h3>模型对比</h3>
      <el-tooltip content="比较不同模型的向量化结果" placement="top">
        <el-icon class="info-icon"><InfoFilled /></el-icon>
      </el-tooltip>
    </div>
    
    <!-- 模型选择 -->
    <div class="model-selector">
      <div class="selector-item" v-for="(model, index) in selectedModels" :key="index">
        <el-select
          v-model="selectedModels[index]"
          placeholder="选择模型"
          clearable
          @change="onModelChange(index)"
        >
          <el-option
            v-for="m in availableModels"
            :key="m.name"
            :label="m.display_name || m.name"
            :value="m.name"
            :disabled="selectedModels.includes(m.name) && selectedModels[index] !== m.name"
          />
        </el-select>
        <el-button
          v-if="index > 1"
          type="danger"
          text
          size="small"
          @click="removeModel(index)"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <el-button
        v-if="selectedModels.length < 4"
        type="primary"
        text
        @click="addModel"
      >
        <el-icon><Plus /></el-icon>
        添加模型
      </el-button>
    </div>
    
    <!-- 对比结果 -->
    <div class="comparison-results" v-if="comparisonData.length > 0">
      <!-- 维度对比 -->
      <div class="dimension-comparison">
        <div class="comparison-item" v-for="model in comparisonData" :key="model.name">
          <div class="model-name">{{ model.display_name }}</div>
          <div class="dimension">
            <span class="label">维度</span>
            <span class="value">{{ model.dimension }}</span>
          </div>
        </div>
      </div>
      
      <!-- 雷达图对比 -->
      <div class="radar-comparison" ref="radarChartRef"></div>
      
      <!-- 详细对比表格 -->
      <el-table :data="comparisonTableData" stripe size="small" class="comparison-table">
        <el-table-column prop="metric" label="指标" width="120" />
        <el-table-column
          v-for="model in comparisonData"
          :key="model.name"
          :prop="model.name"
          :label="model.display_name"
          align="center"
        >
          <template #default="{ row }">
            <span :class="getBestClass(row, model.name)">
              {{ row[model.name] }}
            </span>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 结果操作 -->
      <div class="result-actions" v-if="results.length > 0">
        <div class="result-item" v-for="result in results" :key="result.result_id">
          <div class="result-info">
            <span class="model-tag">{{ result.model }}</span>
            <span class="result-time">{{ formatTime(result.created_at) }}</span>
            <el-tag
              :type="result.is_active ? 'success' : 'info'"
              size="small"
              effect="light"
            >
              {{ result.is_active ? '活跃' : '历史' }}
            </el-tag>
          </div>
          <div class="result-actions-btns">
            <el-button
              v-if="!result.is_active"
              type="primary"
              text
              size="small"
              @click="$emit('activate', result.result_id)"
            >
              设为活跃
            </el-button>
            <el-button
              v-if="!result.is_active"
              type="danger"
              text
              size="small"
              @click="$emit('delete', result.result_id)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 空状态 -->
    <el-empty v-else description="请选择至少两个模型进行对比" :image-size="80" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { InfoFilled, Plus, Close } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps({
  /**
   * 可用模型列表
   */
  availableModels: {
    type: Array,
    default: () => [],
  },
  /**
   * 向量化结果列表
   */
  results: {
    type: Array,
    default: () => [],
  },
  /**
   * 模型能力数据
   */
  modelCapabilities: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['compare', 'activate', 'delete'])

// 状态
const selectedModels = ref(['', ''])
const comparisonData = ref([])
const radarChartRef = ref(null)
let radarChart = null

// 计算对比表格数据
const comparisonTableData = computed(() => {
  if (comparisonData.value.length === 0) return []
  
  const metrics = [
    { key: 'dimension', label: '向量维度' },
    { key: 'language_zh', label: '中文支持' },
    { key: 'language_en', label: '英文支持' },
    { key: 'domain_tech', label: '技术领域' },
    { key: 'domain_business', label: '商业领域' },
    { key: 'multimodal', label: '多模态支持' },
  ]
  
  return metrics.map(m => {
    const row = { metric: m.label }
    comparisonData.value.forEach(model => {
      if (m.key === 'dimension') {
        row[model.name] = model.dimension
      } else if (m.key.startsWith('language_')) {
        const lang = m.key.replace('language_', '')
        const score = model.language_scores?.[lang] || 0
        row[model.name] = formatScore(score)
      } else if (m.key.startsWith('domain_')) {
        const domain = m.key.replace('domain_', '')
        const score = model.domain_scores?.[domain] || 0
        row[model.name] = formatScore(score)
      } else if (m.key === 'multimodal') {
        row[model.name] = formatScore(model.multimodal_score || 0)
      }
    })
    return row
  })
})

// 方法
function addModel() {
  if (selectedModels.value.length < 4) {
    selectedModels.value.push('')
  }
}

function removeModel(index) {
  selectedModels.value.splice(index, 1)
  updateComparison()
}

function onModelChange(index) {
  updateComparison()
}

function updateComparison() {
  const selected = selectedModels.value.filter(m => m)
  if (selected.length < 2) {
    comparisonData.value = []
    return
  }
  
  // 获取模型能力数据
  comparisonData.value = selected.map(modelName => {
    const capability = props.modelCapabilities[modelName] || {}
    const modelInfo = props.availableModels.find(m => m.name === modelName) || {}
    return {
      name: modelName,
      display_name: modelInfo.display_name || modelName,
      dimension: modelInfo.dimension || capability.dimension || 0,
      language_scores: capability.language_scores || {},
      domain_scores: capability.domain_scores || {},
      multimodal_score: capability.multimodal_score || 0,
    }
  })
  
  emit('compare', selected)
  nextTick(() => updateRadarChart())
}

function updateRadarChart() {
  if (!radarChartRef.value || comparisonData.value.length === 0) return
  
  if (!radarChart) {
    radarChart = echarts.init(radarChartRef.value)
  }
  
  const indicators = [
    { name: '中文支持', max: 1 },
    { name: '英文支持', max: 1 },
    { name: '技术领域', max: 1 },
    { name: '商业领域', max: 1 },
    { name: '多模态', max: 1 },
  ]
  
  const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d']
  
  const series = comparisonData.value.map((model, index) => ({
    name: model.display_name,
    value: [
      model.language_scores?.zh || 0,
      model.language_scores?.en || 0,
      model.domain_scores?.tech || 0,
      model.domain_scores?.business || 0,
      model.multimodal_score || 0,
    ],
    itemStyle: { color: colors[index % colors.length] },
    areaStyle: { opacity: 0.2 },
  }))
  
  radarChart.setOption({
    tooltip: {},
    legend: {
      data: comparisonData.value.map(m => m.display_name),
      bottom: 0,
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#666',
        fontSize: 12,
      },
    },
    series: [{
      type: 'radar',
      data: series,
    }],
  })
}

function formatScore(score) {
  return `${(score * 100).toFixed(0)}%`
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getBestClass(row, modelName) {
  const values = comparisonData.value.map(m => {
    const val = row[m.name]
    if (typeof val === 'string' && val.endsWith('%')) {
      return parseFloat(val)
    }
    return parseFloat(val) || 0
  })
  
  const maxVal = Math.max(...values)
  const currentVal = row[modelName]
  const numericVal = typeof currentVal === 'string' && currentVal.endsWith('%')
    ? parseFloat(currentVal)
    : parseFloat(currentVal) || 0
  
  return numericVal === maxVal ? 'best-value' : ''
}

// 监听
watch(() => props.modelCapabilities, () => {
  updateComparison()
}, { deep: true })

onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.model-comparison {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  padding: 20px;
}

.comparison-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.comparison-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.info-icon {
  color: #8c8c8c;
  cursor: help;
}

/* 模型选择器 */
.model-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.selector-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-item .el-select {
  width: 200px;
}

/* 维度对比 */
.dimension-comparison {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.comparison-item {
  flex: 1;
  background: linear-gradient(135deg, #f0f5ff 0%, #fff 100%);
  border: 1px solid #d6e4ff;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.model-name {
  font-weight: 600;
  margin-bottom: 8px;
  color: #1890ff;
}

.dimension {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dimension .label {
  font-size: 12px;
  color: #8c8c8c;
}

.dimension .value {
  font-size: 24px;
  font-weight: 700;
  color: #262626;
}

/* 雷达图 */
.radar-comparison {
  width: 100%;
  height: 300px;
  margin-bottom: 20px;
}

/* 对比表格 */
.comparison-table {
  margin-bottom: 20px;
}

.best-value {
  color: #52c41a;
  font-weight: 600;
}

/* 结果操作 */
.result-actions {
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  margin-bottom: 8px;
}

.result-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-tag {
  font-weight: 500;
  color: #1890ff;
}

.result-time {
  font-size: 12px;
  color: #8c8c8c;
}

.result-actions-btns {
  display: flex;
  gap: 8px;
}
</style>
