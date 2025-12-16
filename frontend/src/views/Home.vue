<template>
  <div class="flex flex-1">
    <ContentArea title="欢迎使用文档处理和检索系统" subtitle="强大的文档智能处理平台">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Feature cards -->
        <router-link
          v-for="feature in features"
          :key="feature.path"
          :to="feature.path"
          class="card hover:shadow-xl transition-shadow"
        >
          <div class="text-4xl mb-4">{{ feature.icon }}</div>
          <h3 class="text-lg font-semibold mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-gray-600">{{ feature.description }}</p>
        </router-link>
      </div>
      
      <div class="mt-12 card bg-primary-50 border border-primary-200">
        <h3 class="text-lg font-semibold mb-2">快速开始</h3>
        <ol class="list-decimal list-inside space-y-2 text-sm text-gray-700">
          <li>上传您的文档 (PDF, DOC, DOCX, TXT)</li>
          <li>选择加载方式和解析选项</li>
          <li>进行文档分块和向量嵌入</li>
          <li>创建向量索引并执行智能搜索</li>
          <li>使用AI生成摘要和内容</li>
        </ol>
      </div>
    </ContentArea>
  </div>
</template>

<script setup>
import ContentArea from '../components/layout/ContentArea.vue'

const features = [
  {
    path: '/documents/load',
    icon: '📄',
    title: '文档加载',
    description: '支持多种文档格式加载，包括PDF、DOC等'
  },
  {
    path: '/documents/parse',
    icon: '📝',
    title: '文档解析',
    description: '智能解析文档内容，支持多种解析策略'
  },
  {
    path: '/documents/chunk',
    icon: '✂️',
    title: '文档分块',
    description: '将文档分割成适合处理的块，支持多种分块策略'
  },
  {
    path: '/documents/embed',
    icon: '🧬',
    title: '文档向量化',
    description: '从分块结果生成向量表示，支持多种向量模型'
  },
  {
    path: '/embeddings',
    icon: '🔢',
    title: '文本向量化',
    description: '单文本和批量文本向量化（开发测试）'
  },
  {
    path: '/index',
    icon: '📇',
    title: '向量索引',
    description: '创建高效的向量索引，支持快速检索'
  },
  {
    path: '/search',
    icon: '🔍',
    title: '搜索查询',
    description: '基于语义的智能搜索，快速找到相关内容'
  },
  {
    path: '/generation',
    icon: '✨',
    title: '文本生成',
    description: '基于文档内容生成摘要、问答等'
  }
]
</script>
