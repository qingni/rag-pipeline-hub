# TDesign 组件库优化升级指南

## 概述

本次优化将前端 UI 从原生 TailwindCSS 升级到 TDesign Vue Next 组件库，提供更专业、统一的设计体验。

## 已完成的优化

### 1. 依赖更新
- ✅ 添加 `tdesign-vue-next@^1.13.1`
- ✅ 添加 `tdesign-icons-vue-next@^0.3.6`
- ✅ 添加 `lucide-vue-next@^0.468.0` (图标库)

### 2. 组件优化

#### NavigationBar.vue
- 使用 TDesign `Menu` 组件替代原生导航
- 使用 Lucide 图标替代 Emoji
- 优化侧边栏布局和样式

#### DocumentList.vue
- 使用 TDesign `Table` 组件
- 使用 TDesign `Tag`、`Popconfirm`、`Pagination` 等组件
- 更专业的表格展示和交互体验

#### DocumentUploader.vue
- 使用 TDesign `Upload` 组件
- 使用 TDesign `Progress` 和 `Alert` 组件
- 更好的拖拽上传体验

#### DocumentLoad.vue
- 使用 TDesign `Card`、`Select`、`Button` 等组件
- 优化布局结构
- 更清晰的信息层次

### 3. 主题配置
- 集成 TDesign 默认主题
- 保留 TailwindCSS 用于辅助样式

## 安装步骤

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

## TDesign 组件使用示例

### 按钮
```vue
<t-button theme="primary" variant="base">
  <template #icon><IconComponent /></template>
  按钮文本
</t-button>
```

### 表格
```vue
<t-table
  :data="tableData"
  :columns="columns"
  :hover="true"
  :stripe="true"
/>
```

### 选择器
```vue
<t-select v-model="value" placeholder="请选择">
  <t-option value="1" label="选项1" />
  <t-option value="2" label="选项2" />
</t-select>
```

### 上传
```vue
<t-upload
  :draggable="true"
  :accept="'.pdf,.doc'"
  @change="handleChange"
/>
```

## 图标使用

### Lucide Icons
```vue
<script setup>
import { FileText, Upload, Download } from 'lucide-vue-next'
</script>

<template>
  <FileText :size="20" />
</template>
```

### TDesign Icons
```vue
<script setup>
import { AddIcon, DeleteIcon } from 'tdesign-icons-vue-next'
</script>

<template>
  <AddIcon />
</template>
```

## 主题定制

TDesign 支持 CSS 变量主题定制，在 `main.css` 中可以覆盖：

```css
:root {
  --td-brand-color: #0052d9;
  --td-warning-color: #e37318;
  --td-error-color: #d54941;
  --td-success-color: #2ba471;
}
```

## 后续优化建议

### 待优化组件
- [ ] ProcessingProgress.vue - 使用 TDesign Progress 组件
- [ ] ResultPreview.vue - 使用 TDesign Card 和 Descriptions 组件
- [ ] DocumentPreview.vue - 优化预览样式
- [ ] ControlPanel.vue - 使用 TDesign Card 组件
- [ ] ContentArea.vue - 使用 TDesign Layout 组件
- [ ] Home.vue - 首页设计优化
- [ ] 其他视图页面 (Parse, Chunk, Embed, Index, Search, Generation)

### 待添加功能
- [ ] 主题切换 (亮色/暗色模式)
- [ ] 全局加载状态
- [ ] 全局消息提示 (Message/Notification)
- [ ] 响应式布局优化

## 参考资源

- [TDesign Vue Next 官方文档](https://tdesign.tencent.com/vue-next/overview)
- [Lucide Icons](https://lucide.dev/icons/)
- [TailwindCSS 文档](https://tailwindcss.com/docs)

## 注意事项

1. **兼容性**: TDesign 和 TailwindCSS 可以并存使用
2. **图标**: 优先使用 Lucide Icons，TDesign Icons 作为补充
3. **样式**: TDesign 组件自带样式，避免过度自定义
4. **主题**: 使用 TDesign 的 CSS 变量系统进行主题定制

## 问题排查

### 样式不生效
确保已正确导入 TDesign 样式：
```js
import 'tdesign-vue-next/es/style/index.css'
```

### 组件未注册
确保已全局注册 TDesign：
```js
import TDesign from 'tdesign-vue-next'
app.use(TDesign)
```

### 图标显示异常
检查图标组件导入路径是否正确

## 总结

本次优化大幅提升了前端 UI 的专业性和一致性，后续可以继续按照 TDesign 规范优化其他组件。
