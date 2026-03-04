"""
搜索查询 API 路由

提供语义搜索、搜索历史管理等功能的 RESTful API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..storage.database import get_db
from ..schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResponseData,
    IndexListResponse,
    HistoryListResponse,
    HistoryListData,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResponseData,
    HybridSearchResultItem,
    SearchTiming,
    CollectionListResponse,
    CollectionInfo,
    RerankerHealthResponse,
    RerankerHealthData,
)
from ..services.search_service import (
    SearchService,
    SearchServiceError,
    EmptyQueryError,
    QueryTooLongError,
    IndexNotFoundError,
    EmbeddingServiceError,
    SearchTimeoutError
)
from ..config import settings

router = APIRouter(prefix="/search", tags=["Search"])


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """获取搜索服务实例"""
    return SearchService(db)


@router.post("", response_model=SearchResponse)
async def execute_search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    执行语义搜索
    
    将查询文本转换为向量并在指定索引中检索相似文档
    """
    try:
        result = await service.search(request)
        return SearchResponse(success=True, data=result)
        
    except EmptyQueryError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "EMPTY_QUERY",
                    "message": str(e)
                }
            }
        )
    except QueryTooLongError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "QUERY_TOO_LONG",
                    "message": str(e)
                }
            }
        )
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "INDEX_NOT_FOUND",
                    "message": str(e)
                }
            }
        )
    except EmbeddingServiceError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "EMBEDDING_SERVICE_ERROR",
                    "message": str(e)
                }
            }
        )
    except SearchTimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail={
                "success": False,
                "error": {
                    "code": "SEARCH_TIMEOUT",
                    "message": str(e)
                }
            }
        )
    except SearchServiceError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "SEARCH_ERROR",
                    "message": str(e)
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"搜索失败: {str(e)}"
                }
            }
        )


@router.post("/hybrid", response_model=HybridSearchResponse)
async def execute_hybrid_search(
    request: HybridSearchRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    执行混合检索（稠密+稀疏双路召回 + RRF + Reranker）
    
    支持多 Collection 联合搜索（最多5个）、智能降级
    """
    try:
        # T030: collection_ids 数量校验
        if request.collection_ids and len(request.collection_ids) > settings.MAX_COLLECTIONS:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "MAX_COLLECTIONS_EXCEEDED",
                        "message": f"联合搜索最多支持 {settings.MAX_COLLECTIONS} 个 Collection"
                    }
                }
            )
        
        result = await service.hybrid_search(request)
        
        # 构造 Timing 对象
        timing_data = result.get("timing")
        timing = SearchTiming(**timing_data) if timing_data else None
        
        # 构造结果项
        all_items = []
        for item in result.get("results", []):
            all_items.append(HybridSearchResultItem(**item))
        
        # T037: 分页截断
        total_count = len(all_items)
        page = getattr(request, 'page', 1) or 1
        page_size = getattr(request, 'page_size', 10) or 10
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = all_items[start_idx:end_idx]
        
        response_data = HybridSearchResponseData(
            query_id=result["query_id"],
            query_text=result["query_text"],
            search_mode=result["search_mode"],
            reranker_available=result.get("reranker_available", False),
            rrf_k=result.get("rrf_k"),
            results=paged_items,
            total_count=total_count,
            execution_time_ms=result["execution_time_ms"],
            timing=timing
        )
        
        return HybridSearchResponse(success=True, data=response_data)
        
    except HTTPException:
        raise
    except EmptyQueryError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": {"code": "EMPTY_QUERY", "message": str(e)}}
        )
    except QueryTooLongError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": {"code": "QUERY_TOO_LONG", "message": str(e)}}
        )
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": {"code": "INDEX_NOT_FOUND", "message": str(e)}}
        )
    except EmbeddingServiceError as e:
        raise HTTPException(
            status_code=503,
            detail={"success": False, "error": {"code": "EMBEDDING_SERVICE_ERROR", "message": str(e)}}
        )
    except SearchTimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail={"success": False, "error": {"code": "SEARCH_TIMEOUT", "message": str(e)}}
        )
    except SearchServiceError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SEARCH_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": f"混合检索失败: {str(e)}"}}
        )


@router.get("/collections", response_model=CollectionListResponse)
async def get_available_collections(
    service: SearchService = Depends(get_search_service)
):
    """
    获取可用 Collection 列表（含 has_sparse 标识）
    """
    try:
        collections = service.get_available_collections()
        collection_infos = [CollectionInfo(**c) for c in collections]
        return CollectionListResponse(success=True, data=collection_infos)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": f"获取 Collection 列表失败: {str(e)}"}}
        )


@router.get("/reranker/health", response_model=RerankerHealthResponse)
async def get_reranker_health():
    """
    Reranker 健康检查
    """
    try:
        from ..services.reranker_service import RerankerService
        reranker = RerankerService.get_instance(
            model_name=settings.RERANKER_MODEL,
            api_key=settings.RERANKER_API_KEY,
            api_base_url=settings.RERANKER_API_BASE_URL,
            timeout=settings.RERANKER_TIMEOUT
        )
        # 确保先初始化 API 客户端（延迟初始化）
        if not reranker.available:
            reranker.init()
        health = reranker.health_check()
        return RerankerHealthResponse(
            success=True,
            data=RerankerHealthData(**health)
        )
    except Exception as e:
        return RerankerHealthResponse(
            success=True,
            data=RerankerHealthData(
                available=False,
                model_name=settings.RERANKER_MODEL,
                api_base_url=settings.RERANKER_API_BASE_URL,
                api_connected=False,
                supported_models=[]
            )
        )


@router.get("/indexes", response_model=IndexListResponse)
async def get_available_indexes(
    service: SearchService = Depends(get_search_service)
):
    """
    获取可用索引列表
    
    返回所有可用于搜索的向量索引
    """
    try:
        indexes = service.get_available_indexes()
        return IndexListResponse(success=True, data=indexes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"获取索引列表失败: {str(e)}"
                }
            }
        )


@router.get("/history", response_model=HistoryListResponse)
async def get_search_history(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    service: SearchService = Depends(get_search_service)
):
    """
    获取搜索历史
    
    返回用户的搜索历史记录
    """
    try:
        result = service.get_history(limit=limit, offset=offset)
        return HistoryListResponse(
            success=True,
            data=HistoryListData(
                items=result["items"],
                total=result["total"],
                limit=result["limit"],
                offset=result["offset"]
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"获取搜索历史失败: {str(e)}"
                }
            }
        )


@router.delete("/history/{history_id}", response_model=SuccessResponse)
async def delete_search_history(
    history_id: str,
    service: SearchService = Depends(get_search_service)
):
    """
    删除单条历史记录
    
    根据ID删除指定的搜索历史记录
    """
    try:
        success = service.delete_history(history_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {
                        "code": "HISTORY_NOT_FOUND",
                        "message": "历史记录不存在"
                    }
                }
            )
        return SuccessResponse(success=True, message="删除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"删除历史记录失败: {str(e)}"
                }
            }
        )


@router.delete("/history", response_model=SuccessResponse)
async def clear_search_history(
    service: SearchService = Depends(get_search_service)
):
    """
    清空搜索历史
    
    删除所有搜索历史记录
    """
    try:
        count = service.clear_history()
        return SuccessResponse(success=True, message=f"已清空 {count} 条历史记录")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"清空历史记录失败: {str(e)}"
                }
            }
        )
