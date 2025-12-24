"""
FAISS 向量索引提供者实现

使用 FAISS 库实现内存中的向量索引和检索
"""
import uuid
import pickle
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np

try:
    import faiss
except ImportError:
    raise ImportError("faiss-cpu or faiss-gpu is required. Install with: pip install faiss-cpu")

from .base_provider import BaseProvider, IndexConfig, SearchResult
from ...vector_config import FAISSConfig
from ...utils.logger import get_logger
from ...utils.vector_utils import validate_vector, normalize_vector
from ...exceptions.vector_index_errors import (
    IndexNotFoundError,
    VectorDimensionError,
    IndexBuildError,
    SearchError
)

logger = get_logger("faiss_provider")


class FAISSProvider(BaseProvider):
    """FAISS 向量索引提供者"""

    def __init__(self, config: Optional[FAISSConfig] = None, **kwargs):
        """
        初始化 FAISS 提供者
        
        Args:
            config: FAISS 配置对象
        """
        # 不调用父类 __init__，因为我们使用不同的初始化方式
        self.config = config or FAISSConfig()
        self._indexes: Dict[str, Dict[str, Any]] = {}
        self._current_index_id: Optional[str] = None
        self._ensure_index_dir()
        
        # 设置默认属性（兼容 BaseProvider 接口）
        self.index_name = kwargs.get('index_name', '')
        self.dimension = kwargs.get('dimension', 0)
        self.metric_type = kwargs.get('metric_type', 'cosine')
        
        logger.info(f"Initialized FAISSProvider with index_dir={self.config.index_dir}")

    def _ensure_index_dir(self) -> None:
        """确保索引目录存在"""
        Path(self.config.index_dir).mkdir(parents=True, exist_ok=True)

    def connect(self) -> None:
        """连接到 FAISS（无操作，FAISS 是本地库）"""
        logger.info("FAISS provider ready (local mode)")

    def disconnect(self) -> None:
        """断开连接（无操作）"""
        self._indexes.clear()
        logger.info("FAISS provider disconnected")

    def create_index(self, config_or_type: Any = None, index_params: Dict[str, Any] = None) -> Any:
        """
        创建 FAISS 索引
        
        支持两种调用方式：
        1. create_index(config: IndexConfig) - 使用 IndexConfig 对象
        2. create_index(index_type: str, index_params: dict) - BaseProvider 抽象方法签名
        
        Args:
            config_or_type: IndexConfig 对象或索引类型字符串
            index_params: 索引参数（仅在第二种调用方式时使用）
            
        Returns:
            索引 ID（第一种方式）或 True（第二种方式）
        """
        try:
            # 判断调用方式
            if isinstance(config_or_type, IndexConfig):
                # 方式1：使用 IndexConfig
                config = config_or_type
                index_id = str(uuid.uuid4())
                
                # 创建 FAISS 索引
                faiss_index = self._build_faiss_index(
                    dimension=config.dimension,
                    metric_type=config.metric_type,
                    index_type=config.index_type
                )
                
                # 存储索引信息
                self._indexes[index_id] = {
                    "index": faiss_index,
                    "index_name": config.index_name,
                    "dimension": config.dimension,
                    "metric_type": config.metric_type,
                    "index_type": config.index_type or "Flat",
                    "metadata": {},  # vector_id -> metadata
                    "vector_ids": [],  # 按插入顺序存储 vector_id
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                self._current_index_id = index_id
                logger.info(f"Created FAISS index: {config.index_name} (ID: {index_id})")
                return index_id
            else:
                # 方式2：BaseProvider 抽象方法签名
                index_type = config_or_type or "Flat"
                index_params = index_params or {}
                
                index_id = str(uuid.uuid4())
                dimension = self.dimension or index_params.get("dimension", 128)
                metric_type = self.metric_type or index_params.get("metric_type", "cosine")
                
                faiss_index = self._build_faiss_index(
                    dimension=dimension,
                    metric_type=metric_type,
                    index_type=index_type
                )
                
                self._indexes[index_id] = {
                    "index": faiss_index,
                    "index_name": self.index_name or f"index_{index_id[:8]}",
                    "dimension": dimension,
                    "metric_type": metric_type,
                    "index_type": index_type,
                    "metadata": {},
                    "vector_ids": [],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                self._current_index_id = index_id
                logger.info(f"Created FAISS index with type {index_type} (ID: {index_id})")
                return True
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {str(e)}")
            raise IndexBuildError(f"FAISS index creation failed: {str(e)}")

    def _build_faiss_index(
        self, 
        dimension: int, 
        metric_type: str,
        index_type: Optional[str] = None
    ) -> faiss.Index:
        """
        构建 FAISS 索引对象
        
        Args:
            dimension: 向量维度
            metric_type: 相似度度量类型
            index_type: 索引类型
            
        Returns:
            FAISS Index 对象
        """
        # 确定度量类型
        if metric_type.lower() in ["cosine", "dot_product"]:
            metric = faiss.METRIC_INNER_PRODUCT
        else:  # euclidean
            metric = faiss.METRIC_L2
        
        # 根据索引类型创建索引
        index_type = (index_type or "Flat").upper()
        
        if index_type == "FLAT":
            # 暴力搜索，精确但慢
            index = faiss.IndexFlatIP(dimension) if metric == faiss.METRIC_INNER_PRODUCT else faiss.IndexFlatL2(dimension)
        
        elif index_type == "IVF_FLAT":
            # IVF (Inverted File) 索引
            quantizer = faiss.IndexFlatL2(dimension)
            nlist = 100  # 聚类中心数量
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist, metric)
        
        elif index_type == "HNSW":
            # HNSW (Hierarchical Navigable Small World) 索引
            M = 32  # 每个节点的连接数
            index = faiss.IndexHNSWFlat(dimension, M, metric)
        
        else:
            # 默认使用 Flat
            logger.warning(f"Unknown index type {index_type}, using Flat")
            index = faiss.IndexFlatIP(dimension) if metric == faiss.METRIC_INNER_PRODUCT else faiss.IndexFlatL2(dimension)
        
        return index

    def add_vectors(
        self, 
        index_id: str, 
        vectors: np.ndarray, 
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        向索引添加向量
        
        Args:
            index_id: 索引 ID
            vectors: 向量数组
            metadata: 元数据列表
            
        Returns:
            向量 ID 列表
        """
        try:
            index_info = self._get_index_info(index_id)
            faiss_index = index_info["index"]
            
            # 验证向量维度
            if vectors.shape[1] != index_info["dimension"]:
                raise VectorDimensionError(
                    f"Expected dimension {index_info['dimension']}, got {vectors.shape[1]}"
                )
            
            # 生成向量 ID
            vector_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            
            # 验证和归一化向量
            normalized_vectors = []
            for vec in vectors:
                validate_vector(vec)
                # 如果是余弦相似度，归一化向量
                if index_info["metric_type"].lower() == "cosine":
                    normalized_vectors.append(normalize_vector(vec))
                else:
                    normalized_vectors.append(vec)
            
            vectors_array = np.array(normalized_vectors, dtype=np.float32)
            
            # 如果是 IVF 索引且未训练，先训练
            if hasattr(faiss_index, 'is_trained') and not faiss_index.is_trained:
                logger.info(f"Training IVF index with {len(vectors_array)} vectors")
                faiss_index.train(vectors_array)
            
            # 添加向量到索引
            faiss_index.add(vectors_array)
            
            # 存储元数据
            for i, vector_id in enumerate(vector_ids):
                index_info["metadata"][vector_id] = metadata[i]
                index_info["vector_ids"].append(vector_id)
            
            index_info["updated_at"] = datetime.now()
            
            logger.info(f"Added {len(vectors)} vectors to FAISS index {index_id}")
            return vector_ids
            
        except Exception as e:
            logger.error(f"Failed to add vectors to FAISS: {str(e)}")
            raise IndexBuildError(f"Failed to add vectors: {str(e)}")

    def search(
        self, 
        index_id: str, 
        query_vector: np.ndarray, 
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        向量相似度搜索
        
        Args:
            index_id: 索引 ID
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件（FAISS 本地模式暂不支持）
            
        Returns:
            搜索结果列表
        """
        try:
            index_info = self._get_index_info(index_id)
            faiss_index = index_info["index"]
            
            # 验证查询向量
            validate_vector(query_vector)
            
            # 归一化（如果使用余弦相似度）
            if index_info["metric_type"].lower() == "cosine":
                query_vector = normalize_vector(query_vector)
            
            query_array = np.array([query_vector], dtype=np.float32)
            
            # 执行搜索
            distances, indices = faiss_index.search(query_array, top_k)
            
            # 转换结果
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS 返回 -1 表示没有更多结果
                    break
                
                # 获取对应的 vector_id
                if idx < len(index_info["vector_ids"]):
                    vector_id = index_info["vector_ids"][idx]
                    metadata = index_info["metadata"].get(vector_id, {})
                    
                    results.append(SearchResult(
                        vector_id=vector_id,
                        score=float(dist),
                        metadata=metadata
                    ))
            
            logger.info(f"FAISS search completed: found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {str(e)}")
            raise SearchError(f"Search failed: {str(e)}")

    def delete_index(self, index_id: str) -> None:
        """
        删除索引
        
        Args:
            index_id: 索引 ID
        """
        try:
            if index_id not in self._indexes:
                raise IndexNotFoundError(f"Index {index_id} not found")
            
            # 删除持久化文件（如果存在）
            index_file = Path(self.config.index_dir) / f"{index_id}.faiss"
            metadata_file = Path(self.config.index_dir) / f"{index_id}.metadata.pkl"
            
            if index_file.exists():
                index_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            # 从内存中删除
            del self._indexes[index_id]
            
            logger.info(f"Deleted FAISS index: {index_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete FAISS index: {str(e)}")
            raise IndexBuildError(f"Failed to delete index: {str(e)}")

    def get_index_stats(self, index_id: str = None) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Args:
            index_id: 索引 ID（可选，如果不提供则使用当前索引）
            
        Returns:
            统计信息字典
        """
        try:
            target_id = index_id or self._current_index_id
            if not target_id:
                return {"vector_count": 0, "index_size_bytes": 0}
            
            index_info = self._get_index_info(target_id)
            faiss_index = index_info["index"]
            
            stats = {
                "vector_count": faiss_index.ntotal,
                "index_type": "FAISS",
                "metric_type": index_info["metric_type"],
                "dimension": index_info["dimension"],
                "index_size_bytes": self._estimate_memory_usage(faiss_index),
                "memory_usage_bytes": self._estimate_memory_usage(faiss_index),
                "last_updated": index_info["updated_at"].isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get FAISS index stats: {str(e)}")
            raise IndexBuildError(f"Failed to get stats: {str(e)}")

    def save_index(self, index_id: str) -> str:
        """
        持久化索引到磁盘
        
        Args:
            index_id: 索引 ID
            
        Returns:
            保存的文件路径
        """
        try:
            index_info = self._get_index_info(index_id)
            faiss_index = index_info["index"]
            
            # 保存 FAISS 索引
            index_file = Path(self.config.index_dir) / f"{index_id}.faiss"
            faiss.write_index(faiss_index, str(index_file))
            
            # 保存元数据
            metadata_file = Path(self.config.index_dir) / f"{index_id}.metadata.pkl"
            metadata_to_save = {
                "index_name": index_info["index_name"],
                "dimension": index_info["dimension"],
                "metric_type": index_info["metric_type"],
                "index_type": index_info["index_type"],
                "metadata": index_info["metadata"],
                "vector_ids": index_info["vector_ids"],
                "created_at": index_info["created_at"],
                "updated_at": index_info["updated_at"]
            }
            
            with open(metadata_file, 'wb') as f:
                pickle.dump(metadata_to_save, f)
            
            logger.info(f"Saved FAISS index {index_id} to {index_file}")
            return str(index_file)
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {str(e)}")
            raise IndexBuildError(f"Failed to save index: {str(e)}")

    def load_index(self, index_id: str = None) -> bool:
        """
        从磁盘加载索引
        
        Args:
            index_id: 索引 ID（可选）
            
        Returns:
            True if successful
        """
        try:
            target_id = index_id or self._current_index_id
            if not target_id:
                return False
            
            index_file = Path(self.config.index_dir) / f"{target_id}.faiss"
            metadata_file = Path(self.config.index_dir) / f"{target_id}.metadata.pkl"
            
            if not index_file.exists() or not metadata_file.exists():
                raise IndexNotFoundError(f"Index files not found for {target_id}")
            
            # 加载 FAISS 索引
            faiss_index = faiss.read_index(str(index_file))
            
            # 加载元数据
            with open(metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            
            # 恢复索引信息
            self._indexes[target_id] = {
                "index": faiss_index,
                **metadata
            }
            
            logger.info(f"Loaded FAISS index {target_id} from {index_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {str(e)}")
            raise IndexBuildError(f"Failed to load index: {str(e)}")

    def _get_index_info(self, index_id: str) -> Dict[str, Any]:
        """获取索引信息"""
        if index_id not in self._indexes:
            raise IndexNotFoundError(f"Index {index_id} not found")
        return self._indexes[index_id]

    def _estimate_memory_usage(self, index: faiss.Index) -> int:
        """估算索引内存使用（字节）"""
        # 简化估算：向量数量 * 维度 * float32 size (4 bytes)
        return index.ntotal * index.d * 4

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态字典
        """
        try:
            # 检查索引目录是否可访问
            exists = Path(self.config.index_dir).exists()
            return {
                "status": "healthy" if exists else "unhealthy",
                "details": {
                    "index_dir": str(self.config.index_dir),
                    "index_count": len(self._indexes)
                }
            }
        except Exception as e:
            logger.error(f"FAISS health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e)}
            }

    # ==================== 实现 BaseProvider 抽象方法 ====================

    def insert_vectors(
        self,
        vectors: np.ndarray,
        vector_ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        插入向量到索引（BaseProvider 抽象方法实现）
        
        Args:
            vectors: 向量数据
            vector_ids: 向量 ID 列表
            metadata: 元数据列表
            
        Returns:
            True if successful
        """
        if not self._current_index_id:
            raise IndexNotFoundError("No active index. Call create_index first.")
        
        # 使用 add_vectors 方法
        self.add_vectors(self._current_index_id, vectors, metadata or [{} for _ in vector_ids])
        return True

    def search_vectors(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        threshold: Optional[float] = None,
        filter_expr: Optional[str] = None,
        **search_params
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量（BaseProvider 抽象方法实现）
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值
            filter_expr: 过滤表达式
            
        Returns:
            搜索结果列表
        """
        if not self._current_index_id:
            raise IndexNotFoundError("No active index. Call create_index first.")
        
        results = self.search(self._current_index_id, query_vector, top_k)
        
        # 转换为字典格式
        return [
            {
                "vector_id": r.vector_id,
                "score": r.score,
                "distance": 1.0 - r.score if self.metric_type == "cosine" else r.score,
                "metadata": r.metadata
            }
            for r in results
            if threshold is None or r.score >= threshold
        ]

    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """
        删除向量（BaseProvider 抽象方法实现）
        
        注意：FAISS 不直接支持按 ID 删除，这是一个简化实现
        
        Args:
            vector_ids: 要删除的向量 ID 列表
            
        Returns:
            True if successful
        """
        if not self._current_index_id:
            raise IndexNotFoundError("No active index.")
        
        index_info = self._get_index_info(self._current_index_id)
        
        # 从元数据中移除
        for vid in vector_ids:
            if vid in index_info["metadata"]:
                del index_info["metadata"][vid]
            if vid in index_info["vector_ids"]:
                index_info["vector_ids"].remove(vid)
        
        logger.warning("FAISS delete_vectors: metadata removed but vectors remain in index until rebuild")
        return True

    def get_vector_count(self) -> int:
        """
        获取向量数量（BaseProvider 抽象方法实现）
        
        Returns:
            向量数量
        """
        if not self._current_index_id:
            return 0
        
        try:
            index_info = self._get_index_info(self._current_index_id)
            return index_info["index"].ntotal
        except:
            return 0

    def persist_index(self) -> bool:
        """
        持久化索引（BaseProvider 抽象方法实现）
        
        Returns:
            True if successful
        """
        if not self._current_index_id:
            raise IndexNotFoundError("No active index.")
        
        self.save_index(self._current_index_id)
        return True
