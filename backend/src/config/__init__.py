"""Configuration module for embedding optimization."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # File Storage
    UPLOAD_DIR: str = "../uploads"
    RESULTS_DIR: str = "./results"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB in bytes
    
    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_USER: str = ""
    MILVUS_PASSWORD: str = ""
    MILVUS_TIMEOUT: int = 30
    
    # Vector Index
    VECTOR_INDEX_RESULTS_DIR: str = "results/vector_index"
    VECTOR_INDEX_DEFAULT_PROVIDER: str = "milvus"
    
    # Reranker 配置 (混合检索精排 - 远程 API)
    RERANKER_MODEL: str = "qwen3-reranker-4b"
    RERANKER_API_KEY: str = ""
    RERANKER_API_BASE_URL: str = ""  # 如 http://your-reranker-server.example.com/api/llmproxy
    RERANKER_TIMEOUT: int = 30
    RERANKER_TOP_N: int = 20
    # qwen3-reranker 任务指令前缀（参考 Qwen3-Reranker 官方 HuggingFace Model Card）
    # 该 instruction 会拼接到 query 前面，帮助 Reranker 理解检索任务意图
    # 格式: "Instruct: {task_description}\nQuery: {actual_query}"
    # 设为空字符串则不添加前缀（适配不需要 instruction 的 Reranker 模型）
    RERANKER_TASK_INSTRUCTION: str = "Given a user query about product features, retrieve the most relevant document passages that directly describe the queried functionality, modules, or UI components."
    
    # 混合检索配置
    RRF_K: int = 60                    # RRF 融合参数（前端不暴露，业内标准默认值）
    MAX_COLLECTIONS: int = 5           # 联合搜索最大 Collection 数
    DEFAULT_SEARCH_MODE: str = "auto"  # auto = 乐观尝试混合检索 + 自动降级
    RERANKER_SCORE_THRESHOLD: float = 0.4  # Reranker 精排后绝对阈值，低于此分数的结果将被过滤（参考 Dify/Cohere 实践）
    RERANKER_DYNAMIC_THRESHOLD_RATIO: float = 0.6  # 动态阈值比例：实际阈值 = max(静态阈值, Top1分数 × 该比例)，参考 Google Vertex AI Search 实践
    RERANKER_DYNAMIC_THRESHOLD_MAX: float = 0.5  # 动态阈值上限：无论 Top1 分数多高，动态阈值不超过此上限，防止 Top1 波动导致误杀（参考 Pinecone 实践）
    RERANKER_MIN_RESULTS: int = 2  # 保底召回数：阈值过滤后至少保留的结果数，防止极端情况下全部被过滤（参考 Dify/LangChain 保底策略）
    
    # 三层防御体系：候选集噪声控制配置
    # 第 1 层：每文档候选配额控制（Reranker 前），限制每个文档（index）最多贡献的候选数量
    # 设为 0 表示不限制。参考 Cohere max_chunks_per_doc 设计
    MAX_CHUNKS_PER_DOC: int = 10
    # 第 1.5 层：近重复内容去重（Reranker 前），基于 N-gram Jaccard 相似度自动检测并去除
    # 不同文档间内容高度相似的 chunk（如导航栏、页脚、免责声明等共用组件）
    # 设为 0 表示禁用。0.5 = 中等严格度（推荐，可有效去除跨文档模板化重复如导航栏/页脚），0.7 = 高严格度，0.85 = 极高严格度
    # 参考 Cohere Rerank 官方建议（Rerank 前去重提升效果）、Google 网页去重（SimHash 汉明距离 ≈ Jaccard 0.4~0.6）、LangChain EnsembleRetriever unique_union 实践
    NEAR_DUPLICATE_THRESHOLD: float = 0.5
    # 第 3 层：文档来源多样性控制（Reranker 后），限制每个文档在最终结果中最多占几条
    # 设为 0 表示不限制。适用于需要结果来源多样化的场景
    MAX_RESULTS_PER_DOC: int = 2
    
    # 查询增强配置 (Query Enhancement)
    QUERY_ENHANCEMENT_ENABLED: bool = True         # 是否启用查询增强（全局开关）
    QUERY_ENHANCEMENT_MODEL: str = "qwen3.5-35b-a3b"  # 查询增强使用的 LLM 模型
    QUERY_ENHANCEMENT_TEMPERATURE: float = 0.3      # 温度参数（查询改写需要精确性，不宜过高）
    QUERY_ENHANCEMENT_MAX_TOKENS: int = 512          # 最大输出 token 数（JSON 输出无需太大）
    QUERY_ENHANCEMENT_TIMEOUT: int = 30              # 请求超时时间（秒）
    
    # Embedding API Configuration
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_API_BASE_URL: str = ""  # 必须通过 .env 配置
    EMBEDDING_DEFAULT_MODEL: str = "qwen3-embedding-8b"
    
    # Embedding Retry Configuration
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_TIMEOUT: int = 60
    EMBEDDING_INITIAL_DELAY: int = 1
    EMBEDDING_MAX_DELAY: int = 32
    
    # Embedding Storage Configuration
    EMBEDDING_RESULTS_DIR: str = "results/embedding"
    
    # Embedding Client Authentication
    EMBEDDING_CLIENT_API_KEY: Optional[str] = None
    FRONTEND_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:4173"
    
    # Docling Serve Configuration
    DOCLING_SERVE_URL: str = "http://localhost:5001"
    DOCLING_SERVE_API_KEY: Optional[str] = None
    DOCLING_SERVE_TIMEOUT: int = 600  # 10 分钟，适应大文件处理
    DOCLING_SERVE_ENABLED: bool = True
    
    # Chunking Optimization Configuration
    # Semantic Chunker: bge-m3 (fast) / qwen3-embedding-8b (high-precision)
    SEMANTIC_CHUNKER_MODEL: str = "bge-m3"
    SEMANTIC_CHUNKER_USE_EMBEDDING: bool = True
    SEMANTIC_CHUNKER_SIMILARITY_THRESHOLD: float = 0.7
    
    # Large document processing
    LARGE_DOCUMENT_THRESHOLD: int = 50000000  # 5000万字符
    STREAM_SEGMENT_SIZE: int = 100000  # 流式处理段大小
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    LOG_LEVEL: str = "info"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# ============================================================================
# Smart chunking parameters - re-export from smart_params module
# ============================================================================

from .smart_params import (
    # Enums
    DocumentLength,
    DocumentCategory,
    
    # Configuration tables
    FORMAT_BASE_PARAMS,
    LENGTH_ADJUSTMENTS,
    EMBEDDING_MODEL_PARAMS,
    HYBRID_STRATEGY_PARAMS,
    PARENT_CHILD_STRATEGY_PARAMS,
    HEADING_STRATEGY_PARAMS,
    PARAGRAPH_STRATEGY_PARAMS,
    
    # Functions
    get_document_length_category,
    get_format_category,
    get_base_text_params,
    get_adaptive_text_params,
    get_semantic_params,
    get_hybrid_params,
    get_parent_child_params,
    get_heading_params,
    get_paragraph_params,
    get_character_params,
    get_smart_params,
    get_all_format_params,
    get_all_embedding_params,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    
    # Enums
    "DocumentLength",
    "DocumentCategory",
    
    # Configuration tables
    "FORMAT_BASE_PARAMS",
    "LENGTH_ADJUSTMENTS",
    "EMBEDDING_MODEL_PARAMS",
    "HYBRID_STRATEGY_PARAMS",
    "PARENT_CHILD_STRATEGY_PARAMS",
    "HEADING_STRATEGY_PARAMS",
    "PARAGRAPH_STRATEGY_PARAMS",
    
    # Functions
    "get_document_length_category",
    "get_format_category",
    "get_base_text_params",
    "get_adaptive_text_params",
    "get_semantic_params",
    "get_hybrid_params",
    "get_parent_child_params",
    "get_heading_params",
    "get_paragraph_params",
    "get_character_params",
    "get_smart_params",
    "get_all_format_params",
    "get_all_embedding_params",
]
