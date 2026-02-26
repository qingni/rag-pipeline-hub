"""
向量索引服务层

提供统一的向量索引管理接口，协调数据库和向量存储提供者

2024-12-24 更新: 添加从向量化任务创建索引的功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import numpy as np
from sqlalchemy.orm import Session

from .providers.base_provider import BaseProvider, IndexConfig, SearchResult
from .providers import (
    MilvusProvider,
    MILVUS_AVAILABLE,
)
from .index_registry import IndexRegistry
from ..models.vector_index import VectorIndex, IndexStatus, IndexProvider, VALID_DIMENSIONS
from ..models.index_statistics import IndexStatistics
from ..models.query_history import QueryHistory
from ..models.embedding_models import EmbeddingResult
from ..utils.logger import get_logger
from ..utils.result_persistence import ResultPersistence
from ..utils.index_logging import IndexOperationLogger, OperationType, OperationStatus
from ..exceptions.vector_index_errors import (
    IndexNotFoundError,
    ProviderNotFoundError,
    IndexBuildError,
    SearchError,
    VectorDimensionError
)
from .bm25_service import BM25SparseService

logger = get_logger("vector_index_service")


class VectorIndexService:
    """向量索引服务"""

    def __init__(
        self,
        db_session: Session,
        result_dir: str = "results/vector_index"
    ):
        """
        初始化向量索引服务
        
        Args:
            db_session: 数据库会话
            result_dir: 结果持久化目录
        """
        self.db = db_session
        self.result_dir = result_dir
        self.registry = IndexRegistry()
        self.result_persistence = ResultPersistence(result_dir)
        self.operation_logger = IndexOperationLogger(db_session)
        
        # 初始化 BM25 稀疏向量服务
        bm25_stats_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results", "bm25_stats")
        self.bm25_service = BM25SparseService(stats_dir=bm25_stats_dir)
        
        # 注册提供者
        self._register_providers()
        
        logger.info("VectorIndexService initialized (BM25 sparse enabled)")

    def _register_providers(self) -> None:
        """注册向量存储提供者"""
        try:
            # 注册 Milvus（如果可用）
            if MILVUS_AVAILABLE and MilvusProvider is not None:
                try:
                    milvus_provider = MilvusProvider()
                    self.registry.register_provider("milvus", milvus_provider)
                    logger.info("Registered Milvus provider")
                except Exception as e:
                    logger.warning(f"Failed to register Milvus provider: {str(e)}")
            else:
                logger.warning("Milvus provider not available (pymilvus not installed)")
                
        except Exception as e:
            logger.error(f"Failed to register providers: {str(e)}")
            raise

    # ==================== 向量化任务集成 API ====================

    def find_matching_index(
        self,
        embedding_result_id: str,
        provider: IndexProvider,
        algorithm_type: str,
        metric_type: str
    ) -> Optional[VectorIndex]:
        """
        查找匹配条件的已存在索引
        
        Args:
            embedding_result_id: 向量化任务结果ID
            provider: 向量数据库提供商
            algorithm_type: 索引算法类型
            metric_type: 相似度度量方法
            
        Returns:
            匹配的 VectorIndex 对象，如果不存在返回 None
        """
        try:
            matching_index = self.db.query(VectorIndex).filter(
                VectorIndex.embedding_result_id == embedding_result_id,
                VectorIndex.index_type == provider,
                VectorIndex.algorithm_type == algorithm_type,
                VectorIndex.metric_type == metric_type
            ).first()
            
            return matching_index
            
        except Exception as e:
            logger.error(f"Failed to find matching index: {str(e)}")
            return None

    def get_embedding_tasks(
        self,
        status: str = "SUCCESS",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取可用的向量化任务列表
        
        Args:
            status: 过滤任务状态 (SUCCESS, PARTIAL_SUCCESS)
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            向量化任务列表和总数
        """
        try:
            query = self.db.query(EmbeddingResult)
            
            if status:
                query = query.filter(EmbeddingResult.status == status)
            
            total = query.count()
            
            tasks = query.order_by(EmbeddingResult.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            # 获取文档名称
            task_list = []
            for task in tasks:
                task_dict = task.to_dict()
                # 尝试获取文档名称
                task_dict["document_name"] = self._get_document_name(task.document_id)
                task_list.append(task_dict)
            
            return {
                "tasks": task_list,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding tasks: {str(e)}")
            raise

    def create_index_from_embedding(
        self,
        embedding_result_id: str,
        name: Optional[str] = None,
        collection_name: Optional[str] = None,
        provider: IndexProvider = IndexProvider.MILVUS,  # 默认使用 Milvus
        index_type: str = "FLAT",  # 默认使用 FLAT
        metric_type: str = "cosine",
        index_params: Optional[Dict[str, Any]] = None,
        namespace: str = "default",
        enable_sparse: bool = True  # 默认启用 BM25 稀疏向量
    ) -> VectorIndex:
        """
        从向量化任务创建索引（向量追加到指定 Collection）
        
        设计说明：
        - 一个知识库对应一个 Milvus Collection
        - 多个文档的向量可以追加到同一个 Collection 中
        - 如果不指定 collection_name，则使用默认 Collection (default_collection)
        - 每次调用会创建一条 VectorIndex 记录，记录本次导入的详情
        
        Args:
            embedding_result_id: 向量化任务结果ID
            name: 索引记录名称（可选，自动生成）
            collection_name: 目标 Collection 名称（可选，不指定则使用默认 Collection）
            provider: 向量数据库提供商
            index_type: 索引算法类型
            metric_type: 相似度度量方法
            index_params: 索引算法参数
            namespace: 命名空间
            enable_sparse: 是否启用 BM25 稀疏向量
            
        Returns:
            VectorIndex 对象
        """
        from ..vector_config import DEFAULT_COLLECTION_NAME, get_physical_collection_name
        
        try:
            # 1. 获取向量化任务
            embedding_result = self.db.query(EmbeddingResult).filter(
                EmbeddingResult.result_id == embedding_result_id
            ).first()
            
            if not embedding_result:
                raise IndexNotFoundError(f"Embedding result {embedding_result_id} not found")
            
            if embedding_result.status not in ["SUCCESS", "PARTIAL_SUCCESS"]:
                raise IndexBuildError(
                    f"Embedding result status is {embedding_result.status}, expected SUCCESS or PARTIAL_SUCCESS"
                )
            
            # 2. 确定目标 Collection 名称
            target_collection = collection_name or DEFAULT_COLLECTION_NAME
            
            # 3. 生成索引记录名称（用于标识本次导入）
            if not name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_name = self._get_document_name(embedding_result.document_id) or "unknown"
                # 清理文档名称，移除非ASCII字符
                doc_name = doc_name.replace(".", "_").replace(" ", "_")[:20]
                name = f"idx_{doc_name}_{timestamp}"
            
            # 4. 检查索引记录名称是否已存在
            existing = self.db.query(VectorIndex).filter(
                VectorIndex.index_name == name
            ).first()
            
            if existing:
                raise IndexBuildError(f"Index with name '{name}' already exists")
            
            # 5. 验证维度
            dimension = embedding_result.vector_dimension
            if dimension not in VALID_DIMENSIONS:
                raise VectorDimensionError(
                    f"Dimension {dimension} not in valid dimensions: {VALID_DIMENSIONS}"
                )
            
            # 6. 创建数据库记录（记录本次导入操作）
            vector_index = VectorIndex(
                index_name=name,
                collection_name=target_collection,
                index_type=provider,
                algorithm_type=index_type,
                dimension=dimension,
                metric_type=metric_type,
                embedding_result_id=embedding_result_id,
                source_document_name=self._get_document_name(embedding_result.document_id),
                source_model=embedding_result.model,
                namespace=namespace,
                index_params=index_params or {},
                status=IndexStatus.BUILDING,
                vector_count=0
            )
            
            self.db.add(vector_index)
            self.db.commit()
            self.db.refresh(vector_index)
            
            # 7. 记录操作日志
            with self.operation_logger.track_operation(
                operation_type=OperationType.CREATE,
                index_id=vector_index.id,
                details={
                    "embedding_result_id": embedding_result_id,
                    "collection_name": target_collection,
                    "provider": provider.value,
                    "index_type": index_type
                }
            ):
                # 8. 先加载向量数据（用于确定索引参数）
                vectors, metadata_list, doc_ids = self._load_vectors_from_embedding(embedding_result)
                num_vectors = len(vectors)
                
                # 9. 获取提供者
                provider_name = provider.value.lower()
                vector_provider = self.registry.get_provider(provider_name)
                
                if vector_provider is None:
                    raise ProviderNotFoundError(
                        f"Provider '{provider_name}' is not available. "
                        f"Please check if the required dependencies are installed and the service is running."
                    )
                
                # 10. 确保 Collection 存在（Dify 方案：按维度拆分物理 Collection）
                # provider_index_id 现在返回的是物理 Collection 名称（如 default_collection_dim1024）
                provider_index_id = vector_provider.ensure_collection_exists(
                    collection_name=target_collection,
                    dimension=dimension,
                    metric_type=metric_type,
                    index_type=index_type,
                    enable_sparse=enable_sparse,
                    description=f"Knowledge base collection: {target_collection}"
                )
                vector_index.provider_index_id = provider_index_id
                
                # 记录物理 Collection 名称（Dify 方案元数据映射）
                vector_index.physical_collection_name = get_physical_collection_name(target_collection, dimension)
                
                if num_vectors > 0:
                    # 10.5 使用 BM25 生成稀疏向量（如果启用）
                    sparse_vectors = None
                    if enable_sparse:
                        try:
                            # 从 metadata 中提取源文本用于 BM25
                            source_texts = [
                                m.get("source_text", "") for m in metadata_list
                            ]
                            # 过滤空文本
                            if any(t.strip() for t in source_texts):
                                sparse_vectors = self.bm25_service.build_and_encode(
                                    index_id=provider_index_id,
                                    texts=source_texts
                                )
                                logger.info(
                                    f"BM25 sparse vectors generated: "
                                    f"{sum(1 for sv in sparse_vectors if sv)} non-empty "
                                    f"out of {len(sparse_vectors)}"
                                )
                            else:
                                logger.warning("所有文档的源文本为空，跳过 BM25 稀疏向量生成")
                        except Exception as bm25_error:
                            logger.warning(f"BM25 稀疏向量生成失败（降级到纯稠密索引）: {bm25_error}")
                            sparse_vectors = None
                    
                    # 11. 批量插入向量到 Collection（追加模式，包含 doc_id 用于 Partition Key 路由）
                    if sparse_vectors and any(sv for sv in sparse_vectors):
                        vector_ids = vector_provider.add_vectors_with_sparse(
                            provider_index_id,
                            vectors,
                            metadata_list,
                            sparse_vectors=sparse_vectors,
                            doc_ids=doc_ids
                        )
                        vector_index.has_sparse = True
                    else:
                        vector_ids = vector_provider.add_vectors(
                            provider_index_id,
                            vectors,
                            metadata_list,
                            doc_ids=doc_ids
                        )
                    
                    # 12. 更新索引状态
                    vector_index.vector_count = num_vectors
                    vector_index.status = IndexStatus.READY
                else:
                    vector_index.status = IndexStatus.READY
                    vector_index.vector_count = 0
                
                self.db.commit()
                self.db.refresh(vector_index)
                
                # 13. 保存索引元数据
                if vector_index.index_type == IndexProvider.MILVUS:
                    try:
                        file_path = vector_provider.get_metadata_file_path(provider_index_id)
                        vector_index.file_path = file_path
                        self.db.commit()
                        logger.info(f"Milvus index metadata saved to {file_path}")
                    except Exception as persist_error:
                        logger.warning(f"Failed to get Milvus metadata path: {persist_error}")
            
            # 14. 创建初始统计记录
            self._create_initial_statistics(vector_index.id)
            
            logger.info(
                f"Added vectors to collection '{target_collection}' from embedding: {name} "
                f"(ID: {vector_index.id}, vectors: {num_vectors})"
            )
            return vector_index
            
        except Exception as e:
            self.db.rollback()
            # 更新错误状态
            if 'vector_index' in locals() and vector_index.id:
                vector_index.status = IndexStatus.ERROR
                vector_index.error_message = str(e)
                self.db.commit()
            logger.error(f"Failed to create index from embedding: {str(e)}")
            raise IndexBuildError(f"Failed to create index from embedding: {str(e)}")

    def get_collections(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的 Milvus Collection 列表
        
        Returns:
            Collection 信息列表
        """
        from ..vector_config import DEFAULT_COLLECTION_NAME, parse_physical_collection_name
        
        try:
            provider = self.registry.get_provider("milvus")
            if provider is None:
                return []
            
            collection_names = provider.get_collection_names()
            
            # Dify 方案：按逻辑知识库名聚合物理 Collection
            logical_map = {}  # {logical_name: [physical_names]}
            for coll_name in collection_names:
                logical_name, dim = parse_physical_collection_name(coll_name)
                if logical_name not in logical_map:
                    logical_map[logical_name] = []
                logical_map[logical_name].append({
                    "physical_name": coll_name,
                    "dimension": dim
                })
            
            from sqlalchemy import func
            
            collections = []
            for logical_name, physical_list in logical_map.items():
                # 统计逻辑知识库关联的文档数量
                doc_count = self.db.query(VectorIndex).filter(
                    VectorIndex.collection_name == logical_name,
                    VectorIndex.status == IndexStatus.READY
                ).count()
                
                # 统计逻辑知识库的总向量数
                total_vectors = self.db.query(func.sum(VectorIndex.vector_count)).filter(
                    VectorIndex.collection_name == logical_name,
                    VectorIndex.status == IndexStatus.READY
                ).scalar() or 0
                
                # 提取所有维度
                dimensions = [p["dimension"] for p in physical_list if p["dimension"] is not None]
                
                collections.append({
                    "collection_name": logical_name,
                    "is_default": logical_name == DEFAULT_COLLECTION_NAME,
                    "document_count": doc_count,
                    "total_vectors": total_vectors,
                    "physical_collections": physical_list,
                    "dimensions": sorted(dimensions),
                    "physical_count": len(physical_list)
                })
            
            return collections
            
        except Exception as e:
            logger.error(f"Failed to get collections: {str(e)}")
            return []

    def _load_vectors_from_embedding(
        self,
        embedding_result: EmbeddingResult
    ) -> tuple:
        """
        从向量化结果加载向量数据
        
        Args:
            embedding_result: 向量化结果对象
            
        Returns:
            (vectors: np.ndarray, metadata: List[Dict], doc_ids: List[str])
        """
        try:
            # 读取 JSON 文件
            json_file_path = embedding_result.json_file_path
            
            # 处理相对路径
            if not os.path.isabs(json_file_path):
                # 获取 backend 目录作为基准
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                
                # 尝试多个可能的路径
                possible_paths = [
                    os.path.join(backend_dir, "results", json_file_path),  # backend/results/embedding/...
                    os.path.join(backend_dir, json_file_path),  # backend/embedding/...
                    os.path.join(os.path.dirname(backend_dir), json_file_path),  # 项目根目录/embedding/...
                ]
                
                json_file_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        json_file_path = path
                        break
                
                if not json_file_path:
                    logger.warning(f"JSON file not found in any of: {possible_paths}")
                    return np.array([]), [], []
            
            if not os.path.exists(json_file_path):
                logger.warning(f"JSON file not found: {json_file_path}")
                return np.array([]), [], []
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            vectors = []
            metadata_list = []
            doc_ids = []
            
            # 解析向量数据
            if "vectors" in data:
                for item in data["vectors"]:
                    if "vector" in item:
                        vectors.append(item["vector"])
                        # doc_id 提升为顶级字段（用于 Partition Key）
                        doc_ids.append(embedding_result.document_id or "unknown")
                        metadata_list.append({
                            "index": item.get("index", len(vectors) - 1),
                            "text_hash": item.get("text_hash"),
                            "text_length": item.get("text_length", 0),
                            "source_text": item.get("source_text", "")[:500],  # 限制长度
                            "document_id": embedding_result.document_id,
                            "embedding_result_id": embedding_result.result_id
                        })
            
            if len(vectors) == 0:
                logger.warning(f"No vectors found in JSON file: {json_file_path}")
                return np.array([]), [], []
            
            vectors_array = np.array(vectors, dtype=np.float32)
            
            logger.info(f"Loaded {len(vectors)} vectors from embedding result (doc_id: {embedding_result.document_id})")
            return vectors_array, metadata_list, doc_ids
            
        except Exception as e:
            logger.error(f"Failed to load vectors from embedding: {str(e)}")
            raise IndexBuildError(f"Failed to load vectors: {str(e)}")

    def _get_document_name(self, document_id: str) -> Optional[str]:
        """获取文档名称"""
        try:
            from ..models.document import Document
            doc = self.db.query(Document).filter(
                Document.id == document_id
            ).first()
            return doc.filename if doc else None
        except Exception:
            return None

    def get_index_history(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取索引历史记录
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            sort_by: 排序字段
            sort_order: 排序方向 (asc/desc)
            
        Returns:
            历史记录列表和分页信息
        """
        try:
            query = self.db.query(VectorIndex)
            
            # 排序
            sort_column = getattr(VectorIndex, sort_by, VectorIndex.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            total = query.count()
            total_pages = (total + page_size - 1) // page_size
            
            items = query.offset((page - 1) * page_size)\
                .limit(page_size)\
                .all()
            
            return {
                "items": [idx.to_dict() for idx in items],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Failed to get index history: {str(e)}")
            raise

    # ==================== 原有 API ====================

    def create_index(
        self,
        index_name: str,
        dimension: int,
        index_type: IndexProvider,
        metric_type: str = "cosine",
        description: Optional[str] = None,
        algorithm_type: str = "FLAT",
        index_params: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> VectorIndex:
        """
        创建新的向量索引
        
        Args:
            index_name: 索引名称
            dimension: 向量维度
            index_type: 索引类型（MILVUS）
            metric_type: 相似度度量类型
            description: 索引描述
            algorithm_type: 索引算法类型
            index_params: 索引参数
            namespace: 命名空间
            
        Returns:
            VectorIndex 对象
        """
        try:
            # 检查索引名称是否已存在
            existing = self.db.query(VectorIndex).filter(
                VectorIndex.index_name == index_name
            ).first()
            
            if existing:
                raise IndexBuildError(f"Index with name '{index_name}' already exists")
            
            # 验证维度
            if dimension not in VALID_DIMENSIONS:
                raise VectorDimensionError(
                    f"Dimension {dimension} not in valid dimensions: {VALID_DIMENSIONS}"
                )
            
            # 获取提供者
            provider_name = index_type.value.lower()
            provider = self.registry.get_provider(provider_name)
            
            # 创建索引配置
            config = IndexConfig(
                index_name=index_name,
                dimension=dimension,
                metric_type=metric_type,
                index_type=algorithm_type
            )
            
            # 在提供者中创建索引
            provider_index_id = provider.create_index(config)
            
            # 创建数据库记录
            vector_index = VectorIndex(
                index_name=index_name,
                index_type=index_type,
                algorithm_type=algorithm_type,
                dimension=dimension,
                metric_type=metric_type,
                description=description,
                provider_index_id=provider_index_id,
                namespace=namespace,
                index_params=index_params or {},
                status=IndexStatus.BUILDING
            )
            
            self.db.add(vector_index)
            self.db.commit()
            self.db.refresh(vector_index)
            
            # 创建初始统计记录
            self._create_initial_statistics(vector_index.id)
            
            # 记录操作日志
            self.operation_logger.log_operation(
                operation_type=OperationType.CREATE,
                index_id=vector_index.id,
                status=OperationStatus.SUCCESS,
                details={"provider": provider_name, "algorithm": algorithm_type}
            )
            
            logger.info(f"Created index: {index_name} (ID: {vector_index.id})")
            return vector_index
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create index: {str(e)}")
            raise IndexBuildError(f"Failed to create index: {str(e)}")

    def add_vectors(
        self,
        index_id: int,
        vectors: np.ndarray,
        metadata: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        向索引添加向量
        
        Args:
            index_id: 索引 ID
            vectors: 向量数组
            metadata: 元数据列表
            
        Returns:
            操作结果
        """
        try:
            # 获取索引
            vector_index = self._get_index_by_id(index_id)
            
            # 验证向量维度
            if vectors.shape[1] != vector_index.dimension:
                raise VectorDimensionError(
                    f"Vector dimension mismatch: expected {vector_index.dimension}, "
                    f"got {vectors.shape[1]}"
                )
            
            # 获取提供者
            provider = self._get_provider_for_index(vector_index)
            
            # 添加向量
            with self.operation_logger.track_operation(
                operation_type=OperationType.ADD_VECTORS,
                index_id=index_id,
                details={"vector_count": len(vectors)}
            ):
                vector_ids = provider.add_vectors(
                    vector_index.provider_index_id,
                    vectors,
                    metadata
                )
            
            # 更新索引状态和统计
            vector_index.status = IndexStatus.READY
            vector_index.vector_count += len(vectors)
            vector_index.updated_at = datetime.now()
            
            self._update_statistics(
                index_id,
                vectors_added=len(vectors)
            )
            
            self.db.commit()
            
            result = {
                "index_id": index_id,
                "vectors_added": len(vectors),
                "vector_ids": vector_ids,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Added {len(vectors)} vectors to index {index_id}")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add vectors: {str(e)}")
            raise IndexBuildError(f"Failed to add vectors: {str(e)}")

    def search(
        self,
        index_id: int,
        query_vector: np.ndarray,
        top_k: int = 10,
        threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        save_result: bool = False
    ) -> Dict[str, Any]:
        """
        向量相似度搜索
        
        Args:
            index_id: 索引 ID
            query_vector: 查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值
            filters: 过滤条件
            save_result: 是否保存结果到文件
            
        Returns:
            搜索结果
        """
        try:
            # 获取索引
            vector_index = self._get_index_by_id(index_id)
            
            if vector_index.status != IndexStatus.READY:
                # 边界情况：索引为空时执行查询 → 返回空结果集
                if vector_index.vector_count == 0:
                    return {
                        "index_id": index_id,
                        "index_name": vector_index.index_name,
                        "top_k": top_k,
                        "results_count": 0,
                        "search_time_ms": 0,
                        "results": [],
                        "timestamp": datetime.now().isoformat()
                    }
                raise SearchError(str(index_id), "Index is not ready for search")
            
            # 验证查询向量维度
            if len(query_vector) != vector_index.dimension:
                raise VectorDimensionError(
                    f"Query vector dimension mismatch: expected {vector_index.dimension}, "
                    f"got {len(query_vector)}"
                )
            
            # 边界情况：K 值大于向量总数 → 返回所有可用向量
            actual_top_k = min(top_k, vector_index.vector_count)
            
            # 获取提供者
            provider = self._get_provider_for_index(vector_index)
            
            # 执行搜索
            start_time = datetime.now()
            search_results = provider.search(
                vector_index.provider_index_id,
                query_vector,
                actual_top_k,
                filters
            )
            search_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # 应用阈值过滤
            if threshold is not None:
                search_results = [r for r in search_results if r.score >= threshold]
            
            # 记录查询历史
            self._record_query_history(
                index_id=index_id,
                query_vector=query_vector,
                top_k=top_k,
                filters=filters,
                results_count=len(search_results),
                search_time_ms=search_time_ms
            )
            
            # 更新统计
            self._update_statistics(
                index_id,
                queries_executed=1,
                avg_search_time_ms=search_time_ms
            )
            
            # 构建结果
            result = {
                "index_id": index_id,
                "index_name": vector_index.index_name,
                "top_k": top_k,
                "results_count": len(search_results),
                "search_time_ms": search_time_ms,
                "results": [
                    {
                        "vector_id": r.vector_id,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in search_results
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            # 保存结果（可选）
            if save_result:
                result_file = self.result_persistence.save_search_result(
                    index_name=vector_index.index_name,
                    result=result
                )
                result["result_file"] = result_file
            
            logger.info(f"Search completed: {len(search_results)} results in {search_time_ms:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(str(index_id), str(e))

    def batch_search(
        self,
        index_id: int,
        query_vectors: np.ndarray,
        top_k: int = 10,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        批量向量搜索
        
        Args:
            index_id: 索引 ID
            query_vectors: 查询向量数组
            top_k: 每个查询返回结果数量
            threshold: 相似度阈值
            
        Returns:
            批量搜索结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            
            if vector_index.status != IndexStatus.READY:
                raise SearchError(str(index_id), "Index is not ready for search")
            
            # 验证维度
            if query_vectors.shape[1] != vector_index.dimension:
                raise VectorDimensionError(
                    f"Query vector dimension mismatch: expected {vector_index.dimension}, "
                    f"got {query_vectors.shape[1]}"
                )
            
            provider = self._get_provider_for_index(vector_index)
            
            start_time = datetime.now()
            all_results = []
            
            for query_vector in query_vectors:
                search_results = provider.search(
                    vector_index.provider_index_id,
                    query_vector,
                    top_k
                )
                
                if threshold is not None:
                    search_results = [r for r in search_results if r.score >= threshold]
                
                all_results.append([
                    {
                        "vector_id": r.vector_id,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in search_results
                ])
            
            total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新统计
            self._update_statistics(
                index_id,
                queries_executed=len(query_vectors),
                avg_search_time_ms=total_time_ms / len(query_vectors)
            )
            
            return {
                "index_id": index_id,
                "index_name": vector_index.index_name,
                "query_count": len(query_vectors),
                "top_k": top_k,
                "total_time_ms": total_time_ms,
                "results": all_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Batch search failed: {str(e)}")
            raise SearchError(str(index_id), str(e))

    def get_index(self, index_id: int) -> VectorIndex:
        """
        获取索引详情
        
        Args:
            index_id: 索引 ID
            
        Returns:
            VectorIndex 对象
        """
        return self._get_index_by_id(index_id)

    def list_indexes(
        self,
        skip: int = 0,
        limit: int = 100,
        namespace: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[VectorIndex]:
        """
        列出所有索引
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            namespace: 筛选命名空间
            status: 筛选状态
            
        Returns:
            VectorIndex 列表
        """
        query = self.db.query(VectorIndex)
        
        if namespace:
            query = query.filter(VectorIndex.namespace == namespace)
        
        if status:
            query = query.filter(VectorIndex.status == status)
        
        return query.offset(skip).limit(limit).all()

    def delete_index(self, index_id: int) -> None:
        """
        删除索引
        
        Args:
            index_id: 索引 ID
        """
        try:
            # 获取索引
            vector_index = self._get_index_by_id(index_id)
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.DELETE,
                index_id=index_id
            ):
                # 从提供者中删除索引
                try:
                    provider = self._get_provider_for_index(vector_index)
                    provider.delete_index(vector_index.provider_index_id)
                except Exception as e:
                    logger.warning(f"Failed to delete from provider: {str(e)}")
                
                # 从数据库中删除
                self.db.delete(vector_index)
                self.db.commit()
            
            logger.info(f"Deleted index {index_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete index: {str(e)}")
            raise IndexBuildError(f"Failed to delete index: {str(e)}")

    def get_statistics(self, index_id: int) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Args:
            index_id: 索引 ID
            
        Returns:
            统计信息字典
        """
        try:
            # 获取数据库统计
            db_stats = self.db.query(IndexStatistics)\
                .filter(IndexStatistics.index_id == index_id)\
                .first()
            
            if not db_stats:
                raise IndexNotFoundError(f"Statistics not found for index {index_id}")
            
            # 获取提供者实时统计
            vector_index = self._get_index_by_id(index_id)
            provider = self._get_provider_for_index(vector_index)
            
            provider_stats = provider.get_index_stats(vector_index.provider_index_id)
            
            # 合并统计信息
            stats = {
                "index_id": index_id,
                "index_name": vector_index.index_name,
                "vector_count": provider_stats.get("vector_count", db_stats.vector_count),
                "dimension": vector_index.dimension,
                "index_type": vector_index.index_type.value,
                "algorithm_type": vector_index.algorithm_type,
                "metric_type": vector_index.metric_type,
                "total_queries": db_stats.total_queries,
                "avg_search_time_ms": float(db_stats.avg_search_time_ms) if db_stats.avg_search_time_ms else 0,
                "memory_usage_bytes": provider_stats.get("memory_usage_bytes", 0),
                "created_at": vector_index.created_at.isoformat(),
                "last_updated": provider_stats.get("last_updated", vector_index.updated_at.isoformat())
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            raise

    def get_query_history(
        self,
        index_id: int,
        limit: int = 100
    ) -> List[QueryHistory]:
        """
        获取查询历史
        
        Args:
            index_id: 索引 ID
            limit: 返回记录数
            
        Returns:
            QueryHistory 列表
        """
        return self.db.query(QueryHistory)\
            .filter(QueryHistory.index_id == index_id)\
            .order_by(QueryHistory.created_at.desc())\
            .limit(limit)\
            .all()

    def _get_index_by_id(self, index_id: int) -> VectorIndex:
        """获取索引对象"""
        vector_index = self.db.query(VectorIndex)\
            .filter(VectorIndex.id == index_id)\
            .first()
        
        if not vector_index:
            raise IndexNotFoundError(f"Index {index_id} not found")
        
        return vector_index

    def _get_provider_for_index(self, vector_index: VectorIndex) -> BaseProvider:
        """获取索引对应的提供者"""
        provider_name = vector_index.index_type.value.lower()
        return self.registry.get_provider(provider_name)

    def _create_initial_statistics(self, index_id: int) -> None:
        """创建初始统计记录"""
        stats = IndexStatistics(
            index_id=index_id,
            vector_count=0,
            total_queries=0,
            avg_search_time_ms=0.0
        )
        self.db.add(stats)
        self.db.commit()

    def _update_statistics(
        self,
        index_id: int,
        vectors_added: int = 0,
        queries_executed: int = 0,
        avg_search_time_ms: Optional[float] = None
    ) -> None:
        """更新统计信息"""
        stats = self.db.query(IndexStatistics)\
            .filter(IndexStatistics.index_id == index_id)\
            .first()
        
        if stats:
            if vectors_added > 0:
                stats.vector_count += vectors_added
            
            if queries_executed > 0:
                stats.total_queries += queries_executed
            
            if avg_search_time_ms is not None:
                # 计算移动平均
                if stats.avg_search_time_ms:
                    stats.avg_search_time_ms = (
                        stats.avg_search_time_ms * 0.9 + avg_search_time_ms * 0.1
                    )
                else:
                    stats.avg_search_time_ms = avg_search_time_ms
            
            stats.last_updated = datetime.now()

    def _record_query_history(
        self,
        index_id: int,
        query_vector: np.ndarray,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        results_count: int,
        search_time_ms: float
    ) -> None:
        """记录查询历史"""
        history = QueryHistory(
            index_id=index_id,
            top_k=top_k,
            results_count=results_count,
            search_time_ms=search_time_ms
        )
        
        # Use setter methods for JSON fields
        history.set_query_vector(query_vector.tolist())
        if filters:
            history.set_filters(filters)
        
        self.db.add(history)
        self.db.commit()

    # ==================== 持久化 API ====================

    def persist_index(self, index_id: int) -> Dict[str, Any]:
        """
        持久化索引元数据
        
        Args:
            index_id: 索引 ID
            
        Returns:
            持久化结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            provider = self._get_provider_for_index(vector_index)
            
            # 检查索引是否在内存中
            if not vector_index.provider_index_id:
                # 索引不在内存中
                if vector_index.file_path:
                    return {
                        "index_id": index_id,
                        "file_path": vector_index.file_path,
                        "message": "Index metadata already saved",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise IndexBuildError(
                        "Index not found. Please recreate the index from the embedding result."
                    )
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.PERSIST,
                index_id=index_id
            ):
                # 获取 Milvus 索引元数据路径
                file_path = provider.get_metadata_file_path(vector_index.provider_index_id)
                
                # 更新数据库记录
                vector_index.file_path = file_path
                vector_index.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Persisted index metadata {index_id} to {file_path}")
            
            return {
                "index_id": index_id,
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
            
        except IndexBuildError:
            raise
        except Exception as e:
            logger.error(f"Failed to persist index: {str(e)}")
            raise IndexBuildError(f"Failed to persist index: {str(e)}")

    def recover_index(self, index_id: int) -> Dict[str, Any]:
        """
        恢复索引连接
        
        Args:
            index_id: 索引 ID
            
        Returns:
            恢复结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            
            if not vector_index.provider_index_id:
                raise IndexBuildError(
                    "No provider index ID found. Please recreate the index from the embedding result."
                )
            
            provider = self._get_provider_for_index(vector_index)
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.RECOVER,
                index_id=index_id
            ):
                # 检查 Milvus 连接并尝试重新建立
                health = provider.health_check()
                
                # 更新状态
                vector_index.status = IndexStatus.READY
                vector_index.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Recovered index {index_id}")
            
            return {
                "index_id": index_id,
                "status": "recovered",
                "provider_health": health,
                "timestamp": datetime.now().isoformat()
            }
            
        except IndexBuildError:
            raise
        except Exception as e:
            logger.error(f"Failed to recover index: {str(e)}")
            raise IndexBuildError(f"Failed to recover index: {str(e)}")

    # ==================== 向量 CRUD API ====================

    def delete_vectors(
        self,
        index_id: int,
        vector_ids: List[str]
    ) -> Dict[str, Any]:
        """
        从索引中删除向量
        
        Args:
            index_id: 索引 ID
            vector_ids: 要删除的向量 ID 列表
            
        Returns:
            删除结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            provider = self._get_provider_for_index(vector_index)
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.DELETE_VECTORS,
                index_id=index_id,
                details={"vector_count": len(vector_ids)}
            ):
                # 调用 provider 的删除方法
                provider.delete_vectors(vector_ids)
                
                # 更新向量计数
                vector_index.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Deleted {len(vector_ids)} vectors from index {index_id}")
            
            return {
                "index_id": index_id,
                "deleted_count": len(vector_ids),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {str(e)}")
            raise IndexBuildError(f"Failed to delete vectors: {str(e)}")

    def update_vector(
        self,
        index_id: int,
        vector_id: str,
        vector: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        更新索引中的向量
        
        Args:
            index_id: 索引 ID
            vector_id: 向量 ID
            vector: 新的向量数据
            metadata: 新的元数据
            
        Returns:
            更新结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            
            # 验证维度
            if len(vector) != vector_index.dimension:
                raise VectorDimensionError(
                    f"Vector dimension mismatch: expected {vector_index.dimension}, got {len(vector)}"
                )
            
            provider = self._get_provider_for_index(vector_index)
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.UPDATE_VECTORS,
                index_id=index_id,
                details={"vector_id": vector_id}
            ):
                # 使用 provider 的 update_vectors 方法
                vectors_array = np.array([vector], dtype=np.float32)
                provider.update_vectors(
                    vectors_array,
                    [vector_id],
                    [metadata or {}]
                )
                
                vector_index.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Updated vector {vector_id} in index {index_id}")
            
            return {
                "index_id": index_id,
                "vector_id": vector_id,
                "updated": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update vector: {str(e)}")
            raise IndexBuildError(f"Failed to update vector: {str(e)}")

    # ==================== 多 Collection 搜索 API ====================

    def multi_collection_search(
        self,
        collection_names: List[str],
        query_vector: np.ndarray,
        top_k: int = 10,
        threshold: Optional[float] = None,
        merge_strategy: str = "score"  # "score" | "round_robin"
    ) -> Dict[str, Any]:
        """
        多 Collection 联合搜索
        
        Args:
            collection_names: Collection 名称列表
            query_vector: 查询向量
            top_k: 每个 Collection 返回结果数量
            threshold: 相似度阈值
            merge_strategy: 结果合并策略 ("score" 按分数排序, "round_robin" 轮询)
            
        Returns:
            合并后的搜索结果
        """
        try:
            start_time = datetime.now()
            all_results = []
            collection_results = {}
            
            # 获取所有匹配的索引
            indexes = self.db.query(VectorIndex).filter(
                VectorIndex.index_name.in_(collection_names),
                VectorIndex.status == IndexStatus.READY
            ).all()
            
            if not indexes:
                raise IndexNotFoundError(f"No ready indexes found for: {collection_names}")
            
            # 在每个 Collection 中搜索
            for vector_index in indexes:
                try:
                    # 验证维度
                    if len(query_vector) != vector_index.dimension:
                        logger.warning(
                            f"Skipping {vector_index.index_name}: dimension mismatch "
                            f"(expected {vector_index.dimension}, got {len(query_vector)})"
                        )
                        continue
                    
                    provider = self._get_provider_for_index(vector_index)
                    
                    results = provider.search(
                        vector_index.provider_index_id,
                        query_vector,
                        top_k
                    )
                    
                    # 应用阈值过滤
                    if threshold is not None:
                        results = [r for r in results if r.score >= threshold]
                    
                    # 添加 collection 来源信息
                    for r in results:
                        r.metadata["_collection_name"] = vector_index.index_name
                        r.metadata["_collection_id"] = vector_index.id
                    
                    collection_results[vector_index.index_name] = results
                    all_results.extend(results)
                    
                except Exception as e:
                    logger.warning(f"Search failed for {vector_index.index_name}: {str(e)}")
                    continue
            
            # 合并结果
            if merge_strategy == "score":
                # 按分数排序
                all_results.sort(key=lambda x: x.score, reverse=True)
                merged_results = all_results[:top_k]
            else:
                # 轮询合并
                merged_results = []
                max_len = max(len(v) for v in collection_results.values()) if collection_results else 0
                for i in range(max_len):
                    for coll_name in collection_names:
                        if coll_name in collection_results and i < len(collection_results[coll_name]):
                            merged_results.append(collection_results[coll_name][i])
                            if len(merged_results) >= top_k:
                                break
                    if len(merged_results) >= top_k:
                        break
            
            total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "collections_searched": len(indexes),
                "collection_names": [idx.index_name for idx in indexes],
                "top_k": top_k,
                "merge_strategy": merge_strategy,
                "results_count": len(merged_results),
                "total_time_ms": total_time_ms,
                "results": [
                    {
                        "vector_id": r.vector_id,
                        "score": r.score,
                        "collection_name": r.metadata.get("_collection_name"),
                        "metadata": {k: v for k, v in r.metadata.items() if not k.startswith("_")}
                    }
                    for r in merged_results
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Multi-collection search failed: {str(e)}")
            raise SearchError("multi-collection", str(e))

    def delete_index_history(self, history_id: int) -> Dict[str, Any]:
        """
        删除索引历史记录
        
        Args:
            history_id: 历史记录 ID（即索引 ID）
            
        Returns:
            删除结果
        """
        try:
            # 获取索引记录
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.id == history_id
            ).first()
            
            if not vector_index:
                raise IndexNotFoundError(f"Index history {history_id} not found")
            
            # 如果索引状态是 READY，需要先删除实际索引
            if vector_index.status == IndexStatus.READY and vector_index.provider_index_id:
                try:
                    provider = self._get_provider_for_index(vector_index)
                    provider.delete_index(vector_index.provider_index_id)
                except Exception as e:
                    logger.warning(f"Failed to delete provider index: {str(e)}")
            
            # 删除相关统计记录
            self.db.query(IndexStatistics).filter(
                IndexStatistics.index_id == history_id
            ).delete()
            
            # 删除相关查询历史
            self.db.query(QueryHistory).filter(
                QueryHistory.index_id == history_id
            ).delete()
            
            # 删除索引记录
            self.db.delete(vector_index)
            self.db.commit()
            
            logger.info(f"Deleted index history {history_id}")
            
            return {
                "history_id": history_id,
                "deleted": True,
                "message": "索引历史记录已删除",
                "timestamp": datetime.now().isoformat()
            }
            
        except IndexNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete index history: {str(e)}")
            raise IndexBuildError(f"Failed to delete index history: {str(e)}")

    def clear_all_index_history(self) -> Dict[str, Any]:
        """
        清空所有索引历史记录
        
        删除所有索引记录，同时清理：
        - Milvus 中的实际索引（如果存在）
        - 相关的统计记录
        - 相关的查询历史
        
        Returns:
            清空结果，包含删除的记录数
        """
        try:
            # 获取所有索引记录
            all_indexes = self.db.query(VectorIndex).all()
            deleted_count = len(all_indexes)
            
            # 逐个清理 Milvus 中的实际索引
            for vector_index in all_indexes:
                if vector_index.status == IndexStatus.READY and vector_index.provider_index_id:
                    try:
                        provider = self._get_provider_for_index(vector_index)
                        provider.delete_index(vector_index.provider_index_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete provider index {vector_index.provider_index_id}: {str(e)}")
            
            # 批量删除所有统计记录
            self.db.query(IndexStatistics).delete()
            
            # 批量删除所有查询历史
            self.db.query(QueryHistory).delete()
            
            # 批量删除所有索引记录
            self.db.query(VectorIndex).delete()
            
            self.db.commit()
            
            logger.info(f"Cleared all index history, deleted {deleted_count} records")
            
            return {
                "deleted_count": deleted_count,
                "message": f"已清空所有索引历史记录，共删除 {deleted_count} 条",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear all index history: {str(e)}")
            raise IndexBuildError(f"Failed to clear all index history: {str(e)}")

    # ==================== 混合检索方法 (T061-T063, T066) ====================

    def hybrid_search(
        self,
        index_id: int,
        query_text: str,
        query_dense_vector: List[float],
        query_sparse_vector: Optional[Dict] = None,
        top_n: int = 20,
        top_k: int = 5,
        enable_reranker: bool = True,
        rrf_k: int = 60,
        search_params: Optional[Dict] = None,
        output_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        混合检索：稠密+稀疏双路召回 → RRF 粗排 → Reranker 精排
        
        自动降级策略：
        - 稀疏向量为空或无效 → 降级到纯稠密检索
        - Reranker 不可用 → 跳过精排，直接返回 RRF 粗排结果
        
        Args:
            index_id: 索引数据库 ID
            query_text: 原始查询文本（用于 Reranker 精排）
            query_dense_vector: 稠密查询向量
            query_sparse_vector: 稀疏查询向量
            top_n: 粗排候选集大小
            top_k: 最终返回结果数量
            enable_reranker: 是否启用 Reranker 精排
            rrf_k: RRF 排名平滑因子
            search_params: 搜索参数
            output_fields: 返回字段列表
            
        Returns:
            HybridSearchResponse 格式的字典
        """
        import time
        total_start = time.time()
        
        try:
            # 获取索引记录
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.id == index_id
            ).first()
            
            if not vector_index:
                raise IndexNotFoundError(f"Index {index_id} not found")
            
            if vector_index.status != IndexStatus.READY:
                raise SearchError(str(index_id), f"Index is not ready (status={vector_index.status.value})")
            
            # 获取 Provider
            provider = self._get_provider_for_index(vector_index)
            provider_index_id = vector_index.provider_index_id
            
            if not provider_index_id:
                raise SearchError(str(index_id), "No provider index ID found")
            
            # ============ Step 0.5: 自动生成 query sparse 向量 ============
            # 如果调用方未提供 sparse 向量，且索引支持 sparse，则使用 BM25 自动生成
            if not query_sparse_vector and vector_index.has_sparse and query_text:
                try:
                    auto_sparse = self.bm25_service.encode_query(
                        index_id=provider_index_id,
                        query_text=query_text
                    )
                    if auto_sparse:
                        query_sparse_vector = auto_sparse
                        logger.info(
                            f"BM25 自动生成 query sparse 向量: "
                            f"{len(auto_sparse)} 个非零维度"
                        )
                except Exception as e:
                    logger.warning(f"BM25 query sparse 生成失败（降级到纯稠密检索）: {e}")
            
            # ============ Step 1: 双路召回 + RRF 粗排 ============
            rrf_start = time.time()
            
            dense_vec = np.array(query_dense_vector, dtype=np.float32)
            
            # 调用 Provider 的 hybrid_search（内含 RRF 融合和降级逻辑）
            candidates, search_mode = provider.hybrid_search(
                index_id=provider_index_id,
                dense_vector=dense_vec,
                sparse_vector=query_sparse_vector,
                top_n=top_n,
                rrf_k=rrf_k,
                output_fields=output_fields,
                **(search_params or {})
            )
            
            rrf_time_ms = (time.time() - rrf_start) * 1000
            total_candidates = len(candidates)
            
            # ============ Step 2: Reranker 精排 ============
            reranker_time_ms = None
            reranker_available = False
            
            if enable_reranker and query_text and query_text.strip():
                try:
                    from .reranker_service import RerankerService
                    reranker = RerankerService.get_instance()
                    
                    if not reranker.available:
                        reranker.init()
                    
                    if reranker.available:
                        reranker_available = True
                        reranker_start = time.time()
                        
                        # 将候选集交给 Reranker 精排
                        candidates = reranker.rerank(
                            query=query_text,
                            candidates=candidates,
                            top_k=top_k,
                            text_key="text"
                        )
                        
                        reranker_time_ms = (time.time() - reranker_start) * 1000
                    else:
                        logger.warning("Reranker 不可用，跳过精排")
                        candidates = candidates[:top_k]
                except Exception as e:
                    logger.warning(f"Reranker 精排失败，跳过: {e}")
                    candidates = candidates[:top_k]
            else:
                # 不启用 Reranker 或查询文本为空
                candidates = candidates[:top_k]
            
            total_time_ms = (time.time() - total_start) * 1000
            
            # ============ Step 3: 构造返回结果 ============
            results = []
            for i, c in enumerate(candidates):
                result_item = {
                    "vector_id": c.get("vector_id", 0),
                    "rrf_score": c.get("rrf_score", 0),
                    "reranker_score": c.get("reranker_score"),
                    "final_score": c.get("reranker_score") if c.get("reranker_score") is not None else c.get("rrf_score", 0),
                    "doc_id": c.get("metadata", {}).get("doc_id", ""),
                    "chunk_index": c.get("metadata", {}).get("chunk_index", 0),
                    "text": c.get("text") or c.get("metadata", {}).get("source_text", ""),
                    "metadata": c.get("metadata", {}),
                    "search_mode": search_mode
                }
                results.append(result_item)
            
            response = {
                "success": True,
                "data": results,
                "search_mode": search_mode,
                "query_time_ms": round(total_time_ms, 2),
                "rrf_time_ms": round(rrf_time_ms, 2) if rrf_time_ms else None,
                "reranker_time_ms": round(reranker_time_ms, 2) if reranker_time_ms else None,
                "total_candidates": total_candidates,
                "reranker_available": reranker_available
            }
            
            # ============ Step 4: 记录查询历史 ============
            try:
                query_record = QueryHistory(
                    index_id=index_id,
                    query_text=query_text[:500] if query_text else "",
                    top_k=top_k,
                    result_count=len(results),
                    response_time_ms=total_time_ms,
                    search_mode=search_mode
                )
                self.db.add(query_record)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to save query history: {e}")
                self.db.rollback()
            
            # ============ Step 5: 结果持久化到 JSON ============
            try:
                self._persist_hybrid_search_result(
                    index_id=index_id,
                    query_text=query_text,
                    response=response
                )
            except Exception as e:
                logger.warning(f"Failed to persist hybrid search result: {e}")
            
            logger.info(
                f"Hybrid search completed: index={index_id}, mode={search_mode}, "
                f"candidates={total_candidates}, results={len(results)}, "
                f"total_time={total_time_ms:.1f}ms"
            )
            
            return response
            
        except (IndexNotFoundError, SearchError):
            raise
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise SearchError(str(index_id), f"Hybrid search failed: {str(e)}")

    def _persist_hybrid_search_result(
        self,
        index_id: int,
        query_text: str,
        response: Dict[str, Any]
    ) -> None:
        """
        持久化混合检索结果到 JSON 文件
        
        Args:
            index_id: 索引 ID
            query_text: 查询文本
            response: 检索响应
        """
        result_dir = os.path.join(self.result_dir, "hybrid_search")
        os.makedirs(result_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"hybrid_{index_id}_{timestamp}.json"
        filepath = os.path.join(result_dir, filename)
        
        persist_data = {
            "index_id": index_id,
            "query_text": query_text[:200] if query_text else "",
            "search_mode": response.get("search_mode"),
            "result_count": len(response.get("data", [])),
            "query_time_ms": response.get("query_time_ms"),
            "rrf_time_ms": response.get("rrf_time_ms"),
            "reranker_time_ms": response.get("reranker_time_ms"),
            "reranker_available": response.get("reranker_available"),
            "timestamp": datetime.now().isoformat(),
            "results": response.get("data", [])[:10]  # 只保存 Top-10
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(persist_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.debug(f"Hybrid search result persisted to {filepath}")
