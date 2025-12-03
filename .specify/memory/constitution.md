<!--
Sync Impact Report:
Version change: [NEW] → 1.0.0
Modified principles: Initial creation
Added sections: All core principles and governance
Removed sections: None
Templates requiring updates: ✅ All templates reviewed and compatible
Follow-up TODOs: None
-->

# 文档处理和检索系统 Constitution

## Core Principles

### I. 模块化架构
每个功能模块必须独立设计和实现；模块间通过明确定义的接口通信；每个模块都有独立的服务层实现（如 loading_service.py, embedding_service.py）；支持插件化扩展，允许添加新的处理方式和提供商。

### II. 多提供商支持
系统必须支持多种技术提供商和实现方式；文档加载支持 PyMuPDF、PyPDF、Unstructured 等多种方式；向量嵌入支持 OpenAI、Bedrock、HuggingFace 等多个提供商；向量数据库支持 Milvus、Pinecone 等多种选择；AI模型支持 Ollama 和 HuggingFace 两个选项。

### III. 结果持久化 (NON-NEGOTIABLE)
每个功能模块的处理结果必须保存为 JSON 格式；文件命名规范：文档名_时间戳.json；结果文件供下一步处理调用；确保处理链路的可追溯性和可恢复性。

### IV. 用户体验优先
前端采用 Vue3 + Vite + TailwindCSS 技术栈；左侧导航栏 + 右侧内容区域的统一布局；每个功能模块页面采用左侧控制面板 + 右侧内容显示的布局；提供文档预览、处理结果预览、嵌入可视化等用户友好功能。

### V. API标准化
后端基于 FastAPI 实现统一的 RESTful API；统一的错误处理和响应格式；统一的加载状态管理；支持 JSON 和人类可读格式的输出；清晰的 API 文档和接口规范。

## 技术约束

### 前端技术栈
- Vue3 + Vite 作为基础开发框架
- TailwindCSS 用于样式管理  
- Vue Router 4 用于路由管理
- Vue 3 Composition API 进行状态管理
- Grid 系统实现响应式布局

### 后端技术栈
- FastAPI 作为 Web 框架
- 支持 Ollama 和 HuggingFace 两种 AI 模型选项
- 每个功能模块独立的 service 文件
- JSON 格式的结果存储
- 统一的错误处理机制

### 核心功能模块
1. 文档加载（LoadFile）- 多种加载方式支持
2. 文档分块（ChunkFile）- 多种分块策略
3. 文档解析（ParseFile）- 多种解析选项
4. 向量嵌入（EmbeddingFile）- 多提供商支持
5. 向量索引（Indexing）- 多数据库支持，包含搜索功能
6. 文本生成（Generation）- 多模型支持

## 开发工作流

### 代码组织
- 前端组件化设计，统一的页面布局模式
- 后端服务层模式，每个功能独立的 service 文件
- 清晰的文件命名和目录结构
- API 接口的统一调用模式

### 质量保证
- 统一的错误处理和状态提示
- 处理结果的预览和验证功能
- 用户操作的反馈和确认机制
- 系统性能和响应时间监控

## Governance

本宪章规定了文档处理和检索系统的核心设计原则和技术约束。所有功能开发必须遵循模块化架构、多提供商支持、结果持久化等核心原则。代码审查过程必须验证是否符合宪章要求。任何违反核心原则的设计必须提供充分的技术理由和替代方案。

**Version**: 1.0.0 | **Ratified**: 2025-12-01 | **Last Amended**: 2025-12-01