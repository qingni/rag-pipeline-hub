# 生成模型与Prompt详解

**生成日期**: 2025-12-26  
**项目**: RAG Framework - 文本生成模块  

---

## 📋 目录

1. [支持的模型](#1-支持的模型)
2. [模型参数配置](#2-模型参数配置)
3. [Prompt模板设计](#3-prompt模板设计)
4. [上下文注入策略](#4-上下文注入策略)
5. [引用标注机制](#5-引用标注机制)
6. [最佳实践](#6-最佳实践)

---

## 1. 支持的模型

### 1.1 模型列表

```python
GENERATION_MODELS = {
    "deepseek-v3.2": {
        "name": "deepseek-v3.2",
        "context_length": 128000,
        "description": "DeepSeek V3.2 - 685B参数，【文本推荐】，工具使用和代理任务方面性能显著提高",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "deepseek-v3.1": {
        "name": "deepseek-v3.1",
        "context_length": 128000,
        "description": "DeepSeek V3.1 - 671B参数，【文本推荐】，支持思考与非思考模式",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
}
```

### 1.2 模型特点对比

| 模型 | 上下文长度 | 特点 | 适用场景 |
|------|-----------|------|----------|
| deepseek-v3.2 | 128K | 685B参数，工具使用和代理任务性能强 | 通用问答、复杂推理（推荐） |
| deepseek-v3.1 | 128K | 671B参数，支持思考模式 | 通用问答、日常使用 |

### 1.3 模型选择建议

```
┌─────────────────────────────────────────────────────────────┐
│                    模型选择决策树                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  问题类型？                                                  │
│  ├── 通用问答 → deepseek-v3.2 (推荐，性能最强)              │
│  └── 日常使用 → deepseek-v3.1 (稳定可靠)                  │
│                                                             │
│  上下文长度？                                                │
│  ├── <10K tokens → 任意模型                                 │
│  └── >10K tokens → 推荐 deepseek-v3.2                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 模型参数配置

### 2.1 温度参数 (Temperature)

**作用**: 控制生成内容的随机性和创造性。

| 温度值 | 特点 | 适用场景 |
|--------|------|----------|
| 0.0-0.3 | 确定性高，输出稳定 | 事实性问答、代码生成 |
| 0.4-0.7 | 平衡创造性和准确性 | 通用问答（推荐） |
| 0.8-1.2 | 创造性高，多样性强 | 创意写作、头脑风暴 |
| 1.3-2.0 | 高度随机 | 特殊创意场景 |

**代码示例**:
```python
# 事实性问答，使用低温度
llm = ChatOpenAI(model="deepseek-v3.2", temperature=0.3)

# 通用问答，使用中等温度
llm = ChatOpenAI(model="deepseek-v3.2", temperature=0.7)

# 创意写作，使用高温度
llm = ChatOpenAI(model="deepseek-v3.2", temperature=1.0)
```

### 2.2 最大Token数 (Max Tokens)

**作用**: 控制生成内容的最大长度。

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| 简短回答 | 512-1024 | 简单问题的快速回答 |
| 标准回答 | 2048-4096 | 详细解释和分析 |
| 长文档 | 4096-8192 | 长篇分析、报告生成 |

**注意事项**:
- 实际输出可能少于设置值
- 过大的值会增加响应时间和成本
- 需要预留足够空间给上下文

### 2.3 上下文长度计算

```python
def check_context_length(self, request: GenerationRequest) -> dict:
    """检查上下文长度是否在限制内"""
    model_info = GENERATION_MODELS.get(request.model)
    max_context = model_info["context_length"]
    
    # 计算各部分Token
    question_tokens = self.estimate_tokens(request.question)
    context_tokens = sum(self.estimate_tokens(item.content) for item in request.context)
    system_prompt_tokens = 500  # 系统提示约500 tokens
    
    total_tokens = question_tokens + context_tokens + system_prompt_tokens
    
    # 预留输出空间
    available_for_input = max_context - request.max_tokens
    
    if total_tokens > available_for_input * 0.9:
        return {
            "valid": False,
            "message": f"输入内容过长。预估 {total_tokens} tokens，"
                      f"模型最大支持 {available_for_input} tokens。"
        }
    
    return {"valid": True, "estimated_tokens": total_tokens}
```

---

## 3. Prompt模板设计

### 3.1 有上下文的系统提示

```python
SYSTEM_PROMPT_TEMPLATE = """你是一个智能问答助手。请基于以下参考资料回答用户的问题。

## 参考资料

{context}

## 回答要求

1. 基于参考资料给出准确、详细的回答
2. 如果引用了某段资料，请在回答中标注来源编号，如 [1]、[2]
3. 如果参考资料不足以回答问题，请明确说明
4. 回答应该条理清晰，易于理解"""
```

### 3.2 无上下文的系统提示

```python
SYSTEM_PROMPT_NO_CONTEXT = """你是一个智能问答助手。请根据你的知识回答用户的问题。

## 回答要求

1. 给出准确、详细的回答
2. 如果不确定答案，请明确说明
3. 回答应该条理清晰，易于理解"""
```

### 3.3 Prompt构建流程

```python
def _build_prompt(
    self,
    question: str,
    context: List[ContextItem],
) -> tuple[str, str]:
    """构建系统提示和用户提示
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    if not context:
        # 无上下文模式
        return SYSTEM_PROMPT_NO_CONTEXT, question
    
    # 构建上下文字符串
    context_parts = []
    for i, item in enumerate(context, 1):
        context_parts.append(f"[{i}] {item.content}\n来源：{item.source_file}")
    
    context_str = "\n\n".join(context_parts)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context_str)
    
    return system_prompt, question
```

### 3.4 完整Prompt示例

**输入**:
- 问题: "如何在自选股中添加股票？"
- 上下文: 2个相关文档片段

**生成的Prompt**:

```
[System]
你是一个智能问答助手。请基于以下参考资料回答用户的问题。

## 参考资料

[1] 在股票APP的自选页面中，添加股票到自选列表主要有以下两种方式：
### 1. 通过"搜索功能"添加
- 点击顶部导航栏区的"搜索栏"（显示提示文字"搜索股票/板块/基金/资讯/选股"）[3]
- 输入股票名称、代码或关键词进行搜索
- 在搜索结果中找到目标股票后，点击"+"或"添加"按钮即可加入自选列表
来源：技术文档.md

[2] ### 2. 通过"推荐引导弹窗"添加（针对新用户或自选较少的用户）
- 系统会自动弹出推荐引导弹窗，展示热门或推荐股票
- 用户可以直接在弹窗中选择感兴趣的股票添加到自选
来源：产品手册.md

## 回答要求

1. 基于参考资料给出准确、详细的回答
2. 如果引用了某段资料，请在回答中标注来源编号，如 [1]、[2]
3. 如果参考资料不足以回答问题，请明确说明
4. 回答应该条理清晰，易于理解

[User]
如何在自选股中添加股票？
```

---

## 4. 上下文注入策略

### 4.1 上下文格式

每个上下文项包含以下信息：

```python
class ContextItem(BaseModel):
    """检索到的上下文项"""
    content: str          # 文档内容
    source_file: str      # 来源文件
    similarity: float     # 相似度分数
    chunk_id: str         # Chunk ID（可选）
    metadata: dict        # 额外元数据（可选）
```

### 4.2 上下文排序策略

```python
# 按相似度降序排列，最相关的放在前面
context_items.sort(key=lambda x: x.similarity, reverse=True)

# 构建上下文时，编号从1开始
for i, item in enumerate(context_items, 1):
    context_parts.append(f"[{i}] {item.content}\n来源：{item.source_file}")
```

### 4.3 上下文长度控制

```python
def truncate_context(context: List[ContextItem], max_tokens: int) -> List[ContextItem]:
    """截断上下文以适应Token限制"""
    total_tokens = 0
    truncated = []
    
    for item in context:
        item_tokens = estimate_tokens(item.content)
        if total_tokens + item_tokens > max_tokens:
            break
        truncated.append(item)
        total_tokens += item_tokens
    
    return truncated
```

### 4.4 多索引上下文合并

当从多个索引检索时，需要合并结果：

```python
def merge_context_from_indexes(results_list: List[List[dict]], top_k: int) -> List[ContextItem]:
    """合并多个索引的检索结果"""
    all_results = []
    for results in results_list:
        all_results.extend(results)
    
    # 按相似度排序
    all_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
    
    # 去重（基于内容哈希）
    seen_hashes = set()
    unique_results = []
    for result in all_results:
        content_hash = hash(result.get('text_content', ''))
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_results.append(result)
    
    # 截取Top-K
    return unique_results[:top_k]
```

---

## 5. 引用标注机制

### 5.1 引用标注原理

LLM在生成回答时，会根据系统提示中的要求，在引用参考资料时标注来源编号。

**系统提示中的要求**:
```
如果引用了某段资料，请在回答中标注来源编号，如 [1]、[2]
```

### 5.2 引用提取与展示

```javascript
// 前端渲染时高亮引用标记
const renderedContent = computed(() => {
  if (!props.content) return ''
  
  let html = props.content
    // 转义 HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 引用标记高亮 [1], [2], etc.
    .replace(/\[(\d+)\]/g, '<span class="source-ref">[$1]</span>')
    // 换行
    .replace(/\n/g, '<br>')
  
  return html
})
```

### 5.3 引用来源展示

```vue
<template>
  <div class="source-reference">
    <h4 class="section-title">
      <FileText :size="18" />
      引用来源
      <span class="source-count">({{ displaySources.length }})</span>
    </h4>
    
    <div class="source-list">
      <div v-for="source in displaySources" :key="source.index" class="source-item">
        <div class="source-header">
          <span class="source-index">[{{ source.index }}]</span>
          <div class="source-info">
            <span class="source-file">{{ source.source_file }}</span>
            <span class="source-similarity">
              相似度: {{ formatSimilarity(source.similarity) }}
            </span>
          </div>
        </div>
        <div class="source-content" v-if="source.content">
          {{ truncateContent(source.content) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 只展示 Top 3 引用
const displaySources = computed(() => {
  return props.sources.slice(0, 3)
})
</script>
```

### 5.4 引用样式

```css
.source-ref {
  display: inline-block;
  background: #eef2ff;
  color: #6366f1;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.85em;
  cursor: pointer;
  transition: background-color 0.2s;
}

.source-ref:hover {
  background: #e0e7ff;
}
```

---

## 6. 最佳实践

### 6.1 Prompt优化技巧

1. **明确角色定位**
   ```
   你是一个智能问答助手。
   ```

2. **清晰的任务说明**
   ```
   请基于以下参考资料回答用户的问题。
   ```

3. **具体的输出要求**
   ```
   1. 基于参考资料给出准确、详细的回答
   2. 如果引用了某段资料，请在回答中标注来源编号
   3. 如果参考资料不足以回答问题，请明确说明
   4. 回答应该条理清晰，易于理解
   ```

### 6.2 上下文质量优化

1. **相似度阈值过滤**: 只保留相似度 > 0.3 的结果
2. **去重处理**: 避免重复内容占用上下文空间
3. **长度控制**: 单个上下文项不超过500字
4. **来源多样性**: 尽量包含不同来源的信息

### 6.3 错误处理

```python
try:
    response = await llm.ainvoke(messages)
except Exception as e:
    if "context_length_exceeded" in str(e):
        raise GenerationError("上下文过长，请减少检索数量或缩短问题")
    elif "rate_limit" in str(e):
        raise GenerationError("请求过于频繁，请稍后重试")
    else:
        raise GenerationError(f"生成失败: {str(e)}")
```

### 6.4 性能优化

1. **流式输出**: 使用SSE流式返回，提升用户体验
2. **Token估算**: 提前估算Token数，避免超限
3. **超时控制**: 设置合理的请求超时时间
4. **重试机制**: 网络错误时自动重试

```python
llm = ChatOpenAI(
    model=model,
    streaming=True,           # 启用流式
    request_timeout=120,      # 120秒超时
    max_retries=3,            # 最多重试3次
)
```

### 6.5 安全考虑

1. **输入验证**: 验证问题长度和内容
2. **敏感词过滤**: 过滤敏感内容
3. **输出审核**: 检查生成内容的合规性
4. **日志记录**: 记录请求和响应用于审计

```python
def _validate_request(self, request: GenerationRequest) -> None:
    """验证生成请求参数"""
    if request.model not in GENERATION_MODELS:
        raise ModelNotFoundError(f"Model '{request.model}' not supported")
    
    # 检查上下文长度
    model_info = GENERATION_MODELS[request.model]
    total_context_length = sum(len(item.content) for item in request.context)
    estimated_tokens = total_context_length // 4 + len(request.question) // 4
    
    if estimated_tokens > model_info["context_length"] * 0.8:
        raise GenerationError("Context too long")
```
