"""
Milvus 向量索引提供者实现

实现 Milvus 向量数据库的索引管理和检索功能
"""
import uuid
import json
import os
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

    def __init__(self, config: Optional[MilvusConfig] = None, index_dir: str = "results/vector_index/milvus"):
        """
        初始化 Milvus 提供者
        
        Args:
            config: Milvus 配置对象，如果为 None 则使用默认配置
            index_dir: 索引元数据存储目录
        """
        self.config = config or MilvusConfig()
        self._connected = False
        self._collections: Dict[str, Collection] = {}
        self._current_index_id: Optional[str] = None
        self._index_dir = index_dir
        
        # 索引元数据映射 (index_id -> metadata)
        self._index_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 确保目录存在
        os.makedirs(self._index_dir, exist_ok=True)
        
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
            # 清理 collection 名称，确保符合 Milvus 要求（以字母或下划线开头，只包含字母数字下划线）
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '', config.index_name.replace(" ", "_"))
            if not safe_name or not safe_name[0].isalpha() and safe_name[0] != '_':
                safe_name = f"idx_{safe_name}" if safe_name else "idx"
            collection_name = f"{safe_name}_{index_id[:8]}"
            
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
            index_type = config.index_type or "IVF_FLAT"
            metric_type = self._convert_metric_type(config.metric_type)
            
            # 根据索引类型设置不同的参数
            index_params = {
                "metric_type": metric_type,
                "index_type": index_type,
                "params": self._get_index_params(index_type, config.dimension)
            }
            
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            self._collections[index_id] = collection
            self._current_index_id = index_id
            
            # 保存索引元数据到本地文件
            metadata = {
                "index_id": index_id,
                "collection_name": collection_name,
                "index_name": config.index_name,
                "dimension": config.dimension,
                "metric_type": config.metric_type,
                "index_type": index_type,
                "index_params": index_params,
                "milvus_host": self.config.host,
                "milvus_port": self.config.port,
                "created_at": datetime.now().isoformat(),
                "vector_count": 0
            }
            self._index_metadata[index_id] = metadata
            self._save_index_metadata(index_id, metadata)
            
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
            
            # 更新元数据
            if index_id in self._index_metadata:
                self._index_metadata[index_id]["vector_count"] = collection.num_entities
                self._index_metadata[index_id]["updated_at"] = datetime.now().isoformat()
                self._save_index_metadata(index_id, self._index_metadata[index_id])
            
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
            
            # 删除元数据文件
            self._delete_index_metadata(index_id)
            
            logger.info(f"Deleted Milvus index: {collection_name} (ID: {index_id})")
            
        except Exception as e:
            logger.error(f"Failed to delete Milvus index: {str(e)}")
            raise IndexBuildError(f"Failed to delete index: {str(e)}")

    def _get_index_stats_by_id(self, index_id: str) -> Dict[str, Any]:
        """
        获取索引统计信息（内部方法，带 index_id 参数）
        
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
                "index_size_bytes": 0,  # Milvus 不直接提供大小信息
                "metric_type": collection.index().params.get("metric_type", "L2"),
                "dimension": self._get_collection_dimension(collection),
                "memory_usage_bytes": 0,
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

    def _get_index_params(self, index_type: str, dimension: int) -> Dict[str, Any]:
        """
        根据索引类型获取对应的参数
        
        Args:
            index_type: 索引类型 (FLAT, IVF_FLAT, IVF_SQ8, IVF_PQ, HNSW)
            dimension: 向量维度
            
        Returns:
            索引参数字典
        """
        # 计算合适的 nlist（聚类中心数量）
        # 一般建议 nlist = 4 * sqrt(n)，但这里我们使用固定值
        nlist = min(1024, max(1, dimension // 2))
        
        # 计算 m 值（用于 IVF_PQ）
        # m 必须能整除 dimension，且 m 越大压缩率越低但精度越高
        # 常见值: 8, 16, 32, 64
        m = 8  # 默认值
        for candidate in [64, 32, 16, 8, 4]:
            if dimension % candidate == 0:
                m = candidate
                break
        
        index_params_map = {
            "FLAT": {},  # FLAT 不需要额外参数
            "IVF_FLAT": {"nlist": nlist},
            "IVF_SQ8": {"nlist": nlist},
            "IVF_PQ": {"nlist": nlist, "m": m, "nbits": 8},
            "HNSW": {"M": 16, "efConstruction": 200},
            "ANNOY": {"n_trees": 8},
            "DISKANN": {}
        }
        
        params = index_params_map.get(index_type.upper(), {"nlist": nlist})
        logger.info(f"Index params for {index_type}: {params}")
        return params

    def _save_index_metadata(self, index_id: str, metadata: Dict[str, Any]) -> str:
        """
        保存索引元数据到本地文件
        
        Args:
            index_id: 索引 ID
            metadata: 元数据字典
            
        Returns:
            保存的文件路径
        """
        file_path = os.path.join(self._index_dir, f"{index_id}.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved Milvus index metadata to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save index metadata: {str(e)}")
            raise IndexBuildError(f"Failed to save metadata: {str(e)}")

    def _load_index_metadata(self, index_id: str) -> Optional[Dict[str, Any]]:
        """
        从本地文件加载索引元数据
        
        Args:
            index_id: 索引 ID
            
        Returns:
            元数据字典，如果不存在返回 None
        """
        file_path = os.path.join(self._index_dir, f"{index_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load index metadata: {str(e)}")
            return None

    def _delete_index_metadata(self, index_id: str) -> None:
        """
        删除索引元数据文件
        
        Args:
            index_id: 索引 ID
        """
        file_path = os.path.join(self._index_dir, f"{index_id}.json")
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted Milvus index metadata: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete metadata file: {str(e)}")
        
        # 从内存缓存中移除
        if index_id in self._index_metadata:
            del self._index_metadata[index_id]

    def get_metadata_file_path(self, index_id: str) -> str:
        """
        获取索引元数据文件路径
        
        Args:
            index_id: 索引 ID
            
        Returns:
            文件路径
        """
        return os.path.join(self._index_dir, f"{index_id}.json")

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息字典
        """
        try:
            self._ensure_connected()
            # 尝试列出所有 collections
            utility.list_collections()
            return {
                "status": "healthy",
                "details": {
                    "connected": self._connected,
                    "host": self.config.host,
                    "port": self.config.port
                }
            }
        except Exception as e:
            logger.error(f"Milvus health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e)}
            }

    # ==================== BaseProvider 抽象方法实现 ====================

    def insert_vectors(
        self,
        vectors: np.ndarray,
        vector_ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        插入向量（BaseProvider 抽象方法实现）
        
        Args:
            vectors: 向量数组
            vector_ids: 向量 ID 列表
            metadata: 元数据列表
            
        Returns:
            True if successful
        """
        if not self._current_index_id:
            raise IndexNotFoundError("No active index. Call create_index first.")
        
        # 使用 add_vectors 方法
        self.add_vectors(
            self._current_index_id, 
            vectors, 
            metadata or [{} for _ in vector_ids]
        )
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
                "distance": 1 - r.score,  # 转换为距离
                "metadata": r.metadata
            }
            for r in results
        ]

    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """
        删除向量（BaseProvider 抽象方法实现）
        
        Args:
            vector_ids: 要删除的向量 ID 列表
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        if not self._current_index_id:
            raise IndexNotFoundError("No active index.")
        
        try:
            collection = self._get_collection(self._current_index_id)
            
            # 构建删除表达式
            ids_str = ", ".join([f'"{vid}"' for vid in vector_ids])
            expr = f"id in [{ids_str}]"
            
            collection.delete(expr)
            collection.flush()
            
            logger.info(f"Deleted {len(vector_ids)} vectors from index {self._current_index_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors from Milvus: {str(e)}")
            raise IndexBuildError(f"Failed to delete vectors: {str(e)}")

    def get_vector_count(self) -> int:
        """
        获取向量数量（BaseProvider 抽象方法实现）
        
        Returns:
            向量数量
        """
        if not self._current_index_id:
            return 0
        
        try:
            collection = self._get_collection(self._current_index_id)
            collection.flush()
            return collection.num_entities
        except Exception:
            return 0

    def persist_index(self) -> bool:
        """
        持久化索引（BaseProvider 抽象方法实现）
        
        Milvus 自动持久化，此方法确保数据刷新到磁盘
        
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        if not self._current_index_id:
            raise IndexNotFoundError("No active index.")
        
        try:
            collection = self._get_collection(self._current_index_id)
            collection.flush()
            logger.info(f"Persisted Milvus index {self._current_index_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist Milvus index: {str(e)}")
            raise IndexBuildError(f"Failed to persist index: {str(e)}")

    def load_index(self) -> bool:
        """
        加载索引（BaseProvider 抽象方法实现）
        
        将 Milvus collection 加载到内存
        
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        if not self._current_index_id:
            raise IndexNotFoundError("No active index.")
        
        try:
            collection = self._get_collection(self._current_index_id)
            collection.load()
            logger.info(f"Loaded Milvus index {self._current_index_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to load Milvus index: {str(e)}")
            raise IndexBuildError(f"Failed to load index: {str(e)}")

    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息（BaseProvider 抽象方法实现，无参数版本）
        
        Returns:
            统计信息字典
        """
        if not self._current_index_id:
            return {
                "vector_count": 0,
                "index_size_bytes": 0,
                "index_type": "MILVUS"
            }
        
        # 调用带参数版本
        return self._get_index_stats_by_id(self._current_index_id)
