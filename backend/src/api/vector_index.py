"""
向量索引 API 路由

提供 REST API 接口用于向量索引管理和检索
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import numpy as np

from ..services.vector_index_service import VectorIndexService
from ..models.vector_index import IndexProvider
from ..storage.database import get_db
from ..utils.logger import get_logger
from ..exceptions.vector_index_errors import (
    IndexNotFoundError,
    IndexBuildError,
    SearchError
)

logger = get_logger("vector_index_api")

router = APIRouter(prefix="/vector-index", tags=["vector-index"])


# ==================== Request/Response Models ====================

class CreateIndexRequest(BaseModel):
    """创建索引请求"""
    index_name: str = Field(..., description="索引名称")
    dimension: int = Field(..., gt=0, description="向量维度")
    index_type: IndexProvider = Field(default=IndexProvider.FAISS, description="索引类型")
    metric_type: str = Field(default="cosine", description="相似度度量类型")
    description: Optional[str] = Field(None, description="索引描述")


class AddVectorsRequest(BaseModel):
    """添加向量请求"""
    vectors: List[List[float]] = Field(..., description="向量列表")
    metadata: List[Dict[str, Any]] = Field(..., description="元数据列表")


class SearchRequest(BaseModel):
    """搜索请求"""
    query_vector: List[float] = Field(..., description="查询向量")
    top_k: int = Field(default=10, gt=0, le=100, description="返回结果数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    save_result: bool = Field(default=False, description="是否保存结果")


class IndexResponse(BaseModel):
    """索引响应"""
    id: int
    index_name: str
    index_type: str
    dimension: int
    metric_type: str
    status: str
    description: Optional[str]
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
    metric_type: str
    total_queries: int
    avg_search_time_ms: float
    memory_usage_bytes: int
    created_at: str
    last_updated: str


# ==================== Dependency ====================

def get_vector_index_service(db: Session = Depends(get_db)) -> VectorIndexService:
    """获取向量索引服务实例"""
    return VectorIndexService(db)


# ==================== API Endpoints ====================

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
            description=request.description
        )
        
        return IndexResponse(
            id=vector_index.id,
            index_name=vector_index.index_name,
            index_type=vector_index.index_type.value,
            dimension=vector_index.dimension,
            metric_type=vector_index.metric_type,
            status=vector_index.status.value,
            description=vector_index.description,
            created_at=vector_index.created_at.isoformat(),
            updated_at=vector_index.updated_at.isoformat()
        )
        
    except IndexBuildError as e:
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
    
    Args:
        index_id: 索引 ID
        request: 添加向量请求
        service: 向量索引服务
        
    Returns:
        添加结果
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
    except IndexBuildError as e:
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
    
    Args:
        index_id: 索引 ID
        request: 搜索请求
        service: 向量索引服务
        
    Returns:
        搜索结果
    """
    try:
        # 转换为 numpy 数组
        query_vector = np.array(request.query_vector, dtype=np.float32)
        
        result = service.search(
            index_id=index_id,
            query_vector=query_vector,
            top_k=request.top_k,
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
    except SearchError as e:
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


@router.get("/indexes/{index_id}", response_model=IndexResponse)
async def get_index(
    index_id: int,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取索引详情
    
    Args:
        index_id: 索引 ID
        service: 向量索引服务
        
    Returns:
        索引信息
    """
    try:
        vector_index = service.get_index(index_id)
        
        return IndexResponse(
            id=vector_index.id,
            index_name=vector_index.index_name,
            index_type=vector_index.index_type.value,
            dimension=vector_index.dimension,
            metric_type=vector_index.metric_type,
            status=vector_index.status.value,
            description=vector_index.description,
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
    skip: int = 0,
    limit: int = 100,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    列出所有索引
    
    Args:
        skip: 跳过记录数
        limit: 返回记录数
        service: 向量索引服务
        
    Returns:
        索引列表
    """
    indexes = service.list_indexes(skip=skip, limit=limit)
    
    return [
        IndexResponse(
            id=idx.id,
            index_name=idx.index_name,
            index_type=idx.index_type.value,
            dimension=idx.dimension,
            metric_type=idx.metric_type,
            status=idx.status.value,
            description=idx.description,
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
    
    Args:
        index_id: 索引 ID
        service: 向量索引服务
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
    
    Args:
        index_id: 索引 ID
        service: 向量索引服务
        
    Returns:
        统计信息
    """
    try:
        stats = service.get_statistics(index_id)
        
        return StatisticsResponse(
            index_id=stats["index_id"],
            index_name=stats["index_name"],
            vector_count=stats["vector_count"],
            dimension=stats["dimension"],
            index_type=stats["index_type"],
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


@router.get("/indexes/{index_id}/history")
async def get_query_history(
    index_id: int,
    limit: int = 100,
    service: VectorIndexService = Depends(get_vector_index_service)
):
    """
    获取查询历史
    
    Args:
        index_id: 索引 ID
        limit: 返回记录数
        service: 向量索引服务
        
    Returns:
        查询历史列表
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
    
    Returns:
        健康状态
    """
    try:
        # 检查提供者健康状态
        providers_health = {}
        for provider_name in ["faiss", "milvus"]:
            try:
                provider = service.registry.get_provider(provider_name)
                providers_health[provider_name] = provider.health_check()
            except Exception as e:
                providers_health[provider_name] = False
        
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
