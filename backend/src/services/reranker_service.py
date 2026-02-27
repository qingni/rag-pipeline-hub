"""
Reranker 精排服务

基于远程 Reranker API（OpenAI-compatible），对 RRF 粗排后的候选集进行精排重排序。
使用 qwen3-reranker-4b 模型进行精排重排序。
"""
import time
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

logger = logging.getLogger("reranker_service")

# 支持的 Reranker 模型列表
SUPPORTED_RERANKER_MODELS = [
    "qwen3-reranker-4b",       # 32K 序列，100+ 语言，多功能检索
]


class RerankerService:
    """
    远程 Reranker 精排服务（OpenAI-compatible API）
    
    功能：
    - 通过远程 API 调用 Reranker 模型进行精排
    - 对候选集进行 batch 精排推理
    - 返回按 reranker_score 排序的结果
    - 健康检查（通过 API 连通性测试）
    
    支持模型：
    - qwen3-reranker-4b: 在各种文本检索场景中表现出色（32K 序列，100+ 语言）
    """
    
    _instance: Optional['RerankerService'] = None
    _initialized: bool = False
    
    def __init__(
        self,
        model_name: str = "qwen3-reranker-4b",
        api_key: str = "",
        api_base_url: str = "",
        timeout: int = 30
    ):
        """
        初始化 Reranker 服务
        
        Args:
            model_name: Reranker 模型名称（默认 qwen3-reranker-4b）
            api_key: API 密钥
            api_base_url: API 基础 URL（如 http://your-reranker-server.example.com/api/llmproxy）
            timeout: API 请求超时时间（秒）
        """
        self.model_name = model_name
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.timeout = timeout
        self._client: Optional[OpenAI] = None
        self._available = False
        
    def init(self) -> bool:
        """
        初始化：创建 OpenAI 客户端并测试连通性
        
        Returns:
            True 如果初始化成功
        """
        if self._client is not None:
            return True
            
        if not self.api_base_url:
            logger.error("Reranker API base URL 未配置，无法初始化")
            self._available = False
            return False
        
        if not self.api_key:
            logger.warning("Reranker API key 未配置，尝试无认证连接")
        
        try:
            logger.info(
                f"正在初始化 Reranker API 客户端: model={self.model_name}, "
                f"base_url={self.api_base_url}"
            )
            
            self._client = OpenAI(
                api_key=self.api_key or "no-key",
                base_url=self.api_base_url,
                timeout=self.timeout
            )
            
            # 测试连通性：发送一个最小化的 rerank 请求
            test_response = self._client.post(
                path="/rerank",
                body={
                    "model": self.model_name,
                    "query": "test",
                    "documents": ["test document"],
                    "top_n": 1,
                    "return_documents": False
                },
                cast_to=Dict[str, Any]
            )
            
            logger.info(f"Reranker API 连通性测试成功: model={self.model_name}")
            self._available = True
            return True
            
        except Exception as e:
            logger.error(f"Reranker API 初始化失败: {e}")
            self._client = None
            self._available = False
            return False
    
    @property
    def available(self) -> bool:
        """Reranker 是否可用"""
        return self._available and self._client is not None
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        text_key: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        对候选集进行精排重排序
        
        Args:
            query: 原始查询文本
            candidates: 候选集列表，每条包含 text 字段
            top_k: 最终返回数量
            text_key: 候选集中文本字段的 key
            
        Returns:
            按 reranker_score 降序排序的 Top-K 结果
        """
        if not self.available:
            logger.warning("Reranker 不可用，跳过精排")
            return candidates[:top_k]
        
        if not candidates:
            return []
        
        if not query or not query.strip():
            logger.warning("查询文本为空，跳过 Reranker 精排")
            return candidates[:top_k]
        
        try:
            start_time = time.time()
            
            # 提取候选文档文本
            documents = []
            for c in candidates:
                doc_text = c.get(text_key, "") or ""
                if not doc_text:
                    # 尝试从 metadata 获取文本
                    metadata = c.get("metadata", {}) or {}
                    doc_text = metadata.get("source_text", "") or metadata.get("text", "") or ""
                documents.append(doc_text)
            
            # 调用远程 Reranker API
            response = self._client.post(
                path="/rerank",
                body={
                    "model": self.model_name,
                    "query": query,
                    "documents": documents,
                    "top_n": min(top_k, len(documents)),
                    "return_documents": False
                },
                cast_to=Dict[str, Any]
            )
            
            # 解析 API 响应，提取 reranker_score
            # 响应格式: { "results": [{"index": 0, "relevance_score": 0.95}, ...] }
            if isinstance(response, dict):
                results = response.get("results") or []
            elif hasattr(response, "results"):
                results = response.results or []
            else:
                results = []
            
            # 构建 index -> score 映射
            score_map = {}
            for item in results:
                idx = item.get("index", 0)
                score = item.get("relevance_score", 0.0)
                score_map[idx] = float(score)
            
            # 将分数附加到候选集
            for i, candidate in enumerate(candidates):
                candidate["reranker_score"] = score_map.get(i, 0.0)
            
            # 按 reranker_score 降序排序
            sorted_results = sorted(
                candidates, 
                key=lambda x: x.get("reranker_score", 0), 
                reverse=True
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Reranker 精排完成: {len(candidates)} 条候选 → Top-{top_k}, "
                f"模型={self.model_name}, 耗时 {elapsed_ms:.1f}ms"
            )
            
            return sorted_results[:top_k]
            
        except Exception as e:
            logger.error(f"Reranker API 调用失败: {e}")
            # 降级：按原始相似度分数排序后返回 top_k（而非按原始顺序截取）
            fallback = sorted(
                candidates,
                key=lambda x: x.get("score", 0),
                reverse=True
            )
            return fallback[:top_k]
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        return {
            "available": self.available,
            "model_name": self.model_name,
            "api_base_url": self.api_base_url,
            "api_connected": self._client is not None,
            "supported_models": SUPPORTED_RERANKER_MODELS
        }
    
    @classmethod
    def get_instance(cls, **kwargs) -> 'RerankerService':
        """
        获取单例实例
        
        Args:
            **kwargs: 传递给构造函数的参数
            
        Returns:
            RerankerService 单例
        """
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（主要用于测试）"""
        cls._instance = None
        cls._initialized = False
