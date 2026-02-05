<template>
  <div class="embedding-results">
    <template v-if="!result">
      <div class="empty-state">
        <Zap :size="48" class="empty-icon" />
        <p class="empty-text">暂无向量化结果</p>
        <p class="empty-hint">选择文档和模型后点击"开始向量化"</p>
      </div>
    </template>
    
    <template v-else>
      <!-- 顶部信息区 - 水平布局 -->
      <div class="top-info-row">
        <!-- 文档来源信息 - 精简版 -->
        <div class="source-info horizontal">
          <div class="source-header">
            <FileText :size="18" class="header-icon" />
            <span class="header-text">文档来源</span>
          </div>
          <div class="info-inline">
            <span class="info-value filename" :title="result.documentInfo?.filename || '未知'">{{ result.documentInfo?.filename || '未知' }}</span>
            <span class="info-divider">|</span>
            <span class="info-tag"><span class="info-label">维度</span>{{ result.metadata?.model_dimension || 0 }}</span>
            <span class="info-divider">|</span>
            <span class="info-tag"><span class="info-label">耗时</span>{{ formatDuration(result.metadata?.processing_time_ms) }}</span>
          </div>
        </div>
        
        <!-- 处理结果摘要 - 水平布局 -->
        <div class="result-summary horizontal" :class="statusClass">
          <div class="summary-left">
            <component :is="statusIcon" :size="18" class="status-icon" />
            <span class="summary-title">{{ statusTitle }}</span>
            <div class="summary-stats">
              <div class="stat-badge success">
                <CheckCircle2 :size="12" />
                <span>{{ result.metadata?.successful_count || 0 }}</span>
              </div>
              <div class="stat-badge" :class="{ 'error': result.metadata?.failed_count > 0, 'neutral': result.metadata?.failed_count === 0 }">
                <XCircle :size="12" />
                <span>{{ result.metadata?.failed_count || 0 }}</span>
              </div>
            </div>
          </div>
          <div class="summary-right">
            <span class="detail-tag"><span class="detail-label">模型</span>{{ result.metadata?.model }}</span>
            <span class="detail-tag highlight"><span class="detail-label">速度</span>{{ result.metadata?.vectors_per_second?.toFixed(2) }} 个/秒</span>
            <span class="detail-tag" v-if="result.metadata?.retry_count > 0"><span class="detail-label">重试</span>{{ result.metadata?.retry_count }}</span>
          </div>
        </div>
      </div>
      
      <!-- 多模态向量统计 - 独立出来，仅在有多种类型时显示 -->
      <div v-if="hasMultimodalStats" class="multimodal-stats standalone">
        <div class="multimodal-header">多模态向量统计</div>
        <div class="multimodal-grid">
          <div class="multimodal-item" v-if="multimodalStats.text > 0">
            <span class="multimodal-icon">📝</span>
            <span class="multimodal-label">文本</span>
            <span class="multimodal-value">{{ multimodalStats.text }}</span>
          </div>
          <div class="multimodal-item" v-if="multimodalStats.table > 0">
            <span class="multimodal-icon">📊</span>
            <span class="multimodal-label">表格</span>
            <span class="multimodal-value">{{ multimodalStats.table }}</span>
          </div>
          <div class="multimodal-item" v-if="multimodalStats.image > 0">
            <span class="multimodal-icon">🖼️</span>
            <span class="multimodal-label">图片</span>
            <span class="multimodal-value">{{ multimodalStats.image }}</span>
          </div>
          <div class="multimodal-item" v-if="multimodalStats.code > 0">
            <span class="multimodal-icon">💻</span>
            <span class="multimodal-label">代码</span>
            <span class="multimodal-value">{{ multimodalStats.code }}</span>
          </div>
        </div>
      </div>
      
      <!-- 向量列表 -->
      <div v-if="result.vectors && result.vectors.length > 0" class="vectors-section">
        <div class="vectors-header">
          <h3 class="section-title">
            向量列表 
            <span class="count-badge">{{ result.vectors.length }}</span>
          </h3>
          <div class="vectors-controls">
            <t-button 
              size="small" 
              variant="outline" 
              @click="viewMode = viewMode === 'compact' ? 'detailed' : 'compact'"
            >
              {{ viewMode === 'compact' ? '详细视图' : '紧凑视图' }}
            </t-button>
            <t-button 
              size="small" 
              variant="outline" 
              @click="downloadVectors($event)"
            >
              <Download :size="14" />
              导出向量
            </t-button>
          </div>
        </div>

        <!-- 统计信息卡片 -->
        <div class="vectors-stats">
          <div class="stat-item">
            <span class="stat-label">平均长度</span>
            <span class="stat-value">{{ getAvgTextLength() }} 字符</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">向量维度</span>
            <span class="stat-value">{{ result.vectors[0]?.dimension || 0 }} 维</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">平均处理时间</span>
            <span class="stat-value">{{ getAvgProcessingTime() }}ms</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">总向量数</span>
            <span class="stat-value highlight">{{ result.vectors.length }}</span>
          </div>
        </div>
        
        <div class="vectors-list">
          <div
            v-for="(vector, idx) in paginatedVectors"
            :key="vector.index"
            class="vector-item"
            :class="{ 'compact': viewMode === 'compact' }"
          >
            <div class="vector-header">
              <div class="vector-title">
                <span class="vector-index">#{{ vector.index }}</span>
                <span class="vector-meta">
                  {{ vector.text_length }} 字符 · 
                  {{ formatDuration(vector.processing_time_ms) }}
                </span>
              </div>
              <t-button 
                size="small" 
                variant="text" 
                @click="toggleVectorExpand(idx, $event)"
              >
                {{ expandedVectors.has(idx) ? '收起' : '展开' }}
              </t-button>
            </div>
            
            <!-- 原始文本显示（新增） -->
            <div v-if="vector.source_text" class="source-text-preview">
              <div class="source-text-label">原始分块文本</div>
              <div class="source-text-content" :class="{ 'expanded': expandedSourceTexts.has(idx) }">
                {{ vector.source_text }}
              </div>
              <t-button 
                v-if="vector.source_text.length > 100"
                size="small" 
                variant="text"
                class="source-text-toggle"
                @click="toggleSourceText(idx, $event)"
              >
                {{ expandedSourceTexts.has(idx) ? '收起' : '展开全文' }}
              </t-button>
            </div>
            
            <!-- 向量可视化（热力图） -->
            <div v-if="viewMode === 'detailed'" class="vector-heatmap">
              <div class="heatmap-label">向量值分布</div>
              <div class="heatmap-container">
                <div 
                  v-for="(val, i) in vector.vector.slice(0, 50)"
                  :key="i"
                  class="heatmap-cell"
                  :style="{ backgroundColor: getHeatmapColor(val) }"
                  :title="`位置 ${i}: ${val.toFixed(4)}`"
                />
                <span v-if="vector.vector.length > 50" class="heatmap-more">
                  +{{ vector.vector.length - 50 }} 维
                </span>
              </div>
            </div>

            <!-- 向量统计 -->
            <div class="vector-stats" :class="{ 'compact': viewMode === 'compact' }">
              <div class="stat-chip">
                <span class="stat-chip-label">均值</span>
                <span class="stat-chip-value">{{ calculateMean(vector.vector).toFixed(4) }}</span>
              </div>
              <div class="stat-chip">
                <span class="stat-chip-label">方差</span>
                <span class="stat-chip-value">{{ calculateVariance(vector.vector).toFixed(4) }}</span>
              </div>
              <div class="stat-chip">
                <span class="stat-chip-label">L2范数</span>
                <span class="stat-chip-value">{{ calculateNorm(vector.vector).toFixed(4) }}</span>
              </div>
              <div class="stat-chip">
                <span class="stat-chip-label">非零率</span>
                <span class="stat-chip-value">{{ (calculateSparsity(vector.vector) * 100).toFixed(1) }}%</span>
              </div>
            </div>

            <!-- 原始向量值（可展开） -->
            <div v-if="expandedVectors.has(idx)" class="vector-raw-data">
              <div class="raw-data-header">
                <span class="raw-data-label">原始向量值</span>
                <t-button 
                  size="small" 
                  variant="text" 
                  @click="copyVector(vector.vector, $event)"
                >
                  <Copy :size="14" />
                  复制
                </t-button>
              </div>
              <div class="raw-data-content">
                {{ JSON.stringify(vector.vector, null, 2) }}
              </div>
            </div>
          </div>
        </div>

        <!-- 分页控制 -->
        <div v-if="result.vectors.length > pageSize" class="pagination-controls">
          <t-button 
            size="small" 
            variant="outline"
            :disabled="currentPage === 1"
            @click="currentPage--"
          >
            上一页
          </t-button>
          <span class="pagination-info">
            第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
            (显示 {{ paginatedVectors.length }} / {{ result.vectors.length }} 个)
          </span>
          <t-button 
            size="small" 
            variant="outline"
            :disabled="currentPage === totalPages"
            @click="currentPage++"
          >
            下一页
          </t-button>
        </div>
      </div>
      
      <!-- 失败列表 -->
      <div v-if="result.failures && result.failures.length > 0" class="failures-section">
        <h3 class="section-title error">
          <AlertCircle :size="18" />
          失败记录
          <span class="count-badge error">{{ result.failures.length }}</span>
        </h3>
        <div class="failures-list">
          <div
            v-for="failure in result.failures"
            :key="failure.index"
            class="failure-item"
          >
            <div class="failure-header">
              <span class="failure-index">#{{ failure.index }}</span>
              <span class="failure-type">{{ failure.error_type }}</span>
            </div>
            <p class="failure-message">{{ failure.error_message }}</p>
            <div class="failure-meta">
              <span>重试 {{ failure.retry_count }} 次</span>
              <span v-if="failure.retry_recommended" class="retry-badge">建议重试</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { 
  FileText, Zap, CheckCircle2, AlertCircle, XCircle, Download, Copy
} from 'lucide-vue-next'

const props = defineProps({
  result: {
    type: Object,
    default: null
  }
})

// 视图状态
const viewMode = ref('detailed') // 'compact' | 'detailed'
const expandedVectors = ref(new Set())
const expandedSourceTexts = ref(new Set())  // Track which source texts are expanded
const currentPage = ref(1)
const pageSize = ref(10)

const statusClass = computed(() => {
  if (!props.result) return ''
  const status = props.result.status
  if (status === 'SUCCESS') return 'status-success'
  if (status === 'PARTIAL_SUCCESS') return 'status-warning'
  if (status === 'FAILED') return 'status-error'
  return ''
})

const statusIcon = computed(() => {
  if (!props.result) return null
  const status = props.result.status
  if (status === 'SUCCESS') return CheckCircle2
  if (status === 'PARTIAL_SUCCESS') return AlertCircle
  if (status === 'FAILED') return XCircle
  return null
})

const statusTitle = computed(() => {
  if (!props.result) return ''
  const status = props.result.status
  if (status === 'SUCCESS') return '向量化成功'
  if (status === 'PARTIAL_SUCCESS') return '部分成功'
  if (status === 'FAILED') return '向量化失败'
  return ''
})

const statusSubtitle = computed(() => {
  if (!props.result?.metadata) return ''
  const { successful_count, failed_count } = props.result.metadata
  return `成功 ${successful_count} 个，失败 ${failed_count} 个`
})

// 多模态向量统计
const multimodalStats = computed(() => {
  const stats = { text: 0, table: 0, image: 0, code: 0 }
  if (!props.result?.vectors) return stats
  
  props.result.vectors.forEach(v => {
    const chunkType = v.chunk_type || 'text'
    if (chunkType === 'text') stats.text++
    else if (chunkType === 'table') stats.table++
    else if (chunkType === 'image') stats.image++
    else if (chunkType === 'code') stats.code++
    else stats.text++  // 默认归为文本
  })
  
  return stats
})

// 是否显示多模态统计（当存在多种类型或有非文本类型时显示）
const hasMultimodalStats = computed(() => {
  const stats = multimodalStats.value
  const typeCount = (stats.text > 0 ? 1 : 0) + (stats.table > 0 ? 1 : 0) + 
                    (stats.image > 0 ? 1 : 0) + (stats.code > 0 ? 1 : 0)
  return typeCount > 1 || stats.table > 0 || stats.image > 0 || stats.code > 0
})

function formatDuration(ms) {
  if (!ms) return '0ms'
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatVectorPreview(vector) {
  if (!vector || !Array.isArray(vector)) return ''
  const preview = vector.slice(0, 5).map(v => v.toFixed(4)).join(', ')
  return `[${preview}, ...]`
}

// 分页计算
const totalPages = computed(() => {
  if (!props.result?.vectors) return 0
  return Math.ceil(props.result.vectors.length / pageSize.value)
})

const paginatedVectors = computed(() => {
  if (!props.result?.vectors) return []
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return props.result.vectors.slice(start, end)
})

// 统计计算
function getAvgTextLength() {
  if (!props.result?.vectors?.length) return 0
  const sum = props.result.vectors.reduce((acc, v) => acc + v.text_length, 0)
  return Math.round(sum / props.result.vectors.length)
}

function getAvgProcessingTime() {
  if (!props.result?.vectors?.length) return 0
  const sum = props.result.vectors.reduce((acc, v) => acc + (v.processing_time_ms || 0), 0)
  return (sum / props.result.vectors.length).toFixed(2)
}

// 向量数学计算
function calculateMean(vector) {
  if (!vector?.length) return 0
  const sum = vector.reduce((a, b) => a + b, 0)
  return sum / vector.length
}

function calculateVariance(vector) {
  if (!vector?.length) return 0
  const mean = calculateMean(vector)
  const squaredDiffs = vector.map(x => Math.pow(x - mean, 2))
  return squaredDiffs.reduce((a, b) => a + b, 0) / vector.length
}

function calculateNorm(vector) {
  if (!vector?.length) return 0
  return Math.sqrt(vector.reduce((a, b) => a + b * b, 0))
}

function calculateSparsity(vector) {
  if (!vector?.length) return 0
  const nonZeroCount = vector.filter(x => Math.abs(x) > 1e-6).length
  return nonZeroCount / vector.length
}

// 热力图颜色映射（深蓝-白-深红）- 优化对比度
function getHeatmapColor(value) {
  // 归一化到 [-1, 1] 范围
  const normalized = Math.max(-1, Math.min(1, value))
  
  if (normalized < -0.1) {
    // 负值：深蓝色系 (深蓝 -> 浅蓝)
    const intensity = Math.abs(normalized)
    // 使用更深的蓝色范围：从 rgb(0,50,150) 到 rgb(150,200,255)
    const r = Math.round(150 * (1 - intensity * 0.7))
    const g = Math.round(50 + 150 * (1 - intensity * 0.7))
    const b = Math.round(150 + 105 * intensity)
    return `rgb(${r}, ${g}, ${b})`
  } else if (normalized > 0.1) {
    // 正值：深红色系 (浅红 -> 深红)
    const intensity = normalized
    // 使用更深的红色范围：从 rgb(255,200,150) 到 rgb(200,0,0)
    const r = Math.round(255 - 55 * (1 - intensity))
    const g = Math.round(200 * (1 - intensity * 0.9))
    const b = Math.round(150 * (1 - intensity))
    return `rgb(${r}, ${g}, ${b})`
  } else {
    // 接近零：浅灰色
    return `rgb(240, 240, 245)`
  }
}

// 交互操作
function toggleVectorExpand(index, event) {
  if (event) {
    event.stopPropagation?.()
    event.preventDefault?.()
  }
  if (expandedVectors.value.has(index)) {
    expandedVectors.value.delete(index)
  } else {
    expandedVectors.value.add(index)
  }
}

function toggleSourceText(index, event) {
  if (event) {
    event.stopPropagation?.()
    event.preventDefault?.()
  }
  if (expandedSourceTexts.value.has(index)) {
    expandedSourceTexts.value.delete(index)
  } else {
    expandedSourceTexts.value.add(index)
  }
}

function copyVector(vector, event) {
  if (event) {
    event.stopPropagation?.()
    event.preventDefault?.()
  }
  const text = JSON.stringify(vector)
  navigator.clipboard.writeText(text).then(() => {
    MessagePlugin.success('向量已复制到剪贴板')
  }).catch(() => {
    MessagePlugin.error('复制失败')
  })
}

function downloadVectors(event) {
  if (event) {
    event.stopPropagation?.()
    event.preventDefault?.()
  }
  if (!props.result?.vectors) return
  
  const data = {
    metadata: props.result.metadata,
    vectors: props.result.vectors,
    timestamp: new Date().toISOString(),
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `vectors_${props.result.request_id || Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  MessagePlugin.success('向量已导出')
}
</script>

<style scoped>
.embedding-results {
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  text-align: center;
}

.empty-icon {
  color: #d1d5db;
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: #6b7280;
  margin: 0 0 0.5rem;
}

.empty-hint {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

/* 顶部信息区 - 水平布局 */
.top-info-row {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.source-info.horizontal {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background-color: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.source-info.horizontal .source-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  padding-right: 1rem;
  border-right: 1px solid #e5e7eb;
}

.header-icon {
  color: #6b7280;
}

.header-text {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}

.info-inline {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  min-width: 0;
}

.info-value.filename {
  font-size: 13px;
  color: #111827;
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-divider {
  color: #d1d5db;
  font-size: 12px;
}

.info-tag {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 13px;
  color: #3b82f6;
  font-weight: 600;
}

.info-tag .info-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 500;
  margin-right: 0.125rem;
}

.result-summary.horizontal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  border: 1px solid;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.result-summary.horizontal.status-success {
  background-color: #f0fdf4;
  border-color: #86efac;
}

.result-summary.horizontal.status-warning {
  background-color: #fefce8;
  border-color: #fde047;
}

.result-summary.horizontal.status-error {
  background-color: #fef2f2;
  border-color: #fca5a5;
}

.summary-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.summary-title {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}

.summary-stats {
  display: flex;
  gap: 0.375rem;
}

.stat-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.stat-badge.success {
  background-color: #86efac;
  color: #16a34a;
}

.stat-badge.error {
  background-color: #fca5a5;
  color: #dc2626;
}

.stat-badge.neutral {
  background-color: #e5e7eb;
  color: #6b7280;
}

.summary-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.detail-tag {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 12px;
  color: #374151;
}

.detail-tag .detail-label {
  font-size: 10px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
}

.detail-tag.highlight {
  color: #3b82f6;
  font-weight: 600;
}

.multimodal-stats {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 6px;
  border: 1px solid #bae6fd;
}

.multimodal-stats.standalone {
  margin-top: 1rem;
}

.multimodal-header {
  font-size: 12px;
  font-weight: 600;
  color: #0369a1;
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.multimodal-grid {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.multimodal-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e0f2fe;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.multimodal-icon {
  font-size: 16px;
}

.multimodal-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.multimodal-value {
  font-size: 16px;
  font-weight: 700;
  color: #0369a1;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-title.error {
  color: #dc2626;
}

.count-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background-color: #e5e7eb;
  color: #374151;
  font-size: 11px;
  font-weight: 600;
  border-radius: 12px;
}

.count-badge.error {
  background-color: #fca5a5;
  color: #991b1b;
}

.vectors-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.vectors-controls {
  display: flex;
  gap: 0.5rem;
}

.vectors-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-align: center;
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 18px;
  color: #ffffff;
  font-weight: 700;
}

.vector-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.vector-meta {
  font-size: 12px;
  color: #6b7280;
}

.vector-heatmap {
  margin-bottom: 0.75rem;
}

.heatmap-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 600;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.heatmap-container {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  align-items: center;
  padding: 0.75rem;
  background-color: #f9fafb;
  border-radius: 6px;
}

.heatmap-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  cursor: pointer;
  transition: transform 0.2s;
}

.heatmap-cell:hover {
  transform: scale(1.5);
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.heatmap-more {
  font-size: 11px;
  color: #9ca3af;
  margin-left: 0.5rem;
  font-style: italic;
}

.vector-stats {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.vector-stats.compact {
  margin-bottom: 0;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background-color: #f3f4f6;
  border-radius: 6px;
  font-size: 12px;
}

.stat-chip-label {
  color: #6b7280;
  font-weight: 500;
}

.stat-chip-value {
  color: #111827;
  font-weight: 700;
  font-family: 'Monaco', 'Courier New', monospace;
}

.vector-raw-data {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #e5e7eb;
}

.raw-data-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.raw-data-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.raw-data-content {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 10px;
  background-color: #1f2937;
  color: #10b981;
  padding: 0.75rem;
  border-radius: 6px;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.pagination-info {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.vector-item {
  padding: 1rem;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.vector-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.vector-item.compact {
  padding: 0.75rem;
}

.vector-index {
  font-size: 14px;
  font-weight: 700;
  color: #3b82f6;
  background-color: #eff6ff;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
}

.vectors-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.vector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.failures-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.failure-item {
  padding: 0.75rem;
  background-color: #fef2f2;
  border-radius: 6px;
  border: 1px solid #fca5a5;
}

.failure-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.failure-index {
  font-size: 12px;
  font-weight: 600;
  color: #dc2626;
}

.failure-type {
  font-size: 11px;
  font-weight: 600;
  color: #991b1b;
  background-color: #fee2e2;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.failure-message {
  font-size: 12px;
  color: #374151;
  margin: 0 0 0.5rem;
}

.failure-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 11px;
  color: #6b7280;
}

.retry-badge {
  background-color: #fde047;
  color: #854d0e;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.source-text-preview {
  margin-bottom: 0.75rem;
  padding: 0.75rem;
  background-color: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}

.source-text-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 600;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.source-text-content {
  font-size: 13px;
  color: #374151;
  line-height: 1.6;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  word-wrap: break-word;
  white-space: pre-wrap;
  transition: max-height 0.3s ease;
}

.source-text-content.expanded {
  max-height: none;
}

.source-text-toggle {
  margin-top: 0.5rem;
  font-size: 12px;
  color: #3b82f6;
}
</style>
