"""
搜索查询服务

提供语义搜索、历史记录管理等核心功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import uuid
import asyncio
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
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger("search_service")

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
        self._vector_index_service = None
        logger.info("SearchService initialized")
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """获取 Embedding 服务实例（延迟初始化）"""
        if self._embedding_service is None:
            api_key = settings.EMBEDDING_API_KEY
            base_url = settings.EMBEDDING_API_BASE_URL
            model = settings.EMBEDDING_DEFAULT_MODEL
            
            if not api_key or not base_url:
                raise EmbeddingServiceError("Embedding API 配置缺失")
            
            self._embedding_service = EmbeddingService(
                api_key=api_key,
                model=model,
                base_url=base_url,
                max_retries=settings.EMBEDDING_MAX_RETRIES,
                request_timeout=settings.EMBEDDING_TIMEOUT
            )
        return self._embedding_service
    
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
    
    async def _embed_query(self, query_text: str) -> np.ndarray:
        """将查询文本转换为向量"""
        try:
            # 使用同步方法，在线程池中执行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.embedding_service.embed_query,
                query_text
            )
            return np.array(result.vector)
        except Exception as e:
            logger.error(f"Embedding failed: {str(e)}")
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
            sparse_vector = self.bm25_service.encode_query(str(index_id), query_text)
        except Exception as e:
            logger.warning(f"BM25 稀疏向量生成失败 (index={index_id}): {str(e)}")
        
        bm25_ms = int((time.time() - bm25_start) * 1000)
        
        try:
            # 将数据库 ID 映射为 Milvus 物理 Collection 名称
            milvus_collection_name = self._resolve_index_id_to_collection_name(index_id)
            
            results, search_mode = self.milvus_provider.hybrid_search(
                index_id=milvus_collection_name,
                dense_vector=query_vector,
                sparse_vector=sparse_vector,
                top_n=top_n,
                rrf_k=rrf_k
            )
            
            # 添加 source_index_id 到结果
            for r in results:
                r["source_index_id"] = index_id
                if r.get("score", 0) < threshold and r.get("rrf_score", 0) < threshold:
                    continue  # 阈值过滤在后续统一处理
            
            logger.info(f"混合检索完成: index={index_id}, mode={search_mode}, 候选集={len(results)}")
            return results, search_mode, bm25_ms
            
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
            # 检查 BM25 统计是否可用
            has_bm25 = self.bm25_service.has_stats(str(index_id))
            
            if not has_bm25:
                logger.info(f"BM25 统计不可用 (index={index_id})，降级到 dense_only")
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
            top_k: 最终返回数量
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
        for c in candidates_for_rerank:
            if "text" not in c:
                metadata = c.get("metadata", {}) or {}
                c["text"] = (
                    metadata.get("source_text") or
                    metadata.get("text") or
                    metadata.get("content") or
                    ""
                )
        
        try:
            reranker = self.reranker_service
            reranker_available = reranker.available
            
            if reranker_available:
                ranked = reranker.rerank(
                    query=query_text,
                    candidates=candidates_for_rerank,
                    top_k=top_k,
                    text_key="text"
                )
                reranker_ms = int((time.time() - reranker_start) * 1000)
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
        embedding_ms: int = 0,
        bm25_ms: int = 0,
        search_ms: int = 0,
        reranker_ms: int = 0
    ) -> Dict[str, int]:
        """
        T008: 构建各阶段耗时数据
        
        Args:
            embedding_ms: 查询向量化耗时
            bm25_ms: BM25 稀疏向量生成耗时
            search_ms: 向量检索耗时（含 RRF）
            reranker_ms: Reranker 精排耗时
            
        Returns:
            SearchTiming 字典
        """
        return {
            "embedding_ms": embedding_ms,
            "bm25_ms": bm25_ms,
            "search_ms": search_ms,
            "reranker_ms": reranker_ms,
            "total_ms": embedding_ms + bm25_ms + search_ms + reranker_ms
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
        
        logger.info(f"Hybrid search started: query_id={query_id}, text_length={len(query_text)}")
        
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
                    "query_text": query_text,
                    "search_mode": "dense_only",
                    "reranker_available": False,
                    "rrf_k": settings.RRF_K,
                    "results": [],
                    "total_count": 0,
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "timing": self._build_search_timing()
                }
            
            # 2. 生成稠密查询向量
            embed_start = time.time()
            query_vector = await self._embed_query(query_text)
            embedding_ms = int((time.time() - embed_start) * 1000)
            
            rrf_k = settings.RRF_K
            reranker_top_n = getattr(request, 'reranker_top_n', settings.RERANKER_TOP_N)
            reranker_top_k = getattr(request, 'reranker_top_k', None) or request.top_k
            search_mode_requested = getattr(request, 'search_mode', 'auto')
            if hasattr(search_mode_requested, 'value'):
                search_mode_requested = search_mode_requested.value
            
            # 3. 单/多 Collection 分发
            if len(collection_ids) > 1:
                # T028-T029: 多 Collection 联合搜索
                result = await self._multi_collection_search(
                    collection_ids=collection_ids,
                    query_text=query_text,
                    query_vector=query_vector,
                    search_mode_requested=search_mode_requested,
                    reranker_top_n=reranker_top_n,
                    reranker_top_k=reranker_top_k,
                    rrf_k=rrf_k,
                    threshold=request.threshold,
                    embedding_ms=embedding_ms,
                    query_id=query_id,
                    start_time=start_time
                )
            else:
                # 单 Collection 检索
                cid = collection_ids[0]
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
                
                search_ms = int((time.time() - search_start) * 1000)
                
                # Reranker 精排
                ranked, reranker_available, reranker_ms = await self._rerank_candidates(
                    query_text=query_text,
                    candidates=candidates,
                    top_k=reranker_top_k,
                    reranker_top_n=reranker_top_n
                )
                
                # 获取索引名称映射
                index_names = self._get_index_names([cid])
                
                # 格式化结果
                formatted = self._format_hybrid_results(
                    ranked, final_mode, index_names
                )
                
                timing = self._build_search_timing(
                    embedding_ms=embedding_ms,
                    bm25_ms=bm25_ms,
                    search_ms=search_ms,
                    reranker_ms=reranker_ms
                )
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                result = {
                    "query_id": query_id,
                    "query_text": query_text,
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
                query_text=query_text,
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

    async def _multi_collection_search(
        self,
        collection_ids: List[str],
        query_text: str,
        query_vector: np.ndarray,
        search_mode_requested: str = "auto",
        reranker_top_n: int = 20,
        reranker_top_k: int = 10,
        rrf_k: int = 60,
        threshold: float = 0.5,
        embedding_ms: int = 0,
        query_id: str = "",
        start_time: float = 0
    ) -> Dict[str, Any]:
        """
        T028: 多 Collection 联合搜索
        
        使用 asyncio.gather() 并行在各 Collection 执行检索，
        合并候选集后统一调用 _rerank_candidates()。
        
        Args:
            collection_ids: Collection ID 列表
            query_text: 查询文本
            query_vector: 稠密查询向量
            其他: 搜索配置参数
            
        Returns:
            HybridSearchResponseData 字典
        """
        search_start = time.time()
        total_bm25_ms = 0
        
        # 并行在各 Collection 执行检索
        async def search_one(cid):
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
            all_candidates.extend(candidates)
        
        search_ms = int((time.time() - search_start) * 1000)
        
        # 统一 Reranker 精排
        ranked, reranker_available, reranker_ms = await self._rerank_candidates(
            query_text=query_text,
            candidates=all_candidates,
            top_k=reranker_top_k,
            reranker_top_n=len(all_candidates)  # 多 Collection 合并后全部送入 Reranker
        )
        
        # 获取索引名称映射
        index_names = self._get_index_names(collection_ids)
        
        # 格式化
        formatted = self._format_hybrid_results(ranked, final_mode, index_names)
        
        timing = self._build_search_timing(
            embedding_ms=embedding_ms,
            bm25_ms=total_bm25_ms,
            search_ms=search_ms,
            reranker_ms=reranker_ms
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "query_id": query_id,
            "query_text": query_text,
            "search_mode": final_mode,
            "reranker_available": reranker_available,
            "rrf_k": rrf_k if final_mode == "hybrid" else None,
            "results": formatted,
            "total_count": len(formatted),
            "execution_time_ms": execution_time_ms,
            "timing": timing
        }

    # ==================== Collection 管理 ====================

    def _resolve_collection_names_to_index_ids(self, collection_names: List[str]) -> List[str]:
        """
        将逻辑 Collection 名称列表解析为对应的索引记录 ID 列表
        
        用户在前端选择的 Collection 是逻辑知识库名（如 default_collection），
        需要映射到该 Collection 下所有 READY 状态的 VectorIndex 记录 ID。
        
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
                
                collections.append({
                    "id": coll_name,  # 使用 collection_name 作为 ID
                    "name": coll_name,
                    "provider": info["provider"],
                    "vector_count": info["vector_count"],
                    "dimension": primary_dimension,
                    "metric_type": primary_metric,
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
            score = result.get("score", 0)
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
