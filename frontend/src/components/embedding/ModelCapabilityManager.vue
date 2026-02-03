<template>
  <div class="model-capability-manager">
    <!-- 标题和操作 -->
    <div class="manager-header">
      <h3>模型能力配置</h3>
      <div class="header-actions">
        <el-button @click="refreshModels" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="reloadConfig" :loading="reloading">
          <el-icon><Upload /></el-icon>
          重新加载配置
        </el-button>
      </div>
    </div>
    
    <!-- 模型列表 -->
    <div class="model-list">
      <el-collapse v-model="expandedModels" accordion>
        <el-collapse-item
          v-for="model in models"
          :key="model.model_name"
          :name="model.model_name"
        >
          <template #title>
            <div class="model-item-header">
              <div class="model-info">
                <span class="model-name">{{ model.display_name || model.model_name }}</span>
                <el-tag
                  :type="model.is_enabled ? 'success' : 'info'"
                  size="small"
                  effect="light"
                >
                  {{ model.is_enabled ? '启用' : '禁用' }}
                </el-tag>
                <el-tag
                  :type="model.model_type === 'multimodal' ? 'warning' : 'primary'"
                  size="small"
                  effect="plain"
                >
                  {{ model.model_type === 'multimodal' ? '多模态' : '文本' }}
                </el-tag>
              </div>
              <div class="model-dimension">
                维度: {{ model.dimension }}
              </div>
            </div>
          </template>
          
          <!-- 模型详情编辑 -->
          <div class="model-detail">
            <!-- 基本信息 -->
            <el-form :model="getEditingModel(model.model_name)" label-width="100px" size="small">
              <el-form-item label="启用状态">
                <el-switch
                  v-model="getEditingModel(model.model_name).is_enabled"
                  active-text="启用"
                  inactive-text="禁用"
                />
              </el-form-item>
              
              <el-form-item label="描述">
                <el-input
                  v-model="getEditingModel(model.model_name).description"
                  type="textarea"
                  :rows="2"
                />
              </el-form-item>
              
              <!-- 语言评分 -->
              <el-divider content-position="left">语言支持评分</el-divider>
              <div class="score-grid">
                <el-form-item
                  v-for="lang in languages"
                  :key="lang.key"
                  :label="lang.label"
                >
                  <el-slider
                    v-model="getEditingModel(model.model_name).language_scores[lang.key]"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :format-tooltip="formatPercent"
                  />
                </el-form-item>
              </div>
              
              <!-- 领域评分 -->
              <el-divider content-position="left">领域专长评分</el-divider>
              <div class="score-grid">
                <el-form-item
                  v-for="domain in domains"
                  :key="domain.key"
                  :label="domain.label"
                >
                  <el-slider
                    v-model="getEditingModel(model.model_name).domain_scores[domain.key]"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :format-tooltip="formatPercent"
                  />
                </el-form-item>
              </div>
              
              <!-- 多模态评分 -->
              <el-divider content-position="left">多模态能力</el-divider>
              <el-form-item label="多模态评分">
                <el-slider
                  v-model="getEditingModel(model.model_name).multimodal_score"
                  :min="0"
                  :max="1"
                  :step="0.05"
                  :format-tooltip="formatPercent"
                />
              </el-form-item>
              
              <!-- 操作按钮 -->
              <el-form-item>
                <el-button
                  type="primary"
                  @click="saveModel(model.model_name)"
                  :loading="savingModel === model.model_name"
                >
                  保存更改
                </el-button>
                <el-button @click="resetModel(model.model_name)">
                  重置
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
    
    <!-- 推荐权重配置 -->
    <div class="weights-section">
      <h4>推荐算法权重</h4>
      <el-form :model="weights" label-width="140px" size="small">
        <el-form-item label="语言匹配权重">
          <el-slider
            v-model="weights.language_match"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
            show-input
          />
        </el-form-item>
        <el-form-item label="领域匹配权重">
          <el-slider
            v-model="weights.domain_match"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
            show-input
          />
        </el-form-item>
        <el-form-item label="多模态支持权重">
          <el-slider
            v-model="weights.multimodal_support"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
            show-input
          />
        </el-form-item>
        <el-form-item>
          <el-tag :type="weightsSumValid ? 'success' : 'danger'">
            权重总和: {{ weightsSum.toFixed(2) }}
            {{ weightsSumValid ? '✓' : '(建议为1.0)' }}
          </el-tag>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Refresh, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  /**
   * API 基础路径
   */
  apiBase: {
    type: String,
    default: '/api/v1',
  },
})

const emit = defineEmits(['model-updated', 'config-reloaded'])

// 语言和领域定义
const languages = [
  { key: 'zh', label: '中文' },
  { key: 'en', label: '英文' },
  { key: 'ja', label: '日语' },
  { key: 'ko', label: '韩语' },
  { key: 'de', label: '德语' },
  { key: 'fr', label: '法语' },
]

const domains = [
  { key: 'tech', label: '技术' },
  { key: 'business', label: '商业' },
  { key: 'medical', label: '医学' },
  { key: 'legal', label: '法律' },
  { key: 'general', label: '通用' },
]

// 状态
const loading = ref(false)
const reloading = ref(false)
const savingModel = ref('')
const models = ref([])
const editingModels = reactive({})
const expandedModels = ref('')
const weights = reactive({
  language_match: 0.40,
  domain_match: 0.35,
  multimodal_support: 0.25,
})

// 计算权重总和
const weightsSum = computed(() => {
  return weights.language_match + weights.domain_match + weights.multimodal_support
})

const weightsSumValid = computed(() => {
  return Math.abs(weightsSum.value - 1.0) < 0.01
})

// 方法
function formatPercent(val) {
  return `${(val * 100).toFixed(0)}%`
}

function getEditingModel(modelName) {
  if (!editingModels[modelName]) {
    const model = models.value.find(m => m.model_name === modelName)
    if (model) {
      editingModels[modelName] = {
        is_enabled: model.is_enabled,
        description: model.description || '',
        language_scores: { ...model.language_scores },
        domain_scores: { ...model.domain_scores },
        multimodal_score: model.multimodal_score || 0,
      }
    } else {
      editingModels[modelName] = {
        is_enabled: true,
        description: '',
        language_scores: {},
        domain_scores: {},
        multimodal_score: 0,
      }
    }
  }
  return editingModels[modelName]
}

function resetModel(modelName) {
  const model = models.value.find(m => m.model_name === modelName)
  if (model) {
    editingModels[modelName] = {
      is_enabled: model.is_enabled,
      description: model.description || '',
      language_scores: { ...model.language_scores },
      domain_scores: { ...model.domain_scores },
      multimodal_score: model.multimodal_score || 0,
    }
  }
}

async function refreshModels() {
  loading.value = true
  try {
    const response = await fetch(`${props.apiBase}/embedding/recommend/models?enabled_only=false`)
    if (!response.ok) throw new Error('Failed to fetch models')
    const data = await response.json()
    models.value = data.models || []
    
    // 获取权重
    const weightsResponse = await fetch(`${props.apiBase}/embedding/recommend/weights`)
    if (weightsResponse.ok) {
      const weightsData = await weightsResponse.json()
      Object.assign(weights, weightsData.weights || {})
    }
  } catch (error) {
    console.error('Failed to refresh models:', error)
    ElMessage.error('获取模型列表失败')
  } finally {
    loading.value = false
  }
}

async function saveModel(modelName) {
  savingModel.value = modelName
  try {
    const editing = editingModels[modelName]
    const response = await fetch(`${props.apiBase}/embedding/recommend/models/${modelName}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        is_enabled: editing.is_enabled,
        description: editing.description,
        language_scores: editing.language_scores,
        domain_scores: editing.domain_scores,
        multimodal_score: editing.multimodal_score,
      }),
    })
    
    if (!response.ok) throw new Error('Failed to update model')
    
    ElMessage.success('模型配置已更新')
    emit('model-updated', modelName)
    await refreshModels()
  } catch (error) {
    console.error('Failed to save model:', error)
    ElMessage.error('保存失败')
  } finally {
    savingModel.value = ''
  }
}

async function reloadConfig() {
  reloading.value = true
  try {
    const response = await fetch(`${props.apiBase}/embedding/recommend/reload`, {
      method: 'POST',
    })
    if (!response.ok) throw new Error('Failed to reload config')
    
    ElMessage.success('配置已重新加载')
    emit('config-reloaded')
    await refreshModels()
  } catch (error) {
    console.error('Failed to reload config:', error)
    ElMessage.error('重新加载失败')
  } finally {
    reloading.value = false
  }
}

onMounted(() => {
  refreshModels()
})
</script>

<style scoped>
.model-capability-manager {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.manager-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 模型列表 */
.model-list {
  margin-bottom: 24px;
}

.model-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 16px;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.model-name {
  font-weight: 600;
  font-size: 15px;
}

.model-dimension {
  font-size: 13px;
  color: #8c8c8c;
}

.model-detail {
  padding: 16px 0;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0 24px;
}

/* 权重配置 */
.weights-section {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
}

.weights-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 500;
}
</style>
