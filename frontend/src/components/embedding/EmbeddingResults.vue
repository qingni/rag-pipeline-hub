<template>
  <div class="results">
    <t-card v-if="!result" title="结果预览" :bordered="false">
      <t-empty description="等待请求" />
    </t-card>

    <template v-else-if="isSingle">
      <t-card title="单文本结果" :bordered="false" class="mb-4">
        <div class="summary-grid">
          <div>
            <p class="label">模型</p>
            <p class="value">{{ singleData.metadata.model }}</p>
          </div>
          <div>
            <p class="label">维度</p>
            <p class="value">{{ singleData.vector.dimension }}</p>
          </div>
          <div>
            <p class="label">耗时 (ms)</p>
            <p class="value">{{ singleData.metadata.processing_time_ms.toFixed(2) }}</p>
          </div>
          <div>
            <p class="label">重试次数</p>
            <p class="value">{{ singleData.metadata.retry_count }}</p>
          </div>
          <div>
            <p class="label">Rate Limit 命中</p>
            <p class="value">{{ singleData.metadata.rate_limit_hits }}</p>
          </div>
        </div>
      </t-card>
      <t-card title="向量预览" :bordered="false">
        <div class="vector-preview">
          <div class="vector-values">
            <span
              v-for="(value, idx) in vectorPreview"
              :key="idx"
              class="vector-chip"
            >
              {{ value.toFixed(4) }}
            </span>
            <span v-if="singleData.vector.vector.length > vectorPreview.length" class="vector-chip muted">
              ... ({{ singleData.vector.vector.length - vectorPreview.length }} more)
            </span>
          </div>
        </div>
      </t-card>
    </template>

    <template v-else>
      <t-card title="批量结果概览" :bordered="false" class="mb-4">
        <div class="summary-grid">
          <div>
            <p class="label">模型</p>
            <p class="value">{{ batchData.metadata.model }}</p>
          </div>
          <div>
            <p class="label">批量大小</p>
            <p class="value">{{ batchData.metadata.batch_size }}</p>
          </div>
          <div>
            <p class="label">成功 / 失败</p>
            <p class="value text-green-600">{{ batchData.metadata.successful_count }} / {{ batchData.metadata.failed_count }}</p>
          </div>
          <div>
            <p class="label">耗时 (ms)</p>
            <p class="value">{{ batchData.metadata.processing_time_ms.toFixed(2) }}</p>
          </div>
          <div>
            <p class="label">吞吐 (向量/秒)</p>
            <p class="value">{{ (batchData.metadata.vectors_per_second || 0).toFixed(2) }}</p>
          </div>
          <div>
            <p class="label">重试 / Rate Limit</p>
            <p class="value">{{ batchData.metadata.retry_count }} / {{ batchData.metadata.rate_limit_hits }}</p>
          </div>
        </div>
      </t-card>

      <div class="grid-cols gap-4">
        <t-card title="成功向量" :bordered="false">
          <t-table
            v-if="batchData.vectors.length"
            :data="batchVectorRows"
            :columns="successColumns"
            row-key="index"
            size="small"
            :pagination="{ pageSize: 10 }"
          />
          <t-empty v-else description="没有成功记录" />
        </t-card>
        <t-card title="失败详情" :bordered="false" class="mt-4">
          <t-table
            v-if="batchData.failures.length"
            :data="batchFailureRows"
            :columns="failureColumns"
            row-key="index"
            size="small"
            :pagination="{ pageSize: 10 }"
          />
          <t-empty v-else description="没有失败记录" />
        </t-card>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

defineOptions({
  name: 'EmbeddingResults',
})

const props = defineProps({
  result: {
    type: Object,
    default: null,
  },
})

const isSingle = computed(() => props.result?.mode === 'single')
const singleData = computed(() => (isSingle.value ? props.result.data : null))
const batchData = computed(() => (!isSingle.value && props.result ? props.result.data : null))

const vectorPreview = computed(() => {
  if (!singleData.value?.vector?.vector) {
    return []
  }
  return singleData.value.vector.vector.slice(0, 12)
})

const batchVectorRows = computed(() => {
  if (!batchData.value) {
    return []
  }
  return batchData.value.vectors.map((item) => ({
    index: item.index,
    textLength: item.text_length,
    dimension: item.dimension,
    processing: item.processing_time_ms ? item.processing_time_ms.toFixed(2) : '—',
    preview: item.vector.slice(0, 4).map((n) => n.toFixed(3)).join(', '),
  }))
})

const batchFailureRows = computed(() => {
  if (!batchData.value) {
    return []
  }
  return batchData.value.failures.map((item) => ({
    index: item.index,
    errorType: item.error_type,
    retryRecommended: item.retry_recommended ? '是' : '否',
    retryCount: item.retry_count,
    message: item.error_message,
    preview: item.text_preview || '—',
  }))
})

const successColumns = [
  { colKey: 'index', title: '索引', width: 80 },
  { colKey: 'textLength', title: '文本长度' },
  { colKey: 'dimension', title: '维度', width: 100 },
  { colKey: 'processing', title: '耗时 (ms)' },
  { colKey: 'preview', title: '向量预览' },
]

const failureColumns = [
  { colKey: 'index', title: '索引', width: 80 },
  { colKey: 'errorType', title: '错误类型', width: 160 },
  { colKey: 'message', title: '错误信息' },
  { colKey: 'retryRecommended', title: '建议重试', width: 120 },
  { colKey: 'retryCount', title: '重试次数', width: 120 },
  { colKey: 'preview', title: '文本预览' },
]
</script>

<style scoped>
.results {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}

.label {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.125rem;
}

.value {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.vector-preview {
  padding: 0.5rem 0;
}

.vector-values {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.vector-chip {
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background-color: #edf2ff;
  font-size: 0.85rem;
  color: #1d4ed8;
}

.vector-chip.muted {
  background-color: #f3f4f6;
  color: #6b7280;
}

.grid-cols {
  display: flex;
  flex-direction: column;
}
</style>
