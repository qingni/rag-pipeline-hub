"""
Milvus 向量索引提供者实现

实现 Milvus 向量数据库的索引管理和检索功能
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)

from .base_provider import BaseProvider, IndexConfig, SearchResult
from ...vector_config import MilvusConfig
from ...utils.logger import get_logger
from ...utils.vector_utils import validate_vector, normalize_vector
from ...exceptions.vector_index_errors import (
    IndexNotFoundError,
    VectorDimensionError,
    IndexBuildError,
    SearchError
)

logger = get_logger("milvus_provider")


class MilvusProvider(BaseProvider):
    """Milvus 向量索引提供者"""

    def __init__(self, config: Optional[MilvusConfig] = None):
        """
        初始化 Milvus 提供者
        
        Args:
            config: Milvus 配置对象，如果为 None 则使用默认配置
        """
        self.config = config or MilvusConfig()
        self._connected = False
        self._collections: Dict[str, Collection] = {}
        
        logger.info(f"Initializing MilvusProvider with host={self.config.host}:{self.config.port}")

    def connect(self) -> None:
        """连接到 Milvus 服务器"""
        try:
            connections.connect(
                alias="default",
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                timeout=self.config.timeout
            )
            self._connected = True
            logger.info("Successfully connected to Milvus")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise IndexBuildError(f"Milvus connection failed: {str(e)}")

    def disconnect(self) -> None:
        """断开与 Milvus 的连接"""
        try:
            connections.disconnect("default")
            self._connected = False
            self._collections.clear()
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {str(e)}")

    def _ensure_connected(self) -> None:
        """确保已连接到 Milvus"""
        if not self._connected:
            self.connect()

    def _create_collection_schema(
        self, 
        index_name: str, 
        dimension: int, 
        metric_type: str
    ) -> CollectionSchema:
        """
        创建 Milvus Collection Schema
        
        Args:
            index_name: 索引名称
            dimension: 向量维度
            metric_type: 相似度度量类型
            
        Returns:
            CollectionSchema 对象
        """
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description=f"Vector index: {index_name}"
        )
        
        return schema

    def create_index(self, config: IndexConfig) -> str:
        """
        创建向量索引
        
        Args:
            config: 索引配置
            
        Returns:
            索引 ID
        """
        self._ensure_connected()
        
        try:
            index_id = str(uuid.uuid4())
            collection_name = f"{config.index_name}_{index_id[:8]}"
            
            # 检查 collection 是否已存在
            if utility.has_collection(collection_name):
                raise IndexBuildError(f"Collection {collection_name} already exists")
            
            # 创建 schema
            schema = self._create_collection_schema(
                config.index_name,
                config.dimension,
                config.metric_type
            )
            
            # 创建 collection
            collection = Collection(
                name=collection_name,
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "metric_type": self._convert_metric_type(config.metric_type),
                "index_type": config.index_type or "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            self._collections[index_id] = collection
            
            logger.info(f"Created Milvus index: {collection_name} (ID: {index_id})")
            return index_id
            
        except Exception as e:
            logger.error(f"Failed to create Milvus index: {str(e)}")
            raise IndexBuildError(f"Milvus index creation failed: {str(e)}")

    def add_vectors(
        self, 
        index_id: str, 
        vectors: np.ndarray, 
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        向索引中添加向量
        
        Args:
            index_id: 索引 ID
            vectors: 向量数组 (n_vectors, dimension)
            metadata: 元数据列表
            
        Returns:
            向量 ID 列表
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            
            # 生成向量 ID
            vector_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            
            # 获取维度信息
            expected_dim = collection.schema.fields[1].params.get("dim", vectors.shape[1] if len(vectors) > 0 else 0)
            
            # 验证和归一化向量
            normalized_vectors = []
            for i, vec in enumerate(vectors):
                validate_vector(vec, expected_dim)
                normalized_vectors.append(normalize_vector(vec).tolist())
            
            # 准备数据
            entities = [
                vector_ids,
                normalized_vectors,
                metadata
            ]
            
            # 插入数据
            insert_result = collection.insert(entities)
            collection.flush()
            
            logger.info(f"Added {len(vectors)} vectors to index {index_id}")
            return vector_ids
            
        except Exception as e:
            logger.error(f"Failed to add vectors to Milvus: {str(e)}")
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
            filters: 过滤条件
            
        Returns:
            搜索结果列表
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            
            # 加载 collection 到内存
            collection.load()
            
            # 获取维度信息
            expected_dim = collection.schema.fields[1].params.get("dim", len(query_vector))
            
            # 验证和归一化查询向量
            validate_vector(query_vector, expected_dim)
            query_vec = normalize_vector(query_vector).tolist()
            
            # 准备搜索参数
            search_params = {
                "metric_type": collection.index().params.get("metric_type", "L2"),
                "params": {"nprobe": 10}
            }
            
            # 执行搜索
            results = collection.search(
                data=[query_vec],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["metadata"]
            )
            
            # 转换结果
            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append(SearchResult(
                        vector_id=hit.id,
                        score=float(hit.score),
                        metadata=hit.entity.get("metadata", {})
                    ))
            
            logger.info(f"Search completed: found {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Milvus search failed: {str(e)}")
            raise SearchError(f"Search failed: {str(e)}")

    def delete_index(self, index_id: str) -> None:
        """
        删除索引
        
        Args:
            index_id: 索引 ID
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            collection_name = collection.name
            
            # 释放 collection
            collection.release()
            
            # 删除 collection
            utility.drop_collection(collection_name)
            
            # 从缓存中移除
            if index_id in self._collections:
                del self._collections[index_id]
            
            logger.info(f"Deleted Milvus index: {collection_name} (ID: {index_id})")
            
        except Exception as e:
            logger.error(f"Failed to delete Milvus index: {str(e)}")
            raise IndexBuildError(f"Failed to delete index: {str(e)}")

    def get_index_stats(self, index_id: str) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Args:
            index_id: 索引 ID
            
        Returns:
            统计信息字典
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            
            # 刷新统计信息
            collection.flush()
            
            stats = {
                "vector_count": collection.num_entities,
                "index_type": "MILVUS",
                "metric_type": collection.index().params.get("metric_type", "L2"),
                "dimension": self._get_collection_dimension(collection),
                "memory_usage_bytes": 0,  # Milvus 不直接提供内存使用信息
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get Milvus index stats: {str(e)}")
            raise IndexBuildError(f"Failed to get stats: {str(e)}")

    def _get_collection(self, index_id: str) -> Collection:
        """
        获取 Collection 对象
        
        Args:
            index_id: 索引 ID
            
        Returns:
            Collection 对象
        """
        if index_id in self._collections:
            return self._collections[index_id]
        
        # 尝试从 Milvus 重新加载
        # 注意：实际应用中需要持久化 index_id 到 collection_name 的映射
        raise IndexNotFoundError(f"Index {index_id} not found in Milvus provider")

    def _get_collection_dimension(self, collection: Collection) -> int:
        """获取 collection 的向量维度"""
        for field in collection.schema.fields:
            if field.dtype == DataType.FLOAT_VECTOR:
                return field.params.get("dim", 0)
        return 0

    def _convert_metric_type(self, metric_type: str) -> str:
        """
        转换相似度度量类型到 Milvus 格式
        
        Args:
            metric_type: 标准度量类型 (cosine, euclidean, dot_product)
            
        Returns:
            Milvus 度量类型 (IP, L2)
        """
        metric_mapping = {
            "cosine": "IP",  # Inner Product (归一化后等价于余弦相似度)
            "euclidean": "L2",
            "dot_product": "IP"
        }
        return metric_mapping.get(metric_type.lower(), "L2")

    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            self._ensure_connected()
            # 尝试列出所有 collections
            utility.list_collections()
            return True
        except Exception as e:
            logger.error(f"Milvus health check failed: {str(e)}")
            return False
