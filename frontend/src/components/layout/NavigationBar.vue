<template>
  <aside class="sidebar">
    <!-- 标题区域 -->
    <div class="sidebar-header">
      <h1 class="sidebar-title">
        <FileText class="inline-block mr-2" :size="24" />
        文档处理系统
      </h1>
    </div>
    
    <!-- 导航菜单 -->
    <t-menu 
      :value="currentPath"
      theme="light"
      class="sidebar-menu"
    >
      <t-menu-item
        v-for="item in navItems"
        :key="item.path"
        :value="item.path"
        @click="handleNavigate(item.path)"
      >
        <template #icon>
          <component :is="item.iconComponent" :size="18" />
        </template>
        {{ item.label }}
      </t-menu-item>
    </t-menu>
    
    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <t-divider />
      <div class="version-info">
        <Info :size="14" class="inline-block mr-1" />
        版本 v1.0.0
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  Home, FileText, FileCode, Scissors, Hash, 
  Database, Search, Sparkles, Info 
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

const currentPath = computed(() => route.path)

const navItems = [
  { path: '/', label: '首页', iconComponent: Home },
  { path: '/documents/load', label: '文档加载', iconComponent: FileText },
  { path: '/documents/parse', label: '文档解析', iconComponent: FileCode },
  { path: '/documents/chunk', label: '文档分块', iconComponent: Scissors },
  { path: '/embeddings', label: '向量嵌入', iconComponent: Hash },
  { path: '/index', label: '向量索引', iconComponent: Database },
  { path: '/search', label: '搜索查询', iconComponent: Search },
  { path: '/generation', label: '文本生成', iconComponent: Sparkles }
]

function handleNavigate(path) {
  router.push(path)
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  display: flex;
  flex-direction: column;
  height: 100vh;
  border-right: 1px solid #e5e7eb;
  background-color: #ffffff;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  margin: 0;
}

.sidebar-menu {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.sidebar-footer {
  margin-top: auto;
}

.version-info {
  font-size: 12px;
  color: #6b7280;
  padding: 8px 24px;
}
</style>
