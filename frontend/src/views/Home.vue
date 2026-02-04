<template>
  <div class="home-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">欢迎使用文档处理和检索系统</h1>
      <p class="page-subtitle">强大的文档智能处理平台</p>
    </div>

    <!-- 功能卡片网格 -->
    <t-row :gutter="[24, 24]">
      <t-col 
        v-for="feature in features" 
        :key="feature.path"
        :xs="12" :sm="6" :md="4" :lg="4"
      >
        <t-card 
          :bordered="true"
          hover-shadow
          class="feature-card"
          @click="navigateTo(feature.path)"
        >
          <div class="feature-content">
            <div class="feature-icon">
              <component :is="feature.iconComponent" :size="28" :stroke-width="1.5" />
            </div>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc">{{ feature.description }}</p>
          </div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 快速开始卡片 -->
    <t-card class="quickstart-card" :bordered="true">
      <template #header>
        <div class="quickstart-header">
          <RocketIcon :size="20" class="quickstart-icon" />
          <span class="quickstart-title">快速开始</span>
        </div>
      </template>
      <t-list :split="false">
        <t-list-item v-for="(step, index) in quickstartSteps" :key="index">
          <div class="step-item">
            <span class="step-number">{{ index + 1 }}.</span>
            <span class="step-text">{{ step }}</span>
          </div>
        </t-list-item>
      </t-list>
    </t-card>

    <!-- 系统管理区域 -->
    <div class="admin-section">
      <div class="admin-header">
        <Settings :size="18" class="admin-header-icon" />
        <span class="admin-header-title">系统管理</span>
      </div>
      <t-row :gutter="[16, 16]">
        <t-col 
          v-for="admin in adminFeatures" 
          :key="admin.path"
          :xs="12" :sm="6" :md="4" :lg="4"
        >
          <t-card 
            :bordered="true"
            hover-shadow
            class="admin-card"
            @click="navigateTo(admin.path)"
          >
            <div class="admin-content">
              <div class="admin-icon">
                <component :is="admin.iconComponent" :size="22" :stroke-width="1.5" />
              </div>
              <div class="admin-info">
                <h4 class="admin-title">{{ admin.title }}</h4>
                <p class="admin-desc">{{ admin.description }}</p>
              </div>
            </div>
          </t-card>
        </t-col>
      </t-row>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Card as TCard, Row as TRow, Col as TCol, List as TList, ListItem as TListItem } from 'tdesign-vue-next'
import { 
  FileText, Scissors, Hash, Database, Search, Sparkles, Rocket as RocketIcon, Settings, Cpu
} from 'lucide-vue-next'

const router = useRouter()

const features = [
  {
    path: '/documents/load',
    iconComponent: FileText,
    title: '文档加载',
    description: '支持多种文档格式加载，包括PDF、DOC等'
  },
  {
    path: '/documents/chunk',
    iconComponent: Scissors,
    title: '文档分块',
    description: '将文档分割成适合处理的块，支持多种分块策略'
  },
  {
    path: '/documents/embed',
    iconComponent: Hash,
    title: '文档向量化',
    description: '从分块结果生成向量表示，支持多种向量模型'
  },
  {
    path: '/index',
    iconComponent: Database,
    title: '向量索引',
    description: '创建高效的向量索引，支持快速检索'
  },
  {
    path: '/search',
    iconComponent: Search,
    title: '搜索查询',
    description: '基于语义的智能搜索，快速找到相关内容'
  },
  {
    path: '/generation',
    iconComponent: Sparkles,
    title: '文本生成',
    description: '基于文档内容生成摘要、问答等'
  }
]

const quickstartSteps = [
  '上传您的文档 (PDF, DOC, DOCX, TXT)',
  '选择加载方式加载文档内容',
  '进行文档分块和向量嵌入',
  '创建向量索引并执行智能搜索',
  '使用AI生成摘要和内容'
]

const adminFeatures = [
  {
    path: '/admin/model-capability',
    iconComponent: Cpu,
    title: '模型能力管理',
    description: '查看和调整嵌入模型的能力评分与推荐权重'
  }
]

function navigateTo(path) {
  router.push(path)
}
</script>

<style scoped>
.home-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
  margin: 0;
}

.feature-card {
  cursor: pointer;
  transition: all 0.3s ease;
  height: 100%;
}

.feature-card:hover {
  transform: translateY(-2px);
}

.feature-content {
  padding: 8px 0;
}

.feature-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: var(--td-brand-color-light, #f2f3ff);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  color: var(--td-brand-color, #0052d9);
}

.feature-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  margin: 0 0 8px 0;
}

.feature-desc {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.6);
  margin: 0;
  line-height: 1.5;
}

.quickstart-card {
  margin-top: 32px;
}

.quickstart-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quickstart-icon {
  color: var(--td-brand-color, #0052d9);
}

.quickstart-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.step-number {
  color: var(--td-brand-color, #0052d9);
  font-weight: 500;
  min-width: 20px;
}

.step-text {
  color: rgba(0, 0, 0, 0.7);
  font-size: 14px;
}

/* 系统管理区域样式 */
.admin-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.admin-header-icon {
  color: rgba(0, 0, 0, 0.5);
}

.admin-header-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.6);
}

.admin-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.admin-card:hover {
  transform: translateY(-2px);
}

.admin-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 0, 0, 0.6);
  flex-shrink: 0;
}

.admin-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.9);
  margin: 0 0 4px 0;
}

.admin-desc {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.5);
  margin: 0;
  line-height: 1.4;
}
</style>
