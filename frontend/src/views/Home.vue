<template>
  <div class="home-container">
    <!-- Hero -->
    <section class="hero">
      <h1 class="hero-title">RAG 各环节独立配置与调试</h1>
      <p class="hero-desc">
        涵盖文档加载、分块、向量化、索引、检索、生成六大模块，每个模块可独立运行、参数可调、结果可查。
      </p>
    </section>

    <!-- 功能模块网格 -->
    <section class="modules">
      <div class="module-grid">
        <div
          v-for="mod in modules"
          :key="mod.path"
          class="module-card"
          :style="{ '--accent': mod.color, '--bg': mod.bgColor }"
          @click="navigateTo(mod.path)"
        >
          <div class="module-icon">
            <component :is="mod.iconComponent" :size="22" />
          </div>
          <div class="module-body">
            <h3 class="module-title">{{ mod.title }}</h3>
            <p class="module-desc">{{ mod.description }}</p>
          </div>
          <div class="module-tags">
            <span v-for="tag in mod.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 底部：系统管理 -->
    <section class="admin-section">
      <div class="admin-bar">
        <div class="admin-left">
          <Settings :size="14" />
          <span>系统管理</span>
        </div>
        <t-button
          v-for="admin in adminFeatures"
          :key="admin.path"
          theme="default"
          variant="text"
          size="small"
          @click="navigateTo(admin.path)"
        >
          <template #icon><component :is="admin.iconComponent" :size="14" /></template>
          {{ admin.title }}
        </t-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import {
  FileUp, SplitSquareHorizontal, Binary,
  Server, SearchCheck, BotMessageSquare,
  Settings, Cpu
} from 'lucide-vue-next'

const router = useRouter()

const modules = [
  {
    path: '/documents/load',
    iconComponent: FileUp,
    title: '文档加载',
    description: '上传并解析多格式文档，提取结构化文本内容',
    color: '#3B82F6',
    bgColor: '#EFF6FF',
    tags: ['PDF', 'DOCX', 'PPTX', 'Markdown', '20+']
  },
  {
    path: '/documents/chunk',
    iconComponent: SplitSquareHorizontal,
    title: '文档分块',
    description: '基于文档特征智能推荐分块策略与参数，支持一键应用',
    color: '#8B5CF6',
    bgColor: '#F5F3FF',
    tags: ['智能推荐', '语义分块', '混合分块', '父子文档']
  },
  {
    path: '/documents/embed',
    iconComponent: Binary,
    title: '文档向量化',
    description: '根据语言、领域、多模态特征智能推荐 Embedding 模型',
    color: '#EC4899',
    bgColor: '#FDF2F8',
    tags: ['智能推荐', 'BGE-M3', 'Qwen', '多模态']
  },
  {
    path: '/index',
    iconComponent: Server,
    title: '向量索引',
    description: '将向量写入数据库并创建高效检索索引',
    color: '#F59E0B',
    bgColor: '#FFFBEB',
    tags: ['Milvus', 'Collection 管理', '统计']
  },
  {
    path: '/search',
    iconComponent: SearchCheck,
    title: '搜索查询',
    description: '语义检索、混合搜索与 Rerank 精排调试',
    color: '#10B981',
    bgColor: '#ECFDF5',
    tags: ['混合检索', 'Rerank', '查询增强']
  },
  {
    path: '/generation',
    iconComponent: BotMessageSquare,
    title: '文本生成',
    description: '配置 Prompt 和上下文，调试 AI 回答生成效果',
    color: '#6366F1',
    bgColor: '#EEF2FF',
    tags: ['DeepSeek', 'Prompt 模板', '流式输出']
  }
]

const adminFeatures = [
  { path: '/admin/model-capability', iconComponent: Cpu, title: '模型能力管理' }
]

function navigateTo(path) {
  router.push(path)
}
</script>

<style scoped>
.home-container {
  padding: 36px 40px 32px;
  max-width: 960px;
  margin: 0 auto;
}

/* ===== Hero ===== */
.hero {
  margin-bottom: 36px;
}

.hero-title {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 10px 0;
  line-height: 1.3;
}

.hero-desc {
  font-size: 14px;
  color: #6B7280;
  margin: 0;
  line-height: 1.7;
  max-width: 560px;
}

/* ===== Modules ===== */
.modules {
  margin-bottom: 40px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.module-card {
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: #fff;
  border: 1px solid #F3F4F6;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.module-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
  border-color: var(--accent);
}

.module-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--bg);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.module-body {
  flex: 1;
  margin-bottom: 12px;
}

.module-title {
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
  margin: 0 0 6px 0;
}

.module-desc {
  font-size: 13px;
  color: #9CA3AF;
  margin: 0;
  line-height: 1.5;
}

.module-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  background: #F9FAFB;
  color: #6B7280;
  border-radius: 4px;
  border: 1px solid #F3F4F6;
}

/* ===== Admin ===== */
.admin-section {
  border-top: 1px solid #F3F4F6;
  padding-top: 16px;
}

.admin-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-left {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: #9CA3AF;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .home-container {
    padding: 24px 20px;
  }

  .hero-title {
    font-size: 22px;
  }

  .module-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .module-grid {
    grid-template-columns: 1fr;
  }
}
</style>
