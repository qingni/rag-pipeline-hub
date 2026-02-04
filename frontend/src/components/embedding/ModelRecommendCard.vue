<template>
  <div class="model-recommend-card">
    <!-- 推荐头部 -->
    <div class="recommend-header">
      <h3 class="title">
        <t-icon name="lightbulb" />
        智能模型推荐
      </h3>
      <t-tag v-if="topRecommendation" :theme="confidenceTheme" size="small">
        {{ confidenceLabel }}
      </t-tag>
    </div>

    <!-- 文档分析摘要 -->
    <div v-if="documentAnalysis" class="analysis-summary">
      <div class="summary-item">
        <span class="label">检测语言</span>
        <span class="value">{{ languageName }} ({{ (documentAnalysis.language_confidence * 100).toFixed(0) }}%)</span>
      </div>
      <div class="summary-item">
        <span class="label">识别领域</span>
        <span class="value">{{ domainName }} ({{ (documentAnalysis.domain_confidence * 100).toFixed(0) }}%)</span>
      </div>
      <div class="summary-item">
        <span class="label">多模态比例</span>
        <span class="value">{{ (documentAnalysis.multimodal_ratio * 100).toFixed(1) }}%</span>
      </div>
    </div>

    <!-- 推荐列表 -->
    <div class="recommendations">
      <div
        v-for="rec in recommendations"
        :key="rec.model.model_name"
        class="recommendation-item"
        :class="{ selected: selectedModel === rec.model.model_name }"
        @click="selectModel(rec)"
      >
        <div class="rank-badge">
          <span v-if="rec.rank === 1" class="rank-1">🥇</span>
          <span v-else-if="rec.rank === 2" class="rank-2">🥈</span>
          <span v-else-if="rec.rank === 3" class="rank-3">🥉</span>
          <span v-else class="rank-n">{{ rec.rank }}</span>
        </div>
        
        <div class="model-info">
          <div class="model-name">
            {{ rec.model.display_name }}
            <t-tag v-if="rec.model.model_type === 'multimodal'" size="small" theme="warning">
              多模态
            </t-tag>
          </div>
          <div class="model-score">
            匹配度: {{ (rec.model.total_score * 100).toFixed(0) }}%
          </div>
        </div>
        
        <div class="score-bar">
          <div 
            class="score-fill" 
            :style="{ width: (rec.model.total_score * 100) + '%' }"
            :class="getScoreClass(rec.model.total_score)"
          ></div>
        </div>
        
        <div class="reasons" v-if="rec.reasons && rec.reasons.length > 0">
          <div 
            v-for="(reason, idx) in rec.reasons.slice(0, 2)" 
            :key="idx"
            class="reason-tag"
            :class="reason.impact"
          >
            <t-icon 
              :name="reason.impact === 'positive' ? 'check-circle' : 
                     reason.impact === 'negative' ? 'error-circle' : 'info-circle'" 
              size="12px"
            />
            {{ reason.description }}
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions" v-if="showActions">
      <t-button 
        theme="primary" 
        :disabled="!selectedModel"
        @click="confirmSelection"
      >
        使用 {{ selectedModelName }}
      </t-button>
      <t-button 
        theme="default" 
        variant="outline"
        @click="$emit('show-detail')"
      >
        查看详情
      </t-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

// Props
const props = defineProps({
  recommendations: {
    type: Array,
    default: () => [],
  },
  documentAnalysis: {
    type: Object,
    default: null,
  },
  topRecommendation: {
    type: Object,
    default: null,
  },
  showActions: {
    type: Boolean,
    default: true,
  },
  initialModel: {
    type: String,
    default: '',
  },
});

// Emits
const emit = defineEmits(['select', 'confirm', 'show-detail']);

// State
const selectedModel = ref(props.initialModel || props.topRecommendation?.model?.model_name || '');

// Watch for changes - 当推荐列表变化时（切换文档），自动选中第一个推荐的模型
watch(() => props.recommendations, (newVal, oldVal) => {
  // 推荐列表有变化（切换文档或重新推荐），自动选中第一个
  if (newVal && newVal.length > 0) {
    // 检查是否是新的推荐列表（通过比较第一个元素的 model_name）
    const isNewRecommendations = !oldVal || oldVal.length === 0 || 
      (oldVal[0]?.model?.model_name !== newVal[0]?.model?.model_name);
    
    if (isNewRecommendations && props.topRecommendation) {
      selectedModel.value = props.topRecommendation.model?.model_name || '';
    }
  }
}, { immediate: true });

// 同时监听 topRecommendation 的变化
watch(() => props.topRecommendation, (newVal) => {
  if (newVal) {
    selectedModel.value = newVal.model?.model_name || '';
  }
});

// Computed
const confidenceTheme = computed(() => {
  if (!props.topRecommendation) return 'default';
  const confidence = props.topRecommendation.confidence;
  if (confidence === 'high') return 'success';
  if (confidence === 'medium') return 'warning';
  return 'danger';
});

const confidenceLabel = computed(() => {
  if (!props.topRecommendation) return '';
  const confidence = props.topRecommendation.confidence;
  if (confidence === 'high') return '高置信度';
  if (confidence === 'medium') return '中置信度';
  return '低置信度';
});

const selectedModelName = computed(() => {
  const rec = props.recommendations.find(r => r.model.model_name === selectedModel.value);
  return rec?.model?.display_name || selectedModel.value;
});

const languageName = computed(() => {
  if (!props.documentAnalysis) return '';
  const langMap = {
    zh: '中文',
    en: '英文',
    ja: '日文',
    ko: '韩文',
    unknown: '未知',
  };
  return langMap[props.documentAnalysis.primary_language] || props.documentAnalysis.primary_language;
});

const domainName = computed(() => {
  if (!props.documentAnalysis) return '';
  const domainMap = {
    general: '通用',
    technical: '技术',
    legal: '法律',
    medical: '医疗',
    financial: '金融',
    academic: '学术',
    news: '新闻',
  };
  return domainMap[props.documentAnalysis.detected_domain] || props.documentAnalysis.detected_domain;
});

// Methods
const selectModel = (rec) => {
  selectedModel.value = rec.model.model_name;
  emit('select', rec);
};

const confirmSelection = () => {
  const rec = props.recommendations.find(r => r.model.model_name === selectedModel.value);
  emit('confirm', rec);
};

const getScoreClass = (score) => {
  if (score >= 0.8) return 'high';
  if (score >= 0.5) return 'medium';
  return 'low';
};
</script>

<style scoped>
.model-recommend-card {
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  padding: 16px;
}

.recommend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.recommend-header .title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  margin: 0;
}

.analysis-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px;
  background: var(--td-bg-color-secondarycontainer);
  border-radius: 6px;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item .label {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.summary-item .value {
  font-size: 14px;
  font-weight: 500;
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.recommendation-item {
  display: grid;
  grid-template-columns: 40px 1fr 100px;
  gap: 12px;
  align-items: center;
  padding: 12px;
  background: var(--td-bg-color-secondarycontainer);
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.recommendation-item:hover {
  border-color: var(--td-brand-color);
}

.recommendation-item.selected {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light);
}

.rank-badge {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 24px;
}

.rank-n {
  width: 28px;
  height: 28px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--td-gray-color-4);
  border-radius: 50%;
  font-size: 14px;
  font-weight: 500;
}

.model-info {
  min-width: 0;
}

.model-name {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  font-weight: 500;
  margin-bottom: 4px;
  line-height: 1.4;
}

.model-score {
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.score-bar {
  width: 100%;
  height: 6px;
  background: var(--td-gray-color-3);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.score-fill.high {
  background: var(--td-success-color);
}

.score-fill.medium {
  background: var(--td-warning-color);
}

.score-fill.low {
  background: var(--td-error-color);
}

.reasons {
  grid-column: 2 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.reason-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.reason-tag.positive {
  background: var(--td-success-color-1);
  color: var(--td-success-color);
}

.reason-tag.negative {
  background: var(--td-error-color-1);
  color: var(--td-error-color);
}

.reason-tag.neutral {
  background: var(--td-gray-color-2);
  color: var(--td-text-color-secondary);
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>
