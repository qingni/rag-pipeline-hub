<template>
  <div class="model-capability-admin">
    <div class="page-header">
      <h1>模型能力管理</h1>
      <p class="page-description">
        配置嵌入模型的能力评分，影响智能推荐算法的结果
      </p>
    </div>
    
    <t-card class="main-card" :bordered="true">
      <ModelCapabilityManager
        @model-updated="onModelUpdated"
        @config-reloaded="onConfigReloaded"
      />
    </t-card>
    
    <!-- 使用说明 -->
    <t-card class="help-card" :bordered="true">
      <template #header>
        <span>使用说明</span>
      </template>
      
      <div class="help-content">
        <h4>推荐算法说明</h4>
        <p>
          智能模型推荐使用加权评分算法，根据文档特征匹配最适合的嵌入模型：
        </p>
        <ul>
          <li><strong>语言匹配（默认40%）</strong>：文档语言与模型语言支持能力的匹配度</li>
          <li><strong>领域匹配（默认35%）</strong>：文档领域与模型专长领域的匹配度</li>
          <li><strong>多模态支持（默认25%）</strong>：对于包含图片/表格的文档，多模态能力的重要性</li>
        </ul>
        
        <h4>配置建议</h4>
        <ul>
          <li>语言评分应基于模型实际的多语言能力</li>
          <li>领域评分应基于模型训练数据和实际测试表现</li>
          <li>多模态评分仅对支持多模态输入的模型有效</li>
          <li>建议定期根据实际使用效果调整配置</li>
        </ul>
        
        <t-alert theme="info" :close="false">
          <template #message>
            注意：修改配置后，新的推荐请求将使用更新后的评分。已完成的推荐结果不受影响。
          </template>
        </t-alert>
      </div>
    </t-card>
  </div>
</template>

<script setup>
import { MessagePlugin } from 'tdesign-vue-next'
import ModelCapabilityManager from '@/components/embedding/ModelCapabilityManager.vue'

function onModelUpdated(modelName) {
  MessagePlugin.success(`模型 ${modelName} 配置已更新`)
}

function onConfigReloaded() {
  MessagePlugin.success('配置已重新加载')
}
</script>

<style scoped>
.model-capability-admin {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #262626;
}

.page-description {
  margin: 0;
  color: #8c8c8c;
}

.main-card {
  margin-bottom: 24px;
}

.help-card {
  background: #fafafa;
}

.help-content h4 {
  margin: 16px 0 8px 0;
  font-size: 15px;
  font-weight: 500;
}

.help-content h4:first-child {
  margin-top: 0;
}

.help-content p,
.help-content ul {
  margin: 0 0 12px 0;
  color: #595959;
  line-height: 1.6;
}

.help-content ul {
  padding-left: 20px;
}

.help-content li {
  margin-bottom: 6px;
}
</style>
