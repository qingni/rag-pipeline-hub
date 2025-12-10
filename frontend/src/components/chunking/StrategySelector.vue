<template>
  <div class="strategy-selector">
    <t-card title="选择分块策略" :bordered="false">
      <t-loading :loading="loading" size="small">
        <t-radio-group v-model="selectedStrategyType" @change="handleSelect">
          <t-space direction="vertical" size="medium" style="width: 100%">
            <t-radio
              v-for="strategy in strategies"
              :key="strategy.type"
              :value="strategy.type"
            >
              <div class="strategy-item">
                <div class="strategy-header">
                  <span class="strategy-name">{{ strategy.name }}</span>
                  <t-tag
                    v-if="strategy.requires_structure"
                    size="small"
                    theme="warning"
                    variant="light"
                  >
                    需要文档结构
                  </t-tag>
                </div>
                <div class="strategy-desc">{{ strategy.description }}</div>
              </div>
            </t-radio>
          </t-space>
        </t-radio-group>

        <t-empty
          v-if="!loading && strategies.length === 0"
          description="暂无可用策略"
        />
      </t-loading>
    </t-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useChunkingStore } from '@/stores/chunkingStore'
import { MessagePlugin } from 'tdesign-vue-next'

const chunkingStore = useChunkingStore()

const loading = computed(() => chunkingStore.strategiesLoading)
const strategies = computed(() => chunkingStore.strategies)
const selectedStrategyType = ref(null)

const loadStrategies = async () => {
  try {
    await chunkingStore.loadStrategies()
    console.log('Loaded strategies:', chunkingStore.strategies.length, chunkingStore.strategies)
  } catch (error) {
    console.error('加载策略列表失败:', error)
    MessagePlugin.error('加载策略列表失败')
  }
}

const handleSelect = (strategyType) => {
  const strategy = chunkingStore.strategies.find(s => s.type === strategyType)
  if (strategy) {
    chunkingStore.selectStrategy(strategy)
  }
}

onMounted(() => {
  loadStrategies()
})
</script>

<style scoped>
.strategy-selector {
  margin-bottom: 20px;
}

.strategy-selector :deep(.t-card__body) {
  padding: 16px 12px;
}

.strategy-selector :deep(.t-radio) {
  align-items: flex-start;
  padding: 6px 0;
}

.strategy-selector :deep(.t-radio__label) {
  flex: 1;
  min-width: 0;
  padding-left: 6px;
}

.strategy-item {
  width: 100%;
  line-height: 1.4;
  min-width: 0;
}

.strategy-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.strategy-name {
  font-weight: 500;
  font-size: 13px;
  white-space: nowrap;
}

.strategy-desc {
  font-size: 11px;
  color: var(--td-text-color-secondary);
  line-height: 1.6;
  word-break: break-all;
  overflow-wrap: break-word;
  hyphens: auto;
  letter-spacing: -0.02em;
}
</style>
