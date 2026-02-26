<template>
  <div class="vector-index-page">
    <t-layout>
      <!-- 左侧控制面板 -->
      <t-aside width="380px" class="control-panel">
        <div class="panel-header">
          <DatabaseIcon :size="24" class="panel-icon" />
          <h2 class="panel-title">向量索引</h2>
        </div>
        
        <div class="panel-content">
          <!-- 向量化结果选择 -->
          <div class="form-section">
            <label class="section-label">
              <FileTextIcon :size="16" />
              文档向量化结果
            </label>
            <t-select
              v-model="selectedEmbeddingId"
              placeholder="请选择已完成的文档向量化结果"
              :loading="loadingEmbeddings"
              filterable
              clearable
              :popup-props="{ overlayClassName: 'vector-index-select-popup' }"
              @change="handleEmbeddingSelect"
            >
              <t-option
                v-for="task in embeddingTasks"
                :key="task.result_id"
                :value="task.result_id"
                :label="task.document_name || task.result_id"
              >
                <div class="select-option-item">
                  <div class="select-option-name">{{ task.document_name || '未命名文档' }}</div>
                  <div class="select-option-desc">{{ task.model }} · {{ task.vector_dimension }}维 · {{ task.successful_count || 0 }}向量</div>
                </div>
              </t-option>
            </t-select>
            <t-button
              variant="text"
              theme="primary"
              size="small"
              class="refresh-btn"
              @click="loadEmbeddingTasks"
            >
              <RefreshIcon :size="14" />
              刷新列表
            </t-button>
          </div>

          <!-- 选中任务的详情 -->
          <div v-if="selectedEmbedding" class="embedding-details">
            <t-descriptions :column="1" size="small">
              <t-descriptions-item label="文档">
                {{ selectedEmbedding.document_name || '未命名' }}
              </t-descriptions-item>
              <t-descriptions-item label="模型">
                {{ selectedEmbedding.model }}
              </t-descriptions-item>
              <t-descriptions-item label="维度">
                {{ selectedEmbedding.vector_dimension }}
              </t-descriptions-item>
              <t-descriptions-item label="向量数">
                {{ selectedEmbedding.successful_count || 0 }}
              </t-descriptions-item>
            </t-descriptions>
          </div>

          <!-- 向量数据库选择 -->
          <div class="form-section">
            <label class="section-label">
              <ServerIcon :size="16" />
              向量数据库
            </label>
            <t-select 
              v-model="indexConfig.provider" 
              placeholder="请选择向量数据库"
              :popup-props="{ overlayClassName: 'vector-index-select-popup' }"
            >
              <t-option value="MILVUS" label="Milvus - 分布式数据库（推荐）">
                <div class="select-option-item">
                  <div class="select-option-name">Milvus（推荐）</div>
                  <div class="select-option-desc">分布式向量数据库，适合生产环境和大规模数据</div>
                </div>
              </t-option>
            </t-select>
          </div>

          <!-- 推荐兜底提示 -->
          <RecommendFallback
            :visible="showFallbackAlert"
            @close="showFallbackAlert = false"
          />

          <!-- 索引算法选择 -->
          <div class="form-section">
            <label class="section-label">
              <CpuIcon :size="16" />
              索引算法
            </label>
            <RecommendBadge
              v-if="recommendation && !recommendLoading"
              :reason="recommendation.reason"
              :is-fallback="recommendation.is_fallback"
            />
            <t-select
              v-model="indexConfig.algorithm"
              placeholder="请选择索引算法"
              :loading="recommendLoading"
              :popup-props="{ overlayClassName: 'vector-index-select-popup' }"
            >
              <t-option value="FLAT" label="FLAT - 暴力搜索（默认）">
                <div class="select-option-item">
                  <div class="select-option-name">FLAT（默认）</div>
                  <div class="select-option-desc">暴力搜索，精确匹配，100%召回率</div>
                </div>
              </t-option>
              <t-option value="HNSW" label="HNSW - 图索引">
                <div class="select-option-item">
                  <div class="select-option-name">HNSW</div>
                  <div class="select-option-desc">图索引，高性能低延迟，适合大规模数据</div>
                </div>
              </t-option>
              <t-option value="IVF_FLAT" label="IVF_FLAT - 倒排索引">
                <div class="select-option-item">
                  <div class="select-option-name">IVF_FLAT</div>
                  <div class="select-option-desc">倒排索引，平衡精度与速度</div>
                </div>
              </t-option>
              <t-option value="IVF_SQ8" label="IVF_SQ8 - 标量量化">
                <div class="select-option-item">
                  <div class="select-option-name">IVF_SQ8</div>
                  <div class="select-option-desc">标量量化，精度损失极小，节省约75%内存</div>
                </div>
              </t-option>
              <t-option value="IVF_PQ" label="IVF_PQ - 乘积量化">
                <div class="select-option-item">
                  <div class="select-option-name">IVF_PQ</div>
                  <div class="select-option-desc">乘积量化，大幅压缩内存，适合超大规模数据</div>
                </div>
              </t-option>
            </t-select>
          </div>

          <!-- 度量类型选择 -->
          <div class="form-section">
            <label class="section-label">
              <RulerIcon :size="16" />
              度量类型
            </label>
            <t-select 
              v-model="indexConfig.metric_type" 
              placeholder="请选择度量类型"
              :popup-props="{ overlayClassName: 'vector-index-select-popup' }"
            >
              <t-option value="cosine" label="余弦相似度">
                <div class="select-option-item">
                  <div class="select-option-name">余弦相似度 (Cosine)</div>
                  <div class="select-option-desc">衡量向量方向相似性，适合文本语义匹配</div>
                </div>
              </t-option>
              <t-option value="euclidean" label="欧氏距离">
                <div class="select-option-item">
                  <div class="select-option-name">欧氏距离 (Euclidean)</div>
                  <div class="select-option-desc">衡量向量空间距离，适合图像特征匹配</div>
                </div>
              </t-option>
              <t-option value="dot_product" label="点积">
                <div class="select-option-item">
                  <div class="select-option-name">点积 (Dot Product)</div>
                  <div class="select-option-desc">向量内积运算，适合归一化向量</div>
                </div>
              </t-option>
            </t-select>
          </div>

          <!-- 索引名称（可选） -->
          <div class="form-section">
            <label class="section-label">
              <TagIcon :size="16" />
              索引名称
              <span class="optional-hint">（可选）</span>
            </label>
            <t-input
              v-model="indexConfig.name"
              placeholder="留空则自动生成"
              clearable
            />
          </div>

          <!-- 开始按钮 -->
          <t-button
            theme="primary"
            size="large"
            block
            :loading="isCreating"
            :disabled="!canStartIndexing"
            @click="handleStartIndexing"
          >
            <template #icon>
              <PlayIcon :size="18" />
            </template>
            {{ buttonText }}
          </t-button>

          <!-- 已存在索引提示 -->
          <div v-if="matchingIndex && !isCreating" class="matching-hint">
            <AlertCircleIcon :size="14" />
            <span>已存在相同配置的索引，点击按钮可覆盖</span>
          </div>

          <!-- 验证提示 -->
          <div v-if="!canStartIndexing && !isCreating" class="validation-hint">
            <AlertCircleIcon :size="14" />
            <span>{{ validationMessage }}</span>
          </div>

          <!-- 错误提示 -->
          <t-alert
            v-if="error"
            theme="error"
            :message="error"
            close
            @close="error = null"
          />
        </div>
      </t-aside>
      
      <!-- 右侧结果面板 -->
      <t-content class="main-content">
        <t-tabs v-model="activeTab" class="full-height-tabs">
          <!-- Tab 1: 索引结果 -->
          <t-tab-panel value="result" label="索引结果" class="tab-panel-content">
            <div v-if="currentIndex" class="result-container">
              <!-- 索引详情卡片 -->
              <t-card class="index-detail-card" :bordered="false">
                <template #header>
                  <div class="card-header">
                    <span class="card-title">索引详情</span>
                    <t-tag :theme="getStatusTheme(currentIndex.status)" variant="light">
                      {{ getStatusText(currentIndex.status) }}
                    </t-tag>
                  </div>
                </template>
                
                <t-descriptions :column="2" bordered>
                  <t-descriptions-item label="索引名称" :span="2">
                    <span class="index-name-text">{{ currentIndex.index_name }}</span>
                  </t-descriptions-item>
                  <t-descriptions-item label="索引ID">
                    <t-tooltip :content="currentIndex.uuid || '-'" placement="top">
                      <span class="uuid-short">{{ currentIndex.uuid ? currentIndex.uuid.substring(0, 8) : '-' }}</span>
                    </t-tooltip>
                  </t-descriptions-item>
                  <t-descriptions-item label="向量数据库">
                    <t-tag variant="outline">{{ currentIndex.index_type }}</t-tag>
                  </t-descriptions-item>
                  <t-descriptions-item label="索引算法">
                    <t-tag variant="outline" theme="warning">{{ currentIndex.algorithm_type || 'FLAT' }}</t-tag>
                  </t-descriptions-item>
                  <t-descriptions-item label="向量维度">
                    {{ currentIndex.dimension }}
                  </t-descriptions-item>
                  <t-descriptions-item label="度量类型">
                    {{ currentIndex.metric_type }}
                  </t-descriptions-item>
                  <t-descriptions-item label="向量数量">
                    <span class="highlight-value">{{ formatNumber(currentIndex.vector_count || 0) }}</span>
                  </t-descriptions-item>
                  <t-descriptions-item label="创建时间">
                    {{ formatDate(currentIndex.created_at) }}
                  </t-descriptions-item>
                  <t-descriptions-item label="Sparse向量">
                    <t-tag :theme="currentIndex.has_sparse ? 'success' : 'default'" variant="light">
                      {{ currentIndex.has_sparse ? '已生成' : '未生成' }}
                    </t-tag>
                  </t-descriptions-item>
                  <t-descriptions-item v-if="currentIndex.source_document_name" label="源文档" :span="2">
                    {{ currentIndex.source_document_name }}
                  </t-descriptions-item>
                  <t-descriptions-item v-if="currentIndex.source_model" label="向量模型" :span="2">
                    {{ currentIndex.source_model }}
                  </t-descriptions-item>
                </t-descriptions>

                <!-- 操作按钮 -->
                <div class="action-buttons">
                  <t-button
                    theme="danger"
                    variant="outline"
                    @click="handleDeleteIndex(currentIndex.id)"
                  >
                    <template #icon><TrashIcon :size="16" /></template>
                    删除索引
                  </t-button>
                </div>
              </t-card>
            </div>
            
            <!-- 空状态 -->
            <div v-else class="empty-result">
              <t-empty :description="emptyDescription">
                <template #image>
                  <DatabaseIcon :size="64" class="empty-icon" />
                </template>
                <p class="empty-hint">{{ emptyHint }}</p>
              </t-empty>
            </div>
          </t-tab-panel>
          
          <!-- Tab 2: 历史记录 -->
          <t-tab-panel value="history" label="历史记录" class="tab-panel-content">
            <t-card :bordered="false" class="history-card">
              <template #header>
                <div class="card-header">
                  <span class="card-title">索引历史</span>
                  <t-space size="small">
                    <t-button variant="text" @click="loadIndexes">
                      <template #icon><RefreshIcon :size="14" /></template>
                      刷新
                    </t-button>
                    <t-popconfirm
                      content="确定要清空所有历史记录吗？此操作不可恢复。"
                      @confirm="handleClearAllHistory"
                    >
                      <t-button variant="text" theme="danger" :disabled="!indexes.length">
                        <template #icon><TrashIcon :size="14" /></template>
                        一键清空
                      </t-button>
                    </t-popconfirm>
                  </t-space>
                </div>
              </template>

              <t-table
                :data="indexes"
                :columns="historyColumns"
                :loading="loadingIndexes"
                row-key="id"
                stripe
                hover
                :pagination="pagination"
              >
                <template #index_name="{ row }">
                  <div class="index-name-cell">
                    <span class="name">{{ row.index_name }}</span>
                    <t-tag v-if="row.source_document_name" size="small" variant="light" theme="primary">
                      {{ row.source_document_name }}
                    </t-tag>
                  </div>
                </template>

                <template #status="{ row }">
                  <t-tag :theme="getStatusTheme(row.status)" variant="light">
                    <template #icon>
                      <LoadingIcon v-if="row.status === 'BUILDING'" class="spin-icon" />
                    </template>
                    {{ getStatusText(row.status) }}
                  </t-tag>
                </template>

                <template #uuid="{ row }">
                  <t-tooltip :content="row.uuid || '-'" placement="top">
                    <span class="uuid-short">{{ row.uuid ? row.uuid.substring(0, 8) : '-' }}</span>
                  </t-tooltip>
                </template>

                <template #created_at="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>

                <template #operation="{ row }">
                  <t-space>
                    <t-button
                      theme="primary"
                      variant="text"
                      size="small"
                      @click="handleViewDetail(row)"
                    >
                      查看详情
                    </t-button>
                    <t-button
                      theme="danger"
                      variant="text"
                      size="small"
                      @click="handleDeleteIndex(row.id)"
                    >
                      删除
                    </t-button>
                  </t-space>
                </template>
              </t-table>
            </t-card>
          </t-tab-panel>
        </t-tabs>
      </t-content>
    </t-layout>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next';
import { 
  Database as DatabaseIcon,
  FileText as FileTextIcon,
  Server as ServerIcon,
  Cpu as CpuIcon,
  Ruler as RulerIcon,
  Tag as TagIcon,
  Play as PlayIcon,
  AlertCircle as AlertCircleIcon,
  Trash2 as TrashIcon,
  RefreshCw as RefreshIcon,
  Loader as LoadingIcon
} from 'lucide-vue-next';
import { useVectorIndexStore } from '../stores/vectorIndexStore';
import { findMatchingIndex } from '../services/vectorIndexApi';
import { storeToRefs } from 'pinia';
import RecommendBadge from '../components/VectorIndex/RecommendBadge.vue';
import RecommendFallback from '../components/VectorIndex/RecommendFallback.vue';

const vectorIndexStore = useVectorIndexStore();
const { indexes, currentIndex, recommendation, recommendLoading } = storeToRefs(vectorIndexStore);

// 状态
const activeTab = ref('result');
const selectedEmbeddingId = ref('');
const selectedEmbedding = ref(null);
const loadingEmbeddings = ref(false);
const loadingIndexes = ref(false);
const isCreating = ref(false);
const error = ref(null);
const embeddingTasks = ref([]);
const matchingIndex = ref(null);  // 匹配的已存在索引
const checkingMatch = ref(false);  // 检查中状态
const showFallbackAlert = ref(false);  // 推荐兜底提示

let refreshInterval = null;

// 索引配置
const indexConfig = reactive({
  provider: 'MILVUS',  // 默认使用 Milvus
  algorithm: 'FLAT',   // 默认使用 FLAT
  metric_type: 'cosine',
  name: ''
});

// 历史记录表格列
const historyColumns = [
{ colKey: 'uuid', title: 'ID', width: 120, cell: 'uuid' },
  { colKey: 'index_name', title: '索引名称', width: 200, cell: 'index_name' },
  { colKey: 'index_type', title: '数据库', width: 80 },
  { colKey: 'metric_type', title: '度量类型', width: 100 },
  { colKey: 'algorithm_type', title: '算法', width: 90 },
  { colKey: 'dimension', title: '维度', width: 70 },
  { colKey: 'vector_count', title: '向量数', width: 80 },
  { colKey: 'status', title: '状态', width: 90, cell: 'status' },
  { colKey: 'created_at', title: '创建时间', width: 150, cell: 'created_at' },
  { colKey: 'operation', title: '操作', width: 150, cell: 'operation', fixed: 'right' }
];

const pagination = computed(() => ({
  total: indexes.value.length,
  pageSize: 10,
  current: 1
}));

// 验证
const canStartIndexing = computed(() => {
  return selectedEmbeddingId.value && !isCreating.value;
});

const validationMessage = computed(() => {
  if (!selectedEmbeddingId.value) {
    return '请选择文档向量化结果';
  }
  return '';
});

// 按钮文字
const buttonText = computed(() => {
  if (isCreating.value) return '索引构建中...';
  if (matchingIndex.value) return '覆盖索引';
  return '开始索引';
});

// 空状态描述
const emptyDescription = computed(() => {
  if (!selectedEmbeddingId.value) {
    return '暂无索引结果';
  }
  if (checkingMatch.value) {
    return '正在检查...';
  }
  return '无匹配的向量索引';
});

// 空状态提示
const emptyHint = computed(() => {
  if (!selectedEmbeddingId.value) {
    return '请在左侧选择向量化任务并开始索引';
  }
  if (checkingMatch.value) {
    return '正在检查当前配置下是否存在向量索引...';
  }
  return '当前配置下不存在向量索引，请点击"开始索引"创建';
});

// 检查是否存在匹配的索引
const checkMatchingIndex = async () => {
  if (!selectedEmbeddingId.value) {
    matchingIndex.value = null;
    vectorIndexStore.setCurrentIndex(null);
    return;
  }
  
  checkingMatch.value = true;
  try {
    const result = await findMatchingIndex({
      embedding_result_id: selectedEmbeddingId.value,
      provider: indexConfig.provider,
      algorithm_type: indexConfig.algorithm,
      metric_type: indexConfig.metric_type
    });
    
    if (result.found && result.index) {
      matchingIndex.value = result.index;
      // 自动展示已存在的索引
      vectorIndexStore.setCurrentIndex(result.index);
      activeTab.value = 'result';
    } else {
      matchingIndex.value = null;
      // 无匹配索引时清除右侧展示，显示无数据状态
      vectorIndexStore.setCurrentIndex(null);
    }
  } catch (err) {
    console.error('检查匹配索引失败:', err);
    matchingIndex.value = null;
    vectorIndexStore.setCurrentIndex(null);
  } finally {
    checkingMatch.value = false;
  }
};

// 监听配置变化，自动检查匹配索引
watch(
  () => [selectedEmbeddingId.value, indexConfig.provider, indexConfig.algorithm, indexConfig.metric_type],
  () => {
    checkMatchingIndex();
  },
  { immediate: false }
);

// 方法
const loadEmbeddingTasks = async () => {
  loadingEmbeddings.value = true;
  try {
    const result = await vectorIndexStore.fetchEmbeddingTasks();
    // API 返回 { tasks: [], total: N, ... }，只显示已完成的任务
    const tasks = result?.tasks || result || [];
    embeddingTasks.value = tasks.filter(t => t.status === 'SUCCESS' || t.status === 'PARTIAL_SUCCESS');
  } catch (err) {
    console.error('加载向量化任务失败:', err);
    embeddingTasks.value = [];
  } finally {
    loadingEmbeddings.value = false;
  }
};

const loadIndexes = async () => {
  loadingIndexes.value = true;
  try {
    await vectorIndexStore.fetchIndexes();
  } catch (err) {
    MessagePlugin.error('加载索引列表失败');
  } finally {
    loadingIndexes.value = false;
  }
};

const handleEmbeddingSelect = async (taskId) => {
  const task = embeddingTasks.value.find(t => t.result_id === taskId);
  selectedEmbedding.value = task || null;
  showFallbackAlert.value = false;
  
  // 通过 store 触发智能推荐
  if (taskId) {
    vectorIndexStore.selectEmbeddingTask(taskId);
  }
  // checkMatchingIndex 会通过 watch 自动触发
};

// Milvus 原生度量类型 → 前端 select value 映射
const mapMetricType = (milvusMetric) => {
  const map = {
    'COSINE': 'cosine',
    'L2': 'euclidean',
    'IP': 'dot_product',
  };
  const upper = (milvusMetric || '').toUpperCase();
  return map[upper] || 'cosine';
};

// 监听推荐结果，自动更新索引算法和度量类型
watch(recommendation, (rec) => {
  if (rec && selectedEmbedding.value) {
    indexConfig.algorithm = rec.recommended_index_type || 'FLAT';
    indexConfig.metric_type = mapMetricType(rec.recommended_metric_type);
    showFallbackAlert.value = rec.is_fallback || false;
  }
});

const handleStartIndexing = async () => {
  if (!canStartIndexing.value) return;
  
  // 如果存在匹配的索引，先确认是否覆盖
  if (matchingIndex.value) {
    const dialog = DialogPlugin.confirm({
      header: '覆盖确认',
      body: `已存在相同配置的索引「${matchingIndex.value.index_name}」，是否删除并重新创建？`,
      confirmBtn: { theme: 'warning', content: '覆盖' },
      cancelBtn: '取消',
      onConfirm: async () => {
        dialog.destroy();
        // 先删除旧索引
        try {
          await vectorIndexStore.removeIndex(matchingIndex.value.id);
          matchingIndex.value = null;
          // 然后创建新索引
          await doCreateIndex();
        } catch (err) {
          error.value = '删除旧索引失败: ' + (err.message || '未知错误');
          MessagePlugin.error(error.value);
        }
      }
    });
    return;
  }
  
  await doCreateIndex();
};

const doCreateIndex = async () => {
  isCreating.value = true;
  error.value = null;
  
  try {
    const result = await vectorIndexStore.createIndexFromEmbedding({
      embedding_result_id: selectedEmbeddingId.value,
      name: indexConfig.name || undefined,
      provider: indexConfig.provider,
      index_type: indexConfig.algorithm,
      metric_type: indexConfig.metric_type,
      index_params: {}
    });
    
    MessagePlugin.success('索引创建任务已提交，正在构建中...');
    activeTab.value = 'result';
    
    // 设置当前索引
    if (result) {
      vectorIndexStore.setCurrentIndex(result);
    }
    
    // 刷新列表并开始轮询
    await loadIndexes();
    startPolling();
  } catch (err) {
    error.value = err.message || '创建索引失败';
    MessagePlugin.error(error.value);
  } finally {
    isCreating.value = false;
  }
};

const handleViewDetail = (row) => {
  vectorIndexStore.setCurrentIndex(row);
  activeTab.value = 'result';
};

const deletingIndexId = ref(null);

const handleClearAllHistory = async () => {
  try {
    const result = await vectorIndexStore.clearAllHistory();
    MessagePlugin.success(result.message || '已清空所有历史记录');
    await loadIndexes();
  } catch (err) {
    MessagePlugin.error('清空失败: ' + (err.message || '未知错误'));
  }
};

const handleDeleteIndex = (indexId) => {
  // 防止重复触发删除
  if (deletingIndexId.value === indexId) return;
  
  const dialog = DialogPlugin.confirm({
    header: '确认删除',
    body: '确定要删除这个索引吗？此操作不可恢复。',
    confirmBtn: { theme: 'danger', content: '删除' },
    onConfirm: async () => {
      // 防止重复点击确认按钮
      if (deletingIndexId.value) return;
      deletingIndexId.value = indexId;
      
      // 更新按钮状态为loading
      dialog.update({ confirmBtn: { theme: 'danger', content: '删除中...', loading: true }, cancelBtn: { disabled: true } });
      
      try {
        await vectorIndexStore.removeIndex(indexId);
        MessagePlugin.success('索引删除成功');
        
        // 如果删除的是当前索引，清空
        if (currentIndex.value?.id === indexId) {
          vectorIndexStore.setCurrentIndex(null);
        }
        
        // 刷新列表
        await loadIndexes();
      } catch (err) {
        MessagePlugin.error('删除失败: ' + (err.message || '未知错误'));
      } finally {
        deletingIndexId.value = null;
        dialog.destroy();
      }
    }
  });
};

// 轮询检查构建状态
const startPolling = () => {
  if (refreshInterval) return;
  
  refreshInterval = setInterval(async () => {
    await loadIndexes();
    
    const buildingIndexes = indexes.value.filter(idx => idx.status === 'BUILDING');
    if (buildingIndexes.length === 0) {
      stopPolling();
      
      // 更新当前索引状态
      if (currentIndex.value) {
        const updated = indexes.value.find(idx => idx.id === currentIndex.value.id);
        if (updated) {
          vectorIndexStore.setCurrentIndex(updated);
        }
      }
    }
  }, 3000);
};

const stopPolling = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
};

// 工具函数
const getStatusTheme = (status) => {
  const map = { BUILDING: 'warning', READY: 'success', UPDATING: 'primary', ERROR: 'danger' };
  return map[status] || 'default';
};

const getStatusText = (status) => {
  const map = { BUILDING: '构建中', READY: '就绪', UPDATING: '更新中', ERROR: '错误' };
  return map[status] || status;
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  // 后端返回的是 UTC 时间，如果没有时区标识则添加 'Z' 确保正确解析
  let str = dateString;
  if (typeof str === 'string' && !str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) {
    str = str + 'Z';
  }
  return new Date(str).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  });
};

const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
};

onMounted(() => {
  loadEmbeddingTasks();
  loadIndexes();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.vector-index-page {
  height: 100vh;
  background-color: var(--td-bg-color-page);
}

.control-panel {
  background-color: var(--td-bg-color-container);
  border-right: 1px solid var(--td-component-border);
  overflow-y: auto;
  height: 100vh;
  flex-shrink: 0;
  min-width: 380px;
  max-width: 380px;
}

.panel-header {
  display: flex;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.panel-icon {
  color: #3b82f6;
  margin-right: 0.75rem;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.panel-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.optional-hint {
  font-size: 12px;
  font-weight: 400;
  color: #9ca3af;
}

.refresh-btn {
  align-self: flex-start;
  margin-top: 4px;
}

.embedding-option {
  padding: 4px 0;
}

.embedding-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.embedding-name {
  font-weight: 500;
}

.embedding-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.embedding-details {
  padding: 12px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  border: 1px solid var(--td-component-border);
  overflow: hidden;

  :deep(.t-descriptions__body) {
    table-layout: fixed;
    width: 100%;
  }

  :deep(.t-descriptions__label) {
    width: 60px;
  }

  :deep(.t-descriptions__content) {
    word-break: break-all;
    overflow-wrap: break-word;
  }
}

/* 下拉选项统一样式 */
.select-option-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
}

.select-option-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
}

.select-option-desc {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  line-height: 1.4;
}

.validation-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background-color: #fef3c7;
  border: 1px solid #fde047;
  border-radius: 6px;
  font-size: 12px;
  color: #92400e;
}

.matching-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background-color: #dbeafe;
  border: 1px solid #93c5fd;
  border-radius: 6px;
  font-size: 12px;
  color: #1e40af;
}

.main-content {
  padding: 0;
  overflow-y: auto;
  height: 100vh;
}

.full-height-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.full-height-tabs :deep(.t-tabs__nav-container) {
  padding: 16px 24px 0;
  background-color: var(--td-bg-color-container);
}

.full-height-tabs :deep(.t-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.tab-panel-content {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.result-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.index-detail-card,
.search-results-card,
.history-card {
  background: var(--td-bg-color-container);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.highlight-value {
  font-weight: 600;
  color: var(--td-brand-color);
}

.index-name-text {
  word-break: break-all;
  white-space: normal;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--td-component-border);
}

.search-results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-result-item {
  padding: 12px;
  background: var(--td-bg-color-page);
  border-radius: 6px;
  border: 1px solid var(--td-component-border);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-rank {
  font-weight: 600;
  color: var(--td-brand-color);
}

.result-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--td-text-color-primary);
}

.result-meta {
  margin-top: 8px;
  font-size: 12px;
  color: var(--td-text-color-secondary);
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}

.empty-icon {
  color: var(--td-text-color-placeholder);
}

.empty-hint {
  margin-top: 8px;
  color: var(--td-text-color-secondary);
  font-size: 14px;
}

.index-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-name-cell .name {
  font-weight: 500;
}

.uuid-short {
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: var(--td-text-color-secondary);
  cursor: default;
  padding: 2px 6px;
  background-color: var(--td-bg-color-container-hover);
  border-radius: 4px;
  white-space: nowrap;
  display: inline-block;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

<!-- 全局样式，用于弹出层 -->
<style>
.vector-index-select-popup .t-select-option {
  padding: 10px 12px !important;
  height: auto !important;
  min-height: auto !important;
}

.vector-index-select-popup .t-select-option__content {
  white-space: normal;
  line-height: 1.5;
}

.vector-index-select-popup .select-option-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vector-index-select-popup .select-option-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--td-text-color-primary);
}

.vector-index-select-popup .select-option-desc {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  line-height: 1.4;
}
</style>
