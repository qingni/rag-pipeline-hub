<template>
  <div class="vector-index-page">
    <t-card :bordered="false" class="page-header">
      <template #header>
        <div class="header-content">
          <div class="title-section">
            <h1>向量索引管理</h1>
            <p class="subtitle">创建和管理向量索引，执行相似度搜索</p>
          </div>
          <t-button theme="primary" @click="showCreateDialog = true">
            <template #icon><add-icon /></template>
            创建索引
          </t-button>
        </div>
      </template>

      <!-- 统计卡片 -->
      <t-row :gutter="16" class="stats-row">
        <t-col :span="3">
          <t-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ indexCount }}</div>
              <div class="stat-label">总索引数</div>
            </div>
          </t-card>
        </t-col>
        <t-col :span="3">
          <t-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ readyIndexCount }}</div>
              <div class="stat-label">就绪索引</div>
            </div>
          </t-card>
        </t-col>
        <t-col :span="3">
          <t-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ currentVectorCount }}</div>
              <div class="stat-label">向量总数</div>
            </div>
          </t-card>
        </t-col>
        <t-col :span="3">
          <t-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ currentQueryCount }}</div>
              <div class="stat-label">查询总数</div>
            </div>
          </t-card>
        </t-col>
      </t-row>
    </t-card>

    <!-- 主要内容区域 -->
    <t-row :gutter="16" class="main-content">
      <t-col :span="12">
        <!-- 索引列表 -->
        <index-list
          :loading="loading.list"
          @select="handleSelectIndex"
          @delete="handleDeleteIndex"
          @refresh="loadIndexes"
        />
      </t-col>

      <t-col :span="12">
        <!-- 向量搜索 -->
        <vector-search
          v-if="currentIndex"
          :index="currentIndex"
          :loading="loading.search"
          @search="handleSearch"
        />
        <t-card v-else class="empty-state">
          <t-empty description="请先选择一个索引" />
        </t-card>
      </t-col>
    </t-row>

    <!-- 创建索引对话框 -->
    <index-create
      :visible="showCreateDialog"
      @update:visible="showCreateDialog = $event"
      :loading="loading.create"
      @create="handleCreateIndex"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { AddIcon } from 'tdesign-icons-vue-next';
import { storeToRefs } from 'pinia';
import { useVectorIndexStore } from '../stores/vectorIndexStore';
import IndexList from '../components/VectorIndex/IndexList.vue';
import IndexCreate from '../components/VectorIndex/IndexCreate.vue';
import VectorSearch from '../components/VectorIndex/VectorSearch.vue';

const vectorIndexStore = useVectorIndexStore();
const { 
  currentIndex, 
  indexCount, 
  readyIndexCount,
  currentVectorCount,
  currentQueryCount,
  loading 
} = storeToRefs(vectorIndexStore);

const showCreateDialog = ref(false);

// 加载索引列表
const loadIndexes = async () => {
  try {
    await vectorIndexStore.fetchIndexes();
  } catch (error) {
    MessagePlugin.error('加载索引列表失败');
  }
};

// 选择索引
const handleSelectIndex = async (index) => {
  try {
    vectorIndexStore.setCurrentIndex(index);
    await vectorIndexStore.fetchStatistics(index.id);
  } catch (error) {
    MessagePlugin.error('加载索引统计失败');
  }
};

// 创建索引
const handleCreateIndex = async (indexData) => {
  try {
    await vectorIndexStore.createNewIndex(indexData);
    MessagePlugin.success('索引创建成功');
    showCreateDialog.value = false;
  } catch (error) {
    MessagePlugin.error(vectorIndexStore.error || '创建索引失败');
  }
};

// 删除索引
const handleDeleteIndex = async (indexId) => {
  try {
    await vectorIndexStore.removeIndex(indexId);
    MessagePlugin.success('索引删除成功');
  } catch (error) {
    MessagePlugin.error('删除索引失败');
  }
};

// 执行搜索
const handleSearch = async (searchData) => {
  try {
    await vectorIndexStore.performSearch(currentIndex.value.id, searchData);
    MessagePlugin.success(`找到 ${vectorIndexStore.searchResults.results_count} 个结果`);
  } catch (error) {
    MessagePlugin.error('搜索失败');
  }
};

onMounted(() => {
  loadIndexes();
});
</script>

<style scoped>
.vector-index-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0;
  color: var(--td-text-color-secondary);
  font-size: 14px;
}

.stats-row {
  margin-top: 16px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  padding: 8px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--td-brand-color);
  line-height: 1.2;
}

.stat-label {
  margin-top: 8px;
  color: var(--td-text-color-secondary);
  font-size: 14px;
}

.main-content {
  margin-top: 24px;
}

.empty-state {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
