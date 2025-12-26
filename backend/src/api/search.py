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
    ErrorDetail
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
