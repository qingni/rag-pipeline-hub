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
    FAISSProvider,
    MILVUS_AVAILABLE,
    FAISS_AVAILABLE
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
        self.registry = IndexRegistry()
        self.result_persistence = ResultPersistence(result_dir)
        self.operation_logger = IndexOperationLogger(db_session)
        
        # 注册提供者
        self._register_providers()
        
        logger.info("VectorIndexService initialized")

    def _register_providers(self) -> None:
        """注册所有向量存储提供者"""
        try:
            # 注册 FAISS（如果可用）
            if FAISS_AVAILABLE and FAISSProvider is not None:
                faiss_provider = FAISSProvider()
                self.registry.register_provider("faiss", faiss_provider)
                logger.info("Registered FAISS provider")
            else:
                logger.warning("FAISS provider not available (faiss-cpu not installed)")
            
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
        provider: IndexProvider = IndexProvider.MILVUS,  # 默认使用 Milvus
        index_type: str = "FLAT",  # 默认使用 FLAT
        metric_type: str = "cosine",
        index_params: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> VectorIndex:
        """
        从向量化任务创建索引
        
        Args:
            embedding_result_id: 向量化任务结果ID
            name: 索引名称（可选，自动生成）
            provider: 向量数据库提供商
            index_type: 索引算法类型
            metric_type: 相似度度量方法
            index_params: 索引算法参数
            namespace: 命名空间
            
        Returns:
            VectorIndex 对象
        """
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
            
            # 2. 生成索引名称
            if not name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_name = self._get_document_name(embedding_result.document_id) or "unknown"
                # 清理文档名称，移除非ASCII字符（Milvus要求collection名称以字母或下划线开头）
                doc_name = doc_name.replace(".", "_").replace(" ", "_")[:20]
                # 确保名称以字母开头（Milvus要求）
                name = f"idx_{doc_name}_{timestamp}"
            
            # 3. 检查索引名称是否已存在
            existing = self.db.query(VectorIndex).filter(
                VectorIndex.index_name == name
            ).first()
            
            if existing:
                raise IndexBuildError(f"Index with name '{name}' already exists")
            
            # 4. 验证维度
            dimension = embedding_result.vector_dimension
            if dimension not in VALID_DIMENSIONS:
                raise VectorDimensionError(
                    f"Dimension {dimension} not in valid dimensions: {VALID_DIMENSIONS}"
                )
            
            # 5. 创建数据库记录
            vector_index = VectorIndex(
                index_name=name,
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
            
            # 6. 记录操作日志
            with self.operation_logger.track_operation(
                operation_type=OperationType.CREATE,
                index_id=vector_index.id,
                details={
                    "embedding_result_id": embedding_result_id,
                    "provider": provider.value,
                    "index_type": index_type
                }
            ):
                # 7. 先加载向量数据（用于确定索引参数）
                vectors, metadata_list = self._load_vectors_from_embedding(embedding_result)
                num_vectors = len(vectors)
                
                # 8. 获取提供者
                provider_name = provider.value.lower()
                vector_provider = self.registry.get_provider(provider_name)
                
                if vector_provider is None:
                    raise ProviderNotFoundError(
                        f"Provider '{provider_name}' is not available. "
                        f"Please check if the required dependencies are installed and the service is running."
                    )
                
                # 9. 创建索引配置（传入向量数量用于动态调整参数）
                config = IndexConfig(
                    index_name=name,
                    dimension=dimension,
                    metric_type=metric_type,
                    index_type=index_type,
                    num_vectors=num_vectors  # 传入向量数量
                )
                
                # 10. 在提供者中创建索引
                provider_index_id = vector_provider.create_index(config)
                vector_index.provider_index_id = provider_index_id
                
                if num_vectors > 0:
                    # 11. 批量插入向量
                    vector_ids = vector_provider.add_vectors(
                        provider_index_id,
                        vectors,
                        metadata_list
                    )
                    
                    # 12. 更新索引状态
                    vector_index.vector_count = num_vectors
                    vector_index.status = IndexStatus.READY
                else:
                    vector_index.status = IndexStatus.READY
                    vector_index.vector_count = 0
                
                self.db.commit()
                self.db.refresh(vector_index)
                
                # 13. 自动持久化索引信息到磁盘
                if vector_index.index_type == IndexProvider.FAISS and len(vectors) > 0:
                    try:
                        file_path = vector_provider.save_index(provider_index_id)
                        vector_index.file_path = file_path
                        self.db.commit()
                        logger.info(f"Auto-persisted FAISS index to {file_path}")
                    except Exception as persist_error:
                        logger.warning(f"Failed to auto-persist index: {persist_error}")
                
                # Milvus 索引元数据文件路径
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
            
            logger.info(f"Created index from embedding: {name} (ID: {vector_index.id})")
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

    def _load_vectors_from_embedding(
        self,
        embedding_result: EmbeddingResult
    ) -> tuple:
        """
        从向量化结果加载向量数据
        
        Args:
            embedding_result: 向量化结果对象
            
        Returns:
            (vectors: np.ndarray, metadata: List[Dict])
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
                    return np.array([]), []
            
            if not os.path.exists(json_file_path):
                logger.warning(f"JSON file not found: {json_file_path}")
                return np.array([]), []
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            vectors = []
            metadata_list = []
            
            # 解析向量数据
            if "vectors" in data:
                for item in data["vectors"]:
                    if "vector" in item:
                        vectors.append(item["vector"])
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
                return np.array([]), []
            
            vectors_array = np.array(vectors, dtype=np.float32)
            
            logger.info(f"Loaded {len(vectors)} vectors from embedding result")
            return vectors_array, metadata_list
            
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
            index_type: 索引类型（MILVUS 或 FAISS）
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
                raise SearchError(f"Index {index_id} is not ready for search")
            
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
            raise SearchError(f"Search failed: {str(e)}")

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
                raise SearchError(f"Index {index_id} is not ready for search")
            
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
            raise SearchError(f"Batch search failed: {str(e)}")

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
        持久化索引到磁盘
        
        Args:
            index_id: 索引 ID
            
        Returns:
            持久化结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            
            if vector_index.index_type != IndexProvider.FAISS:
                raise IndexBuildError("Only FAISS indexes support local persistence")
            
            provider = self._get_provider_for_index(vector_index)
            
            # 检查索引是否在内存中
            if not vector_index.provider_index_id or \
               vector_index.provider_index_id not in provider._indexes:
                # 索引不在内存中，可能是服务重启后丢失
                # 检查是否已经有持久化文件
                if vector_index.file_path:
                    return {
                        "index_id": index_id,
                        "file_path": vector_index.file_path,
                        "message": "Index already persisted",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise IndexBuildError(
                        "Index not found in memory. The index may have been lost after service restart. "
                        "Please recreate the index from the embedding result."
                    )
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.PERSIST,
                index_id=index_id
            ):
                # 调用 FAISS provider 的持久化方法
                file_path = provider.save_index(vector_index.provider_index_id)
                
                # 更新数据库记录
                vector_index.file_path = file_path
                vector_index.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Persisted index {index_id} to {file_path}")
            
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
        从磁盘恢复索引
        
        Args:
            index_id: 索引 ID
            
        Returns:
            恢复结果
        """
        try:
            vector_index = self._get_index_by_id(index_id)
            
            if vector_index.index_type != IndexProvider.FAISS:
                raise IndexBuildError("Only FAISS indexes support local recovery")
            
            if not vector_index.file_path:
                raise IndexBuildError(
                    "No persisted file found for this index. "
                    "Please persist the index first or recreate it from the embedding result."
                )
            
            provider = self._get_provider_for_index(vector_index)
            
            # 检查索引是否已经在内存中
            if vector_index.provider_index_id and \
               vector_index.provider_index_id in provider._indexes:
                return {
                    "index_id": index_id,
                    "status": "already_loaded",
                    "message": "Index is already loaded in memory",
                    "timestamp": datetime.now().isoformat()
                }
            
            with self.operation_logger.track_operation(
                operation_type=OperationType.RECOVER,
                index_id=index_id
            ):
                # 调用 FAISS provider 的加载方法
                provider.load_index(vector_index.provider_index_id)
                
                # 更新状态
                vector_index.status = IndexStatus.READY
                vector_index.updated_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Recovered index {index_id}")
            
            return {
                "index_id": index_id,
                "status": "recovered",
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
                
                # 更新向量计数（注意：FAISS 不支持真正删除，只是标记）
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
