"""
Reranker 精排服务

基于 bge-reranker-v2-m3 模型，对 RRF 粗排后的候选集进行精排重排序。
支持 FP16 推理加速和 batch 处理。
"""
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("reranker_service")

# 尝试导入 FlagEmbedding
try:
    from FlagEmbedding import FlagReranker
    FLAG_EMBEDDING_AVAILABLE = True
except ImportError:
    FLAG_EMBEDDING_AVAILABLE = False
    logger.warning("FlagEmbedding 未安装，Reranker 服务不可用。请运行: pip install FlagEmbedding>=1.2.0")


class RerankerService:
    """
    bge-reranker-v2-m3 精排服务
    
    功能：
    - 加载 bge-reranker-v2-m3 模型
    - 对候选集进行 batch 精排推理
    - 返回按 reranker_score 排序的结果
    - 健康检查
    """
    
    _instance: Optional['RerankerService'] = None
    _initialized: bool = False
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        use_fp16: bool = True,
        batch_size: int = 32
    ):
        """
        初始化 Reranker 服务
        
        Args:
            model_name: Reranker 模型名称
            use_fp16: 是否使用 FP16 推理（加速）
            batch_size: 批处理大小
        """
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self._reranker = None
        self._available = False
        
    def init(self) -> bool:
        """
        延迟初始化：加载模型
        
        Returns:
            True 如果加载成功
        """
        if self._reranker is not None:
            return True
            
        if not FLAG_EMBEDDING_AVAILABLE:
            logger.error("FlagEmbedding 库未安装，无法初始化 Reranker")
            self._available = False
            return False
        
        try:
            logger.info(f"正在加载 Reranker 模型: {self.model_name} (fp16={self.use_fp16})")
            start_time = time.time()
            
            self._reranker = FlagReranker(
                self.model_name,
                use_fp16=self.use_fp16
            )
            
            load_time = time.time() - start_time
            logger.info(f"Reranker 模型加载成功，耗时 {load_time:.2f}s")
            self._available = True
            return True
            
        except Exception as e:
            logger.error(f"Reranker 模型加载失败: {e}")
            self._available = False
            return False
    
    @property
    def available(self) -> bool:
        """Reranker 是否可用"""
        return self._available and self._reranker is not None
    
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
            
            # 构造 query-document pairs
            pairs = []
            for c in candidates:
                doc_text = c.get(text_key, "") or ""
                if not doc_text:
                    # 尝试从 metadata 获取文本
                    metadata = c.get("metadata", {}) or {}
                    doc_text = metadata.get("source_text", "") or metadata.get("text", "") or ""
                pairs.append([query, doc_text])
            
            # batch 推理
            scores = self._reranker.compute_score(pairs, normalize=True)
            
            # 处理单条结果的情况
            if not isinstance(scores, list):
                scores = [scores]
            
            # 将分数附加到候选集
            for i, candidate in enumerate(candidates):
                if i < len(scores):
                    candidate["reranker_score"] = float(scores[i])
                else:
                    candidate["reranker_score"] = 0.0
            
            # 按 reranker_score 降序排序
            sorted_results = sorted(
                candidates, 
                key=lambda x: x.get("reranker_score", 0), 
                reverse=True
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Reranker 精排完成: {len(candidates)} 条候选 → Top-{top_k}, "
                f"耗时 {elapsed_ms:.1f}ms"
            )
            
            return sorted_results[:top_k]
            
        except Exception as e:
            logger.error(f"Reranker 推理失败: {e}")
            # 降级：返回原始候选集的前 top_k 条
            return candidates[:top_k]
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        return {
            "available": self.available,
            "model_name": self.model_name,
            "use_fp16": self.use_fp16,
            "flag_embedding_installed": FLAG_EMBEDDING_AVAILABLE,
            "model_loaded": self._reranker is not None
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
