<template>
  <div class="strategy-selector">
    <!-- Smart Recommendation Section -->
    <div v-if="hasDocument && topRecommendation" class="smart-recommend-section">
      <div class="section-header">
        <div class="section-title">
          <t-icon name="lightbulb" class="lightbulb-icon" />
          <span>智能推荐</span>
          <t-tag theme="primary" size="small" variant="light">AI</t-tag>
        </div>
        <t-button
          v-if="!recommendationsLoading"
          theme="default"
          variant="text"
          size="small"
          @click="refreshRecommendations"
        >
          <template #icon><t-icon name="refresh" /></template>
          重新分析
        </t-button>
      </div>
      
      <t-loading :loading="recommendationsLoading" size="small" text="正在分析文档特征...">
        <!-- Top Recommendation Card -->
        <div 
          class="top-recommend-card" 
          :class="{ 'is-applied': selectedStrategyType === topRecommendation.strategy }"
        >
          <!-- 第一行：图标 + 中间区域（策略名、进度条+匹配度） + 按钮 -->
          <div class="top-card-header">
            <ChunkTypeIcon :type="topRecommendation.strategy" class="top-strategy-icon" />
            <div class="top-card-center">
              <span class="top-strategy-name">{{ topRecommendation.strategy_name }}</span>
              <div class="top-card-confidence">
                <div class="confidence-bar">
                  <div class="confidence-fill" :style="{ width: (topRecommendation.confidence * 100) + '%', background: getConfidenceColor(topRecommendation.confidence) }"></div>
                </div>
                <span class="confidence-text">{{ Math.round(topRecommendation.confidence * 100) }}% 匹配</span>
              </div>
            </div>
            <t-button 
              :theme="selectedStrategyType === topRecommendation.strategy ? 'default' : 'primary'" 
              size="small" 
              class="apply-btn" 
              @click.stop="handleApplyTopRecommendation"
            >
              <template #icon><t-icon :name="selectedStrategyType === topRecommendation.strategy ? 'check-circle-filled' : 'check'" /></template>
              {{ selectedStrategyType === topRecommendation.strategy ? '已应用' : '应用' }}
            </t-button>
          </div>
          <!-- 第二行：推荐理由 -->
          <p class="top-strategy-reason">{{ topRecommendation.reason }}</p>
          <!-- 第四行：统计数据 -->
          <div class="top-card-stats">
            <span class="stat-item">
              <t-icon name="grid-view" />
              预估 {{ topRecommendation.estimated_chunks }} 块
            </span>
            <span class="stat-item">
              <t-icon name="file" />
              平均 {{ topRecommendation.estimated_avg_chunk_size }} 字/块
            </span>
          </div>
        </div>

        <!-- Other Recommendations Collapse -->
        <t-collapse v-if="otherRecommendations.length > 0" class="other-collapse" :default-expand-all="false">
          <t-collapse-panel :value="1">
            <template #header>
              <span class="collapse-header">查看其他 {{ otherRecommendations.length }} 个推荐方案</span>
            </template>
            <div class="other-recommend-list">
              <div
                v-for="rec in otherRecommendations"
                :key="rec.strategy"
                class="other-recommend-item"
                :class="{ 'is-applied': selectedStrategyType === rec.strategy }"
                @click="handleApplyRecommendation(rec)"
              >
                <ChunkTypeIcon :type="rec.strategy" />
                <span class="other-name">{{ rec.strategy_name }}</span>
                <span class="other-confidence">{{ Math.round(rec.confidence * 100) }}%</span>
                <t-button 
                  :theme="selectedStrategyType === rec.strategy ? 'default' : 'default'" 
                  variant="outline" 
                  size="small"
                >
                  {{ selectedStrategyType === rec.strategy ? '已应用' : '应用' }}
                </t-button>
              </div>
            </div>
          </t-collapse-panel>
        </t-collapse>

        <!-- Document Features Collapse -->
        <t-collapse v-if="documentFeatures" class="features-collapse" :default-expand-all="false">
          <t-collapse-panel :value="1">
            <template #header>
              <span class="collapse-header">
                <t-icon name="chart-bar" />
                文档特征分析
              </span>
            </template>
            <div class="feature-list">
              <!-- 基础统计 -->
              <div class="feature-row">
                <span class="feature-label">段落数</span>
                <span class="feature-value">{{ documentFeatures.paragraph_count }}</span>
              </div>
              <div class="feature-row">
                <span class="feature-label">总字符</span>
                <span class="feature-value">{{ formatNumber(documentFeatures.total_char_count) }}</span>
              </div>
              <div class="feature-row">
                <span class="feature-label">平均段落</span>
                <span class="feature-value">{{ getAvgParagraphSize() }} 字</span>
              </div>
              <!-- 特殊特征（高亮） -->
              <div v-if="documentFeatures.heading_count > 0" class="feature-row highlight">
                <span class="feature-label">
                  <t-icon name="view-list" class="feature-icon" />
                  标题结构
                </span>
                <span class="feature-value">{{ getHeadingSummary() }}</span>
              </div>
              <div v-if="documentFeatures.table_count > 0" class="feature-row highlight">
                <span class="feature-label">
                  <t-icon name="table" class="feature-icon" />
                  表格
                </span>
                <span class="feature-value">{{ documentFeatures.table_count }} 个</span>
              </div>
              <div v-if="documentFeatures.image_count > 0" class="feature-row highlight">
                <span class="feature-label">
                  <t-icon name="image" class="feature-icon" />
                  图片
                </span>
                <span class="feature-value">{{ documentFeatures.image_count }} 个</span>
              </div>
              <div v-if="documentFeatures.code_block_count > 0" class="feature-row highlight">
                <span class="feature-label">
                  <t-icon name="code" class="feature-icon" />
                  代码块
                </span>
                <span class="feature-value">{{ documentFeatures.code_block_count }} 个</span>
              </div>
            </div>
          </t-collapse-panel>
        </t-collapse>
      </t-loading>
    </div>
    
    <!-- No Document Selected Hint -->
    <div v-else-if="!hasDocument" class="no-document-hint">
      <t-icon name="info-circle-filled" />
      <span>请先选择文档，系统将自动分析并推荐最佳分块策略</span>
    </div>

    <!-- Strategy Selection - Two-tier Layout -->
    <t-card title="选择分块策略" :bordered="false" class="strategies-card">
      <template #actions>
        <t-radio-group
          v-model="strategyLevel"
          variant="default-filled"
          size="small"
        >
          <t-radio-button value="advanced">
            <t-icon name="star" style="margin-right: 4px;" />高级策略
          </t-radio-button>
          <t-radio-button value="basic">
            <t-icon name="root-list" style="margin-right: 4px;" />基础策略
          </t-radio-button>
        </t-radio-group>
      </template>

      <t-loading :loading="loading" size="small">
        <!-- Level Description -->
        <div class="level-description">
          <t-icon :name="strategyLevel === 'advanced' ? 'star-filled' : 'root-list'" />
          <span v-if="strategyLevel === 'advanced'">
            高级策略使用智能算法，适合复杂文档和高质量知识库场景
          </span>
          <span v-else>
            基础策略简单高效，适合快速处理和简单文档场景
          </span>
        </div>

        <div class="strategy-grid">
          <div
            v-for="strategy in displayStrategies"
            :key="strategy.type"
            class="strategy-card"
            :class="{
              'is-selected': selectedStrategyType === strategy.type
            }"
            @click="handleSelect(strategy.type)"
          >
            <div class="strategy-card-content">
              <div class="strategy-card-header">
                <ChunkTypeIcon :type="strategy.type" />
                <span class="strategy-card-name">{{ strategy.name }}</span>
              </div>
              <t-popup
                trigger="hover"
                placement="bottom"
                :show-arrow="true"
                :overlay-style="{ maxWidth: '320px' }"
              >
                <t-icon name="info-circle" class="info-icon" />
                <template #content>
                  <div class="strategy-tooltip">
                    <div class="tooltip-desc">{{ getStrategyDetail(strategy.type, 'description') }}</div>
                    <div class="tooltip-grid">
                      <div class="tooltip-item pros">
                        <span class="tooltip-label">✓ 优点</span>
                        <span class="tooltip-value">{{ getStrategyDetail(strategy.type, 'pros') }}</span>
                      </div>
                      <div class="tooltip-item cons">
                        <span class="tooltip-label">✗ 缺点</span>
                        <span class="tooltip-value">{{ getStrategyDetail(strategy.type, 'cons') }}</span>
                      </div>
                    </div>
                    <div class="tooltip-usecase">
                      <span class="tooltip-label">📌 适用场景</span>
                      <span class="tooltip-value">{{ getStrategyDetail(strategy.type, 'useCase') }}</span>
                    </div>
                  </div>
                </template>
              </t-popup>
            </div>
          </div>
        </div>

        <t-empty
          v-if="!loading && strategies.length === 0"
          description="暂无可用策略"
        />
      </t-loading>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin } from 'tdesign-vue-next'
import ChunkTypeIcon from './ChunkTypeIcon.vue'

const chunkingStore = useChunkingStore()

const loading = computed(() => chunkingStore.strategiesLoading)
const strategies = computed(() => chunkingStore.strategies)
const recommendations = computed(() => chunkingStore.recommendations)
const recommendationsLoading = computed(() => chunkingStore.recommendationsLoading)
const documentFeatures = computed(() => chunkingStore.documentFeatures)
const hasDocument = computed(() => chunkingStore.hasSelectedDocument)

// Top recommendation (first one with is_top or highest confidence)
const topRecommendation = computed(() => {
  if (!recommendations.value || recommendations.value.length === 0) return null
  return recommendations.value.find(r => r.is_top) || recommendations.value[0]
})

// Other recommendations (excluding top)
const otherRecommendations = computed(() => {
  if (!recommendations.value || recommendations.value.length <= 1) return []
  return recommendations.value.filter(r => r !== topRecommendation.value)
})

const selectedStrategyType = computed(() => chunkingStore.selectedStrategy?.type || null)
const strategyLevel = ref('advanced')

// Strategy classification
const advancedStrategies = ['semantic', 'parent_child', 'hybrid']
const basicStrategies = ['character', 'paragraph', 'heading']

// New strategies added in this optimization
const newStrategies = ['parent_child', 'hybrid']

// Strategy details for tooltip
const strategyDetails = {
  character: {
    description: '按固定字符数切分文档，适合一般文本',
    pros: '简单快速、分块大小可控',
    cons: '可能切断语义',
    useCase: '一般文本、性能优先场景'
  },
  paragraph: {
    description: '以自然段落为基本单位分块，保持语义完整性',
    pros: '语义完整、切分自然',
    cons: '段落大小不均匀',
    useCase: '小说、文章、博客'
  },
  heading: {
    description: '按标题层级分块，适合结构化文档',
    pros: '保留文档结构、边界清晰',
    cons: '需要文档有标题结构',
    useCase: '技术文档、Markdown 文件'
  },
  semantic: {
    description: '使用 Embedding 相似度智能识别语义边界进行分块',
    pros: '语义完整、智能边界识别',
    cons: '需要 API、处理较慢',
    useCase: '高质量知识库、问答系统'
  },
  parent_child: {
    description: '生成父块和子块的两层结构，子块用于检索，父块提供上下文',
    pros: '上下文丰富、检索精确',
    cons: '存储空间较大',
    useCase: '长文档、需要上下文的问答'
  },
  hybrid: {
    description: '针对不同内容类型（正文、代码块、表格、图片）智能应用最合适的分块策略，支持自定义阈值',
    pros: '智能适配、灵活度高、支持多内容类型提取',
    cons: '配置项较多',
    useCase: '混合内容文档、技术手册、富媒体文档'
  }
}

const displayStrategies = computed(() => {
  const targetTypes = strategyLevel.value === 'advanced' ? advancedStrategies : basicStrategies
  return strategies.value.filter(s => targetTypes.includes(s.type))
})

const isNewStrategy = (type) => newStrategies.includes(type)

// Check if strategy is in recommendations list
const isRecommendedStrategy = (type) => {
  return recommendations.value?.some(r => r.strategy === type)
}

// Check if strategy is the top recommendation
const isTopRecommendedStrategy = (type) => {
  return topRecommendation.value?.strategy === type
}

const getStrategyDetail = (type, field) => {
  const details = strategyDetails[type]
  return details ? details[field] : ''
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#52c41a'
  if (confidence >= 0.6) return '#1890ff'
  return '#faad14'
}

const getHeadingSummary = () => {
  if (!documentFeatures.value?.heading_levels) return '无标题'
  const levels = documentFeatures.value.heading_levels
  const parts = Object.entries(levels)
    .filter(([, count]) => count > 0)
    .map(([level, count]) => `H${level}: ${count}`)
  return parts.length ? parts.join(', ') : '无标题'
}

const getAvgParagraphSize = () => {
  if (!documentFeatures.value) return 0
  const { paragraph_count, total_char_count } = documentFeatures.value
  if (!paragraph_count || paragraph_count === 0) return 0
  return Math.round(total_char_count / paragraph_count)
}

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

const loadStrategies = async () => {
  try {
    await chunkingStore.loadStrategies()
  } catch (error) {
    console.error('加载策略列表失败:', error)
    MessagePlugin.error('加载策略列表失败')
  }
}

const refreshRecommendations = async () => {
  try {
    await chunkingStore.loadRecommendations()
  } catch (error) {
    console.error('加载推荐失败:', error)
    MessagePlugin.error('加载推荐失败')
  }
}

const handleSelect = (strategyType) => {
  selectedStrategyType.value = strategyType
  const strategy = chunkingStore.strategies.find(s => s.type === strategyType)
  if (strategy) {
    chunkingStore.selectStrategy(strategy)
  }
}

// Apply recommendation helper
const applyRecommendationInternal = (recommendation) => {
  chunkingStore.applyRecommendation(recommendation)
  // selectedStrategyType is now computed from store, no need to set manually
  // Auto-switch to the correct level based on the recommended strategy
  if (advancedStrategies.includes(recommendation.strategy)) {
    strategyLevel.value = 'advanced'
  } else if (basicStrategies.includes(recommendation.strategy)) {
    strategyLevel.value = 'basic'
  }
}

const handleApplyRecommendation = (recommendation) => {
  applyRecommendationInternal(recommendation)
  MessagePlugin.success(`已应用推荐策略: ${recommendation.strategy_name}`)
}

// Apply the top recommendation with one click
const handleApplyTopRecommendation = () => {
  if (topRecommendation.value) {
    applyRecommendationInternal(topRecommendation.value)
    MessagePlugin.success({
      content: `已应用最佳推荐: ${topRecommendation.value.strategy_name}`,
      duration: 3000
    })
  }
}

// Watch for document selection changes
watch(() => chunkingStore.selectedDocument, async (newDoc) => {
  if (newDoc) {
    // Load recommendations when document is selected
    await refreshRecommendations()
  } else {
    chunkingStore.clearRecommendations()
  }
})

// Sync strategy level with store (selectedStrategyType is now computed)
watch(() => chunkingStore.selectedStrategy, (strategy) => {
  if (strategy) {
    // Auto-switch to the correct level
    if (advancedStrategies.includes(strategy.type)) {
      strategyLevel.value = 'advanced'
    } else if (basicStrategies.includes(strategy.type)) {
      strategyLevel.value = 'basic'
    }
  }
}, { immediate: true })

onMounted(() => {
  loadStrategies()
  // If document is already selected, load recommendations
  if (hasDocument.value) {
    refreshRecommendations()
  }
})
</script>

<style scoped>
.strategy-selector {
  margin-bottom: 20px;
}

/* Smart Recommendation Section */
.smart-recommend-section {
  margin-bottom: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #f6f9ff 0%, #f0f5ff 100%);
  border: 1px solid var(--td-brand-color-light-hover);
  border-radius: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.lightbulb-icon {
  color: #faad14;
  font-size: 16px;
}

/* Top Recommendation Card */
.top-recommend-card {
  padding: 16px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-component-stroke);
  border-radius: 8px;
  margin-bottom: 10px;
  transition: all 0.2s ease;
}

.top-recommend-card.is-applied {
  background: var(--td-brand-color-light);
  border-color: var(--td-brand-color);
}

/* 顶部行：图标 + 中间区域 + 按钮 */
.top-card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.top-strategy-icon {
  font-size: 40px;
  flex-shrink: 0;
}

.top-card-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.top-strategy-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.top-card-confidence {
  display: flex;
  align-items: center;
  gap: 12px;
}

.confidence-bar {
  width: 60px;
  height: 8px;
  background: var(--td-bg-color-component);
  border-radius: 4px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.confidence-text {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.apply-btn {
  flex-shrink: 0;
  padding: 0 12px;
}

.top-strategy-reason {
  font-size: 14px;
  color: var(--td-text-color-secondary);
  margin: 0 0 12px 0;
  line-height: 1.6;
}

.top-card-stats {
  display: flex;
  gap: 20px;
}

.top-card-stats .stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.top-card-stats .stat-item .t-icon {
  font-size: 14px;
}

/* Collapse Panels */
.other-collapse,
.features-collapse {
  margin-top: 10px;
  background: var(--td-bg-color-container);
  border-radius: 8px;
  overflow: hidden;
}

.other-collapse :deep(.t-collapse-panel__header),
.features-collapse :deep(.t-collapse-panel__header) {
  padding: 12px 16px;
  background: transparent;
}

.other-collapse :deep(.t-collapse-panel__body),
.features-collapse :deep(.t-collapse-panel__body) {
  padding: 0 12px 12px;
}

.other-collapse :deep(.t-collapse-panel__content),
.features-collapse :deep(.t-collapse-panel__content) {
  padding-left: 12px;
}

.collapse-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.collapse-header .t-icon {
  font-size: 16px;
  color: var(--td-brand-color);
}

/* Other Recommendations List */
.other-recommend-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.other-recommend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.other-recommend-item:hover {
  background: var(--td-bg-color-container-hover);
}

.other-recommend-item.is-applied {
  background: var(--td-brand-color-light);
  border: 1px solid var(--td-brand-color);
}

.other-recommend-item .other-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--td-text-color-primary);
  white-space: nowrap;
}

.other-recommend-item .other-confidence {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  padding: 2px 6px;
  background: var(--td-bg-color-component);
  border-radius: 10px;
  flex-shrink: 0;
}

/* Document Features List */
.feature-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
}

.feature-row.highlight {
  background: linear-gradient(135deg, #f6f9ff 0%, #eef4ff 100%);
}

.feature-row .feature-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.feature-row .feature-icon {
  font-size: 14px;
  color: var(--td-brand-color);
}

.feature-row .feature-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.feature-row.highlight .feature-value {
  color: var(--td-brand-color);
}

/* No Document Hint */
.no-document-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: var(--td-bg-color-container-hover);
  border-radius: 6px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.no-document-hint .t-icon {
  color: var(--td-brand-color);
  font-size: 16px;
}

/* Strategy Card */
.strategies-card {
  background: linear-gradient(135deg, #f9fbff 0%, #f5f8ff 100%);
  border: 1px solid var(--td-component-stroke);
  border-radius: 10px;
}

.strategies-card :deep(.t-card__body) {
  padding: 12px;
}

.strategies-card :deep(.t-card__header) {
  padding-bottom: 8px;
}

/* Level Description */
.level-description {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: var(--td-bg-color-container-hover);
  border-radius: 6px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.level-description .t-icon {
  color: var(--td-brand-color);
  font-size: 16px;
}

/* Compact Grid Layout */
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.strategy-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid var(--td-component-stroke);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--td-bg-color-container);
}

.strategy-card:hover {
  border-color: var(--td-brand-color);
  background: var(--td-bg-color-container-hover);
}

.strategy-card.is-selected {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light);
}

.strategy-card-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.strategy-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.strategy-card-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--td-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.new-tag,
.recommend-tag {
  flex-shrink: 0;
}

.info-icon {
  color: var(--td-text-color-placeholder);
  cursor: help;
  flex-shrink: 0;
  font-size: 14px;
  transition: color 0.2s;
}

.info-icon:hover {
  color: var(--td-brand-color);
}

/* Responsive */
@media (max-width: 500px) {
  .strategy-grid {
    grid-template-columns: 1fr;
  }
  
  .other-cards {
    flex-direction: column;
  }
  
  .card-main {
    flex-direction: column;
    gap: 12px;
  }
  
  .card-right {
    flex-direction: row;
    justify-content: space-between;
    width: 100%;
  }
}

/* Tooltip Styles */
.strategy-tooltip {
  padding: 4px 0;
  font-size: 13px;
  line-height: 1.5;
}

.tooltip-desc {
  color: var(--td-text-color-primary);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--td-component-stroke);
}

.tooltip-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 8px;
}

.tooltip-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tooltip-item.pros .tooltip-label {
  color: var(--td-success-color);
}

.tooltip-item.cons .tooltip-label {
  color: var(--td-error-color);
}

.tooltip-label {
  font-size: 12px;
  font-weight: 500;
}

.tooltip-value {
  color: var(--td-text-color-secondary);
  font-size: 12px;
}

.tooltip-usecase {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 8px;
  border-top: 1px solid var(--td-component-stroke);
}

.tooltip-usecase .tooltip-label {
  color: var(--td-brand-color);
}
</style>
