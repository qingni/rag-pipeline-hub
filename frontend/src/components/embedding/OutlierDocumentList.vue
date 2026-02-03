<template>
  <div class="outlier-document-list" v-if="outliers.length > 0">
    <!-- 标题区域 -->
    <div class="outlier-header">
      <el-icon class="warning-icon"><WarningFilled /></el-icon>
      <span class="header-title">检测到 {{ outliers.length }} 个异常文档</span>
      <el-tooltip content="这些文档的特征与其他文档差异较大，建议单独选择模型" placement="top">
        <el-icon class="info-icon"><InfoFilled /></el-icon>
      </el-tooltip>
    </div>
    
    <!-- 异常文档列表 -->
    <div class="outlier-items">
      <div
        v-for="(outlier, index) in outliers"
        :key="outlier.document_id"
        class="outlier-item"
        :class="{ 'selected': selectedDocIds.includes(outlier.document_id) }"
        @click="toggleSelection(outlier.document_id)"
      >
        <div class="item-header">
          <el-checkbox
            :model-value="selectedDocIds.includes(outlier.document_id)"
            @click.stop
            @change="toggleSelection(outlier.document_id)"
          />
          <span class="doc-name" :title="outlier.document_name">
            {{ truncateName(outlier.document_name) }}
          </span>
          <el-tag 
            :type="getDeviationType(outlier.deviation_score)" 
            size="small"
            effect="light"
          >
            偏离: {{ formatScore(outlier.deviation_score) }}
          </el-tag>
        </div>
        
        <div class="item-body">
          <div class="deviation-reason">
            <el-icon><Document /></el-icon>
            <span>{{ outlier.deviation_reason }}</span>
          </div>
          
          <div class="suggested-action" v-if="outlier.suggested_action">
            <el-icon><Promotion /></el-icon>
            <span>{{ outlier.suggested_action }}</span>
          </div>
        </div>
        
        <!-- 单独推荐按钮 -->
        <div class="item-actions">
          <el-button
            type="primary"
            text
            size="small"
            @click.stop="$emit('recommend-single', outlier.document_id)"
          >
            <el-icon><MagicStick /></el-icon>
            单独推荐
          </el-button>
          <el-button
            type="warning"
            text
            size="small"
            @click.stop="$emit('exclude', outlier.document_id)"
          >
            <el-icon><Remove /></el-icon>
            排除
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 批量操作 -->
    <div class="batch-actions" v-if="outliers.length > 1">
      <el-button
        size="small"
        @click="selectAll"
        :disabled="selectedDocIds.length === outliers.length"
      >
        全选
      </el-button>
      <el-button
        size="small"
        @click="clearSelection"
        :disabled="selectedDocIds.length === 0"
      >
        取消全选
      </el-button>
      <el-divider direction="vertical" />
      <el-button
        type="warning"
        size="small"
        :disabled="selectedDocIds.length === 0"
        @click="$emit('exclude-selected', selectedDocIds)"
      >
        排除选中 ({{ selectedDocIds.length }})
      </el-button>
      <el-button
        type="success"
        size="small"
        :disabled="selectedDocIds.length === 0"
        @click="$emit('proceed-anyway')"
      >
        继续使用统一模型
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  WarningFilled,
  InfoFilled,
  Document,
  Promotion,
  MagicStick,
  Remove,
} from '@element-plus/icons-vue'

const props = defineProps({
  /**
   * 异常文档列表
   * @type {Array<{
   *   document_id: string,
   *   document_name: string,
   *   deviation_score: number,
   *   deviation_reason: string,
   *   suggested_action: string
   * }>}
   */
  outliers: {
    type: Array,
    default: () => [],
  },
  /**
   * 异常阈值
   */
  threshold: {
    type: Number,
    default: 0.3,
  },
})

const emit = defineEmits([
  'recommend-single',
  'exclude',
  'exclude-selected',
  'proceed-anyway',
])

// 选中的文档ID列表
const selectedDocIds = ref([])

/**
 * 切换文档选中状态
 */
function toggleSelection(docId) {
  const index = selectedDocIds.value.indexOf(docId)
  if (index > -1) {
    selectedDocIds.value.splice(index, 1)
  } else {
    selectedDocIds.value.push(docId)
  }
}

/**
 * 全选
 */
function selectAll() {
  selectedDocIds.value = props.outliers.map(o => o.document_id)
}

/**
 * 取消全选
 */
function clearSelection() {
  selectedDocIds.value = []
}

/**
 * 截断文件名
 */
function truncateName(name, maxLen = 30) {
  if (!name) return ''
  if (name.length <= maxLen) return name
  return name.substring(0, maxLen - 3) + '...'
}

/**
 * 格式化偏离分数
 */
function formatScore(score) {
  return (score * 100).toFixed(1) + '%'
}

/**
 * 根据偏离分数获取标签类型
 */
function getDeviationType(score) {
  if (score > 0.5) return 'danger'
  if (score > 0.4) return 'warning'
  return 'info'
}
</script>

<style scoped>
.outlier-document-list {
  background: linear-gradient(135deg, #fff7e6 0%, #fffbe6 100%);
  border: 1px solid #faad14;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}

.outlier-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #faad14;
}

.warning-icon {
  font-size: 20px;
  color: #faad14;
}

.header-title {
  font-weight: 600;
  color: #d46b08;
  flex: 1;
}

.info-icon {
  font-size: 16px;
  color: #8c8c8c;
  cursor: help;
}

.outlier-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.outlier-item {
  background: #fff;
  border: 1px solid #ffe58f;
  border-radius: 6px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.outlier-item:hover {
  border-color: #faad14;
  box-shadow: 0 2px 8px rgba(250, 173, 20, 0.15);
}

.outlier-item.selected {
  border-color: #1890ff;
  background: #e6f7ff;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.doc-name {
  flex: 1;
  font-weight: 500;
  color: #262626;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-left: 28px;
  margin-bottom: 8px;
}

.deviation-reason,
.suggested-action {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  color: #595959;
}

.deviation-reason .el-icon,
.suggested-action .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.suggested-action {
  color: #8c8c8c;
  font-style: italic;
}

.item-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #f0f0f0;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ffe58f;
}

/* 滚动条样式 */
.outlier-items::-webkit-scrollbar {
  width: 6px;
}

.outlier-items::-webkit-scrollbar-track {
  background: #fffbe6;
  border-radius: 3px;
}

.outlier-items::-webkit-scrollbar-thumb {
  background: #fadb14;
  border-radius: 3px;
}

.outlier-items::-webkit-scrollbar-thumb:hover {
  background: #faad14;
}
</style>
