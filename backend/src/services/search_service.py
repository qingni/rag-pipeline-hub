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
