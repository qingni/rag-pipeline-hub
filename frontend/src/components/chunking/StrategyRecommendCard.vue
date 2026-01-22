<template>
  <div class="strategy-recommend-card">
    <t-card
      :class="{ 'is-top': recommendation.is_top }"
      :bordered="true"
      hover-shadow
    >
      <template #header>
        <div class="card-header">
          <div class="strategy-info">
            <ChunkTypeIcon :type="recommendation.strategy" />
            <span class="strategy-name">{{ recommendation.strategy_name }}</span>
            <t-tag
              v-if="recommendation.is_top"
              theme="primary"
              size="small"
            >
              推荐
            </t-tag>
          </div>
          <div class="confidence">
            <t-progress
              :percentage="Math.round(recommendation.confidence * 100)"
              :color="getConfidenceColor(recommendation.confidence)"
              size="small"
              :label="false"
              style="width: 60px"
            />
            <span class="confidence-text">{{ Math.round(recommendation.confidence * 100) }}%</span>
          </div>
        </div>
      </template>
      
      <div class="card-content">
        <p class="reason">{{ recommendation.reason }}</p>
        
        <div class="estimation">
          <t-space size="large">
            <div class="stat-item">
              <span class="stat-label">预估块数</span>
              <span class="stat-value">{{ recommendation.estimated_chunks }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">平均大小</span>
              <span class="stat-value">{{ recommendation.estimated_avg_chunk_size }} 字符</span>
            </div>
          </t-space>
        </div>
        
        <div v-if="showDetails" class="details">
          <div v-if="recommendation.pros?.length" class="pros">
            <span class="detail-label">优点:</span>
            <t-tag
              v-for="(pro, index) in recommendation.pros"
              :key="index"
              theme="success"
              variant="light"
              size="small"
            >
              {{ pro }}
            </t-tag>
          </div>
          <div v-if="recommendation.cons?.length" class="cons">
            <span class="detail-label">注意:</span>
            <t-tag
              v-for="(con, index) in recommendation.cons"
              :key="index"
              theme="warning"
              variant="light"
              size="small"
            >
              {{ con }}
            </t-tag>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="card-footer">
          <t-button
            theme="default"
            variant="text"
            size="small"
            @click="showDetails = !showDetails"
          >
            {{ showDetails ? '收起详情' : '查看详情' }}
          </t-button>
          <t-button
            theme="primary"
            size="small"
            @click="$emit('apply', recommendation)"
          >
            应用此策略
          </t-button>
        </div>
      </template>
    </t-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChunkTypeIcon from './ChunkTypeIcon.vue'

const props = defineProps({
  recommendation: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['apply'])

const showDetails = ref(false)

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#52c41a'
  if (confidence >= 0.6) return '#1890ff'
  return '#faad14'
}
</script>

<style scoped>
.strategy-recommend-card {
  margin-bottom: 12px;
}

.strategy-recommend-card :deep(.t-card) {
  transition: all 0.3s ease;
}

.strategy-recommend-card :deep(.t-card.is-top) {
  border-color: var(--td-brand-color);
  box-shadow: 0 2px 8px rgba(0, 82, 217, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strategy-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-name {
  font-weight: 600;
  font-size: 14px;
}

.confidence {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-text {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  min-width: 36px;
}

.card-content {
  padding: 8px 0;
}

.reason {
  color: var(--td-text-color-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.estimation {
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}

.details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--td-component-border);
}

.pros, .cons {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.detail-label {
  font-size: 12px;
  color: var(--td-text-color-secondary);
  min-width: 40px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
