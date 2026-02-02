/**
 * 分块可视化工具函数
 */

/**
 * 将分块数据转换为 Mermaid 图语法
 * @param {Array} chunks - 分块数组
 * @param {string} strategy - 分块策略
 * @param {Array} parentChunks - 父块数组 (仅 parent_child)
 * @returns {string} Mermaid 图定义
 */
export function chunksToMermaid(chunks, strategy, parentChunks = []) {
  if (strategy === 'heading') {
    return headingChunksToMermaid(chunks)
  } else if (strategy === 'parent_child') {
    return parentChildChunksToMermaid(parentChunks, chunks)
  } else {
    return linearChunksToMermaid(chunks, strategy)
  }
}

/**
 * 标题分块转 Mermaid
 */
function headingChunksToMermaid(chunks) {
  const lines = ['graph TD']
  
  // 添加根节点
  lines.push('    root["📄 文档"]')
  
  // 为每个标题创建节点
  chunks.forEach((chunk, idx) => {
    const id = `node_${idx}`
    const label = escapeLabel(
      chunk.metadata?.heading_text || 
      chunk.content?.slice(0, 30) || 
      `块${idx + 1}`
    )
    const level = chunk.metadata?.heading_level || 1
    const charCount = chunk.metadata?.char_count || chunk.content?.length || 0
    
    // 添加节点定义
    lines.push(`    ${id}["${label}<br/>(H${level}, ${charCount}字)"]`)
    
    // 连接到父节点或根节点
    const parentHeading = chunk.metadata?.parent_heading
    if (parentHeading) {
      // 查找父节点索引
      const parentIdx = chunks.findIndex(c => 
        c.metadata?.heading_text === parentHeading
      )
      if (parentIdx >= 0) {
        lines.push(`    node_${parentIdx} --> ${id}`)
      } else {
        lines.push(`    root --> ${id}`)
      }
    } else if (level <= 2) {
      lines.push(`    root --> ${id}`)
    }
  })
  
  // 添加样式
  lines.push('')
  lines.push('    classDef h1 fill:#1890ff,color:#fff')
  lines.push('    classDef h2 fill:#52c41a,color:#fff')
  lines.push('    classDef h3 fill:#faad14,color:#fff')
  lines.push('    classDef h4 fill:#eb2f96,color:#fff')
  lines.push('    classDef h5 fill:#722ed1,color:#fff')
  lines.push('    classDef h6 fill:#13c2c2,color:#fff')
  
  // 应用样式
  chunks.forEach((chunk, idx) => {
    const level = chunk.metadata?.heading_level || 1
    lines.push(`    class node_${idx} h${level}`)
  })
  
  return lines.join('\n')
}

/**
 * 父子分块转 Mermaid
 */
function parentChildChunksToMermaid(parentChunks, childChunks) {
  const lines = ['graph TD']
  
  // 文档根节点
  lines.push('    root["📄 文档"]')
  
  // 创建父节点
  parentChunks.forEach((parent, pIdx) => {
    const pId = `parent_${pIdx}`
    const charCount = parent.metadata?.char_count || parent.content?.length || 0
    const pLabel = `父块 ${parent.sequence_number + 1 || pIdx + 1}<br/>(${charCount}字符)`
    lines.push(`    ${pId}["${pLabel}"]`)
    lines.push(`    root --> ${pId}`)
    
    // 查找该父块的所有子块
    const parentId = parent.id || parent.metadata?.chunk_id
    const children = childChunks.filter(c => 
      c.parent_id === parentId ||
      c.metadata?.parent_id === parentId
    )
    
    // 限制显示的子块数量
    const displayChildren = children.slice(0, 5)
    displayChildren.forEach((child, cIdx) => {
      const cId = `child_${pIdx}_${cIdx}`
      const cCharCount = child.metadata?.char_count || child.content?.length || 0
      const cLabel = `子块 ${child.sequence_number + 1 || cIdx + 1}<br/>(${cCharCount}字符)`
      lines.push(`    ${cId}["${cLabel}"]`)
      lines.push(`    ${pId} --> ${cId}`)
    })
    
    // 如果有更多子块，显示省略节点
    if (children.length > 5) {
      const moreId = `more_${pIdx}`
      lines.push(`    ${moreId}["... 还有 ${children.length - 5} 个子块"]`)
      lines.push(`    ${pId} --> ${moreId}`)
    }
  })
  
  // 添加样式
  lines.push('')
  lines.push('    classDef parent fill:#1890ff,color:#fff')
  lines.push('    classDef child fill:#52c41a,color:#fff')
  lines.push('    classDef more fill:#f5f5f5,color:#999,stroke-dasharray:5')
  
  parentChunks.forEach((_, idx) => {
    lines.push(`    class parent_${idx} parent`)
  })
  
  return lines.join('\n')
}

/**
 * 线性分块转 Mermaid (流程图)
 */
function linearChunksToMermaid(chunks, strategy) {
  const lines = ['graph LR']
  
  // 限制显示数量
  const displayChunks = chunks.slice(0, 15)
  
  displayChunks.forEach((chunk, idx) => {
    const id = `chunk_${idx}`
    const size = chunk.metadata?.char_count || chunk.content?.length || 0
    
    // 根据策略类型添加额外信息
    let extraInfo = ''
    if (strategy === 'semantic' && chunk.metadata?.avg_similarity) {
      extraInfo = `<br/>相似度: ${(chunk.metadata.avg_similarity * 100).toFixed(0)}%`
    } else if (strategy === 'hybrid' && chunk.chunk_type) {
      extraInfo = `<br/>类型: ${chunk.chunk_type}`
    }
    
    lines.push(`    ${id}["#${idx + 1}<br/>${size}字符${extraInfo}"]`)
    
    if (idx > 0) {
      lines.push(`    chunk_${idx - 1} --> ${id}`)
    }
  })
  
  if (chunks.length > 15) {
    lines.push(`    more["... 还有 ${chunks.length - 15} 个块"]`)
    lines.push(`    chunk_14 --> more`)
  }
  
  return lines.join('\n')
}

/**
 * 转义 Mermaid 标签中的特殊字符
 */
function escapeLabel(label) {
  if (!label) return ''
  return label
    .replace(/"/g, "'")
    .replace(/\n/g, ' ')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .slice(0, 40)
}

/**
 * 计算分块覆盖率
 * @param {Array} chunks - 分块数组
 * @param {number} totalLength - 原文档总长度
 * @returns {number} 覆盖率 (0-1)
 */
export function calculateCoverage(chunks, totalLength) {
  if (!chunks?.length || !totalLength) return 0
  
  const ranges = []
  
  chunks.forEach(chunk => {
    const start = chunk.metadata?.start_position || chunk.start_position || 0
    const end = chunk.metadata?.end_position || chunk.end_position || 0
    if (end > start) {
      ranges.push({ start, end })
    }
  })
  
  // 合并重叠区间
  ranges.sort((a, b) => a.start - b.start)
  const merged = []
  
  for (const range of ranges) {
    if (merged.length === 0 || merged[merged.length - 1].end < range.start) {
      merged.push({ ...range })
    } else {
      merged[merged.length - 1].end = Math.max(merged[merged.length - 1].end, range.end)
    }
  }
  
  let covered = 0
  merged.forEach(r => covered += (r.end - r.start))
  
  return totalLength > 0 ? covered / totalLength : 0
}

/**
 * 计算分块统计信息
 * @param {Array} chunks - 分块数组
 * @param {Array} parentChunks - 父块数组 (可选)
 * @returns {Object} 统计信息
 */
export function calculateChunkStatistics(chunks, parentChunks = []) {
  if (!chunks?.length) {
    return {
      total_chunks: 0,
      total_characters: 0,
      avg_chunk_size: 0,
      min_chunk_size: 0,
      max_chunk_size: 0,
      size_distribution: []
    }
  }
  
  const sizes = chunks.map(c => 
    c.metadata?.char_count || c.token_count || c.content?.length || 0
  )
  
  const total = sizes.reduce((sum, s) => sum + s, 0)
  const avg = total / sizes.length
  const min = Math.min(...sizes)
  const max = Math.max(...sizes)
  
  // 计算大小分布
  const buckets = [
    { name: '0-200', min: 0, max: 200, count: 0 },
    { name: '200-500', min: 200, max: 500, count: 0 },
    { name: '500-800', min: 500, max: 800, count: 0 },
    { name: '800-1200', min: 800, max: 1200, count: 0 },
    { name: '>1200', min: 1200, max: Infinity, count: 0 }
  ]
  
  sizes.forEach(size => {
    const bucket = buckets.find(b => size >= b.min && size < b.max)
    if (bucket) bucket.count++
  })
  
  // 父子块统计
  let parentChildStats = null
  if (parentChunks?.length) {
    const parentSizes = parentChunks.map(p => 
      p.metadata?.char_count || p.content?.length || 0
    )
    const childCounts = parentChunks.map(p => p.child_count || 0)
    
    parentChildStats = {
      parent_count: parentChunks.length,
      child_count: chunks.length,
      avg_parent_size: parentSizes.reduce((a, b) => a + b, 0) / parentSizes.length,
      avg_children_per_parent: childCounts.reduce((a, b) => a + b, 0) / childCounts.length
    }
  }
  
  return {
    total_chunks: chunks.length,
    total_characters: total,
    avg_chunk_size: avg,
    min_chunk_size: min,
    max_chunk_size: max,
    size_distribution: buckets,
    parent_child_stats: parentChildStats
  }
}

/**
 * 获取策略的可视化配置
 */
export function getVisualizationConfig(strategyType) {
  const configs = {
    character: {
      defaultView: 'linear',
      supportsTree: false,
      showOverlap: true,
      colorScheme: 'gradient',
      description: '按字符分块 - 固定大小切分'
    },
    paragraph: {
      defaultView: 'linear',
      supportsTree: false,
      showOverlap: false,
      colorScheme: 'alternate',
      description: '按段落分块 - 基于段落边界'
    },
    heading: {
      defaultView: 'tree',
      supportsTree: true,
      showOverlap: false,
      colorScheme: 'level',
      description: '按标题分块 - 层级结构'
    },
    semantic: {
      defaultView: 'linear',
      supportsTree: false,
      showOverlap: false,
      colorScheme: 'similarity',
      description: '语义分块 - 基于语义相似度'
    },
    parent_child: {
      defaultView: 'tree',
      supportsTree: true,
      showOverlap: false,
      colorScheme: 'type',
      description: '父子分块 - 双层结构'
    },
    hybrid: {
      defaultView: 'hybrid',
      supportsTree: false,
      showOverlap: false,
      colorScheme: 'type',
      description: '混合分块 - 多类型内容'
    }
  }
  
  return configs[strategyType] || configs.character
}

/**
 * 获取标题层级颜色
 */
export function getHeadingLevelColor(level) {
  const colors = {
    1: '#1890ff',
    2: '#52c41a',
    3: '#faad14',
    4: '#eb2f96',
    5: '#722ed1',
    6: '#13c2c2'
  }
  return colors[level] || '#999'
}

/**
 * 获取块类型颜色
 */
export function getChunkTypeColor(type) {
  const colors = {
    text: '#1890ff',
    table: '#52c41a',
    code: '#722ed1',
    image: '#faad14'
  }
  return colors[type] || '#999'
}

/**
 * 构建标题层级树结构
 */
export function buildHeadingTree(chunks) {
  const root = { 
    id: 'root', 
    name: '文档', 
    children: [],
    level: 0,
    value: 0
  }
  
  const levelStack = [root]
  
  for (const chunk of chunks) {
    const level = chunk.metadata?.heading_level || 1
    const charCount = chunk.metadata?.char_count || chunk.content?.length || 0
    
    const node = {
      id: chunk.metadata?.chunk_id || chunk.id,
      name: chunk.metadata?.heading_text || chunk.content?.slice(0, 30) || `块`,
      level,
      value: charCount,
      charCount,
      originalChunk: chunk,
      children: []
    }
    
    // 找到正确的父节点
    while (levelStack.length > 1 && levelStack[levelStack.length - 1].level >= level) {
      levelStack.pop()
    }
    
    levelStack[levelStack.length - 1].children.push(node)
    levelStack.push(node)
  }
  
  // 计算每个节点的总值（包含子节点）
  function calculateTotalValue(node) {
    if (node.children.length === 0) {
      return node.value
    }
    const childrenValue = node.children.reduce((sum, child) => sum + calculateTotalValue(child), 0)
    node.value = Math.max(node.value, childrenValue)
    return node.value
  }
  calculateTotalValue(root)
  
  return root
}

/**
 * 构建父子分块树结构
 * @param {Array} parentChunks - 父块数组（可能包含children字段）
 * @param {Array} childChunks - 子块数组（作为fallback）
 */
export function buildParentChildTree(parentChunks, childChunks = []) {
  const root = {
    id: 'root',
    name: '文档',
    children: [],
    value: 0,
    isParent: false
  }
  
  // 构建树
  for (const parent of parentChunks) {
    const parentId = parent.id || parent.metadata?.chunk_id
    const charCount = parent.metadata?.char_count || parent.content?.length || 0
    
    // 优先从父块的children字段获取子块数据（后端includeChildren=true时会返回）
    // 如果父块没有children字段，则从childChunks数组中按parent_id匹配
    let children = parent.children || []
    
    // Fallback: 如果父块没有children字段，从childChunks数组查找
    if (children.length === 0 && childChunks.length > 0) {
      children = childChunks.filter(c => 
        c.parent_id === parentId || c.metadata?.parent_id === parentId
      )
    }
    
    const parentNode = {
      id: parentId,
      name: `父块 ${(parent.sequence_number ?? 0) + 1}`,
      isParent: true,
      charCount,
      value: charCount,
      childCount: children.length || parent.child_count || 0,
      originalChunk: parent,
      children: children.map((child, idx) => {
        const cCharCount = child.metadata?.char_count || child.content?.length || 0
        return {
          id: child.id || child.metadata?.chunk_id,
          name: `子块 ${(child.sequence_number ?? idx) + 1}`,
          isParent: false,
          charCount: cCharCount,
          value: cCharCount,
          originalChunk: child,
          children: []
        }
      })
    }
    
    root.children.push(parentNode)
  }
  
  // 计算根节点总值
  root.value = root.children.reduce((sum, child) => sum + child.value, 0)
  
  return root
}

/**
 * 导出为 SVG 字符串
 */
export function getSvgString(svgElement) {
  if (!svgElement) return ''
  const serializer = new XMLSerializer()
  return serializer.serializeToString(svgElement)
}

/**
 * 导出为 SVG 文件
 * @param {HTMLElement} svgElement - SVG DOM 元素
 * @param {string} filename - 文件名
 */
export function exportToSVG(svgElement, filename = 'chunk-visualization.svg') {
  const svgString = getSvgString(svgElement)
  if (!svgString) return
  
  const blob = new Blob([svgString], { type: 'image/svg+xml' })
  
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

/**
 * 导出为 PNG
 * @param {HTMLElement} svgElement - SVG DOM 元素
 * @param {string} filename - 文件名
 */
export async function exportToPNG(svgElement, filename = 'chunk-visualization.png') {
  const svgString = getSvgString(svgElement)
  if (!svgString) return
  
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const img = new Image()
  
  return new Promise((resolve, reject) => {
    img.onload = () => {
      canvas.width = img.width * 2 // 2x 分辨率
      canvas.height = img.height * 2
      ctx.scale(2, 2)
      ctx.fillStyle = '#fff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)
      
      canvas.toBlob(blob => {
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = filename
        link.click()
        URL.revokeObjectURL(link.href)
        resolve()
      }, 'image/png')
    }
    img.onerror = reject
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgString)))
  })
}

/**
 * 导出为 JSON
 */
export function exportToJSON(data, filename = 'chunk-data.json') {
  const jsonString = JSON.stringify(data, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

/**
 * 按类型分组分块数据
 */
export function groupChunksByType(chunks) {
  const groups = {}
  for (const chunk of chunks) {
    const type = chunk.chunk_type || 'text'
    if (!groups[type]) {
      groups[type] = []
    }
    groups[type].push(chunk)
  }
  return groups
}

/**
 * 按标题层级分组
 */
export function groupChunksByLevel(chunks) {
  const groups = {}
  for (const chunk of chunks) {
    const level = chunk.metadata?.heading_level || 1
    if (!groups[level]) {
      groups[level] = []
    }
    groups[level].push(chunk)
  }
  return groups
}
