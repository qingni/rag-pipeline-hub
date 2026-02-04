"""
向量索引 API 路由

提供 REST API 接口用于向量索引管理和检索

2024-12-24 更新: 添加向量化任务集成 API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import numpy as np

from ..services.vector_index_service import VectorIndexService
from ..models.vector_index import (
    IndexProvider, 
    IndexStatus,
    CreateIndexFromEmbeddingRequest,
    IndexHistoryResponse
)
from ..storage.database import get_db
from ..utils.logger import get_logger
from ..exceptions.vector_index_errors import (
    IndexNotFoundError,
    IndexBuildError,
    SearchError,
    VectorDimensionError,
    ProviderNotFoundError
)

logger = get_logger("vector_index_api")

router = APIRouter(prefix="/vector-index", tags=["vector-index"])


# ==================== Request/Response Models ====================

class CreateIndexRequest(BaseModel):
    """创建索引请求"""
    index_name: str = Field(..., description="索引名称")
    dimension: int = Field(..., gt=0, description="向量维度")
    index_type: IndexProvider = Field(default=IndexProvider.MILVUS, description="索引类型")
    algorithm_type: str = Field(default="FLAT", description="索引算法类型")
    metric_type: str = Field(default="cosine", description="相似度度量类型")
    description: Optional[str] = Field(None, description="索引描述")
    namespace: Optional[str] = Field(default="default", description="命名空间")
    index_params: Optional[Dict[str, Any]] = Field(default={}, description="索引参数")


class AddVectorsRequest(BaseModel):
    """添加向量请求"""
    vectors: List[List[float]] = Field(..., description="向量列表")
    metadata: List[Dict[str, Any]] = Field(..., description="元数据列表")


class SearchRequest(BaseModel):
    """搜索请求"""
    query_vector: List[float] = Field(..., description="查询向量")
    top_k: int = Field(default=10, gt=0, le=100, description="返回结果数量")
    threshold: Optional[float] = Field(None, ge=0, le=1, description="相似度阈值")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    save_result: bool = Field(default=False, description="是否保存结果")


class BatchSearchRequest(BaseModel):
    """批量搜索请求"""
    query_vectors: List[List[float]] = Field(..., description="查询向量列表")
    top_k: int = Field(default=10, gt=0, le=100, description="返回结果数量")
    threshold: Optional[float] = Field(None, ge=0, le=1, description="相似度阈值")


class IndexResponse(BaseModel):
    """索引响应"""
    id: int
    index_name: str
    index_type: str
    algorithm_type: Optional[str]
    dimension: int
    metric_type: str
    status: str
    description: Optional[str]
    embedding_result_id: Optional[str]
    source_document_name: Optional[str]
    source_model: Optional[str]
    vector_count: int
    namespace: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SearchResultItem(BaseModel):
    """搜索结果项"""
    vector_id: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """搜索响应"""
    index_id: int
    index_name: str
    top_k: int
    results_count: int
    search_time_ms: float
    results: List[SearchResultItem]
    timestamp: str
    result_file: Optional[str] = None


class StatisticsResponse(BaseModel):
    """统计信息响应"""
    index_id: int
    index_name: str
    vector_count: int
    dimension: int
    index_type: str
    algorithm_type: Optional[str]
    metric_type: str
    total_queries: int
    avg_search_time_ms: float
    memory_usage_bytes: int
    created_at: str
    last_updated: str


class EmbeddingTaskResponse(BaseModel):
    """向量化任务响应"""
    result_id: str
    document_id: str
    document_name: Optional[str]
    model: str
    vector_dimension: int
    successful_count: int
    status: str
    created_at: str


class EmbeddingTaskListResponse(BaseModel):
    """向量化任务列表响应"""
    tasks: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


# ==================== Dependency ====================

def get_vector_index_service(db: Session = Depends(get_db)) -> VectorIndexService:
    """获取向量索引服务实例"""
    return VectorIndexService(db)


# ==================== 向量化任务集成 API ====================

@router.get("/embedding-tasks", response_model=EmbeddingTaskListResponse)
async def get_embedding_tasks(
    status: str = Query(default="SUCCESS", description="过滤任务状态"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="分页偏移量"),
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取可用的向量化任务列表
    
    用于创建索引时选择数据源
    """
    try:
        result = service.get_embedding_tasks(
            status=status,
            limit=limit,
            offset=offset
        )
        return EmbeddingTaskListResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to get embedding tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get embedding tasks: {str(e)}"
        )


@router.get("/indexes/find-matching")
async def find_matching_index(
    embedding_result_id: str = Query(..., description="向量化任务结果ID"),
    provider: str = Query(..., description="向量数据库类型"),
    algorithm_type: str = Query(..., description="索引算法类型"),
    metric_type: str = Query(..., description="度量类型"),
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    查找匹配条件的已存在索引
    
    根据向量化任务ID、数据库类型、算法类型和度量类型查找是否已存在匹配的索引
    """
    try:
        # 转换 provider 字符串为枚举
        try:
            provider_enum = IndexProvider(provider.upper())
        except ValueError:
            provider_enum = IndexProvider.MILVUS
        
        matching_index = service.find_matching_index(
            embedding_result_id=embedding_result_id,
            provider=provider_enum,
            algorithm_type=algorithm_type.upper(),
            metric_type=metric_type.lower()
        )
        
        if matching_index:
            return {
                "found": True,
                "index": IndexResponse(
                    id=matching_index.id,
                    index_name=matching_index.index_name,
                    index_type=matching_index.index_type.value,
                    algorithm_type=matching_index.algorithm_type,
                    dimension=matching_index.dimension,
                    metric_type=matching_index.metric_type,
                    status=matching_index.status.value,
                    description=matching_index.description,
                    embedding_result_id=matching_index.embedding_result_id,
                    source_document_name=matching_index.source_document_name,
                    source_model=matching_index.source_model,
                    vector_count=matching_index.vector_count,
                    namespace=matching_index.namespace,
                    created_at=matching_index.created_at.isoformat(),
                    updated_at=matching_index.updated_at.isoformat()
                )
            }
        else:
            return {"found": False, "index": None}
        
    except Exception as e:
        logger.error(f"Failed to find matching index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find matching index: {str(e)}"
        )


@router.post("/indexes/from-embedding", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def create_index_from_embedding(
    request: CreateIndexFromEmbeddingRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    从向量化任务创建索引
    
    基于已完成的向量化任务创建向量索引，系统会自动读取向量化结果中的向量数据
    并导入到选定的向量数据库。
    """
    try:
        vector_index = service.create_index_from_embedding(
            embedding_result_id=request.embedding_result_id,
            name=request.name,
            provider=request.provider,
            index_type=request.index_type,
            metric_type=request.metric_type,
            index_params=request.index_params,
            namespace=request.namespace
        )
        
        return IndexResponse(
            id=vector_index.id,
            index_name=vector_index.index_name,
            index_type=vector_index.index_type.value,
            algorithm_type=vector_index.algorithm_type,
            dimension=vector_index.dimension,
            metric_type=vector_index.metric_type,
            status=vector_index.status.value,
            description=vector_index.description,
            embedding_result_id=vector_index.embedding_result_id,
            source_document_name=vector_index.source_document_name,
            source_model=vector_index.source_model,
            vector_count=vector_index.vector_count,
            namespace=vector_index.namespace,
            created_at=vector_index.created_at.isoformat(),
            updated_at=vector_index.updated_at.isoformat()
        )
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except (IndexBuildError, VectorDimensionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create index from embedding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create index: {str(e)}"
        )


@router.get("/indexes/history")
async def get_index_history(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query(default="created_at", description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向"),
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取索引历史记录
    
    支持分页和排序
    """
    try:
        result = service.get_index_history(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return result
        
    except Exception as e:
        logger.error(f"Failed to get index history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index history: {str(e)}"
        )


# ==================== 原有 API ====================

@router.post("/indexes", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def create_index(
    request: CreateIndexRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    创建向量索引
    
    Args:
        request: 创建索引请求
        service: 向量索引服务
        
    Returns:
        创建的索引信息
    """
    try:
        vector_index = service.create_index(
            index_name=request.index_name,
            dimension=request.dimension,
            index_type=request.index_type,
            metric_type=request.metric_type,
            description=request.description,
            algorithm_type=request.algorithm_type,
            index_params=request.index_params,
            namespace=request.namespace
        )
        
        return IndexResponse(
            id=vector_index.id,
            index_name=vector_index.index_name,
            index_type=vector_index.index_type.value,
            algorithm_type=vector_index.algorithm_type,
            dimension=vector_index.dimension,
            metric_type=vector_index.metric_type,
            status=vector_index.status.value,
            description=vector_index.description,
            embedding_result_id=vector_index.embedding_result_id,
            source_document_name=vector_index.source_document_name,
            source_model=vector_index.source_model,
            vector_count=vector_index.vector_count,
            namespace=vector_index.namespace,
            created_at=vector_index.created_at.isoformat(),
            updated_at=vector_index.updated_at.isoformat()
        )
        
    except (IndexBuildError, VectorDimensionError) as e:
        logger.error(f"Failed to create index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create index: {str(e)}"
        )


@router.post("/indexes/{index_id}/vectors", status_code=status.HTTP_201_CREATED)
async def add_vectors(
    index_id: int,
    request: AddVectorsRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    向索引添加向量
    """
    try:
        # 验证向量和元数据数量一致
        if len(request.vectors) != len(request.metadata):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vectors and metadata count mismatch"
            )
        
        # 转换为 numpy 数组
        vectors_array = np.array(request.vectors, dtype=np.float32)
        
        result = service.add_vectors(
            index_id=index_id,
            vectors=vectors_array,
            metadata=request.metadata
        )
        
        return result
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except (IndexBuildError, VectorDimensionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error adding vectors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add vectors: {str(e)}"
        )


@router.post("/indexes/{index_id}/search", response_model=SearchResponse)
async def search_vectors(
    index_id: int,
    request: SearchRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    向量相似度搜索
    """
    try:
        # 转换为 numpy 数组
        query_vector = np.array(request.query_vector, dtype=np.float32)
        
        result = service.search(
            index_id=index_id,
            query_vector=query_vector,
            top_k=request.top_k,
            threshold=request.threshold,
            filters=request.filters,
            save_result=request.save_result
        )
        
        return SearchResponse(
            index_id=result["index_id"],
            index_name=result["index_name"],
            top_k=result["top_k"],
            results_count=result["results_count"],
            search_time_ms=result["search_time_ms"],
            results=[
                SearchResultItem(
                    vector_id=r["vector_id"],
                    score=r["score"],
                    metadata=r["metadata"]
                )
                for r in result["results"]
            ],
            timestamp=result["timestamp"],
            result_file=result.get("result_file")
        )
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except (SearchError, VectorDimensionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/indexes/{index_id}/batch-search")
async def batch_search_vectors(
    index_id: int,
    request: BatchSearchRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    批量向量搜索
    """
    try:
        query_vectors = np.array(request.query_vectors, dtype=np.float32)
        
        result = service.batch_search(
            index_id=index_id,
            query_vectors=query_vectors,
            top_k=request.top_k,
            threshold=request.threshold
        )
        
        return result
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except (SearchError, VectorDimensionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch search failed: {str(e)}"
        )


@router.get("/indexes/{index_id}", response_model=IndexResponse)
async def get_index(
    index_id: int,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取索引详情
    """
    try:
        vector_index = service.get_index(index_id)
        
        return IndexResponse(
            id=vector_index.id,
            index_name=vector_index.index_name,
            index_type=vector_index.index_type.value,
            algorithm_type=vector_index.algorithm_type,
            dimension=vector_index.dimension,
            metric_type=vector_index.metric_type,
            status=vector_index.status.value,
            description=vector_index.description,
            embedding_result_id=vector_index.embedding_result_id,
            source_document_name=vector_index.source_document_name,
            source_model=vector_index.source_model,
            vector_count=vector_index.vector_count,
            namespace=vector_index.namespace,
            created_at=vector_index.created_at.isoformat(),
            updated_at=vector_index.updated_at.isoformat()
        )
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/indexes", response_model=List[IndexResponse])
async def list_indexes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    namespace: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    列出所有索引
    """
    indexes = service.list_indexes(
        skip=skip, 
        limit=limit,
        namespace=namespace,
        status=status
    )
    
    return [
        IndexResponse(
            id=idx.id,
            index_name=idx.index_name,
            index_type=idx.index_type.value,
            algorithm_type=idx.algorithm_type,
            dimension=idx.dimension,
            metric_type=idx.metric_type,
            status=idx.status.value,
            description=idx.description,
            embedding_result_id=idx.embedding_result_id,
            source_document_name=idx.source_document_name,
            source_model=idx.source_model,
            vector_count=idx.vector_count,
            namespace=idx.namespace,
            created_at=idx.created_at.isoformat(),
            updated_at=idx.updated_at.isoformat()
        )
        for idx in indexes
    ]


@router.delete("/indexes/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(
    index_id: int,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    删除索引
    """
    try:
        service.delete_index(index_id)
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete index: {str(e)}"
        )


@router.get("/indexes/{index_id}/statistics", response_model=StatisticsResponse)
async def get_statistics(
    index_id: int,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取索引统计信息
    """
    try:
        stats = service.get_statistics(index_id)
        
        return StatisticsResponse(
            index_id=stats["index_id"],
            index_name=stats["index_name"],
            vector_count=stats["vector_count"],
            dimension=stats["dimension"],
            index_type=stats["index_type"],
            algorithm_type=stats.get("algorithm_type"),
            metric_type=stats["metric_type"],
            total_queries=stats["total_queries"],
            avg_search_time_ms=stats["avg_search_time_ms"],
            memory_usage_bytes=stats["memory_usage_bytes"],
            created_at=stats["created_at"],
            last_updated=stats["last_updated"]
        )
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/indexes/{index_id}/query-history")
async def get_query_history(
    index_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取查询历史
    """
    try:
        history = service.get_query_history(index_id, limit)
        
        return [
            {
                "id": h.id,
                "index_id": h.index_id,
                "query_vector": h.query_vector,
                "top_k": h.top_k,
                "filters": h.filters,
                "results_count": h.results_count,
                "search_time_ms": float(h.search_time_ms),
                "created_at": h.created_at.isoformat()
            }
            for h in history
        ]
        
    except Exception as e:
        logger.error(f"Failed to get query history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query history: {str(e)}"
        )


@router.get("/health")
async def health_check(
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    健康检查
    """
    try:
        # 检查提供者健康状态
        providers_health = {}
        for provider_name in ["milvus"]:
            try:
                provider = service.registry.get_provider(provider_name)
                providers_health[provider_name] = provider.health_check()
            except Exception:
                providers_health[provider_name] = {"status": "unavailable"}
        
        return {
            "status": "healthy",
            "providers": providers_health,
            "timestamp": str(np.datetime64('now'))
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


# ==================== 持久化 API ====================

@router.post("/indexes/{index_id}/persist")
async def persist_index(
    index_id: int,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    持久化索引到磁盘
    """
    try:
        result = service.persist_index(index_id)
        return result
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except IndexBuildError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to persist index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist index: {str(e)}"
        )


@router.post("/indexes/{index_id}/recover")
async def recover_index(
    index_id: int,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    从磁盘恢复索引
    """
    try:
        result = service.recover_index(index_id)
        return result
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except IndexBuildError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to recover index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recover index: {str(e)}"
        )


# ==================== 向量 CRUD API ====================

class DeleteVectorsRequest(BaseModel):
    """删除向量请求"""
    vector_ids: List[str] = Field(..., description="要删除的向量ID列表")


class UpdateVectorRequest(BaseModel):
    """更新向量请求"""
    vector_id: str = Field(..., description="向量ID")
    vector: List[float] = Field(..., description="新的向量数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="新的元数据")


@router.delete("/indexes/{index_id}/vectors")
async def delete_vectors(
    index_id: int,
    request: DeleteVectorsRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    从索引中删除向量
    """
    try:
        result = service.delete_vectors(index_id, request.vector_ids)
        return result
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except IndexBuildError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete vectors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete vectors: {str(e)}"
        )


@router.put("/indexes/{index_id}/vectors")
async def update_vector(
    index_id: int,
    request: UpdateVectorRequest,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    更新索引中的向量
    """
    try:
        vector_array = np.array(request.vector, dtype=np.float32)
        result = service.update_vector(
            index_id=index_id,
            vector_id=request.vector_id,
            vector=vector_array,
            metadata=request.metadata
        )
        return result
        
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except (IndexBuildError, VectorDimensionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update vector: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update vector: {str(e)}"
        )
