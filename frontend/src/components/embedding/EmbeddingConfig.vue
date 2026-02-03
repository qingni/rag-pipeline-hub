<template>
  <div class="embedding-config">
    <el-form :model="config" label-position="top" size="default">
      <!-- 基本配置 -->
      <el-card class="config-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Setting /></el-icon>
            <span>基本配置</span>
          </div>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="嵌入模型">
              <el-select v-model="config.model" style="width: 100%">
                <el-option-group label="文本模型">
                  <el-option
                    v-for="model in textModels"
                    :key="model.name"
                    :label="model.display_name"
                    :value="model.name"
                  >
                    <span>{{ model.display_name }}</span>
                    <el-tag size="small" type="info" style="margin-left: 8px">
                      {{ model.dimension }}维
                    </el-tag>
                  </el-option>
                </el-option-group>
                <el-option-group label="多模态模型">
                  <el-option
                    v-for="model in multimodalModels"
                    :key="model.name"
                    :label="model.display_name"
                    :value="model.name"
                  >
                    <span>{{ model.display_name }}</span>
                    <el-tag size="small" type="warning" style="margin-left: 8px">
                      多模态
                    </el-tag>
                  </el-option>
                </el-option-group>
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="向量维度">
              <el-input :value="selectedModelDimension" disabled>
                <template #suffix>维</template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>
      
      <!-- 批量处理配置 -->
      <el-card class="config-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Collection /></el-icon>
            <span>批量处理</span>
            <el-switch
              v-model="config.batchEnabled"
              style="margin-left: auto"
              active-text="启用"
            />
          </div>
        </template>
        
        <template v-if="config.batchEnabled">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="批次大小">
                <el-slider
                  v-model="config.batchSize"
                  :min="10"
                  :max="100"
                  :step="10"
                  show-input
                />
              </el-form-item>
            </el-col>
            
            <el-col :span="12">
              <el-form-item label="并发数">
                <el-slider
                  v-model="config.concurrency"
                  :min="1"
                  :max="10"
                  show-input
                />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="重试策略">
            <el-radio-group v-model="config.retryStrategy">
              <el-radio value="exponential">指数退避</el-radio>
              <el-radio value="fixed">固定间隔</el-radio>
              <el-radio value="none">不重试</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-row :gutter="20" v-if="config.retryStrategy !== 'none'">
            <el-col :span="12">
              <el-form-item label="最大重试次数">
                <el-input-number
                  v-model="config.maxRetries"
                  :min="1"
                  :max="10"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </template>
      </el-card>
      
      <!-- 增量配置 -->
      <el-card class="config-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Refresh /></el-icon>
            <span>增量向量化</span>
            <el-switch
              v-model="config.incrementalEnabled"
              style="margin-left: auto"
              active-text="启用"
            />
          </div>
        </template>
        
        <template v-if="config.incrementalEnabled">
          <el-alert type="info" :closable="false" style="margin-bottom: 16px">
            <template #title>
              启用增量模式后，仅对新增或变更的分块进行向量化，复用未变化内容的向量。
            </template>
          </el-alert>
          
          <el-form-item label="强制重新计算">
            <el-switch v-model="config.forceRecompute" />
            <span class="form-hint">忽略缓存，重新计算所有向量</span>
          </el-form-item>
        </template>
      </el-card>
      
      <!-- 缓存配置 -->
      <el-card class="config-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Box /></el-icon>
            <span>向量缓存</span>
            <el-switch
              v-model="config.cacheEnabled"
              style="margin-left: auto"
              active-text="启用"
            />
          </div>
        </template>
        
        <template v-if="config.cacheEnabled">
          <CacheStatus compact :auto-refresh-interval="30000" />
        </template>
      </el-card>
      
      <!-- 多模态配置 -->
      <el-card class="config-section" shadow="never" v-if="isMultimodalModel">
        <template #header>
          <div class="section-header">
            <el-icon><Picture /></el-icon>
            <span>多模态处理</span>
          </div>
        </template>
        
        <el-form-item label="图片处理策略">
          <el-radio-group v-model="config.imageStrategy">
            <el-radio value="native">原生多模态（推荐）</el-radio>
            <el-radio value="caption">使用图片描述</el-radio>
            <el-radio value="skip">跳过图片</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="表格处理策略">
          <el-radio-group v-model="config.tableStrategy">
            <el-radio value="markdown">转换为Markdown</el-radio>
            <el-radio value="text">纯文本</el-radio>
            <el-radio value="skip">跳过表格</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-card>
      
      <!-- 操作按钮 -->
      <div class="form-actions">
        <el-button @click="resetConfig">重置</el-button>
        <el-button type="primary" @click="applyConfig">
          应用配置
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Setting, Collection, Refresh, Box, Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import CacheStatus from './CacheStatus.vue'

const props = defineProps({
  /**
   * 可用模型列表
   */
  models: {
    type: Array,
    default: () => [],
  },
  /**
   * 初始配置
   */
  initialConfig: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['config-change', 'apply'])

// 默认配置
const defaultConfig = {
  model: 'qwen3-embedding-8b',
  batchEnabled: true,
  batchSize: 50,
  concurrency: 3,
  retryStrategy: 'exponential',
  maxRetries: 3,
  incrementalEnabled: true,
  forceRecompute: false,
  cacheEnabled: true,
  imageStrategy: 'native',
  tableStrategy: 'markdown',
}

// 配置状态
const config = ref({ ...defaultConfig, ...props.initialConfig })

// 计算属性
const textModels = computed(() => {
  return props.models.filter(m => m.model_type !== 'multimodal')
})

const multimodalModels = computed(() => {
  return props.models.filter(m => m.model_type === 'multimodal')
})

const selectedModel = computed(() => {
  return props.models.find(m => m.name === config.value.model)
})

const selectedModelDimension = computed(() => {
  return selectedModel.value?.dimension || '-'
})

const isMultimodalModel = computed(() => {
  return selectedModel.value?.model_type === 'multimodal'
})

// 方法
function resetConfig() {
  config.value = { ...defaultConfig }
  ElMessage.info('配置已重置')
}

function applyConfig() {
  emit('apply', { ...config.value })
  ElMessage.success('配置已应用')
}

// 监听配置变化
watch(config, (newConfig) => {
  emit('config-change', { ...newConfig })
}, { deep: true })

// 初始化
onMounted(() => {
  if (props.models.length > 0 && !config.value.model) {
    config.value.model = props.models[0]?.name
  }
})
</script>

<style scoped>
.embedding-config {
  max-width: 800px;
}

.config-section {
  margin-bottom: 16px;
}

.config-section :deep(.el-card__header) {
  padding: 12px 16px;
  background: #fafafa;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.section-header .el-icon {
  color: #1890ff;
}

.form-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #8c8c8c;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
