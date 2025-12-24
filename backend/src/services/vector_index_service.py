"""
向量索引服务层

提供统一的向量索引管理接口，协调数据库和向量存储提供者
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
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
from ..models.vector_index import VectorIndex, IndexStatus, IndexProvider
from ..models.index_statistics import IndexStatistics
from ..models.query_history import QueryHistory
from ..utils.logger import get_logger
from ..utils.result_persistence import ResultPersistence
from ..exceptions.vector_index_errors import (
    IndexNotFoundError,
    ProviderNotFoundError,
    IndexBuildError,
    SearchError
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

    def create_index(
        self,
        index_name: str,
        dimension: int,
        index_type: IndexProvider,
        metric_type: str = "cosine",
        description: Optional[str] = None
    ) -> VectorIndex:
        """
        创建新的向量索引
        
        Args:
            index_name: 索引名称
            dimension: 向量维度
            index_type: 索引类型（MILVUS 或 FAISS）
            metric_type: 相似度度量类型
            description: 索引描述
            
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
            
            # 获取提供者
            provider_name = index_type.value.lower()
            provider = self.registry.get_provider(provider_name)
            
            # 创建索引配置
            config = IndexConfig(
                index_name=index_name,
                dimension=dimension,
                metric_type=metric_type,
                index_type="HNSW" if index_type == IndexProvider.FAISS else "IVF_FLAT"
            )
            
            # 在提供者中创建索引
            provider_index_id = provider.create_index(config)
            
            # 创建数据库记录
            vector_index = VectorIndex(
                index_name=index_name,
                index_type=index_type,
                dimension=dimension,
                metric_type=metric_type,
                description=description,
                provider_index_id=provider_index_id,
                status=IndexStatus.CREATED
            )
            
            self.db.add(vector_index)
            self.db.commit()
            self.db.refresh(vector_index)
            
            # 创建初始统计记录
            self._create_initial_statistics(vector_index.id)
            
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
                raise IndexBuildError(
                    f"Vector dimension mismatch: expected {vector_index.dimension}, "
                    f"got {vectors.shape[1]}"
                )
            
            # 获取提供者
            provider = self._get_provider_for_index(vector_index)
            
            # 添加向量
            vector_ids = provider.add_vectors(
                vector_index.provider_index_id,
                vectors,
                metadata
            )
            
            # 更新索引状态和统计
            vector_index.status = IndexStatus.READY
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
        filters: Optional[Dict[str, Any]] = None,
        save_result: bool = False
    ) -> Dict[str, Any]:
        """
        向量相似度搜索
        
        Args:
            index_id: 索引 ID
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件
            save_result: 是否保存结果到文件
            
        Returns:
            搜索结果
        """
        try:
            # 获取索引
            vector_index = self._get_index_by_id(index_id)
            
            if vector_index.status != IndexStatus.READY:
                raise SearchError(f"Index {index_id} is not ready for search")
            
            # 验证查询向量维度
            if len(query_vector) != vector_index.dimension:
                raise SearchError(
                    f"Query vector dimension mismatch: expected {vector_index.dimension}, "
                    f"got {len(query_vector)}"
                )
            
            # 获取提供者
            provider = self._get_provider_for_index(vector_index)
            
            # 执行搜索
            start_time = datetime.now()
            search_results = provider.search(
                vector_index.provider_index_id,
                query_vector,
                top_k,
                filters
            )
            search_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
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
        limit: int = 100
    ) -> List[VectorIndex]:
        """
        列出所有索引
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            
        Returns:
            VectorIndex 列表
        """
        return self.db.query(VectorIndex)\
            .offset(skip)\
            .limit(limit)\
            .all()

    def delete_index(self, index_id: int) -> None:
        """
        删除索引
        
        Args:
            index_id: 索引 ID
        """
        try:
            # 获取索引
            vector_index = self._get_index_by_id(index_id)
            
            # 从提供者中删除索引
            try:
                provider = self._get_provider_for_index(vector_index)
                provider.delete_index(vector_index.provider_index_id)
            except Exception as e:
                logger.warning(f"Failed to delete from provider: {str(e)}")
            
            # 更新状态为已删除
            vector_index.status = IndexStatus.DELETED
            vector_index.updated_at = datetime.now()
            
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
        import json
        
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
