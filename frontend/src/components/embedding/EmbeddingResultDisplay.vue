<template>
  <div class="embedding-result-display">
    <t-card title="向量化结果" :bordered="false">
      <template #actions>
        <t-space>
          <t-button
            v-if="result"
            theme="default"
            size="small"
            @click="downloadResult"
          >
            <template #icon><t-icon name="download" /></template>
            下载结果
          </t-button>
          <t-button
            v-if="result"
            theme="default"
            size="small"
            @click="viewJsonFile"
          >
            <template #icon><t-icon name="file" /></template>
            查看JSON
          </t-button>
        </t-space>
      </template>
      
      <div v-if="!result" class="empty-state">
        <t-empty description="暂无向量化结果" />
      </div>
      
      <div v-else class="result-content">
        <!-- 概览信息 -->
        <t-card title="概览" size="small" :bordered="true">
          <t-descriptions bordered size="small" :column="2">
            <t-descriptions-item label="结果ID" :span="2">
              <t-tag theme="primary" variant="light">{{ result.result_id }}</t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="状态">
              <t-tag :theme="getStatusTheme(result.status)">
                {{ getStatusLabel(result.status) }}
              </t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="模型">
              {{ result.model_name }}
            </t-descriptions-item>
            <t-descriptions-item label="向量维度">
              {{ result.model_dimension }}
            </t-descriptions-item>
            <t-descriptions-item label="完成时间">
              {{ formatTime(result.timestamp) }}
            </t-descriptions-item>
            <t-descriptions-item label="成功数">
              <span class="success-count">{{ result.successful_count }}</span>
            </t-descriptions-item>
            <t-descriptions-item label="失败数">
              <span :class="result.failed_count > 0 ? 'failed-count' : ''">
                {{ result.failed_count }}
              </span>
            </t-descriptions-item>
            <t-descriptions-item label="成功率" :span="2">
              <t-progress
                :percentage="successRate"
                :theme="successRate === 100 ? 'success' : 'warning'"
                :label="false"
              />
              <span style="margin-left: 8px;">{{ successRate }}%</span>
            </t-descriptions-item>
          </t-descriptions>
        </t-card>
        
        <!-- 来源信息 -->
        <t-card title="来源信息" size="small" :bordered="true" style="margin-top: 16px;">
          <t-descriptions bordered size="small" :column="2">
            <t-descriptions-item label="来源类型">
              <t-tag>{{ getSourceTypeLabel(result.source.type) }}</t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="分块结果ID">
              {{ result.source.chunking_result_id || 'N/A' }}
            </t-descriptions-item>
            <t-descriptions-item v-if="result.source.document_id" label="文档ID">
              {{ result.source.document_id }}
            </t-descriptions-item>
            <t-descriptions-item v-if="result.source.document_name" label="文档名称">
              {{ result.source.document_name }}
            </t-descriptions-item>
          </t-descriptions>
        </t-card>
        
        <!-- 统计信息 -->
        <t-card title="性能统计" size="small" :bordered="true" style="margin-top: 16px;">
          <t-descriptions bordered size="small" :column="2">
            <t-descriptions-item label="总分块数">
              {{ result.statistics.total_chunks }}
            </t-descriptions-item>
            <t-descriptions-item label="成功向量化">
              {{ result.statistics.successful_embeddings }}
            </t-descriptions-item>
            <t-descriptions-item label="失败向量化">
              {{ result.statistics.failed_embeddings }}
            </t-descriptions-item>
            <t-descriptions-item label="总耗时">
              {{ result.statistics.total_processing_time_seconds.toFixed(2) }}s
            </t-descriptions-item>
            <t-descriptions-item label="平均耗时" :span="2">
              {{ result.statistics.average_time_per_chunk_ms.toFixed(2) }}ms/块
            </t-descriptions-item>
          </t-descriptions>
        </t-card>
        
        <!-- 错误列表 -->
        <t-card
          v-if="result.errors && result.errors.length > 0"
          title="错误详情"
          size="small"
          :bordered="true"
          style="margin-top: 16px;"
        >
          <t-alert theme="warning" message="以下分块向量化失败" style="margin-bottom: 12px;" />
          
          <t-table
            :data="result.errors"
            :columns="errorColumns"
            row-key="chunk_id"
            size="small"
            :max-height="300"
            stripe
            bordered
          />
        </t-card>
        
        <!-- 向量预览（前5个） -->
        <t-card
          v-if="result.vectors && result.vectors.length > 0"
          title="向量预览"
          size="small"
          :bordered="true"
          style="margin-top: 16px;"
        >
          <t-collapse default-value="[]">
            <t-collapse-panel
              v-for="vector in previewVectors"
              :key="vector.chunk_id"
              :value="vector.chunk_id"
              :header="`分块 #${vector.sequence_number} (${vector.chunk_id})`"
            >
              <div class="vector-detail">
                <div class="text-preview">
                  <strong>文本预览:</strong>
                  <p>{{ vector.text_preview }}</p>
                </div>
                <div class="vector-data">
                  <strong>向量 (前20维):</strong>
                  <div class="vector-values">
                    <t-tag
                      v-for="(val, i) in vector.vector.slice(0, 20)"
                      :key="i"
                      size="small"
                      variant="outline"
                    >
                      {{ val.toFixed(4) }}
                    </t-tag>
                    <span v-if="vector.vector.length > 20">...</span>
                  </div>
                </div>
                <div v-if="vector.metadata" class="metadata">
                  <strong>元数据:</strong>
                  <pre>{{ JSON.stringify(vector.metadata, null, 2) }}</pre>
                </div>
              </div>
            </t-collapse-panel>
          </t-collapse>
          
          <div v-if="result.vectors.length > 5" style="margin-top: 12px;">
            <t-alert
              theme="info"
              :message="`仅显示前5个向量，完整结果包含 ${result.vectors.length} 个向量`"
            />
          </div>
        </t-card>
        
        <!-- JSON文件路径 -->
        <t-card title="存储信息" size="small" :bordered="true" style="margin-top: 16px;">
          <div class="file-path">
            <strong>JSON文件路径:</strong>
            <t-tooltip :content="result.json_file_path">
              <t-tag theme="default" variant="outline" style="margin-left: 8px;">
                {{ result.json_file_path }}
              </t-tag>
            </t-tooltip>
          </div>
        </t-card>
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'

const props = defineProps({
  result: {
    type: Object,
    default: null
  }
})

const successRate = computed(() => {
  if (!props.result) return 0
  const { successful_count, failed_count } = props.result
  const total = successful_count + failed_count
  return total > 0 ? Math.round((successful_count / total) * 100) : 0
})

const previewVectors = computed(() => {
  if (!props.result?.vectors) return []
  return props.result.vectors.slice(0, 5)
})

const errorColumns = [
  {
    colKey: 'sequence_number',
    title: '序号',
    width: 80,
    align: 'center'
  },
  {
    colKey: 'chunk_id',
    title: '分块ID',
    width: 200,
    ellipsis: true
  },
  {
    colKey: 'error_type',
    title: '错误类型',
    width: 120,
    cell: (h, { row }) => {
      const themeMap = {
        rate_limit: 'warning',
        timeout: 'danger',
        network_error: 'danger',
        authentication_error: 'danger',
        invalid_text: 'warning',
        dimension_mismatch: 'danger',
        unknown: 'default'
      }
      return h('t-tag', {
        theme: themeMap[row.error_type] || 'default',
        size: 'small'
      }, row.error_type)
    }
  },
  {
    colKey: 'message',
    title: '错误信息',
    ellipsis: true
  },
  {
    colKey: 'timestamp',
    title: '时间',
    width: 160,
    cell: (h, { row }) => formatTime(row.timestamp)
  }
]

const getStatusTheme = (status) => {
  const themeMap = {
    success: 'success',
    partial_success: 'warning',
    failed: 'danger'
  }
  return themeMap[status] || 'default'
}

const getStatusLabel = (status) => {
  const labelMap = {
    success: '完全成功',
    partial_success: '部分成功',
    failed: '失败'
  }
  return labelMap[status] || status
}

const getSourceTypeLabel = (type) => {
  const labelMap = {
    chunking_result: '分块结果',
    document: '文档',
    manual_text: '手动文本'
  }
  return labelMap[type] || type
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const downloadResult = () => {
  if (!props.result) return
  
  const dataStr = JSON.stringify(props.result, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `embedding_result_${props.result.result_id}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  MessagePlugin.success('结果已下载')
}

const viewJsonFile = () => {
  if (!props.result?.json_file_path) return
  MessagePlugin.info('JSON文件路径: ' + props.result.json_file_path)
}
</script>

<style scoped>
.embedding-result-display {
  height: 100%;
}

.empty-state {
  padding: 40px;
  text-align: center;
}

.result-content {
  max-height: 800px;
  overflow-y: auto;
}

.success-count {
  color: var(--td-success-color);
  font-weight: 500;
}

.failed-count {
  color: var(--td-error-color);
  font-weight: 500;
}

.vector-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px;
}

.text-preview p {
  margin-top: 6px;
  padding: 8px;
  background: var(--td-bg-color-container);
  border-radius: 4px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.vector-values {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.metadata pre {
  margin-top: 6px;
  padding: 8px;
  background: var(--td-bg-color-container);
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.file-path {
  display: flex;
  align-items: center;
  font-size: 14px;
}
</style>
