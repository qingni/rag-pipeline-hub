/**
 * 分块可视化组件
 * 
 * 支持的分块策略:
 * - character: 按字符分块
 * - paragraph: 按段落分块
 * - heading: 按标题分块
 * - semantic: 语义分块
 * - parent_child: 父子分块
 * - hybrid: 混合分块
 */

// 主入口组件
export { default as ChunkVisualizer } from './ChunkVisualizer.vue'

// 子组件
export { default as TreeVisualizer } from './TreeVisualizer.vue'
export { default as LinearVisualizer } from './LinearVisualizer.vue'
export { default as HybridVisualizer } from './HybridVisualizer.vue'
export { default as ChunkStatsChart } from './ChunkStatsChart.vue'
export { default as TreeNode } from './TreeNode.vue'

// 工具函数
export * from './utils/visualizerUtils'
