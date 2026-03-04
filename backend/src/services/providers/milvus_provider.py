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
    utility,
    AnnSearchRequest,
    RRFRanker
)

from .base_provider import BaseProvider, IndexConfig, SearchResult
from ...vector_config import MilvusConfig, get_physical_collection_name, parse_physical_collection_name
from ...utils.logger import get_logger
from ...utils.vector_utils import validate_vector
from ...exceptions.vector_index_errors import (
    IndexNotFoundError,
    VectorDimensionError,
    IndexBuildError,
    SearchError
)

logger = get_logger("milvus_provider")


class MilvusProvider(BaseProvider):
    """Milvus 向量索引提供者
    
    参考 Dify 方案实现「逻辑与物理分层」：
    - 对外暴露「逻辑知识库」（如 default_collection），用户无感知底层拆分
    - 底层按「知识库 + 维度」拆分为多个物理 Collection（如 default_collection_dim1024）
    - 每个物理 Collection 只包含一个固定维度的 embedding 字段，从根源避免维度冲突
    - 通过元数据映射实现检索/写入时的自动路由
    
    优势：
    1. 彻底解决 Milvus 不支持同一 Collection 存储不同维度向量的问题
    2. 消除零向量填充浪费，节省存储空间
    3. 每个物理 Collection 可独立优化索引参数
    4. 天然支持嵌入模型版本迭代
    """

    # 稠密向量字段名（Dify 方案：每个物理 Collection 只有一个固定字段名）
    DENSE_FIELD_NAME = "embedding"

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

    # ==================== 物理 Collection 路由辅助方法（Dify 方案） ====================

    @staticmethod
    def _get_physical_name(logical_name: str, dimension: int) -> str:
        """生成物理 Collection 名称（逻辑名 + 维度后缀）"""
        return get_physical_collection_name(logical_name, dimension)

    @staticmethod
    def _get_collection_dimension(collection: Collection) -> int:
        """获取 Collection 的稠密向量字段维度"""
        for field in collection.schema.fields:
            if field.dtype == DataType.FLOAT_VECTOR:
                return field.params.get("dim", 0)
        return 0

    def _get_all_physical_collections(self, logical_name: str) -> List[str]:
        """获取一个逻辑知识库对应的所有物理 Collection 名称列表"""
        self._ensure_connected()
        all_collections = utility.list_collections()
        prefix = f"{logical_name}_dim"
        return [c for c in all_collections if c.startswith(prefix)]

    def _get_physical_collection_dimensions(self, logical_name: str) -> Dict[str, int]:
        """获取逻辑知识库下所有物理 Collection 的维度映射 {physical_name: dimension}"""
        result = {}
        for physical_name in self._get_all_physical_collections(logical_name):
            _, dim = parse_physical_collection_name(physical_name)
            if dim is not None:
                result[physical_name] = dim
        return result

    # ==================== 兼容旧代码的辅助方法 ====================

    @staticmethod
    def _dense_field_name(dimension: int) -> str:
        """向后兼容：根据维度生成稠密向量字段名
        
        Dify 方案下每个物理 Collection 只有一个 'embedding' 字段，
        此方法保留用于兼容旧元数据记录。
        """
        return "embedding"

    @staticmethod
    def _get_dense_field_names(collection: Collection) -> List[str]:
        """获取 Collection 中所有稠密向量字段名"""
        return [
            field.name for field in collection.schema.fields
            if field.dtype == DataType.FLOAT_VECTOR
        ]

    @staticmethod
    def _get_dense_field_dimensions(collection: Collection) -> Dict[str, int]:
        """获取 Collection 中所有稠密向量字段的维度映射 {field_name: dim}"""
        result = {}
        for field in collection.schema.fields:
            if field.dtype == DataType.FLOAT_VECTOR:
                result[field.name] = field.params.get("dim", 0)
        return result

    def _has_dense_field_for_dimension(self, collection: Collection, dimension: int) -> bool:
        """检查 Collection 的 embedding 字段维度是否匹配"""
        for field in collection.schema.fields:
            if field.dtype == DataType.FLOAT_VECTOR and field.params.get("dim") == dimension:
                return True
        return False

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
        metric_type: str,
        enable_sparse: bool = False
    ) -> CollectionSchema:
        """
        创建 Milvus Collection Schema（Dify 方案：固定 embedding 字段）
        
        每个物理 Collection 只包含一个固定名称的 'embedding' 字段，
        维度由物理 Collection 决定，不同维度拆分到不同的物理 Collection。
        
        Args:
            index_name: 索引名称（用于 Schema 描述）
            dimension: 向量维度
            metric_type: 相似度度量类型
            enable_sparse: 是否启用稀疏向量字段（用于混合检索）
            
        Returns:
            CollectionSchema 对象
        """
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(
                name="doc_id",
                dtype=DataType.VARCHAR,
                max_length=256,
                is_partition_key=True,
                description="文档ID（Partition Key，Milvus 自动按此字段哈希分区）"
            ),
            FieldSchema(
                name=self.DENSE_FIELD_NAME,
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description=f"稠密向量（维度={dimension}）"
            ),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        # 新增：稀疏向量字段（用于混合检索）
        if enable_sparse:
            fields.insert(3, FieldSchema(
                name="sparse_embedding",
                dtype=DataType.SPARSE_FLOAT_VECTOR,
                description="稀疏向量（BM25 sparse output）"
            ))
        
        schema = CollectionSchema(
            fields=fields,
            description=f"Vector index: {index_name} (dim={dimension})",
            enable_dynamic_field=True  # 启用动态字段，支持灵活的元数据存储
        )
        
        return schema

    def ensure_collection_exists(
        self, 
        collection_name: str, 
        dimension: int, 
        metric_type: str = "cosine",
        index_type: str = "FLAT",
        enable_sparse: bool = True,
        description: str = ""
    ) -> str:
        """
        确保物理 Collection 存在（Dify 方案：按维度拆分）
        
        参考 Dify 的「逻辑与物理分层」策略：
        - collection_name 为逻辑知识库名（如 default_collection）
        - 实际创建的物理 Collection 名为 {逻辑名}_dim{维度}（如 default_collection_dim1024）
        - 不同维度的嵌入模型会自动创建各自的物理 Collection，互不冲突
        - 切换模型时旧 Collection 保留，支持历史数据检索
        
        Args:
            collection_name: 逻辑知识库名称（对外暴露的名称）
            dimension: 向量维度
            metric_type: 相似度度量类型
            index_type: 索引算法类型
            enable_sparse: 是否启用稀疏向量字段
            description: Collection 描述
            
        Returns:
            physical_collection_name（物理 Collection 名称，作为索引 ID）
        """
        self._ensure_connected()
        
        # 生成物理 Collection 名称
        physical_name = self._get_physical_name(collection_name, dimension)
        
        try:
            if utility.has_collection(physical_name):
                # 物理 Collection 已存在，直接复用
                collection = Collection(physical_name)
                self._collections[physical_name] = collection
                self._current_index_id = physical_name
                
                existing_dim = self._get_collection_dimension(collection)
                all_physical = self._get_all_physical_collections(collection_name)
                logger.info(
                    f"Physical Collection '{physical_name}' exists (dim={existing_dim}), "
                    f"reusing it. All physical collections for '{collection_name}': {all_physical}"
                )
                return physical_name
            
            # 物理 Collection 不存在，创建新的
            schema = self._create_collection_schema(
                physical_name,
                dimension,
                metric_type,
                enable_sparse=enable_sparse
            )
            
            collection = Collection(
                name=physical_name,
                schema=schema,
                num_partitions=64  # Partition Key 模式下的分区数量
            )
            
            # 创建稠密向量索引（固定字段名 embedding）
            milvus_metric_type = self._convert_metric_type(metric_type)
            index_params = {
                "metric_type": milvus_metric_type,
                "index_type": index_type,
                "params": self._get_index_params(index_type, dimension)
            }
            collection.create_index(
                field_name=self.DENSE_FIELD_NAME,
                index_params=index_params
            )
            
            # 创建稀疏向量索引（如果启用）
            if enable_sparse:
                sparse_index_params = {
                    "metric_type": "IP",
                    "index_type": "SPARSE_INVERTED_INDEX",
                    "params": {"drop_ratio_build": 0.2}
                }
                collection.create_index(
                    field_name="sparse_embedding",
                    index_params=sparse_index_params
                )
                logger.info(f"Created sparse index (SPARSE_INVERTED_INDEX) for {physical_name}")
            
            self._collections[physical_name] = collection
            self._current_index_id = physical_name
            
            # 保存元数据
            metadata = {
                "index_id": physical_name,
                "logical_collection_name": collection_name,
                "physical_collection_name": physical_name,
                "collection_name": collection_name,
                "index_name": physical_name,
                "dimension": dimension,
                "dense_field": self.DENSE_FIELD_NAME,
                "metric_type": metric_type,
                "index_type": index_type,
                "enable_sparse": enable_sparse,
                "milvus_host": self.config.host,
                "milvus_port": self.config.port,
                "created_at": datetime.now().isoformat(),
                "vector_count": 0
            }
            self._index_metadata[physical_name] = metadata
            self._save_index_metadata(physical_name, metadata)
            
            all_physical = self._get_all_physical_collections(collection_name)
            logger.info(
                f"Created new physical Collection: {physical_name} "
                f"(logical='{collection_name}', dim={dimension}, sparse={enable_sparse}). "
                f"All physical collections for '{collection_name}': {all_physical}"
            )
            return physical_name
            
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {str(e)}")
            raise IndexBuildError(f"Failed to ensure collection: {str(e)}")

    def get_collection_names(self) -> list:
        """
        获取 Milvus 中所有 Collection 名称列表
        
        Returns:
            Collection 名称列表
        """
        self._ensure_connected()
        try:
            return utility.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            return []

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
            enable_sparse = getattr(config, 'enable_sparse', False)
            schema = self._create_collection_schema(
                config.index_name,
                config.dimension,
                config.metric_type,
                enable_sparse=enable_sparse
            )
            
            # 创建 collection
            collection = Collection(
                name=collection_name,
                schema=schema,
                num_partitions=64  # Partition Key 模式下的分区数量
            )
            
            # 创建稠密向量索引
            index_type = config.index_type or "IVF_FLAT"
            metric_type = self._convert_metric_type(config.metric_type)
            
            # 根据索引类型设置不同的参数
            index_params = {
                "metric_type": metric_type,
                "index_type": index_type,
                "params": self._get_index_params(index_type, config.dimension)
            }
            
            collection.create_index(
                field_name=self.DENSE_FIELD_NAME,
                index_params=index_params
            )
            
            # 创建稀疏向量索引（如果启用）
            if enable_sparse:
                sparse_index_params = {
                    "metric_type": "IP",
                    "index_type": "SPARSE_INVERTED_INDEX",
                    "params": {"drop_ratio_build": 0.2}
                }
                collection.create_index(
                    field_name="sparse_embedding",
                    index_params=sparse_index_params
                )
                logger.info(f"Created sparse index (SPARSE_INVERTED_INDEX) for {collection_name}")
            
            self._collections[index_id] = collection
            self._current_index_id = index_id
            
            # 保存索引元数据到本地文件
            metadata = {
                "index_id": index_id,
                "collection_name": collection_name,
                "index_name": config.index_name,
                "dimension": config.dimension,
                "dense_field": self.DENSE_FIELD_NAME,
                "metric_type": config.metric_type,
                "index_type": index_type,
                "index_params": index_params,
                "enable_sparse": enable_sparse,
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
        metadata: List[Dict[str, Any]],
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        向索引中添加向量（Dify 方案：直接写入对应维度的物理 Collection）
        
        每个物理 Collection 只有一个固定的 embedding 字段，
        无需为其他维度填充零向量，节省存储空间。
        
        Args:
            index_id: 索引 ID（即物理 Collection 名称）
            vectors: 向量数组 (n_vectors, dimension)
            metadata: 元数据列表
            doc_ids: 文档 ID 列表（用于 Partition Key 路由）
            
        Returns:
            向量 ID 列表
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            
            # 生成向量 ID
            vector_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            
            # 准备 doc_id 列表（从 metadata 中提取或使用传入的）
            if doc_ids is None:
                doc_ids = [m.get("document_id", "unknown") for m in metadata]
            
            # 确定当前向量的维度
            vec_dim = vectors.shape[1] if len(vectors) > 0 else 0
            
            # 验证向量
            processed_vectors = []
            for i, vec in enumerate(vectors):
                validate_vector(vec, vec_dim)
                processed_vectors.append(vec.tolist() if isinstance(vec, np.ndarray) else list(vec))
            
            # Dify 方案：每个物理 Collection 只有一个 embedding 字段，直接插入即可
            entities = []
            for i in range(len(vectors)):
                row = {
                    "id": vector_ids[i],
                    "doc_id": doc_ids[i],
                    self.DENSE_FIELD_NAME: processed_vectors[i],
                    "metadata": metadata[i]
                }
                entities.append(row)
            
            # 插入数据
            insert_result = collection.insert(entities)
            collection.flush()
            
            # 更新元数据
            if index_id in self._index_metadata:
                self._index_metadata[index_id]["vector_count"] = collection.num_entities
                self._index_metadata[index_id]["updated_at"] = datetime.now().isoformat()
                self._save_index_metadata(index_id, self._index_metadata[index_id])
            
            logger.info(f"Added {len(vectors)} vectors to index {index_id} (field={self.DENSE_FIELD_NAME}, dim={vec_dim})")
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
        
        根据查询向量的维度自动选择对应的 dense_dim{N} 字段进行搜索。
        
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
            
            # Dify 方案：每个物理 Collection 只有一个 embedding 字段
            query_dim = len(query_vector)
            target_field = self.DENSE_FIELD_NAME
            
            # 校验查询向量维度与物理 Collection 的维度是否匹配
            collection_dim = self._get_collection_dimension(collection)
            if collection_dim > 0 and query_dim != collection_dim:
                raise VectorDimensionError(
                    f"Query vector dimension ({query_dim}) does not match "
                    f"collection '{collection.name}' dimension ({collection_dim}). "
                    f"Please use the correct physical collection for this dimension."
                )
            
            # 验证查询向量
            validate_vector(query_vector, query_dim)
            query_vec = query_vector.tolist() if isinstance(query_vector, np.ndarray) else list(query_vector)
            
            # 获取该字段的索引度量类型
            metric_type = "L2"
            try:
                # 尝试从指定字段的索引信息获取 metric_type
                idx_info = collection.index(index_name=self.DENSE_FIELD_NAME)
                if idx_info:
                    metric_type = idx_info.params.get("metric_type", "L2")
            except Exception:
                # 降级：尝试从任意索引获取
                try:
                    idx_info = collection.index()
                    if idx_info:
                        metric_type = idx_info.params.get("metric_type", "L2")
                except Exception:
                    pass
            
            search_params = {
                "metric_type": metric_type,
                "params": {"nprobe": 10}
            }
            
            # 执行搜索（Dify 方案：固定 embedding 字段名）
            results = collection.search(
                data=[query_vec],
                anns_field=target_field,
                param=search_params,
                limit=top_k,
                output_fields=["doc_id", "metadata"]
            )
            
            # 转换结果
            search_results = []
            for hits in results:
                for hit in hits:
                    # pymilvus Hit.entity.get() 只接受字段名，不接受默认值
                    try:
                        metadata = hit.entity.get("metadata")
                        if metadata is None:
                            metadata = {}
                    except Exception:
                        metadata = {}
                    
                    # 将 Milvus 返回的分数转换为相似度分数 (0-1，越大越相似)
                    raw_score = float(hit.score)
                    if metric_type == "COSINE":
                        # COSINE: Milvus 2.5+ 原生返回余弦相似度，值在 [-1, 1] 之间
                        # 转换为 [0, 1] 范围的相似度
                        similarity_score = (raw_score + 1) / 2
                    elif metric_type == "IP":
                        # Inner Product: 值范围取决于向量，归一化向量在 [-1, 1] 之间
                        similarity_score = (raw_score + 1) / 2
                    elif metric_type == "L2":
                        # L2 距离: 值越小越相似，转换为相似度
                        # 使用公式: similarity = 1 / (1 + distance)
                        similarity_score = 1 / (1 + raw_score)
                    else:
                        # 其他度量类型，假设已经是相似度
                        similarity_score = raw_score
                    
                    search_results.append(SearchResult(
                        vector_id=hit.id,
                        score=similarity_score,
                        metadata=metadata
                    ))
            
            logger.info(f"Search completed: found {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Milvus search failed: {str(e)}")
            raise SearchError(index_id, str(e))

    def delete_by_doc_id(self, index_id: str, doc_id: str) -> int:
        """
        按 doc_id 删除 Collection 中属于指定文档的所有向量
        
        这是「逻辑与物理分层」架构下的正确删除方式：
        多个文档共享同一个物理 Collection，删除某个文档的索引记录时
        只应删除该文档的向量，而非 drop 整个 Collection。
        
        Args:
            index_id: 物理 Collection 名称（即 provider_index_id）
            doc_id: 文档 ID（Partition Key 字段值）
            
        Returns:
            删除的向量数量（近似值）
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            collection.load()
            
            # 先查询该 doc_id 下有多少条向量（用于日志记录）
            try:
                count_results = collection.query(
                    expr=f'doc_id == "{doc_id}"',
                    output_fields=["count(*)"],
                )
                deleted_count = count_results[0].get("count(*)", 0) if count_results else 0
            except Exception:
                deleted_count = -1  # 查询计数失败，不影响删除
            
            # 按 doc_id 删除该文档的所有向量
            expr = f'doc_id == "{doc_id}"'
            collection.delete(expr)
            collection.flush()
            
            logger.info(
                f"Deleted vectors by doc_id from Collection '{collection.name}': "
                f"doc_id='{doc_id}', deleted_count≈{deleted_count}"
            )
            return deleted_count if deleted_count >= 0 else 0
            
        except Exception as e:
            logger.error(f"Failed to delete vectors by doc_id: {str(e)}")
            raise IndexBuildError(f"Failed to delete vectors by doc_id: {str(e)}")

    def get_collection_entity_count(self, index_id: str) -> int:
        """
        获取物理 Collection 中的实体总数
        
        Args:
            index_id: 物理 Collection 名称
            
        Returns:
            实体总数
        """
        self._ensure_connected()
        try:
            collection = self._get_collection(index_id)
            collection.flush()
            return collection.num_entities
        except Exception as e:
            logger.warning(f"Failed to get entity count for {index_id}: {e}")
            return -1

    def drop_collection_if_empty(self, index_id: str) -> bool:
        """
        如果物理 Collection 为空，则 drop 它
        
        在删除文档向量后调用此方法进行清理：
        - 如果 Collection 中还有其他文档的向量 → 保留 Collection
        - 如果 Collection 已经完全为空 → drop Collection 释放资源
        
        Args:
            index_id: 物理 Collection 名称
            
        Returns:
            True 如果 Collection 被 drop 了，False 如果保留
        """
        self._ensure_connected()
        
        try:
            entity_count = self.get_collection_entity_count(index_id)
            
            if entity_count == 0:
                collection = self._get_collection(index_id)
                collection_name = collection.name
                collection.release()
                utility.drop_collection(collection_name)
                
                # 从缓存中移除
                if index_id in self._collections:
                    del self._collections[index_id]
                
                # 删除元数据文件
                self._delete_index_metadata(index_id)
                
                logger.info(f"Collection '{collection_name}' is empty after deletion, dropped it.")
                return True
            else:
                logger.info(
                    f"Collection '{index_id}' still has {entity_count} entities, keeping it."
                )
                return False
                
        except Exception as e:
            logger.warning(f"Failed to check/drop empty collection {index_id}: {e}")
            return False

    def delete_index(self, index_id: str) -> None:
        """
        删除索引（强制 drop 整个物理 Collection）
        
        ⚠️ 警告：此方法会删除整个物理 Collection，包括其中所有文档的向量。
        一般情况下应使用 delete_by_doc_id() + drop_collection_if_empty() 组合。
        此方法仅在明确需要清除整个 Collection 时使用（如 clear_all）。
        
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
            
            logger.info(f"Force dropped Milvus Collection: {collection_name} (ID: {index_id})")
            
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
            index_id: 索引 ID (UUID 格式)
            
        Returns:
            Collection 对象
        """
        if index_id in self._collections:
            return self._collections[index_id]
        
        # 尝试从 Milvus 重新加载
        self._ensure_connected()
        
        # 尝试直接使用 index_id 作为 collection 名称加载
        try:
            if utility.has_collection(index_id):
                collection = Collection(index_id)
                self._collections[index_id] = collection
                logger.info(f"Loaded existing collection: {index_id}")
                return collection
        except Exception as e:
            logger.warning(f"Failed to load collection by index_id: {str(e)}")
        
        # 提取 UUID 前缀用于匹配（UUID 前 8 位）
        uuid_prefix = index_id.split('-')[0] if '-' in index_id else index_id[:8]
        
        # 尝试查找匹配的 collection（遍历所有 collection）
        try:
            collections = utility.list_collections()
            for coll_name in collections:
                # 检查 collection 名称是否以 UUID 前缀结尾
                if coll_name.endswith(f"_{uuid_prefix}"):
                    collection = Collection(coll_name)
                    self._collections[index_id] = collection
                    logger.info(f"Found and loaded collection: {coll_name} for index_id: {index_id}")
                    return collection
        except Exception as e:
            logger.warning(f"Failed to search collections: {str(e)}")
        
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
            Milvus 度量类型 (COSINE, L2, IP)
        """
        metric_mapping = {
            "cosine": "COSINE",  # Milvus 2.5+ 原生支持 COSINE，无需手动归一化
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
        
        meta_list = metadata or [{} for _ in vector_ids]
        # 从 metadata 中提取 doc_ids
        doc_ids = [m.get("document_id", "unknown") for m in meta_list]
        
        # 使用 add_vectors 方法
        self.add_vectors(
            self._current_index_id, 
            vectors, 
            meta_list,
            doc_ids=doc_ids
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

    # ==================== 混合检索扩展方法 ====================

    def _collection_has_sparse_field(self, collection: Collection) -> bool:
        """
        检测 Collection 是否包含稀疏向量字段
        
        Args:
            collection: Milvus Collection 对象
            
        Returns:
            True 如果包含 SPARSE_FLOAT_VECTOR 字段
        """
        try:
            for field in collection.schema.fields:
                if field.dtype == DataType.SPARSE_FLOAT_VECTOR:
                    return True
            return False
        except Exception as e:
            logger.warning(f"检测稀疏字段失败: {e}")
            return False

    def add_vectors_with_sparse(
        self,
        index_id: str,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]],
        sparse_vectors: Optional[List[Dict]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        向索引中添加向量（支持稠密+稀疏双路向量，Dify 方案）
        
        每个物理 Collection 只有一个固定的 embedding 字段，
        无需为其他维度填充零向量。
        
        Args:
            index_id: 索引 ID（即物理 Collection 名称）
            vectors: 稠密向量数组 (n_vectors, dimension)
            metadata: 元数据列表
            sparse_vectors: 稀疏向量列表（可选，每个元素为 {int_index: weight} 字典）
            doc_ids: 文档 ID 列表（用于 Partition Key 路由）
            
        Returns:
            向量 ID 列表
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            has_sparse = self._collection_has_sparse_field(collection)
            
            # 生成向量 ID
            vector_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            
            # 准备 doc_id 列表（从 metadata 中提取或使用传入的）
            if doc_ids is None:
                doc_ids = [m.get("document_id", "unknown") for m in metadata]
            
            # 确定当前向量的维度
            vec_dim = vectors.shape[1] if len(vectors) > 0 else 0
            
            # 验证向量
            processed_vectors = []
            for i, vec in enumerate(vectors):
                validate_vector(vec, vec_dim)
                processed_vectors.append(vec.tolist() if isinstance(vec, np.ndarray) else list(vec))
            
            # 预处理稀疏向量
            milvus_sparse = None
            if has_sparse and sparse_vectors:
                from ...utils.sparse_utils import convert_sparse_to_milvus_format
                
                milvus_sparse = []
                for sv in sparse_vectors:
                    if sv and isinstance(sv, dict) and len(sv) > 0:
                        milvus_sparse.append(convert_sparse_to_milvus_format(sv))
                    else:
                        milvus_sparse.append({0: 0.0})  # 占位符
            
            # Dify 方案：每个物理 Collection 只有一个 embedding 字段，直接插入
            entities = []
            for i in range(len(vectors)):
                row = {
                    "id": vector_ids[i],
                    "doc_id": doc_ids[i],
                    self.DENSE_FIELD_NAME: processed_vectors[i],
                    "metadata": metadata[i]
                }
                # 添加稀疏向量
                if milvus_sparse:
                    row["sparse_embedding"] = milvus_sparse[i]
                entities.append(row)
            
            # 插入数据
            insert_result = collection.insert(entities)
            collection.flush()
            
            # 更新元数据
            if index_id in self._index_metadata:
                self._index_metadata[index_id]["vector_count"] = collection.num_entities
                self._index_metadata[index_id]["updated_at"] = datetime.now().isoformat()
                self._save_index_metadata(index_id, self._index_metadata[index_id])
            
            logger.info(
                f"Added {len(vectors)} vectors to index {index_id} "
                f"(field={self.DENSE_FIELD_NAME}, dim={vec_dim}, sparse={'yes' if has_sparse and sparse_vectors else 'no'})"
            )
            return vector_ids
            
        except Exception as e:
            logger.error(f"Failed to add vectors with sparse to Milvus: {str(e)}")
            raise IndexBuildError(f"Failed to add vectors: {str(e)}")

    def hybrid_search(
        self,
        index_id: str,
        dense_vector: np.ndarray,
        sparse_vector: Optional[Dict] = None,
        top_n: int = 20,
        rrf_k: int = 60,
        output_fields: Optional[List[str]] = None,
        filter_expr: Optional[str] = None,
        **search_params
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        混合检索：稠密+稀疏双路召回 + RRF 粗排融合
        
        当稀疏向量为空或 Collection 不含稀疏字段时，自动降级到纯稠密检索。
        
        Args:
            index_id: 索引 ID
            dense_vector: 稠密查询向量
            sparse_vector: 稀疏查询向量 ({int_index: weight})
            top_n: 粗排候选集大小
            rrf_k: RRF 排名平滑因子
            output_fields: 返回字段列表
            filter_expr: 过滤表达式（如 'doc_id == "xxx"'），用于 Partition Key 级别的文档隔离
            
        Returns:
            (results: List[Dict], search_mode: str)
            - results: 候选集列表，每条包含 vector_id, score/rrf_score, metadata
            - search_mode: "hybrid" 或 "dense_only"
        """
        self._ensure_connected()
        
        try:
            collection = self._get_collection(index_id)
            collection.load()
            
            has_sparse = self._collection_has_sparse_field(collection)
            
            # 判断是否可以使用混合检索
            from ...utils.sparse_utils import is_sparse_vector_valid
            use_hybrid = (
                has_sparse
                and sparse_vector is not None
                and is_sparse_vector_valid(sparse_vector)
            )
            
            if output_fields is None:
                output_fields = ["doc_id", "metadata"]
            
            if use_hybrid:
                # === 混合检索模式 ===
                logger.info(f"执行混合检索 (hybrid): index={index_id}, top_n={top_n}, rrf_k={rrf_k}")
                
                # Dify 方案：每个物理 Collection 只有一个固定的 embedding 字段
                dense_dim = len(dense_vector)
                target_dense_field = self.DENSE_FIELD_NAME
                
                # 校验查询向量维度与物理 Collection 的维度是否匹配
                collection_dim = self._get_collection_dimension(collection)
                if collection_dim > 0 and dense_dim != collection_dim:
                    raise SearchError(
                        index_id,
                        f"Query vector dimension ({dense_dim}) does not match "
                        f"collection '{collection.name}' dimension ({collection_dim})."
                    )
                
                # 准备稠密向量（Milvus 2.5+ 原生支持 COSINE，无需手动归一化）
                validate_vector(dense_vector, dense_dim)
                dense_vec = dense_vector.tolist() if isinstance(dense_vector, np.ndarray) else list(dense_vector)
                
                # 获取稠密索引的度量类型和搜索参数
                metric_type = "L2"
                dense_search_params = {"nprobe": 16}
                try:
                    idx_info = collection.index(index_name=self.DENSE_FIELD_NAME)
                    if idx_info:
                        metric_type = idx_info.params.get("metric_type", "L2")
                except Exception:
                    try:
                        idx_info = collection.index()
                        if idx_info:
                            metric_type = idx_info.params.get("metric_type", "L2")
                    except Exception:
                        pass
                
                # HNSW 使用 ef 参数
                if search_params.get("ef"):
                    dense_search_params = {"ef": search_params["ef"]}
                
                # 构建过滤表达式（用于 Partition Key 文档隔离）
                # 参考 Dify 架构：多文档共享同一物理 Collection 时，
                # 通过 expr 过滤实现文档级别的检索隔离
                expr = filter_expr if filter_expr else None
                if expr:
                    logger.info(f"混合检索应用文档过滤: {expr}")
                
                # 稠密向量检索请求（Dify 方案：固定 embedding 字段名）
                dense_req = AnnSearchRequest(
                    data=[dense_vec],
                    anns_field=target_dense_field,
                    param={"metric_type": metric_type, "params": dense_search_params},
                    limit=top_n,
                    expr=expr
                )
                
                # 准备稀疏向量
                from ...utils.sparse_utils import convert_sparse_to_milvus_format
                milvus_sparse = convert_sparse_to_milvus_format(sparse_vector)
                
                # 稀疏向量检索请求
                sparse_req = AnnSearchRequest(
                    data=[milvus_sparse],
                    anns_field="sparse_embedding",
                    param={"metric_type": "IP", "params": {}},
                    limit=top_n,
                    expr=expr
                )
                
                # RRF 融合
                reranker = RRFRanker(k=rrf_k)
                
                results = collection.hybrid_search(
                    reqs=[dense_req, sparse_req],
                    rerank=reranker,
                    limit=top_n,
                    output_fields=output_fields
                )
                
                # 转换结果
                search_results = []
                for hits in results:
                    for hit in hits:
                        try:
                            metadata = hit.entity.get("metadata")
                            if metadata is None:
                                metadata = {}
                        except Exception:
                            metadata = {}
                        
                        search_results.append({
                            "vector_id": hit.id,
                            "rrf_score": float(hit.score),
                            "score": float(hit.score),
                            "metadata": metadata,
                            "search_mode": "hybrid"
                        })
                
                logger.info(f"混合检索完成: {len(search_results)} 条结果")
                return search_results, "hybrid"
                
            else:
                # === 降级模式：纯稠密检索 ===
                reason = "Collection 无稀疏字段" if not has_sparse else "稀疏向量为空或无效"
                logger.info(f"降级到纯稠密检索 (dense_only): {reason}")
                
                # 执行纯稠密检索
                dense_results = self.search(index_id, dense_vector, top_n)
                
                search_results = []
                for r in dense_results:
                    search_results.append({
                        "vector_id": r.vector_id,
                        "rrf_score": r.score,
                        "score": r.score,
                        "metadata": r.metadata,
                        "search_mode": "dense_only"
                    })
                
                return search_results, "dense_only"
                
        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            raise SearchError(index_id, str(e))
