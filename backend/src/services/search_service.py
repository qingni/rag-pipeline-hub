"""
搜索查询服务

提供语义搜索、历史记录管理等核心功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import uuid
import asyncio
import hashlib
import re
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.search import SearchHistory, SearchConfig
from ..models.vector_index import VectorIndex, IndexStatus
from ..schemas.search import (
    SearchRequest,
    SearchResponseData,
    SearchResultItem,
    MetricType,
    IndexInfo,
    HistoryItem,
    HistoryConfig
)
from ..services.embedding_service import EmbeddingService
from ..services.vector_index_service import VectorIndexService
from ..services.query_enhancement_service import QueryEnhancementService, QueryEnhancementResult
from ..config import settings
from ..utils.logger import get_logger
import os

import logging as _logging

logger = get_logger("search_service")

# 模块加载标记：如果在服务启动日志中看到这行，说明 search_service.py 被正确加载
logger.info("[诊断] search_service.py 模块已加载 (版本: v2_三层防御体系)")

# 创建专用的召回调试 logger，仅输出到文件，不输出到控制台
def _create_recall_debug_logger():
    """创建召回调试专用 logger，日志写入 backend/logs/search_recall_debug.log"""
    _logger = _logging.getLogger("search_recall_debug")
    _logger.setLevel(_logging.DEBUG)
    _logger.handlers.clear()
    _logger.propagate = False  # 不向父 logger 传播，避免输出到控制台
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "search_recall_debug.log")
    
    handler = _logging.FileHandler(
        log_file,
        mode='a',  # 追加模式（每次查询开始时会通过 _reset_recall_debug_log 清空）
        encoding="utf-8"
    )
    handler.setLevel(_logging.DEBUG)
    handler.setFormatter(_logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    _logger.addHandler(handler)
    return _logger

recall_debug_logger = _create_recall_debug_logger()


def _reset_recall_debug_log():
    """每次查询开始时清空召回调试日志文件，只保留当前查询的日志信息"""
    for handler in recall_debug_logger.handlers:
        if isinstance(handler, _logging.FileHandler):
            handler.flush()
            handler.stream.seek(0)
            handler.stream.truncate(0)

# 搜索历史最大记录数
MAX_HISTORY_COUNT = 50
# 搜索超时时间（秒）
SEARCH_TIMEOUT = 30
# 查询文本最大长度
MAX_QUERY_LENGTH = 2000


class SearchServiceError(Exception):
    """搜索服务错误基类"""
    pass


class EmptyQueryError(SearchServiceError):
    """空查询错误"""
    pass


class QueryTooLongError(SearchServiceError):
    """查询文本过长错误"""
    pass


class IndexNotFoundError(SearchServiceError):
    """索引不存在错误"""
    pass


class EmbeddingServiceError(SearchServiceError):
    """向量化服务错误"""
    pass


class SearchTimeoutError(SearchServiceError):
    """搜索超时错误"""
    pass


class SearchService:
    """搜索查询服务"""
    
    def __init__(self, db_session: Session):
        """
        初始化搜索服务
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self._embedding_service = None
        self._embedding_services = {}  # 按模型名缓存 EmbeddingService 实例
        self._vector_index_service = None
        self._query_enhancement_service = None  # 查询增强服务（延迟初始化）
        # P2 优化：BM25 查询级缓存，避免同一次搜索请求中多个 Collection 共享 bm25_key 时重复计算
        # key: (bm25_key, query_text), value: sparse_vector
        self._bm25_query_cache: Dict[tuple, Any] = {}
        logger.info("SearchService initialized")
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """获取默认 Embedding 服务实例（延迟初始化）"""
        if self._embedding_service is None:
            self._embedding_service = self._get_embedding_service_for_model(
                settings.EMBEDDING_DEFAULT_MODEL
            )
        return self._embedding_service
    
    def _get_embedding_service_for_model(self, model_name: str) -> EmbeddingService:
        """
        按模型名获取 EmbeddingService 实例（缓存复用）
        
        设计理念：一个知识库绑定一种 Embedding 模型，搜索时需要使用
        与入库时相同的模型来嵌入查询文本，确保语义空间一致。
        
        Args:
            model_name: 嵌入模型名称（如 qwen3-embedding-8b, bge-m3）
            
        Returns:
            对应模型的 EmbeddingService 实例
        """
        if model_name not in self._embedding_services:
            api_key = settings.EMBEDDING_API_KEY
            base_url = settings.EMBEDDING_API_BASE_URL
            
            if not api_key or not base_url:
                raise EmbeddingServiceError("Embedding API 配置缺失")
            
            self._embedding_services[model_name] = EmbeddingService(
                api_key=api_key,
                model=model_name,
                base_url=base_url,
                max_retries=settings.EMBEDDING_MAX_RETRIES,
                request_timeout=settings.EMBEDDING_TIMEOUT
            )
            logger.info(f"Created EmbeddingService instance for model: {model_name}")
        
        return self._embedding_services[model_name]
    
    @property
    def query_enhancement_service(self) -> QueryEnhancementService:
        """获取查询增强服务实例（延迟初始化）"""
        if self._query_enhancement_service is None:
            self._query_enhancement_service = QueryEnhancementService(
model=getattr(settings, 'QUERY_ENHANCEMENT_MODEL', 'qwen3.5-35b-a3b'),
                temperature=getattr(settings, 'QUERY_ENHANCEMENT_TEMPERATURE', 0.3),
                max_tokens=getattr(settings, 'QUERY_ENHANCEMENT_MAX_TOKENS', 512),
                request_timeout=getattr(settings, 'QUERY_ENHANCEMENT_TIMEOUT', 30),
            )
        return self._query_enhancement_service

    @property
    def vector_index_service(self) -> VectorIndexService:
        """获取向量索引服务实例（延迟初始化）"""
        if self._vector_index_service is None:
            self._vector_index_service = VectorIndexService(self.db)
        return self._vector_index_service
    
    # ==================== 核心搜索功能 (US1) ====================
    
    async def search(
        self,
        request: SearchRequest
    ) -> SearchResponseData:
        """
        执行语义搜索
        
        Args:
            request: 搜索请求
            
        Returns:
            搜索响应数据
        """
        start_time = time.time()
        query_id = str(uuid.uuid4())
        
        # 验证查询文本
        query_text = self._validate_query_text(request.query_text)
        
        logger.info(f"Search started: query_id={query_id}, text_length={len(query_text)}")
        
        try:
            # 1. 获取目标索引
            index_ids = request.index_ids or []
            target_indexes = self._get_target_indexes(index_ids)
            
            if not target_indexes:
                # 无可用索引，返回空结果
                return SearchResponseData(
                    query_id=query_id,
                    query_text=query_text,
                    results=[],
                    total_count=0,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # 2. 将查询文本转换为向量
            query_vector = await self._embed_query(query_text)
            
            # 3. 在各索引中执行搜索
            all_results = []
            for index in target_indexes:
                try:
                    index_results = self._search_in_index(
                        index=index,
                        query_vector=query_vector,
                        top_k=request.top_k,
                        threshold=request.threshold,
                        metric_type=request.metric_type
                    )
                    all_results.extend(index_results)
                except Exception as e:
                    logger.warning(f"Search in index {index.id} failed: {str(e)}")
                    continue
            
            # 4. 合并排序结果
            sorted_results = self._merge_and_sort_results(
                all_results, 
                top_k=request.top_k,
                threshold=request.threshold
            )
            
            # 5. 格式化结果
            formatted_results = self._format_results(sorted_results)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 6. 保存搜索历史
            self._save_history_async(
                query_text=query_text,
                index_ids=[idx.id for idx in target_indexes],
                config={
                    "top_k": request.top_k,
                    "threshold": request.threshold,
                    "metric_type": request.metric_type.value
                },
                result_count=len(formatted_results),
                execution_time_ms=execution_time_ms
            )
            
            logger.info(f"Search completed: query_id={query_id}, results={len(formatted_results)}, time={execution_time_ms}ms")
            
            return SearchResponseData(
                query_id=query_id,
                query_text=query_text,
                results=formatted_results,
                total_count=len(formatted_results),
                execution_time_ms=execution_time_ms
            )
            
        except SearchServiceError:
            raise
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchServiceError(f"搜索失败: {str(e)}")
    
    def _validate_query_text(self, query_text: str) -> str:
        """验证查询文本"""
        if not query_text or not query_text.strip():
            raise EmptyQueryError("查询文本不能为空")
        
        query_text = query_text.strip()
        
        if len(query_text) > MAX_QUERY_LENGTH:
            raise QueryTooLongError(f"查询文本超过最大长度限制 ({MAX_QUERY_LENGTH} 字符)")
        
        return query_text
    
    def _get_target_indexes(self, index_ids: List[str]) -> List[VectorIndex]:
        """获取目标索引列表"""
        query = self.db.query(VectorIndex).filter(
            VectorIndex.status == IndexStatus.READY
        )
        
        if index_ids:
            # 验证指定的索引是否存在
            query = query.filter(VectorIndex.id.in_([int(id) for id in index_ids if id.isdigit()]))
        
        indexes = query.all()
        
        if index_ids and not indexes:
            raise IndexNotFoundError("所选索引不存在或已被删除")
        
        return indexes
    
    async def _embed_query(self, query_text: str, model_name: str = None) -> np.ndarray:
        """
        将查询文本转换为向量
        
        Args:
            query_text: 查询文本
            model_name: 指定使用的嵌入模型（不指定则使用默认模型）
        """
        try:
            # 选择对应模型的 EmbeddingService 实例
            if model_name:
                service = self._get_embedding_service_for_model(model_name)
            else:
                service = self.embedding_service
            
            # 使用同步方法，在线程池中执行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                service.embed_query,
                query_text
            )
            return np.array(result.vector)
        except Exception as e:
            logger.error(f"Embedding failed (model={model_name}): {str(e)}")
            raise EmbeddingServiceError("向量化服务暂时不可用，请稍后重试")
    
    def _search_in_index(
        self,
        index: VectorIndex,
        query_vector: np.ndarray,
        top_k: int,
        threshold: float,
        metric_type: MetricType
    ) -> List[Dict[str, Any]]:
        """在单个索引中执行搜索"""
        try:
            result = self.vector_index_service.search(
                index_id=index.id,
                query_vector=query_vector,
                top_k=top_k,
                threshold=threshold
            )
            
            # 添加索引信息到结果
            for item in result.get("results", []):
                item["source_index_id"] = index.id
                item["source_index_name"] = index.index_name
            
            return result.get("results", [])
        except Exception as e:
            logger.warning(f"Search in index {index.id} failed: {str(e)}")
            return []
    
    def _merge_and_sort_results(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """合并并排序搜索结果"""
        # 按相似度分数降序排序
        sorted_results = sorted(
            results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        # 应用阈值过滤
        filtered_results = [
            r for r in sorted_results
            if r.get("score", 0) >= threshold
        ]
        
        # 限制返回数量
        return filtered_results[:top_k]
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[SearchResultItem]:
        """格式化搜索结果"""
        formatted = []
        for rank, result in enumerate(results, start=1):
            # 获取文本内容和元数据
            metadata = result.get("metadata", {})
            
            # 尝试多个可能的字段名获取文本内容
            text_content = (
                metadata.get("source_text") or 
                metadata.get("text") or 
                metadata.get("content") or 
                ""
            )
            
            # 尝试获取文档名称
            source_document = (
                metadata.get("document_name") or 
                metadata.get("source") or 
                metadata.get("filename") or
                "未知文档"
            )
            
            # 如果只有 document_id，尝试查询文档名称
            if source_document == "未知文档" and metadata.get("document_id"):
                doc_name = self._get_document_name(metadata.get("document_id"))
                if doc_name:
                    source_document = doc_name
            
            # 获取片段位置
            chunk_position = (
                metadata.get("chunk_index") or 
                metadata.get("position") or 
                metadata.get("index")
            )
            
            # 生成摘要
            text_summary = self._generate_summary(text_content, max_length=200)
            
            # 计算相似度百分比
            score = result.get("score", 0)
            similarity_percent = f"{score * 100:.1f}%"
            
            formatted.append(SearchResultItem(
                id=str(uuid.uuid4()),
                chunk_id=str(result.get("vector_id", "")),
                text_content=text_content,
                text_summary=text_summary,
                similarity_score=score,
                similarity_percent=similarity_percent,
                source_index=result.get("source_index_name", ""),
                source_document=source_document,
                chunk_position=chunk_position,
                metadata=metadata,
                rank=rank
            ))
        
        return formatted
    
    def _get_document_name(self, document_id: str) -> Optional[str]:
        """根据文档ID获取文档名称"""
        try:
            from ..models.document import Document
            doc = self.db.query(Document).filter(
                Document.id == document_id
            ).first()
            return doc.filename if doc else None
        except Exception:
            return None
    
    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """生成文本摘要"""
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        # 截断并添加省略号
        return text[:max_length - 3] + "..."
    
    def _save_history_async(
        self,
        query_text: str,
        index_ids: List[int],
        config: Dict[str, Any],
        result_count: int,
        execution_time_ms: int
    ) -> None:
        """异步保存搜索历史（不阻塞主流程）"""
        try:
            self.save_history(
                query_text=query_text,
                index_ids=[str(id) for id in index_ids],
                config=config,
                result_count=result_count,
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            logger.warning(f"Failed to save search history: {str(e)}")
    
    # ==================== 索引管理 (US3) ====================
    
    def get_available_indexes(self) -> List[IndexInfo]:
        """
        获取可用于搜索的索引列表
        
        Returns:
            索引信息列表
        """
        try:
            indexes = self.db.query(VectorIndex).filter(
                VectorIndex.status == IndexStatus.READY
            ).order_by(desc(VectorIndex.created_at)).all()
            
            return [
                IndexInfo(
                    id=str(index.id),
                    name=index.index_name,
                    provider=index.index_type.value if index.index_type else "unknown",
                    vector_count=index.vector_count or 0,
                    dimension=index.dimension or 0,
                    metric_type=index.metric_type or "cosine",
                    created_at=index.created_at
                )
                for index in indexes
            ]
        except Exception as e:
            logger.error(f"Failed to get available indexes: {str(e)}")
            return []
    
    # ==================== 历史记录管理 (US4) ====================
    
    def save_history(
        self,
        query_text: str,
        index_ids: List[str],
        config: Dict[str, Any],
        result_count: int,
        execution_time_ms: int
    ) -> SearchHistory:
        """
        保存搜索历史
        
        Args:
            query_text: 查询文本
            index_ids: 索引ID列表
            config: 搜索配置
            result_count: 结果数量
            execution_time_ms: 执行耗时
            
        Returns:
            搜索历史记录
        """
        try:
            # 先清理超出限制的历史记录
            self._cleanup_old_history()
            
            history = SearchHistory(
                query_text=query_text,
                index_ids=index_ids,
                config=config,
                result_count=result_count,
                execution_time_ms=execution_time_ms
            )
            
            self.db.add(history)
            self.db.commit()
            self.db.refresh(history)
            
            logger.info(f"Search history saved: {history.id}")
            return history
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save search history: {str(e)}")
            raise
    
    def get_history(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取搜索历史列表
        
        Args:
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            历史记录列表和分页信息
        """
        try:
            # 获取总数
            total = self.db.query(SearchHistory).count()
            
            # 获取分页数据
            histories = self.db.query(SearchHistory)\
                .order_by(desc(SearchHistory.created_at))\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            items = [
                HistoryItem(
                    id=h.id,
                    query_text=h.query_text,
                    index_ids=h.index_ids or [],
                    config=HistoryConfig(
                        top_k=h.config.get("top_k", 10) if h.config else 10,
                        threshold=h.config.get("threshold", 0.5) if h.config else 0.5,
                        metric_type=h.config.get("metric_type", "cosine") if h.config else "cosine"
                    ),
                    result_count=h.result_count,
                    execution_time_ms=h.execution_time_ms,
                    created_at=h.created_at
                )
                for h in histories
            ]
            
            return {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get search history: {str(e)}")
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }
    
    def delete_history(self, history_id: str) -> bool:
        """
        删除单条历史记录
        
        Args:
            history_id: 历史记录ID
            
        Returns:
            是否删除成功
        """
        try:
            history = self.db.query(SearchHistory).filter(
                SearchHistory.id == history_id
            ).first()
            
            if not history:
                return False
            
            self.db.delete(history)
            self.db.commit()
            
            logger.info(f"Search history deleted: {history_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete search history: {str(e)}")
            return False
    
    def clear_history(self) -> int:
        """
        清空所有历史记录
        
        Returns:
            删除的记录数
        """
        try:
            count = self.db.query(SearchHistory).delete()
            self.db.commit()
            
            logger.info(f"Search history cleared: {count} records")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear search history: {str(e)}")
            return 0
    
    def _cleanup_old_history(self) -> None:
        """清理超出限制的历史记录"""
        try:
            # 获取当前记录数
            count = self.db.query(SearchHistory).count()
            
            if count >= MAX_HISTORY_COUNT:
                # 删除最旧的记录
                excess = count - MAX_HISTORY_COUNT + 1
                oldest = self.db.query(SearchHistory)\
                    .order_by(SearchHistory.created_at)\
                    .limit(excess)\
                    .all()
                
                for h in oldest:
                    self.db.delete(h)
                
                self.db.commit()
                logger.info(f"Cleaned up {len(oldest)} old search history records")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old history: {str(e)}")

    # ==================== 混合检索核心方法 (Phase 2: Foundational) ====================

    @property
    def bm25_service(self):
        """获取 BM25 稀疏向量服务实例（延迟初始化）"""
        if not hasattr(self, '_bm25_service') or self._bm25_service is None:
            from ..services.bm25_service import BM25SparseService
            self._bm25_service = BM25SparseService()
        return self._bm25_service

    @property
    def reranker_service(self):
        """获取 Reranker 服务实例（单例 + 延迟初始化）"""
        if not hasattr(self, '_reranker_service') or self._reranker_service is None:
            from ..services.reranker_service import RerankerService
            self._reranker_service = RerankerService.get_instance(
                model_name=settings.RERANKER_MODEL,
                api_key=settings.RERANKER_API_KEY,
                api_base_url=settings.RERANKER_API_BASE_URL,
                timeout=settings.RERANKER_TIMEOUT
            )
            # 延迟初始化 API 客户端
            if not self._reranker_service.available:
                self._reranker_service.init()
        return self._reranker_service

    @property
    def milvus_provider(self):
        """获取 MilvusProvider 实例（延迟初始化）"""
        if not hasattr(self, '_milvus_provider') or self._milvus_provider is None:
            from ..services.providers.milvus_provider import MilvusProvider
            from ..vector_config import MilvusConfig
            config = MilvusConfig(
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                user=settings.MILVUS_USER,
                password=settings.MILVUS_PASSWORD,
                timeout=settings.MILVUS_TIMEOUT,
            )
            self._milvus_provider = MilvusProvider(
                config=config,
                index_dir=settings.VECTOR_INDEX_RESULTS_DIR
            )
        return self._milvus_provider

    def _resolve_index_id_to_collection_name(self, index_id: str) -> str:
        """
        将数据库索引 ID 解析为 Milvus 物理 Collection 名称
        
        MilvusProvider 需要的是物理 Collection 名称（如 default_collection_dim1024），
        而非数据库自增 ID（如 1, 3, 4）。
        
        Args:
            index_id: 数据库索引 ID（字符串形式的整数）
            
        Returns:
            物理 Collection 名称
            
        Raises:
            IndexNotFoundError: 索引不存在或缺少物理 Collection 名称
        """
        try:
            idx = self.db.query(VectorIndex).filter(
                VectorIndex.id == int(index_id)
            ).first()
            
            if not idx:
                raise IndexNotFoundError(f"索引 {index_id} 不存在")
            
            # 优先使用 physical_collection_name，其次 provider_index_id
            collection_name = idx.physical_collection_name or idx.provider_index_id
            
            if not collection_name:
                raise IndexNotFoundError(
                    f"索引 {index_id} ({idx.index_name}) 缺少物理 Collection 名称，"
                    f"请检查 physical_collection_name 或 provider_index_id 字段"
                )
            
            return collection_name
        except (ValueError, TypeError):
            # index_id 不是有效的整数，可能本身就是 collection 名称，直接返回
            return index_id

    def _get_doc_id_for_index(self, index_id: str) -> Optional[str]:
        """
        根据索引记录 ID 获取对应的 doc_id（用于 Milvus Partition Key 过滤）
        
        设计理念：多个文档索引共享同一个物理 Collection（按维度拆分），
        入库时每条向量的 doc_id 字段存储的是 EmbeddingResult.document_id。
        检索时需要通过 doc_id 过滤限定文档范围，避免跨文档干扰。
        
        数据链路：VectorIndex.embedding_result_id → EmbeddingResult.document_id
        
        参考业界最佳实践：
        - Dify: 通过 dataset_id 作为 Partition Key，检索时传 expr 过滤
        - Weaviate: 通过 tenant 实现多租户隔离
        
        Args:
            index_id: 数据库索引记录 ID（字符串形式的整数）
            
        Returns:
            doc_id 字符串，解析失败返回 None（不过滤，全量检索）
        """
        try:
            idx = self.db.query(VectorIndex).filter(
                VectorIndex.id == int(index_id)
            ).first()
            
            if not idx:
                return None
            
            # 通过 embedding_result_id 关联查询 EmbeddingResult 获取 document_id
            if idx.embedding_result_id:
                try:
                    from ..models.embedding_models import EmbeddingResult
                    embedding_result = self.db.query(EmbeddingResult).filter(
                        EmbeddingResult.result_id == idx.embedding_result_id
                    ).first()
                    if embedding_result and embedding_result.document_id:
                        logger.info(
                            f"解析 doc_id: index_id={index_id}, "
                            f"embedding_result_id={idx.embedding_result_id}, "
                            f"document_id={embedding_result.document_id}"
                        )
                        return str(embedding_result.document_id)
                except Exception as e:
                    logger.warning(f"通过 EmbeddingResult 解析 doc_id 失败: {e}")
            
            logger.warning(
                f"无法解析 doc_id (index_id={index_id}): "
                f"embedding_result_id={idx.embedding_result_id}，将执行全量检索"
            )
            return None
            
        except (ValueError, TypeError):
            return None

    async def _dense_search_in_collection(
        self,
        index_id: str,
        query_vector: np.ndarray,
        top_n: int = 20,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        T004: 单 Collection 纯稠密检索
        
        封装 EmbeddingService → MilvusProvider.search() 的纯稠密检索逻辑。
        
        Args:
            index_id: Collection/索引 ID
            query_vector: 稠密查询向量
            top_n: 候选集大小
            threshold: 相似度阈值
            
        Returns:
            带 search_mode="dense_only" 标签的候选集列表
        """
        try:
            # 将数据库 ID 映射为 Milvus 物理 Collection 名称
            milvus_collection_name = self._resolve_index_id_to_collection_name(index_id)
            
            results = self.milvus_provider.search(
                index_id=milvus_collection_name,
                query_vector=query_vector,
                top_k=top_n
            )
            
            # 转换为统一格式
            candidates = []
            for r in results:
                score = r.score if hasattr(r, 'score') else r.get('score', 0)
                vector_id = r.vector_id if hasattr(r, 'vector_id') else r.get('vector_id', '')
                metadata = r.metadata if hasattr(r, 'metadata') else r.get('metadata', {})
                
                if score >= threshold:
                    candidates.append({
                        "vector_id": vector_id,
                        "score": score,
                        "rrf_score": score,  # 纯稠密模式下 rrf_score 等于 similarity_score
                        "metadata": metadata,
                        "search_mode": "dense_only",
                        "source_index_id": index_id
                    })
            
            logger.info(f"纯稠密检索完成: index={index_id}, 候选集={len(candidates)}")
            return candidates
            
        except Exception as e:
            logger.error(f"纯稠密检索失败 (index={index_id}): {str(e)}")
            return []

    async def _hybrid_search_in_collection(
        self,
        index_id: str,
        query_text: str,
        query_vector: np.ndarray,
        top_n: int = 20,
        rrf_k: int = 60,
        threshold: float = 0.5
    ) -> tuple:
        """
        T005: 单 Collection 混合检索
        
        封装 EmbeddingService + BM25SparseService.encode_query() → 
        MilvusProvider.hybrid_search() 的混合检索逻辑。
        
        Args:
            index_id: Collection/索引 ID
            query_text: 原始查询文本（用于 BM25 稀疏向量生成）
            query_vector: 稠密查询向量
            top_n: 候选集大小
            rrf_k: RRF 融合参数
            threshold: 相似度阈值
            
        Returns:
            (candidates, search_mode, bm25_ms):
            - candidates: 候选集列表
            - search_mode: 实际使用的检索模式
            - bm25_ms: BM25 生成耗时
        """
        bm25_start = time.time()
        sparse_vector = None
        
        try:
            # 将数据库 ID 映射为物理 Collection 名称（BM25 统计以物理 Collection 名称为 key）
            try:
                bm25_index_key = self._resolve_index_id_to_collection_name(str(index_id))
            except Exception:
                bm25_index_key = str(index_id)
            # P2 优化：使用 BM25 查询级缓存，避免同一个 bm25_key 被多个 Collection 重复调用
            cache_key = (bm25_index_key, query_text)
            bm25_cache_hit = cache_key in self._bm25_query_cache
            if bm25_cache_hit:
                sparse_vector = self._bm25_query_cache[cache_key]
                recall_debug_logger.info(
                    f"===== BM25 查询缓存命中 (index={index_id}, bm25_key={bm25_index_key}) ====="
                )
            else:
                sparse_vector = self.bm25_service.encode_query(bm25_index_key, query_text)
                self._bm25_query_cache[cache_key] = sparse_vector
            
            # 输出 BM25 查询分词与词条匹配详情到调试日志（缓存命中时跳过，避免冗余输出）
            if not bm25_cache_hit:
                try:
                    from .bm25_service import tokenize, CHINESE_STOPWORDS
                    generator = self.bm25_service.get_generator(bm25_index_key)
                    if generator:
                        raw_tokens = tokenize(query_text)
                        filtered_tokens = [t for t in raw_tokens if t.lower() not in CHINESE_STOPWORDS]
                        matched_tokens = [t for t in filtered_tokens if t in generator.vocab]
                        unmatched_tokens = [t for t in filtered_tokens if t not in generator.vocab]
                        
                        recall_debug_logger.info(f"===== BM25 查询分词详情 (index={index_id}, bm25_key={bm25_index_key}) =====")
                        recall_debug_logger.info(f"  原始查询: {query_text}")
                        recall_debug_logger.info(f"  jieba 分词结果 (过滤前): {raw_tokens}")
                        recall_debug_logger.info(f"  停用词过滤后: {filtered_tokens}")
                        recall_debug_logger.info(f"  词表匹配的词条 ({len(matched_tokens)}个): {matched_tokens}")
                        recall_debug_logger.info(f"  词表未匹配的词条 ({len(unmatched_tokens)}个): {unmatched_tokens}")
                        recall_debug_logger.info(f"  词表总大小: {len(generator.vocab)}")
                        recall_debug_logger.info(f"  词表内容 (token→id): {dict(list(generator.vocab.items())[:50])}{'...(仅展示前50个)' if len(generator.vocab) > 50 else ''}")
                        
                        if sparse_vector:
                            # 将 token_id 反向映射回 token 文本
                            id_to_token = {v: k for k, v in generator.vocab.items()}
                            sparse_detail = {id_to_token.get(tid, f"id_{tid}"): weight for tid, weight in sparse_vector.items()}
                            recall_debug_logger.info(f"  BM25 稀疏向量 ({len(sparse_vector)}个非零维度): {sparse_detail}")
                        else:
                            recall_debug_logger.info(f"  BM25 稀疏向量: 空 (无匹配词条)")
                        recall_debug_logger.info(f"===== BM25 查询分词详情结束 =====")
                except Exception as debug_e:
                    recall_debug_logger.warning(f"BM25 调试日志输出失败: {debug_e}")
                
        except Exception as e:
            logger.warning(f"BM25 稀疏向量生成失败 (index={index_id}): {str(e)}")
        
        bm25_ms = int((time.time() - bm25_start) * 1000)
        
        try:
            # 将数据库 ID 映射为 Milvus 物理 Collection 名称
            milvus_collection_name = self._resolve_index_id_to_collection_name(index_id)
            
            # 获取当前索引记录对应的 doc_id，用于 Partition Key 过滤
            # 设计理念：多个文档索引共享同一个物理 Collection（按维度拆分），
            # 检索时必须通过 doc_id 过滤限定文档范围，避免跨文档干扰。
            # 参考 Dify 架构：Partition Key 模式下通过 expr 过滤实现文档隔离。
            doc_id_filter = self._get_doc_id_for_index(index_id)
            
            results, search_mode = self.milvus_provider.hybrid_search(
                index_id=milvus_collection_name,
                dense_vector=query_vector,
                sparse_vector=sparse_vector,
                top_n=top_n,
                rrf_k=rrf_k,
                filter_expr=f'doc_id == "{doc_id_filter}"' if doc_id_filter else None
            )
            
            # 添加 source_index_id 并进行阈值过滤
            # 设计理念：hybrid 模式下 RRF score 值域（~0.01-0.03）与 cosine similarity（0-1）完全不同，
            # 不能使用 cosine similarity 的阈值进行过滤。参考 Dify/LangChain 实践：
            # 粗排阶段仅按 top_n 截取候选集，质量控制统一交由 Reranker 精排后的阈值过滤完成。
            filtered_results = []
            for r in results:
                r["source_index_id"] = index_id
            
            if search_mode == "hybrid":
                # hybrid 模式：跳过粗排阈值过滤，直接保留所有结果送入 Reranker 精排
                filtered_results = results
                logger.info(
                    f"Hybrid 模式跳过粗排阈值过滤 (index={index_id}), "
                    f"保留全部 {len(results)} 条候选送入 Reranker"
                )
            else:
                # dense_only 模式：使用 cosine similarity 阈值过滤
                for r in results:
                    if r.get("score", 0) >= threshold:
                        filtered_results.append(r)
                
                # 如果全部被过滤，降级保留原始结果（避免空结果）
                if not filtered_results and results:
                    logger.warning(
                        f"阈值过滤后无结果 (index={index_id}, threshold={threshold}), "
                        f"保留原始 {len(results)} 条结果"
                    )
                    filtered_results = results
            
            logger.info(f"混合检索完成: index={index_id}, mode={search_mode}, 候选集={len(filtered_results)}")
            return filtered_results, search_mode, bm25_ms
            
        except Exception as e:
            logger.error(f"混合检索失败 (index={index_id}): {str(e)}")
            # 降级到纯稠密
            logger.info(f"混合检索失败，降级到纯稠密: index={index_id}")
            dense_results = await self._dense_search_in_collection(
                index_id, query_vector, top_n, threshold
            )
            return dense_results, "dense_only", bm25_ms

    def _determine_search_mode(
        self,
        index_id: str,
        requested_mode: str = "auto"
    ) -> str:
        """
        T006: 检索模式自动检测和降级判断
        
        根据请求模式和 Collection 能力决定实际检索模式。
        
        Args:
            index_id: Collection/索引 ID
            requested_mode: 请求的检索模式 (auto/hybrid/dense_only)
            
        Returns:
            实际应使用的检索模式 (hybrid/dense_only)
        """
        if requested_mode == "dense_only":
            return "dense_only"
        
        # auto 或 hybrid 模式：检查 Collection 是否支持混合检索
        try:
            # 将数据库 ID 映射为物理 Collection 名称（BM25 统计以物理 Collection 名称为 key）
            try:
                bm25_index_key = self._resolve_index_id_to_collection_name(str(index_id))
            except Exception:
                bm25_index_key = str(index_id)
            
            # 检查 BM25 统计是否可用
            has_bm25 = self.bm25_service.has_stats(bm25_index_key)
            
            if not has_bm25:
                logger.info(f"BM25 统计不可用 (index={index_id}, bm25_key={bm25_index_key})，降级到 dense_only")
                return "dense_only"
            
            # 实际的稀疏字段检查由 MilvusProvider.hybrid_search 内部处理
            # 这里只做 BM25 统计可用性检查
            return "hybrid"
            
        except Exception as e:
            logger.warning(f"检索模式判断异常 (index={index_id}): {str(e)}，降级到 dense_only")
            return "dense_only"

    async def _rerank_candidates(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10,
        reranker_top_n: int = 20
    ) -> tuple:
        """
        T007: Reranker 精排封装
        
        调用 RerankerService.rerank() 对候选集进行精排，
        Reranker 不可用时跳过精排返回原始排序。
        
        Args:
            query_text: 原始查询文本
            candidates: 粗排候选集
            top_k: 最大返回数量
            reranker_top_n: 送入 Reranker 的候选集大小
            
        Returns:
            (ranked_results, reranker_available, reranker_ms):
            - ranked_results: 精排后的结果
            - reranker_available: Reranker 是否可用
            - reranker_ms: Reranker 耗时
        """
        reranker_start = time.time()
        
        # 截取 Top-N 送入 Reranker
        candidates_for_rerank = candidates[:reranker_top_n]
        
        # 为候选集准备文本字段（Reranker 需要）
        # P0 优化：为每个候选片段拼接文档级上下文（文档名称、章节标题等），
        # 帮助 Reranker 理解片段所属文档的语境，显著提升排序准确度。
        # 参考业内最佳实践：LlamaIndex MetadataReplacementPostProcessor、
        # LangChain ContextualCompressionRetriever
        for c in candidates_for_rerank:
            metadata = c.get("metadata", {}) or {}
            raw_text = (
                c.get("text") or
                metadata.get("source_text") or
                metadata.get("text") or
                metadata.get("content") or
                ""
            )
            # 拼接文档级上下文前缀：仅保留 [文档: xxx]
            # 不再拼接 [章节: xxx]，因为 section_title / heading_path 会引入 Reranker 上下文污染：
            #   - heading_path 完整路径中的关键词（如"功能"）会干扰 cross-encoder 打分，
            #     导致无关 chunk 因路径关键词匹配而分数异常升高
            #   - section_title fallback 同理，即使只有单层标题也会引入噪声
            # 注意：自然语言格式（如"以下内容来自《xxx》："）经测试会加剧关键词污染，
            # cross-encoder 会将文档名中的关键词当作正文内容参与语义匹配，
            # 方括号格式更中性，不会干扰打分。
            doc_name = metadata.get("document_name", "")
            if not doc_name and metadata.get("document_id"):
                doc_name = self._get_document_name(metadata.get("document_id")) or ""
            context_prefix = f"[文档: {doc_name}]" if doc_name else ""
            
            # 对非文本类型 chunk（table/code/image），拼接上下文信息帮助 Reranker 理解语境
            # 参考业界实践：Unstructured.io 在检索时会把元素的周边上下文拼入候选文本
            chunk_type = metadata.get("chunk_type", "text")
            if chunk_type in ("table", "code", "image"):
                ctx_before = metadata.get("context_before", "")
                ctx_after = metadata.get("context_after", "")
                if ctx_before or ctx_after:
                    context_parts = []
                    if ctx_before:
                        context_parts.append(f"[上文: {ctx_before}]")
                    context_parts.append(raw_text)
                    if ctx_after:
                        context_parts.append(f"[下文: {ctx_after}]")
                    raw_text = "\n".join(context_parts)
            elif chunk_type == "text" and len(raw_text) < 100:
                # 兜底保护：对任何类型的短文本 chunk（< 100 字符），
                # 如果 metadata 中有 context_after/context_before，自动拼接
                # 防止 Reranker 对碎片短文本给出伪高分
                ctx_before = metadata.get("context_before", "")
                ctx_after = metadata.get("context_after", "")
                if ctx_before or ctx_after:
                    context_parts = []
                    if ctx_before:
                        context_parts.append(f"[上文: {ctx_before}]")
                    context_parts.append(raw_text)
                    if ctx_after:
                        context_parts.append(f"[下文: {ctx_after}]")
                    raw_text = "\n".join(context_parts)
            
            c["text"] = f"{context_prefix}\n{raw_text}" if context_prefix else raw_text
        
        # 输出传给 Reranker 的实际文本详情（写入调试日志文件）
        recall_debug_logger.info(f"===== 送入 Reranker 的候选集详情 (共 {len(candidates_for_rerank)} 条) =====")
        for i, c in enumerate(candidates_for_rerank):
            metadata = c.get("metadata", {}) or {}
            # 候选集日志中也做同样的文档名兜底
            log_doc_name = metadata.get("document_name", "")
            if not log_doc_name and metadata.get("document_id"):
                log_doc_name = self._get_document_name(metadata.get("document_id")) or "未知"
            if not log_doc_name:
                log_doc_name = "未知"
            chunk_idx = metadata.get("chunk_index", "?")
            rrf_score = c.get("score", 0)
            text_preview = (c.get("text", "") or "")[:200]
            recall_debug_logger.info(
                f"  [候选 {i+1}] 文档={log_doc_name}, 片段={chunk_idx}, "
                f"RRF_score={rrf_score:.6f}, "
                f"传给Reranker的文本={text_preview}"
            )
        recall_debug_logger.info(f"===== 候选集详情结束 =====")
        logger.info(f"送入 Reranker 候选集共 {len(candidates_for_rerank)} 条，详情已写入 logs/search_recall_debug.log")
        
        try:
            reranker = self.reranker_service
            reranker_available = reranker.available
            
            if reranker_available:
                # [诊断] 调用前日志
                logger.info(
                    f"[诊断] _rerank_candidates 调用 reranker.rerank(): "
                    f"candidates={len(candidates_for_rerank)}, top_k={top_k}"
                )
                ranked = reranker.rerank(
                    query=query_text,
                    candidates=candidates_for_rerank,
                    top_k=top_k,
                    text_key="text"
                )
                reranker_ms = int((time.time() - reranker_start) * 1000)
                # [诊断] 调用后日志 — 如果 ranked 数量等于 top_k 而非 candidates 数量，说明 rerank 方法内部仍在截取
                logger.info(
                    f"[诊断] reranker.rerank() 返回 {len(ranked)} 条 "
                    f"(应等于 {len(candidates_for_rerank)} 条，不应等于 top_k={top_k})"
                )
                logger.info(f"Reranker 精排完成: {len(candidates_for_rerank)} → {len(ranked)}, 耗时 {reranker_ms}ms")
                return ranked, True, reranker_ms
            else:
                logger.warning("Reranker 不可用，跳过精排，按相似度分数排序")
                reranker_ms = int((time.time() - reranker_start) * 1000)
                # 降级：按 score 降序排序后截取 top_k
                fallback = sorted(
                    candidates_for_rerank,
                    key=lambda x: x.get("score", 0),
                    reverse=True
                )
                return fallback[:top_k], False, reranker_ms
                
        except Exception as e:
            logger.error(f"Reranker 精排失败: {str(e)}")
            reranker_ms = int((time.time() - reranker_start) * 1000)
            # 降级：按 score 降序排序后截取 top_k
            fallback = sorted(
                candidates_for_rerank,
                key=lambda x: x.get("score", 0),
                reverse=True
            )
            return fallback[:top_k], False, reranker_ms

    def _build_search_timing(
        self,
        query_enhancement_ms: int = 0,
        embedding_ms: int = 0,
        bm25_ms: int = 0,
        search_ms: int = 0,
        reranker_ms: int = 0
    ) -> Dict[str, int]:
        """
        T008: 构建各阶段耗时数据
        
        Args:
            query_enhancement_ms: 查询增强耗时（Query Rewrite + Multi-query）
            embedding_ms: 查询向量化耗时
            bm25_ms: BM25 稀疏向量生成耗时
            search_ms: 向量检索耗时（含 RRF）
            reranker_ms: Reranker 精排耗时
            
        Returns:
            SearchTiming 字典
        """
        return {
            "query_enhancement_ms": query_enhancement_ms,
            "embedding_ms": embedding_ms,
            "bm25_ms": bm25_ms,
            "search_ms": search_ms,
            "reranker_ms": reranker_ms,
            "total_ms": query_enhancement_ms + embedding_ms + bm25_ms + search_ms + reranker_ms
        }

    # ==================== 混合检索公开接口 (Phase 4: US2) ====================

    async def hybrid_search(
        self,
        request
    ) -> Dict[str, Any]:
        """
        T011: 混合检索公开方法
        
        编排完整的混合检索流程：
        _determine_search_mode() → _hybrid/_dense_search_in_collection() → 
        _rerank_candidates() → _build_search_timing()
        
        T029: 当 collection_ids 包含多个 ID 时分发到 _multi_collection_search()
        
        Args:
            request: HybridSearchRequest
            
        Returns:
            HybridSearchResponseData 字典
        """
        start_time = time.time()
        query_id = str(uuid.uuid4())
        
        # 验证查询文本
        query_text = self._validate_query_text(request.query_text)
        original_query_text = query_text
        
        logger.info(f"Hybrid search started: query_id={query_id}, text_length={len(query_text)}")
        
        # 每次查询开始时清空召回调试日志，只保留当前查询的信息
        _reset_recall_debug_log()
        # P2 优化：清空 BM25 查询级缓存，确保每次搜索请求独立
        self._bm25_query_cache.clear()
        recall_debug_logger.info(f"===== 新查询开始: query_id={query_id}, query='{query_text}' =====")
        
        # ============ 查询增强（Query Enhancement）============
        # 在验证查询文本之后、检索之前执行查询改写和多查询生成
        enable_enhancement = getattr(request, 'enable_query_enhancement', True)
        global_enhancement_enabled = getattr(settings, 'QUERY_ENHANCEMENT_ENABLED', True)
        enhancement_result: Optional[QueryEnhancementResult] = None
        enhancement_ms = 0
        
        if enable_enhancement and global_enhancement_enabled:
            try:
                enhancement_result = await self.query_enhancement_service.enhance_query(query_text)
                enhancement_ms = enhancement_result.enhancement_time_ms
                
                # 用改写后的查询替换原始查询（用于后续的向量嵌入和检索）
                enhanced_query_text = enhancement_result.rewritten_query
                
                recall_debug_logger.info(f"===== 查询增强结果 =====")
                recall_debug_logger.info(f"  原始查询: {query_text}")
                recall_debug_logger.info(f"  改写查询: {enhanced_query_text}")
                recall_debug_logger.info(f"  是否复杂: {enhancement_result.is_complex}")
                recall_debug_logger.info(f"  变体查询: {enhancement_result.sub_queries}")
                recall_debug_logger.info(f"  所有查询: {enhancement_result.all_queries}")
                recall_debug_logger.info(f"  增强耗时: {enhancement_ms}ms")
                if enhancement_result.error:
                    recall_debug_logger.info(f"  增强错误: {enhancement_result.error}")
                recall_debug_logger.info(f"===== 查询增强结果结束 =====")
                
                logger.info(
                    f"查询增强完成: '{query_text}' → '{enhanced_query_text}', "
                    f"is_complex={enhancement_result.is_complex}, "
                    f"sub_queries_count={len(enhancement_result.sub_queries)}, "
                    f"耗时={enhancement_ms}ms"
                )
                
                # 使用改写后的查询替换原始 query_text
                query_text = enhanced_query_text
                
            except Exception as e:
                logger.warning(f"查询增强异常，降级使用原始查询: {str(e)}")
                enhancement_result = QueryEnhancementResult(
                    original_query=query_text,
                    rewritten_query=query_text,
                    is_complex=False,
                    sub_queries=[],
                    all_queries=[query_text],
                    error=str(e)
                )
        else:
            logger.info(f"查询增强已禁用 (request={enable_enhancement}, global={global_enhancement_enabled})")
        
        try:
            # 1. 获取目标 Collection 列表
            # collection_ids 现在传入的是 collection_name（逻辑知识库名），
            # 需要映射到实际的索引记录 ID 列表
            requested_collections = request.collection_ids or []
            if requested_collections:
                collection_ids = self._resolve_collection_names_to_index_ids(requested_collections)
            else:
                # 未指定 collection，使用所有可用索引
                target_indexes = self._get_target_indexes([])
                collection_ids = [str(idx.id) for idx in target_indexes]
            
            if not collection_ids:
                return {
                    "query_id": query_id,
                    "query_text": original_query_text,
                    "search_mode": "dense_only",
                    "reranker_available": False,
                    "rrf_k": settings.RRF_K,
                    "results": [],
                    "total_count": 0,
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "timing": self._build_search_timing()
                }
            
            # 2. 按 Embedding 模型分组 Collection，各自嵌入查询文本
            # 设计理念：不同知识库可能绑定不同的 Embedding 模型，
            # 跨模型联合搜索时需按模型分组，各自使用对应模型嵌入查询文本，
            # 确保各 Collection 的检索在正确的语义空间中进行。
            model_groups = self._group_collections_by_embedding_model(collection_ids)
            
            embed_start = time.time()
            
            # 判断是否有 Multi-query（多查询变体）需要处理
            has_multi_query = (
                enhancement_result is not None 
                and enhancement_result.is_complex 
                and len(enhancement_result.sub_queries) > 0
            )
            all_search_queries = (
                enhancement_result.all_queries 
                if has_multi_query and enhancement_result 
                else [query_text]
            )
            
            if has_multi_query:
                logger.info(
                    f"Multi-query 模式: 共 {len(all_search_queries)} 个查询 "
                    f"(1 主查询 + {len(enhancement_result.sub_queries)} 变体)"
                )
                recall_debug_logger.info(
                    f"===== Multi-query 嵌入开始: {len(all_search_queries)} 个查询 ====="
                )
            
            if len(model_groups) <= 1:
                # 所有 Collection 使用相同模型（或只有一个 Collection）：单次嵌入
                search_model = next(iter(model_groups.keys())) if model_groups else None
                if search_model == "__default__":
                    search_model = None
                
                if has_multi_query:
                    # Multi-query: 并行嵌入所有查询变体
                    embed_tasks = [
                        self._embed_query(q, model_name=search_model)
                        for q in all_search_queries
                    ]
                    all_vectors = await asyncio.gather(*embed_tasks, return_exceptions=True)
                    
                    # 主查询的 collection_vectors（用于主检索路径）
                    primary_vector = all_vectors[0] if not isinstance(all_vectors[0], Exception) else None
                    if primary_vector is None:
                        raise EmbeddingServiceError("主查询向量嵌入失败")
                    collection_vectors = {cid: primary_vector for cid in collection_ids}
                    
                    # 收集所有有效的查询向量（含变体）
                    multi_query_vectors = []
                    for i, (q, v) in enumerate(zip(all_search_queries, all_vectors)):
                        if isinstance(v, Exception):
                            logger.warning(f"Multi-query 变体嵌入失败 ({i}): {q} → {str(v)}")
                            continue
                        multi_query_vectors.append((q, v))
                    
                    logger.info(
                        f"Multi-query 嵌入完成: {len(multi_query_vectors)}/{len(all_search_queries)} 成功"
                    )
                else:
                    query_vector = await self._embed_query(query_text, model_name=search_model)
                    collection_vectors = {cid: query_vector for cid in collection_ids}
                    multi_query_vectors = [(query_text, query_vector)]
                
                if search_model:
                    logger.info(f"Using embedding model '{search_model}' for query (all collections same model)")
            else:
                # 跨模型联合搜索：按模型分组并行嵌入查询文本
                # 注意：Multi-query 模式下，跨模型联合搜索仅使用主查询（rewritten_query），
                # 因为 multi-query 的变体查询在跨模型场景下嵌入开销过大，ROI 不高
                logger.info(f"跨模型联合搜索: 检测到 {len(model_groups)} 种不同 Embedding 模型，按模型分组嵌入")
                if has_multi_query:
                    logger.info("跨模型场景下 Multi-query 降级为仅使用主查询（变体查询跳过）")
                collection_vectors = await self._embed_query_per_model_group(
                    query_text=query_text,
                    model_groups=model_groups
                )
                multi_query_vectors = None  # 跨模型场景不使用 multi_query_vectors
            
            embedding_ms = int((time.time() - embed_start) * 1000)
            
            rrf_k = settings.RRF_K
            reranker_top_n = getattr(request, 'reranker_top_n', settings.RERANKER_TOP_N)
            reranker_top_k = getattr(request, 'reranker_top_k', None) or request.top_k
            search_mode_requested = getattr(request, 'search_mode', 'auto')
            if hasattr(search_mode_requested, 'value'):
                search_mode_requested = search_mode_requested.value
            
            # 3. 单/多 Collection 分发
            # Multi-query 额外参数
            _multi_query_vectors = multi_query_vectors if has_multi_query and multi_query_vectors and len(multi_query_vectors) > 1 else None
            
            if len(collection_ids) > 1:
                # T028-T029: 多 Collection 联合搜索（支持跨模型）
                result = await self._multi_collection_search(
                    collection_ids=collection_ids,
                    query_text=query_text,
                    collection_vectors=collection_vectors,
                    search_mode_requested=search_mode_requested,
                    reranker_top_n=reranker_top_n,
                    reranker_top_k=reranker_top_k,
                    rrf_k=rrf_k,
                    threshold=request.threshold,
                    query_enhancement_ms=enhancement_ms,
                    embedding_ms=embedding_ms,
                    query_id=query_id,
                    start_time=start_time,
                    original_query_text=original_query_text,
                    multi_query_vectors=_multi_query_vectors
                )
            else:
                # 单 Collection 检索
                cid = collection_ids[0]
                query_vector = collection_vectors[cid]
                actual_mode = self._determine_search_mode(cid, search_mode_requested)
                
                search_start = time.time()
                if actual_mode == "hybrid":
                    candidates, final_mode, bm25_ms = await self._hybrid_search_in_collection(
                        index_id=cid,
                        query_text=query_text,
                        query_vector=query_vector,
                        top_n=reranker_top_n,
                        rrf_k=rrf_k,
                        threshold=request.threshold
                    )
                else:
                    candidates = await self._dense_search_in_collection(
                        index_id=cid,
                        query_vector=query_vector,
                        top_n=reranker_top_n,
                        threshold=request.threshold
                    )
                    final_mode = "dense_only"
                    bm25_ms = 0
                
                # Multi-query: 对单 Collection 执行变体查询的额外检索，合并去重
                if _multi_query_vectors and len(_multi_query_vectors) > 1:
                    sub_candidates = await self._execute_multi_query_searches(
                        collection_id=cid,
                        multi_query_vectors=_multi_query_vectors[1:],  # 跳过主查询（已检索）
                        search_mode=actual_mode,
                        top_n=reranker_top_n,
                        rrf_k=rrf_k,
                        threshold=request.threshold
                    )
                    if sub_candidates:
                        before_count = len(candidates)
                        candidates = self._merge_and_deduplicate_candidates(candidates, sub_candidates)
                        logger.info(
                            f"Multi-query 合并去重 (单Collection): "
                            f"主查询 {before_count} + 变体 {len(sub_candidates)} "
                            f"→ 去重后 {len(candidates)} 条"
                        )
                        recall_debug_logger.info(
                            f"===== Multi-query 合并去重: "
                            f"主查询={before_count}, 变体={len(sub_candidates)}, "
                            f"去重后={len(candidates)} ====="
                        )
                
                search_ms = int((time.time() - search_start) * 1000)
                
                # 第 1.5 层防御：近重复内容去重（vector_id 去重后、Reranker 前）
                # 自动检测并去除不同文档间内容高度相似的 chunk（如导航栏、页脚等共用组件），
                # 无需硬编码任何规则，纯粹基于文本内容相似度。
                # 参考 Cohere（Rerank 前去重）、Google 网页去重、LangChain EnsembleRetriever 实践。
                near_dedup_threshold = getattr(settings, 'NEAR_DUPLICATE_THRESHOLD', 0.7)
                if near_dedup_threshold > 0:
                    recall_debug_logger.info(
                        f"===== 第 1.5 层防御: 近重复内容去重 (阈值={near_dedup_threshold}) ====="
                    )
                    candidates = self._deduplicate_near_duplicate_content(
                        candidates,
                        jaccard_threshold=near_dedup_threshold
                    )
                
                # 输出 Reranker 之前的粗排原始结果（写入调试日志文件）
                recall_debug_logger.info(f"===== Reranker 之前的粗排原始结果 (共 {len(candidates)} 条) =====")
                for _i, _c in enumerate(candidates):
                    _meta = _c.get("metadata", {}) or {}
                    _doc_name = _meta.get("document_name", "未知")
                    _chunk_idx = _meta.get("chunk_index", "?")
                    _rrf = _c.get("score", 0)
                    _text = (_meta.get("source_text") or _meta.get("text") or "")[:150]
                    recall_debug_logger.info(
                        f"  [粗排 {_i+1}] 文档={_doc_name}, 片段={_chunk_idx}, "
                        f"RRF_score={_rrf:.6f}, 内容={_text}"
                    )
                recall_debug_logger.info(f"===== 粗排原始结果结束 =====")
                logger.info(f"粗排原始结果共 {len(candidates)} 条，详情已写入 logs/search_recall_debug.log")
                
                # Reranker 精排
                ranked, reranker_available, reranker_ms = await self._rerank_candidates(
                    query_text=query_text,
                    candidates=candidates,
                    top_k=reranker_top_k,
                    reranker_top_n=reranker_top_n
                )
                
                # 第 2 层防御：Reranker 精排后动态阈值过滤
                # 设计理念：参考 Dify（score_threshold）、Cohere（relevance_score 过滤）等业内实践，
                # 在 Reranker 精排后通过 reranker_score 动态阈值过滤低相关性结果，
                # 避免无关文档混入最终召回结果。
                # hybrid 模式下粗排阶段已跳过阈值过滤，此处为统一的质量控制关口。
                # 动态阈值自适应不同查询的分数分布，参考 Google Vertex AI Search 实践。
                if reranker_available and ranked:
                    static_threshold = getattr(settings, 'RERANKER_SCORE_THRESHOLD', 0.4)
                    dynamic_ratio = getattr(settings, 'RERANKER_DYNAMIC_THRESHOLD_RATIO', 0.0)
                    # 方案 B：动态阈值上限 cap，防止 Top1 分数波动导致阈值过高误杀相关结果
                    # 参考 Pinecone score-based filtering 实践：阈值不应随 Top1 无限增长
                    dynamic_threshold_max = getattr(settings, 'RERANKER_DYNAMIC_THRESHOLD_MAX', 0.5)
                    # 方案 C：保底召回数，无论阈值多严格至少保留 N 条结果
                    # 参考 Dify/LangChain 实践：防止极端情况下召回集为空
                    min_results = getattr(settings, 'RERANKER_MIN_RESULTS', 3)
                    if dynamic_ratio > 0 and ranked:
                        top1_score = ranked[0].get("reranker_score", 0)
                        dynamic_threshold = top1_score * dynamic_ratio
                        # 对动态阈值施加上限 cap
                        dynamic_threshold = min(dynamic_threshold, dynamic_threshold_max)
                        reranker_threshold = max(static_threshold, dynamic_threshold)
                        logger.info(
                            f"第 2 层防御 - Reranker 动态阈值: static={static_threshold}, "
                            f"top1={top1_score:.4f} × ratio={dynamic_ratio} = {top1_score * dynamic_ratio:.4f}, "
                            f"cap={dynamic_threshold_max} → capped={dynamic_threshold:.4f}, "
                            f"final_threshold={reranker_threshold:.4f}, min_results={min_results}"
                        )
                    else:
                        reranker_threshold = static_threshold
                    before_count = len(ranked)
                    filtered_ranked = [
                        r for r in ranked
                        if r.get("reranker_score", 0) >= reranker_threshold
                    ]
                    # 保底召回：如果过滤后不足 min_results 条，则从原排序中补齐
                    if len(filtered_ranked) < min_results and len(ranked) > len(filtered_ranked):
                        shortfall = min_results - len(filtered_ranked)
                        # 从被过滤掉的结果中按分数从高到低补回
                        filtered_ids = {id(r) for r in filtered_ranked}
                        fallback_candidates = [r for r in ranked if id(r) not in filtered_ids]
                        fallback_candidates.sort(key=lambda x: x.get("reranker_score", 0), reverse=True)
                        supplemented = fallback_candidates[:shortfall]
                        filtered_ranked.extend(supplemented)
                        logger.info(
                            f"第 2 层防御 - 保底召回: 阈值过滤后仅 {len(filtered_ranked) - len(supplemented)} 条 "
                            f"< min_results={min_results}, 补回 {len(supplemented)} 条 "
                            f"(补回项最低分={supplemented[-1].get('reranker_score', 0):.4f})"
                        )
                    ranked = filtered_ranked
                    filtered_count = before_count - len(ranked)
                    if filtered_count > 0:
                        logger.info(
                            f"第 2 层防御 - Reranker 阈值过滤: {before_count} → {len(ranked)} "
                            f"(阈值={reranker_threshold:.4f}, 过滤 {filtered_count} 条低相关结果)"
                        )
                
                # 第 3 层防御：文档来源多样性/聚焦控制（Reranker 后）
                # 限制每个文档来源在最终结果中最多占 max_results_per_doc 个位置
                max_results_per_doc = getattr(settings, 'MAX_RESULTS_PER_DOC', 0)
                if max_results_per_doc > 0 and ranked:
                    doc_count = {}
                    diverse_ranked = []
                    for r in ranked:
                        metadata = r.get("metadata", {}) or {}
                        doc_name = metadata.get("document_name", "")
                        if not doc_name and metadata.get("document_id"):
                            doc_name = self._get_document_name(metadata.get("document_id")) or "unknown"
                        if not doc_name:
                            doc_name = "unknown"
                        doc_count[doc_name] = doc_count.get(doc_name, 0) + 1
                        if doc_count[doc_name] <= max_results_per_doc:
                            diverse_ranked.append(r)
                    if len(diverse_ranked) < len(ranked):
                        logger.info(
                            f"第 3 层防御 - 文档来源多样性控制: {len(ranked)} → {len(diverse_ranked)} "
                            f"(max_results_per_doc={max_results_per_doc})"
                        )
                    ranked = diverse_ranked
                
                # 最终 top_k 截取：三层防御过滤完成后，截取最终结果
                ranked = ranked[:reranker_top_k]
                
                # 获取索引名称映射
                index_names = self._get_index_names([cid])
                
                # 格式化结果
                formatted = self._format_hybrid_results(
                    ranked, final_mode, index_names
                )
                
                timing = self._build_search_timing(
                    query_enhancement_ms=enhancement_ms,
                    embedding_ms=embedding_ms,
                    bm25_ms=bm25_ms,
                    search_ms=search_ms,
                    reranker_ms=reranker_ms
                )
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                result = {
                    "query_id": query_id,
                    "query_text": enhancement_result.original_query if enhancement_result else query_text,
                    "search_mode": final_mode,
                    "reranker_available": reranker_available,
                    "rrf_k": rrf_k if final_mode == "hybrid" else None,
                    "results": formatted,
                    "total_count": len(formatted),
                    "execution_time_ms": execution_time_ms,
                    "timing": timing
                }
            
            # 4. 保存搜索历史（T026）
            # 使用 requested_collections（逻辑 Collection 名称）而非 collection_ids（数据库 ID），
            # 以便前端从历史恢复时能正确匹配 Collection 选择
            self._save_history_async(
                query_text=original_query_text,
                index_ids=requested_collections,
                config={
                    "top_k": request.top_k,
                    "threshold": request.threshold,
                    "metric_type": request.metric_type.value if hasattr(request.metric_type, 'value') else str(request.metric_type),
                    "search_mode": result.get("search_mode", "unknown"),
                    "reranker_available": result.get("reranker_available", False),
                    "reranker_top_n": reranker_top_n,
                    "rrf_k": rrf_k
                },
                result_count=result.get("total_count", 0),
                execution_time_ms=result.get("execution_time_ms", 0)
            )
            
            # 输出最终召回结果详情到调试日志文件，便于排查召回质量
            final_results = result.get("results", [])
            if final_results:
                recall_debug_logger.info(f"===== 最终召回结果详情 (共 {len(final_results)} 条) =====")
                for item in final_results:
                    text_preview = (item.get("text_content") or "")[:200]
                    if len(item.get("text_content") or "") > 200:
                        text_preview += "..."
                    recall_debug_logger.info(
                        f"  [排名 {item.get('rank')}] "
                        f"文档={item.get('source_document', '未知')}, "
                        f"Collection={item.get('source_collection', '未知')}, "
                        f"相似度={item.get('similarity_percent', 'N/A')}, "
                        f"RRF={item.get('rrf_score', 'N/A')}, "
                        f"Reranker={item.get('reranker_score', 'N/A')}, "
                        f"内容={text_preview}"
                    )
                recall_debug_logger.info("===== 召回结果详情结束 =====")
                logger.info(f"最终召回结果共 {len(final_results)} 条，详情已写入 logs/search_recall_debug.log")
            
            # 5. 附加查询增强信息到响应
            if enhancement_result:
                result["query_enhancement"] = {
                    "enabled": True,
                    "original_query": enhancement_result.original_query,
                    "rewritten_query": enhancement_result.rewritten_query,
                    "is_complex": enhancement_result.is_complex,
                    "sub_queries": enhancement_result.sub_queries,
                    "all_queries": enhancement_result.all_queries,
                    "enhancement_time_ms": enhancement_result.enhancement_time_ms,
                    "error": enhancement_result.error
                }
            else:
                result["query_enhancement"] = {
                    "enabled": False,
                    "original_query": original_query_text,
                    "rewritten_query": original_query_text,
                    "is_complex": False,
                    "sub_queries": [],
                    "all_queries": [original_query_text],
                    "enhancement_time_ms": 0,
                    "error": None
                }
            
            logger.info(
                f"Hybrid search completed: query_id={query_id}, "
                f"mode={result.get('search_mode')}, "
                f"results={result.get('total_count')}, "
                f"time={result.get('execution_time_ms')}ms"
            )
            
            return result
            
        except SearchServiceError:
            raise
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise SearchServiceError(f"混合检索失败: {str(e)}")

    # ==================== 多 Collection 联合搜索 (Phase 8: US6) ====================

    async def _embed_query_per_model_group(
        self,
        query_text: str,
        model_groups: Dict[str, List[str]]
    ) -> Dict[str, np.ndarray]:
        """
        按模型分组并行嵌入查询文本，返回 collection_id → query_vector 映射
        
        设计理念：跨模型联合搜索时，各 Collection 需要使用各自绑定的 Embedding
        模型来嵌入查询文本，确保在正确的语义空间中检索。
        
        参考业界最佳实践：
        - LlamaIndex MultiIndex: 各 Index 绑定自己的 QueryEngine，独立 embed + 检索
        - LangChain EnsembleRetriever: 各 retriever 独立运行（含各自的 embedding），
          RRF/Reranker 融合结果
        
        Args:
            query_text: 查询文本
            model_groups: {model_name: [collection_id, ...]} 分组映射
            
        Returns:
            {collection_id: query_vector} 映射
        """
        collection_vectors: Dict[str, np.ndarray] = {}
        
        # 并行为每种模型嵌入查询文本
        async def embed_for_model(model_name: str, cids: List[str]):
            actual_model = None if model_name == "__default__" else model_name
            vector = await self._embed_query(query_text, model_name=actual_model)
            return cids, vector
        
        tasks = [
            embed_for_model(model_name, cids)
            for model_name, cids in model_groups.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"按模型嵌入查询失败: {str(res)}")
                continue
            cids, vector = res
            for cid in cids:
                collection_vectors[cid] = vector
        
        logger.info(
            f"跨模型嵌入完成: {len(model_groups)} 种模型, "
            f"{len(collection_vectors)} 个 Collection 获得查询向量"
        )
        return collection_vectors

    async def _multi_collection_search(
        self,
        collection_ids: List[str],
        query_text: str,
        collection_vectors: Dict[str, np.ndarray],
        search_mode_requested: str = "auto",
        reranker_top_n: int = 20,
        reranker_top_k: int = 10,
        rrf_k: int = 60,
        threshold: float = 0.5,
        query_enhancement_ms: int = 0,
        embedding_ms: int = 0,
        query_id: str = "",
        start_time: float = 0,
        original_query_text: str = "",
        multi_query_vectors: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        T028: 多 Collection 联合搜索（支持跨模型）
        
        使用 asyncio.gather() 并行在各 Collection 执行检索，
        每个 Collection 使用各自对应的 query_vector（按绑定的 Embedding 模型嵌入），
        合并候选集后统一调用 _rerank_candidates()（Reranker 基于文本，不涉及向量，
        天然支持跨模型精排）。
        
        Args:
            collection_ids: Collection ID 列表
            query_text: 查询文本
            collection_vectors: {collection_id: query_vector} 映射
            multi_query_vectors: Multi-query 变体查询列表 [(query, vector), ...]，用于额外的变体查询检索
            其他: 搜索配置参数
            
        Returns:
            HybridSearchResponseData 字典
        """
        search_start = time.time()
        total_bm25_ms = 0
        
        # 并行在各 Collection 执行检索，每个 Collection 使用对应的 query_vector
        async def search_one(cid):
            query_vector = collection_vectors.get(cid)
            if query_vector is None:
                logger.warning(f"Collection {cid} 无对应的查询向量，跳过")
                return [], "dense_only", 0
            
            actual_mode = self._determine_search_mode(cid, search_mode_requested)
            if actual_mode == "hybrid":
                results, mode, bm25_ms = await self._hybrid_search_in_collection(
                    index_id=cid,
                    query_text=query_text,
                    query_vector=query_vector,
                    top_n=reranker_top_n,
                    rrf_k=rrf_k,
                    threshold=threshold
                )
            else:
                results = await self._dense_search_in_collection(
                    index_id=cid,
                    query_vector=query_vector,
                    top_n=reranker_top_n,
                    threshold=threshold
                )
                mode = "dense_only"
                bm25_ms = 0
            return results, mode, bm25_ms
        
        # asyncio.gather 并行
        try:
            tasks = [search_one(cid) for cid in collection_ids]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"多 Collection 并行检索失败: {str(e)}")
            results_list = []
        
        # 合并候选集
        # 第 1 层防御：每文档候选配额控制（Reranker 前）
        # 限制每个文档（index）最多贡献 max_chunks_per_doc 条候选进入合并池，
        # 防止某个无关文档的大量 chunk 稀释相关文档的占比。
        # 参考 Cohere 的 max_chunks_per_doc 参数设计。
        max_chunks_per_doc = getattr(settings, 'MAX_CHUNKS_PER_DOC', 0)
        all_candidates = []
        final_mode = "dense_only"
        for i, res in enumerate(results_list):
            if isinstance(res, Exception):
                logger.warning(f"Collection {collection_ids[i]} 检索失败: {str(res)}")
                continue
            candidates, mode, bm25_ms = res
            if mode == "hybrid":
                final_mode = "hybrid"
            total_bm25_ms = max(total_bm25_ms, bm25_ms)
            # 标注 source_collection
            for c in candidates:
                c["source_index_id"] = collection_ids[i]
            # 第 1 层防御：每文档候选配额截取（候选已按 RRF/相似度分数排序，截取前 N 条即最高分的 N 条）
            if max_chunks_per_doc > 0 and len(candidates) > max_chunks_per_doc:
                before_count = len(candidates)
                candidates = candidates[:max_chunks_per_doc]
                logger.info(
                    f"第 1 层防御 - 候选配额控制: Collection {collection_ids[i]} "
                    f"从 {before_count} 条截取为 {len(candidates)} 条 (max_chunks_per_doc={max_chunks_per_doc})"
                )
            all_candidates.extend(candidates)
        
        # Multi-query: 对各 Collection 并行执行变体查询的额外检索，合并去重
        # 设计理念：将所有 Collection × 变体查询 扁平化为并行任务，一次性 asyncio.gather 执行
        # 参考 LangChain MultiQueryRetriever 和 Qdrant batch_search 的并发策略
        if multi_query_vectors and len(multi_query_vectors) > 1:
            multi_query_tasks = [
                self._execute_multi_query_searches(
                    collection_id=cid,
                    multi_query_vectors=multi_query_vectors[1:],  # 跳过主查询
                    search_mode=self._determine_search_mode(cid, search_mode_requested),
                    top_n=reranker_top_n,
                    rrf_k=rrf_k,
                    threshold=threshold
                )
                for cid in collection_ids
            ]
            
            logger.info(
                f"Multi-query 跨Collection并行检索: {len(collection_ids)} 个Collection × "
                f"{len(multi_query_vectors) - 1} 个变体 = {len(multi_query_tasks)} 个并行任务"
            )
            
            multi_query_results = await asyncio.gather(*multi_query_tasks, return_exceptions=True)
            
            sub_query_candidates = []
            for i, result in enumerate(multi_query_results):
                if isinstance(result, Exception):
                    logger.warning(
                        f"Multi-query Collection {collection_ids[i]} 并行执行异常: {str(result)}"
                    )
                    continue
                if isinstance(result, list):
                    sub_query_candidates.extend(result)
            
            if sub_query_candidates:
                before_count = len(all_candidates)
                all_candidates = self._merge_and_deduplicate_candidates(all_candidates, sub_query_candidates)
                logger.info(
                    f"Multi-query 合并去重 (多Collection): "
                    f"主查询 {before_count} + 变体 {len(sub_query_candidates)} "
                    f"→ 去重后 {len(all_candidates)} 条"
                )
                recall_debug_logger.info(
                    f"===== Multi-query 合并去重 (多Collection): "
                    f"主查询={before_count}, 变体={len(sub_query_candidates)}, "
                    f"去重后={len(all_candidates)} ====="
                )
        
        search_ms = int((time.time() - search_start) * 1000)
        
        # 第 1.5 层防御：近重复内容去重（vector_id 去重后、Reranker 前）
        # 自动检测并去除不同文档间内容高度相似的 chunk（如导航栏、页脚等共用组件），
        # 无需硬编码任何规则，纯粹基于文本内容相似度。
        # 参考 Cohere（Rerank 前去重）、Google 网页去重、LangChain EnsembleRetriever 实践。
        near_dedup_threshold = getattr(settings, 'NEAR_DUPLICATE_THRESHOLD', 0.7)
        if near_dedup_threshold > 0:
            recall_debug_logger.info(
                f"===== 第 1.5 层防御: 近重复内容去重 - 多Collection (阈值={near_dedup_threshold}) ====="
            )
            all_candidates = self._deduplicate_near_duplicate_content(
                all_candidates,
                jaccard_threshold=near_dedup_threshold
            )
        
        # [诊断] 三层防御体系入口
        logger.info(
            f"[诊断] 多Collection搜索 - 进入三层防御体系: "
            f"candidates={len(all_candidates)}, reranker_top_k={reranker_top_k}"
        )
        
        # 统一 Reranker 精排
        ranked, reranker_available, reranker_ms = await self._rerank_candidates(
            query_text=query_text,
            candidates=all_candidates,
            top_k=reranker_top_k,
            reranker_top_n=len(all_candidates)  # 多 Collection 合并后全部送入 Reranker
        )
        
        # [诊断] Reranker 返回后的结果数量
        logger.info(
            f"[诊断] Reranker 返回: {len(ranked)} 条, reranker_available={reranker_available}"
        )
        
        # 第 2 层防御：Reranker 精排后动态阈值过滤（与单 Collection 路径保持一致）
        # 设计理念：参考 Dify（score_threshold）、Google Vertex AI Search（relevance_threshold）、
        # Pinecone（score-based filtering）等业内实践，通过 reranker_score 动态阈值过滤低相关性噪声。
        # 动态阈值自适应不同查询的分数分布，比纯静态阈值更稳健。
        if reranker_available and ranked:
            static_threshold = getattr(settings, 'RERANKER_SCORE_THRESHOLD', 0.4)
            dynamic_ratio = getattr(settings, 'RERANKER_DYNAMIC_THRESHOLD_RATIO', 0.0)
            # 方案 B：动态阈值上限 cap，防止 Top1 分数波动导致阈值过高误杀相关结果
            dynamic_threshold_max = getattr(settings, 'RERANKER_DYNAMIC_THRESHOLD_MAX', 0.5)
            # 方案 C：保底召回数，无论阈值多严格至少保留 N 条结果
            min_results = getattr(settings, 'RERANKER_MIN_RESULTS', 3)
            if dynamic_ratio > 0 and ranked:
                top1_score = ranked[0].get("reranker_score", 0)
                dynamic_threshold = top1_score * dynamic_ratio
                # 对动态阈值施加上限 cap
                dynamic_threshold = min(dynamic_threshold, dynamic_threshold_max)
                reranker_threshold = max(static_threshold, dynamic_threshold)
                logger.info(
                    f"第 2 层防御 - Reranker 动态阈值 (多Collection): static={static_threshold}, "
                    f"top1={top1_score:.4f} × ratio={dynamic_ratio} = {top1_score * dynamic_ratio:.4f}, "
                    f"cap={dynamic_threshold_max} → capped={dynamic_threshold:.4f}, "
                    f"final_threshold={reranker_threshold:.4f}, min_results={min_results}"
                )
            else:
                reranker_threshold = static_threshold
            before_count = len(ranked)
            filtered_ranked = [
                r for r in ranked
                if r.get("reranker_score", 0) >= reranker_threshold
            ]
            # 保底召回：如果过滤后不足 min_results 条，则从原排序中补齐
            if len(filtered_ranked) < min_results and len(ranked) > len(filtered_ranked):
                shortfall = min_results - len(filtered_ranked)
                filtered_ids = {id(r) for r in filtered_ranked}
                fallback_candidates = [r for r in ranked if id(r) not in filtered_ids]
                fallback_candidates.sort(key=lambda x: x.get("reranker_score", 0), reverse=True)
                supplemented = fallback_candidates[:shortfall]
                filtered_ranked.extend(supplemented)
                logger.info(
                    f"第 2 层防御 - 保底召回 (多Collection): 阈值过滤后仅 {len(filtered_ranked) - len(supplemented)} 条 "
                    f"< min_results={min_results}, 补回 {len(supplemented)} 条 "
                    f"(补回项最低分={supplemented[-1].get('reranker_score', 0):.4f})"
                )
            ranked = filtered_ranked
            filtered_count = before_count - len(ranked)
            if filtered_count > 0:
                logger.info(
                    f"第 2 层防御 - Reranker 阈值过滤 (多Collection): {before_count} → {len(ranked)} "
                    f"(阈值={reranker_threshold:.4f}, 过滤 {filtered_count} 条低相关结果)"
                )
        
        # 第 3 层防御：文档来源多样性/聚焦控制（Reranker 后）
        # 限制每个文档来源在最终结果中最多占 max_results_per_doc 个位置，
        # 防止单个文档垄断所有结果名额。
        # 参考 Cohere 官方建议和 Google Vertex AI Search 的 boost/bury 策略。
        max_results_per_doc = getattr(settings, 'MAX_RESULTS_PER_DOC', 0)
        if max_results_per_doc > 0 and ranked:
            doc_count = {}  # document_name → 已占用名额数
            diverse_ranked = []
            dropped_items = []  # 被多样性控制移除的项
            for r in ranked:
                metadata = r.get("metadata", {}) or {}
                # 使用 document_name 作为文档来源标识
                doc_name = metadata.get("document_name", "")
                if not doc_name and metadata.get("document_id"):
                    doc_name = self._get_document_name(metadata.get("document_id")) or "unknown"
                if not doc_name:
                    doc_name = "unknown"
                doc_count[doc_name] = doc_count.get(doc_name, 0) + 1
                if doc_count[doc_name] <= max_results_per_doc:
                    diverse_ranked.append(r)
                else:
                    dropped_items.append((doc_name, r.get("reranker_score", 0)))
            if dropped_items:
                logger.info(
                    f"第 3 层防御 - 文档来源多样性控制: {len(ranked)} → {len(diverse_ranked)} "
                    f"(max_results_per_doc={max_results_per_doc}, "
                    f"移除项: {[(d, f'{s:.4f}') for d, s in dropped_items]})"
                )
            ranked = diverse_ranked
        
        # 最终 top_k 截取：三层防御过滤完成后，截取最终结果
        before_topk = len(ranked)
        ranked = ranked[:reranker_top_k]
        logger.info(
            f"[诊断] 最终 top_k 截取 (多Collection): {before_topk} → {len(ranked)} "
            f"(reranker_top_k={reranker_top_k})"
        )
        
        # 获取索引名称映射
        index_names = self._get_index_names(collection_ids)
        
        # 格式化
        formatted = self._format_hybrid_results(ranked, final_mode, index_names)
        
        timing = self._build_search_timing(
            query_enhancement_ms=query_enhancement_ms,
            embedding_ms=embedding_ms,
            bm25_ms=total_bm25_ms,
            search_ms=search_ms,
            reranker_ms=reranker_ms
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "query_id": query_id,
            "query_text": original_query_text or query_text,
            "search_mode": final_mode,
            "reranker_available": reranker_available,
            "rrf_k": rrf_k if final_mode == "hybrid" else None,
            "results": formatted,
            "total_count": len(formatted),
            "execution_time_ms": execution_time_ms,
            "timing": timing
        }

    # ==================== Multi-query 辅助方法 ====================

    async def _execute_multi_query_searches(
        self,
        collection_id: str,
        multi_query_vectors: list,
        search_mode: str = "hybrid",
        top_n: int = 20,
        rrf_k: int = 60,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        对单个 Collection 并行执行多个变体查询的检索
        
        设计理念：Multi-query 中的每个变体查询通过 asyncio.gather 并行检索，
        结果汇总后与主查询的候选集合并去重，统一送入 Reranker 精排。
        参考 LangChain MultiQueryRetriever 和 LlamaIndex SubQuestionQueryEngine 的并发实践。
        
        Args:
            collection_id: Collection ID
            multi_query_vectors: 变体查询列表 [(query_text, query_vector), ...]
            search_mode: 检索模式
            top_n: 每个变体查询的候选集大小
            rrf_k: RRF 融合参数
            threshold: 相似度阈值
            
        Returns:
            所有变体查询的候选集合并
        """
        
        async def _search_one_variant(q_text: str, q_vector, variant_idx: int) -> List[Dict[str, Any]]:
            """执行单个变体查询的检索（用于并行调度）"""
            try:
                if search_mode == "hybrid":
                    candidates, _, _ = await self._hybrid_search_in_collection(
                        index_id=collection_id,
                        query_text=q_text,
                        query_vector=q_vector,
                        top_n=top_n,
                        rrf_k=rrf_k,
                        threshold=threshold
                    )
                else:
                    candidates = await self._dense_search_in_collection(
                        index_id=collection_id,
                        query_vector=q_vector,
                        top_n=top_n,
                        threshold=threshold
                    )
                
                # 标注来源
                for c in candidates:
                    c["source_index_id"] = collection_id
                    c["source_query"] = q_text  # 记录来自哪个变体查询
                
                recall_debug_logger.info(
                    f"  Multi-query 变体检索 (并行): collection={collection_id}, "
                    f"variant={variant_idx}, query='{q_text}', 候选集={len(candidates)}"
                )
                return candidates
                
            except Exception as e:
                logger.warning(
                    f"Multi-query 变体检索失败: collection={collection_id}, "
                    f"variant={variant_idx}, query='{q_text}', error={str(e)}"
                )
                return []
        
        # 构建并行任务
        tasks = [
            _search_one_variant(q_text, q_vector, i)
            for i, (q_text, q_vector) in enumerate(multi_query_vectors)
        ]
        
        logger.info(
            f"Multi-query 并行检索开始: collection={collection_id}, "
            f"变体数={len(tasks)}"
        )
        
        # 并行执行所有变体查询
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集所有成功的结果
        all_sub_candidates = []
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Multi-query 变体 {i} 并行执行异常: {str(result)}"
                )
                continue
            if isinstance(result, list):
                all_sub_candidates.extend(result)
                success_count += 1
        
        logger.info(
            f"Multi-query 并行检索完成: collection={collection_id}, "
            f"成功={success_count}/{len(tasks)}, "
            f"候选总数={len(all_sub_candidates)}"
        )
        
        return all_sub_candidates

    def _merge_and_deduplicate_candidates(
        self,
        primary_candidates: List[Dict[str, Any]],
        sub_candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并并去重主查询和变体查询的候选集
        
        去重策略：按 vector_id 去重，保留分数更高的版本。
        主查询结果优先级高于变体查询。
        
        参考业界实践：
        - LangChain MultiQueryRetriever: unique_union 去重
        - Cohere: 按 document_id 去重，保留最高分
        
        Args:
            primary_candidates: 主查询候选集
            sub_candidates: 变体查询候选集
            
        Returns:
            去重后的合并候选集
        """
        # 以 vector_id 为 key 去重，主查询优先
        seen = {}  # vector_id → candidate
        
        # 先加入主查询结果（优先级高）
        for c in primary_candidates:
            vid = c.get("vector_id", "")
            if vid:
                seen[vid] = c
            else:
                # 无 vector_id 的结果直接保留
                seen[f"__no_vid_{id(c)}"] = c
        
        # 再加入变体查询结果（仅新增的）
        new_count = 0
        for c in sub_candidates:
            vid = c.get("vector_id", "")
            if vid and vid not in seen:
                seen[vid] = c
                new_count += 1
            elif vid and vid in seen:
                # 已存在，保留分数更高的
                existing_score = seen[vid].get("score", 0)
                new_score = c.get("score", 0)
                if new_score > existing_score:
                    seen[vid] = c
        
        if new_count > 0:
            recall_debug_logger.info(
                f"  Multi-query 去重: 变体查询新增 {new_count} 条不重复候选"
            )
        
        return list(seen.values())

    def _deduplicate_near_duplicate_content(
        self,
        candidates: List[Dict[str, Any]],
        jaccard_threshold: float = 0.7,
        ngram_size: int = 3,
        cross_doc_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        通用近重复内容去重（无需硬编码任何规则）
        
        设计理念：
        参考 Cohere 官方建议（Rerank 前去重提升效果）、
        Google 网页去重（SimHash/MinHash）、
        LangChain EnsembleRetriever（unique_union）的实践。
        
        本方法采用两层去重策略：
        Layer 1 - 精确哈希去重：SHA256 完全匹配（O(n)）
        Layer 2 - N-gram Jaccard 近重复去重：字符级 n-gram 相似度（O(n²)）
        
        两层策略互补：
        - 精确哈希：快速消除完全相同的内容（如模板化的页脚、免责声明）
        - Jaccard：捕获"几乎一样但有微小差异"的内容（如不同页面的导航栏，
          可能有"（当前页）"等细微差别）
        
        性能分析：
        - 50 条候选: ~1ms
        - 128 条候选: ~5ms
        - 500 条候选: ~20ms
        相比 Reranker 的 100-300ms 可忽略不计。
        若未来候选集超过 500 条，可考虑引入 MinHash（datasketch 库）替代 Jaccard。
        
        Args:
            candidates: 去重前的候选集（已完成 vector_id 去重）
            jaccard_threshold: Jaccard 相似度阈值，超过则判定为近重复。
                - 0.7: 中等严格度（推荐，适合共用组件去重）
                - 0.85: 高严格度（几乎完全一样才去重）
                - 0.5: 低严格度（较激进的去重）
            ngram_size: 字符级 n-gram 的大小（默认 3，即 trigram）
            cross_doc_only: 是否仅跨文档去重。
                - True: 只在不同 document_name 之间做去重（推荐）
                  同一文档内的多个 chunk 即使相似也保留，因为它们
                  可能是同一章节的连续段落（有 overlap）。
                - False: 不区分文档来源，全局去重
                
        Returns:
            去重后的候选集（保留分数最高的版本）
        """
        if len(candidates) <= 1:
            return candidates
        
        original_count = len(candidates)
        dedup_start = time.time()
        
        # 文档名缓存：避免通过 document_id 重复查数据库
        _doc_name_cache = {}
        def _resolve_doc_name(meta: dict) -> str:
            """从 metadata 中解析文档名，优先 document_name 字段，fallback 通过 document_id 查数据库（带缓存）"""
            name = meta.get("document_name", "")
            if name:
                return name
            doc_id = meta.get("document_id")
            if not doc_id:
                return ""
            if doc_id not in _doc_name_cache:
                _doc_name_cache[doc_id] = self._get_document_name(doc_id) or ""
            return _doc_name_cache[doc_id]
        
        # ======== 诊断日志：打印前3个候选的数据结构 ========
        recall_debug_logger.info(
            f"  [去重诊断] 候选总数={original_count}, jaccard_threshold={jaccard_threshold}, "
            f"ngram_size={ngram_size}, cross_doc_only={cross_doc_only}"
        )
        for diag_i in range(min(3, len(candidates))):
            diag_c = candidates[diag_i]
            diag_meta = diag_c.get("metadata", {}) or {}
            diag_source_text = diag_meta.get("source_text", None)
            diag_text = diag_meta.get("text", None)
            diag_content = diag_meta.get("content", None)
            diag_top_text = diag_c.get("text", None)
            recall_debug_logger.info(
                f"  [去重诊断] 候选[{diag_i}] metadata_keys={list(diag_meta.keys())} | "
                f"meta.source_text: {'None' if diag_source_text is None else f'len={len(diag_source_text)}'} | "
                f"meta.text: {'None' if diag_text is None else f'len={len(diag_text)}'} | "
                f"meta.content: {'None' if diag_content is None else f'len={len(diag_content)}'} | "
                f"c['text']: {'None' if diag_top_text is None else f'len={len(diag_top_text)}'} | "
                f"doc_name={_resolve_doc_name(diag_meta) or '?'} | "
                f"chunk_index={diag_meta.get('chunk_index', '?')} | "
                f"score={diag_c.get('score', 0):.6f}"
            )
            # 打印实际文本内容的前100字符
            actual_text = diag_source_text or diag_text or diag_content or ""
            recall_debug_logger.info(
                f"  [去重诊断] 候选[{diag_i}] 实际获取到的text(前100字符): [{actual_text[:100]}]"
            )
        
        # ======== Layer 1: 精确哈希去重 ========
        # 利用 SHA256 哈希，快速消除完全相同的内容
        hash_seen = {}  # content_hash → (index, score, doc_name)
        exact_dup_indices = set()
        
        # 统计文本获取情况
        _empty_text_count = 0
        _nonempty_text_count = 0
        
        for i, c in enumerate(candidates):
            meta = c.get("metadata", {}) or {}
            text = meta.get("source_text") or meta.get("text") or ""
            if not text.strip():
                _empty_text_count += 1
                continue
            _nonempty_text_count += 1
                
            # 计算文本内容的哈希
            content_hash = hashlib.sha256(text.strip().encode('utf-8')).hexdigest()
            score = c.get("score", 0)
            doc_name = _resolve_doc_name(meta)
            
            if content_hash in hash_seen:
                prev_idx, prev_score, prev_doc = hash_seen[content_hash]
                # 跨文档检查：同一文档内的相同内容不去重
                if cross_doc_only and doc_name == prev_doc:
                    continue
                # 保留分数更高的
                if score > prev_score:
                    exact_dup_indices.add(prev_idx)
                    hash_seen[content_hash] = (i, score, doc_name)
                else:
                    exact_dup_indices.add(i)
            else:
                hash_seen[content_hash] = (i, score, doc_name)
        
        # 诊断日志：统计文本获取情况
        recall_debug_logger.info(
            f"  [去重诊断] Layer1 文本获取统计: "
            f"非空text={_nonempty_text_count}, 空text={_empty_text_count}, "
            f"总候选={original_count}, 精确重复对={len(exact_dup_indices)}"
        )
        
        # 移除精确重复
        exact_dup_count = len(exact_dup_indices)
        if exact_dup_count > 0:
            candidates = [c for i, c in enumerate(candidates) if i not in exact_dup_indices]
            recall_debug_logger.info(
                f"  [近重复去重] Layer1 精确哈希去重: 移除 {exact_dup_count} 条完全相同的跨文档内容"
            )
        
        # ======== Layer 2: N-gram Jaccard 近重复去重 ========
        def get_ngram_set(text: str, n: int) -> set:
            """提取字符级 n-gram 集合"""
            text = text.strip()
            if len(text) < n:
                return {text} if text else set()
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        # 预计算所有候选的 n-gram 集合和文档名
        ngram_sets = []
        doc_names = []
        for c in candidates:
            meta = c.get("metadata", {}) or {}
            text = meta.get("source_text") or meta.get("text") or ""
            ngram_sets.append(get_ngram_set(text, ngram_size))
            doc_names.append(_resolve_doc_name(meta))
        
        # 按分数降序排列索引（贪心策略：优先保留高分候选）
        sorted_indices = sorted(
            range(len(candidates)),
            key=lambda i: candidates[i].get("score", 0),
            reverse=True
        )
        
        kept = []  # 保留的 (index, ngram_set, doc_name)
        near_dup_count = 0
        
        # 诊断日志：统计 Layer2 的空ngram数量
        _empty_ngram_count = sum(1 for ns in ngram_sets if not ns)
        _nonempty_ngram_count = len(ngram_sets) - _empty_ngram_count
        recall_debug_logger.info(
            f"  [去重诊断] Layer2 ngram统计: "
            f"非空ngram={_nonempty_ngram_count}, 空ngram={_empty_ngram_count}"
        )
        
        # 诊断日志：采样打印前5对跨文档候选的Jaccard比较结果
        _diag_cross_doc_comparisons = 0
        _diag_max_comparisons = 5
        
        for idx in sorted_indices:
            current_ngrams = ngram_sets[idx]
            current_doc = doc_names[idx]
            
            # 空文本直接保留
            if not current_ngrams:
                kept.append((idx, current_ngrams, current_doc))
                continue
            
            is_near_dup = False
            for kept_idx, kept_ngrams, kept_doc in kept:
                # 跨文档检查：同一文档的 chunk 不做近重复去重
                if cross_doc_only and current_doc == kept_doc:
                    continue
                
                # 空集跳过
                if not kept_ngrams:
                    continue
                
                # 计算 Jaccard 相似度
                intersection = len(current_ngrams & kept_ngrams)
                union = len(current_ngrams | kept_ngrams)
                
                jaccard_sim = intersection / union if union > 0 else 0.0
                
                # 诊断日志：打印前N对跨文档比较的Jaccard值（无论是否命中）
                if _diag_cross_doc_comparisons < _diag_max_comparisons:
                    _diag_cross_doc_comparisons += 1
                    c_meta = candidates[idx].get("metadata", {}) or {}
                    k_meta = candidates[kept_idx].get("metadata", {}) or {}
                    c_text = (c_meta.get("source_text") or c_meta.get("text") or "")[:80]
                    k_text = (k_meta.get("source_text") or k_meta.get("text") or "")[:80]
                    recall_debug_logger.info(
                        f"  [去重诊断] 跨文档Jaccard采样[{_diag_cross_doc_comparisons}]: "
                        f"Jaccard={jaccard_sim:.4f} (阈值={jaccard_threshold}) | "
                        f"ngram_size_A={len(current_ngrams)}, ngram_size_B={len(kept_ngrams)} | "
                        f"A: doc={c_meta.get('document_name', '?')}, chunk={c_meta.get('chunk_index', '?')}, text=[{c_text}] | "
                        f"B: doc={k_meta.get('document_name', '?')}, chunk={k_meta.get('chunk_index', '?')}, text=[{k_text}]"
                    )
                
                if jaccard_sim >= jaccard_threshold:
                    is_near_dup = True
                    near_dup_count += 1
                    # 调试日志：记录被去重的具体内容
                    current_meta = candidates[idx].get("metadata", {}) or {}
                    kept_meta = candidates[kept_idx].get("metadata", {}) or {}
                    recall_debug_logger.info(
                        f"    [近重复命中] Jaccard={intersection / union:.3f} >= {jaccard_threshold} | "
                        f"移除: 文档={current_meta.get('document_name', '?')}, "
                        f"片段={current_meta.get('chunk_index', '?')}, "
                        f"score={candidates[idx].get('score', 0):.6f} | "
                        f"保留: 文档={kept_meta.get('document_name', '?')}, "
                        f"片段={kept_meta.get('chunk_index', '?')}, "
                        f"score={candidates[kept_idx].get('score', 0):.6f}"
                    )
                    break
            
            if not is_near_dup:
                kept.append((idx, current_ngrams, current_doc))
        
        if near_dup_count > 0:
            recall_debug_logger.info(
                f"  [近重复去重] Layer2 N-gram Jaccard 近重复去重: 移除 {near_dup_count} 条近似重复 "
                f"(阈值={jaccard_threshold}, ngram={ngram_size}, cross_doc_only={cross_doc_only})"
            )
        
        # 按原始分数降序排列结果
        result = [candidates[idx] for idx, _, _ in kept]
        
        total_removed = exact_dup_count + near_dup_count
        dedup_ms = int((time.time() - dedup_start) * 1000)
        
        if total_removed > 0:
            logger.info(
                f"近重复内容去重: {original_count} → {len(result)} "
                f"(精确去重 {exact_dup_count} + 近似去重 {near_dup_count}, 耗时 {dedup_ms}ms)"
            )
            recall_debug_logger.info(
                f"===== 近重复内容去重完成: "
                f"原始={original_count}, "
                f"精确去重={exact_dup_count}, "
                f"近似去重={near_dup_count}, "
                f"最终={len(result)}, "
                f"耗时={dedup_ms}ms ====="
            )
        else:
            recall_debug_logger.info(
                f"===== 近重复内容去重: 未发现近重复内容 "
                f"(候选={original_count}, 阈值={jaccard_threshold}, 耗时={dedup_ms}ms) ====="
            )
        
        return result

    # ==================== Collection 管理 ====================

    def _resolve_collection_names_to_index_ids(self, collection_names: List[str]) -> List[str]:
        """
        将逻辑 Collection 名称列表解析为对应的索引记录 ID 列表
        
        用户在前端选择的 Collection 是逻辑知识库名（如 default_kb_qwen3_embedding_8b），
        需要映射到该 Collection 下所有 READY 状态的 VectorIndex 记录 ID。
        
        设计理念：一个知识库对应一种 Embedding 模型，同一逻辑 Collection 下
        所有索引的 source_model 和 dimension 天然一致，无需额外过滤。
        
        Args:
            collection_names: 逻辑 Collection 名称列表
            
        Returns:
            索引记录 ID 列表（字符串）
        """
        from ..vector_config import DEFAULT_COLLECTION_NAME
        
        try:
            indexes = self.db.query(VectorIndex).filter(
                VectorIndex.collection_name.in_(collection_names),
                VectorIndex.status == IndexStatus.READY
            ).all()
            
            if not indexes:
                # 兼容旧数据：collection_names 可能是数字 ID（旧前端传入的索引 ID）
                try:
                    numeric_ids = [int(n) for n in collection_names if n.isdigit()]
                    if numeric_ids:
                        indexes = self.db.query(VectorIndex).filter(
                            VectorIndex.id.in_(numeric_ids),
                            VectorIndex.status == IndexStatus.READY
                        ).all()
                except (ValueError, TypeError):
                    pass
            
            return [str(idx.id) for idx in indexes]
        except Exception as e:
            logger.error(f"Failed to resolve collection names to index IDs: {str(e)}")
            return []

    def _resolve_embedding_model_for_collections(self, collection_ids: List[str]) -> Optional[str]:
        """
        根据目标索引 ID 列表，解析知识库绑定的嵌入模型（返回第一个模型，
        用于单 Collection 场景或所有 Collection 使用相同模型的场景）
        
        Args:
            collection_ids: 索引记录 ID 列表（数据库自增 ID 字符串）
            
        Returns:
            嵌入模型名称，如 "qwen3-embedding-8b"，解析失败返回 None
        """
        model_groups = self._group_collections_by_embedding_model(collection_ids)
        if not model_groups:
            return None
        # 返回第一个模型（兼容单 Collection 场景）
        return next(iter(model_groups.keys()))

    def _group_collections_by_embedding_model(self, collection_ids: List[str]) -> Dict[str, List[str]]:
        """
        按 Embedding 模型对 Collection 进行分组
        
        设计理念：不同知识库可能绑定不同的 Embedding 模型（如 qwen3-embedding-8b、bge-m3）。
        跨模型联合搜索时，需要按模型分组，各自使用对应模型嵌入查询文本，
        确保各 Collection 的检索在正确的语义空间中进行。
        
        参考业界最佳实践：
        - LlamaIndex MultiIndex: 各 Index 绑定自己的 QueryEngine，独立 embed
        - LangChain EnsembleRetriever: 各 retriever 独立运行（含各自的 embedding）
        
        Args:
            collection_ids: 索引记录 ID 列表（数据库自增 ID 字符串）
            
        Returns:
            {model_name: [index_id, ...]} 分组映射，
            模型未知的索引归入 "__default__" 组
        """
        try:
            ids = [int(id) for id in collection_ids if str(id).isdigit()]
            if not ids:
                return {}
            
            indexes = self.db.query(VectorIndex).filter(
                VectorIndex.id.in_(ids),
                VectorIndex.status == IndexStatus.READY
            ).all()
            
            model_groups: Dict[str, List[str]] = {}
            for idx in indexes:
                model_name = idx.source_model or "__default__"
                if model_name not in model_groups:
                    model_groups[model_name] = []
                model_groups[model_name].append(str(idx.id))
            
            if len(model_groups) > 1:
                models_info = {m: len(ids) for m, ids in model_groups.items()}
                logger.info(f"多 Collection 跨模型分组: {models_info}")
            elif model_groups:
                model_name = next(iter(model_groups.keys()))
                logger.info(
                    f"Resolved embedding model for search: {model_name} "
                    f"(all {len(ids)} collections use same model)"
                )
            
            return model_groups
        except Exception as e:
            logger.warning(f"Failed to group collections by embedding model: {str(e)}")
            return {}

    def get_available_collections(self) -> List[Dict[str, Any]]:
        """
        T014: 获取可用 Collection 列表（含 has_sparse 标识）
        
        按 collection_name 聚合 VectorIndex 记录，返回逻辑 Collection 级别数据，
        而非单个文档/索引记录。参考 Dify 架构：对外暴露逻辑知识库名，底层按维度
        拆分物理 Collection。
        
        Returns:
            CollectionInfo 字典列表
        """
        from sqlalchemy import func
        from ..vector_config import DEFAULT_COLLECTION_NAME
        
        try:
            # 查询所有 READY 状态的索引记录
            indexes = self.db.query(VectorIndex).filter(
                VectorIndex.status == IndexStatus.READY
            ).all()
            
            if not indexes:
                return []
            
            # 按 collection_name 聚合（逻辑 Collection 级别）
            collection_map = {}  # {collection_name: {aggregated_info}}
            for index in indexes:
                coll_name = index.collection_name or DEFAULT_COLLECTION_NAME
                
                if coll_name not in collection_map:
                    collection_map[coll_name] = {
                        "index_ids": [],           # 该 Collection 下所有索引记录 ID
                        "provider": index.index_type.value if index.index_type else "unknown",
                        "vector_count": 0,
                        "dimensions": set(),
                        "metric_types": set(),
                        "embedding_models": set(),  # 该 Collection 绑定的嵌入模型集合
                        "has_sparse": False,
                        "document_count": 0,
                        "created_at": index.created_at,
                    }
                
                info = collection_map[coll_name]
                info["index_ids"].append(str(index.id))
                info["vector_count"] += (index.vector_count or 0)
                info["document_count"] += 1
                if index.dimension:
                    info["dimensions"].add(index.dimension)
                if index.metric_type:
                    info["metric_types"].add(index.metric_type)
                if index.source_model:
                    info["embedding_models"].add(index.source_model)
                if index.has_sparse:
                    info["has_sparse"] = True
                # 取最新的 created_at
                if index.created_at and (info["created_at"] is None or index.created_at > info["created_at"]):
                    info["created_at"] = index.created_at
            
            # 额外检查 BM25 统计可用性（检查该 Collection 下任一索引是否有 BM25 stats）
            for coll_name, info in collection_map.items():
                if not info["has_sparse"]:
                    for idx_id in info["index_ids"]:
                        try:
                            if self.bm25_service.has_stats(idx_id):
                                info["has_sparse"] = True
                                break
                        except Exception:
                            pass
            
            # 构建返回列表
            collections = []
            for coll_name, info in collection_map.items():
                # 取主要维度（最常见的）
                dimensions = sorted(info["dimensions"]) if info["dimensions"] else [0]
                primary_dimension = dimensions[0]
                
                # 取主要度量类型
                metric_types = list(info["metric_types"])
                primary_metric = metric_types[0] if metric_types else "cosine"
                
                # 取绑定的嵌入模型（一个知识库应该只有一种模型）
                embedding_models = list(info["embedding_models"])
                primary_model = embedding_models[0] if embedding_models else None
                
                collections.append({
                    "id": coll_name,  # 使用 collection_name 作为 ID
                    "name": coll_name,
                    "provider": info["provider"],
                    "vector_count": info["vector_count"],
                    "dimension": primary_dimension,
                    "metric_type": primary_metric,
                    "embedding_model": primary_model,  # 知识库绑定的嵌入模型
                    "has_sparse": info["has_sparse"],
                    "document_count": info["document_count"],
                    "created_at": info["created_at"].isoformat() if info["created_at"] else None
                })
            
            # 按 vector_count 降序排列
            collections.sort(key=lambda x: x["vector_count"], reverse=True)
            
            return collections
        except Exception as e:
            logger.error(f"Failed to get available collections: {str(e)}")
            return []

    def _get_index_names(self, index_ids: List[str]) -> Dict[str, str]:
        """获取索引 ID → 显示名称映射
        
        优先使用 collection_name（逻辑知识库名），其次 source_document_name，
        最后回退到 index_name。
        """
        try:
            ids = [int(id) for id in index_ids if str(id).isdigit()]
            indexes = self.db.query(VectorIndex).filter(
                VectorIndex.id.in_(ids)
            ).all()
            result = {}
            for idx in indexes:
                # 优先显示逻辑知识库名（用户可读），其次文档名，最后回退到 index_name
                display_name = idx.collection_name or idx.source_document_name or idx.index_name
                result[str(idx.id)] = display_name
            return result
        except Exception:
            return {}

    def _format_hybrid_results(
        self,
        results: List[Dict[str, Any]],
        search_mode: str,
        index_names: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        格式化混合检索结果为 HybridSearchResultItem 格式
        """
        formatted = []
        for rank, result in enumerate(results, start=1):
            metadata = result.get("metadata", {}) or {}
            
            # 获取文本内容
            text_content = (
                metadata.get("source_text") or
                metadata.get("text") or
                metadata.get("content") or
                ""
            )
            
            # 获取文档名称
            source_document = (
                metadata.get("document_name") or
                metadata.get("source") or
                metadata.get("filename") or
                "未知文档"
            )
            
            if source_document == "未知文档" and metadata.get("document_id"):
                doc_name = self._get_document_name(metadata.get("document_id"))
                if doc_name:
                    source_document = doc_name
            
            # 获取片段位置
            chunk_position = (
                metadata.get("chunk_index") or
                metadata.get("position") or
                metadata.get("index")
            )
            
            # 生成摘要
            text_summary = self._generate_summary(text_content, max_length=200)
            
            # 相似度分数和百分比
            # 设计理念：hybrid 模式下 score 字段存储的是 RRF score（值域 ~0.01-0.03），
            # 不能直接当作余弦相似度展示。如果有 reranker_score 则优先使用，更有参考意义。
            score = result.get("score", 0)
            reranker_score = result.get("reranker_score")
            item_mode_for_display = result.get("search_mode", search_mode)
            if reranker_score is not None and item_mode_for_display == "hybrid":
                similarity_percent = f"{reranker_score * 100:.1f}%"
            else:
                similarity_percent = f"{score * 100:.1f}%"
            
            # 来源 Collection
            source_id = str(result.get("source_index_id", ""))
            source_collection = index_names.get(source_id, source_id)
            
            # 结果项的 search_mode
            item_mode = result.get("search_mode", search_mode)
            
            formatted.append({
                "id": str(uuid.uuid4()),
                "chunk_id": str(result.get("vector_id", "")),
                "text_content": text_content,
                "text_summary": text_summary,
                "similarity_score": score,
                "similarity_percent": similarity_percent,
                "rrf_score": result.get("rrf_score"),
                "reranker_score": result.get("reranker_score"),
                "search_mode": item_mode,
                "source_collection": source_collection,
                "source_document": source_document,
                "chunk_position": chunk_position,
                "metadata": metadata,
                "rank": rank
            })
        
        return formatted
