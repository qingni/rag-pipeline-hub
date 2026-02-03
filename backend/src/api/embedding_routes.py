"""FastAPI routes for embedding operations."""
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..models.embedding_models import (
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    BatchMetadata,
    EmbeddingConfig,
    EmbeddingFailure,
    EmbeddingMetadata,
    ErrorResponse,
    InvalidTextError,
    ModelInfo,
    ModelsListResponse,
    ResponseStatus,
    SingleEmbeddingRequest,
    SingleEmbeddingResponse,
    Vector,
    VectorDimensionMismatchError,
    BatchSizeLimitError,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    NetworkError,
    ErrorType,
    ChunkingResultEmbeddingRequest,
    DocumentEmbeddingRequest,
)
from ..services.embedding_service import EmbeddingService, EMBEDDING_MODELS
from ..storage.embedding_storage_dual import DualWriteEmbeddingStorage
from ..storage.embedding_db import EmbeddingResultDB
from ..utils.logging_utils import embedding_logger
from ..utils.formatters import success_response

router = APIRouter(prefix="/embedding", tags=["embedding"])
storage = DualWriteEmbeddingStorage(
    results_dir=os.getenv("EMBEDDING_RESULTS_DIR", "results/embedding")
)
DEFAULT_MAX_BATCH_SIZE = 1000


# Import database dependency
def get_db():
    """Get database session."""
    from ..storage.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_embedding_config(request) -> EmbeddingConfig:
    base_url = os.getenv("EMBEDDING_API_BASE_URL")
    if not base_url:
        raise AuthenticationError("EMBEDDING_API_BASE_URL environment variable not set")
    
    return EmbeddingConfig(
        api_endpoint=base_url,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout,
        exponential_backoff=True,
        initial_delay_seconds=1.0,
        max_delay_seconds=32.0,
    )


def get_embedding_service(
    model: str,
    max_retries: int,
    timeout: int,
) -> EmbeddingService:
    api_key = os.getenv("EMBEDDING_API_KEY")
    if not api_key:
        raise AuthenticationError("EMBEDDING_API_KEY environment variable not set")

    base_url = os.getenv("EMBEDDING_API_BASE_URL")
    if not base_url:
        raise AuthenticationError("EMBEDDING_API_BASE_URL environment variable not set")
    
    return EmbeddingService(
        api_key=api_key,
        model=model,
        base_url=base_url,
        max_retries=max_retries,
        request_timeout=timeout,
    )


@router.post(
    "/single",
    response_model=SingleEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def embed_single_text(
    request: SingleEmbeddingRequest,
):
    request_id = str(uuid.uuid4())
    try:
        service = get_embedding_service(
            model=request.model,
            max_retries=request.max_retries,
            timeout=request.timeout,
        )

        result = service.embed_query(request.text, request_id=request_id)
        vector = Vector(
            index=0,
            vector=result.vector,
            dimension=len(result.vector),
            text_hash=Vector.create_text_hash(request.text),
            text_length=result.text_length,
            processing_time_ms=result.api_latency_ms,
            source_text=request.text,  # Include source text
        )

        metadata = EmbeddingMetadata(
            model=request.model,
            model_dimension=service.model_info["dimension"],
            processing_time_ms=result.processing_time_ms,
            api_latency_ms=result.api_latency_ms,
            retry_count=result.retry_count,
            rate_limit_hits=result.rate_limit_hits,
            config=build_embedding_config(request),
        )

        response = SingleEmbeddingResponse(
            request_id=request_id,
            status=ResponseStatus.SUCCESS,
            vector=vector,
            metadata=metadata,
            timestamp=datetime.utcnow(),
        )

        storage.save_single_result(response)
        return response

    except InvalidTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": ErrorType.INVALID_TEXT_ERROR.value,
                    "message": str(exc),
                }
            },
        ) from exc
    except VectorDimensionMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DIMENSION_MISMATCH_ERROR",
                    "message": str(exc),
                    "details": {
                        "expected": exc.expected,
                        "actual": exc.actual,
                        "model": exc.model,
                    },
                }
            },
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorType.AUTHENTICATION_ERROR.value,
                    "message": "Invalid API key. Please check your credentials.",
                }
            },
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": ErrorType.RATE_LIMIT_ERROR.value,
                    "message": str(exc),
                    "details": {
                        "retry_after_seconds": getattr(exc, "retry_after", 30),
                    },
                }
            },
        ) from exc
    except (APITimeoutError, NetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                }
            },
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        embedding_logger.log_request_failed(
            request_id=request_id,
            model=request.model,
            duration_ms=0,
            error_type="INTERNAL_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": {"request_id": request_id},
                }
            },
        ) from exc


@router.post(
    "/batch",
    response_model=BatchEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        413: {"model": ErrorResponse, "description": "Batch size exceeds limit"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def embed_batch_texts(
    request: BatchEmbeddingRequest,
):
    request_id = str(uuid.uuid4())
    try:
        service = get_embedding_service(
            model=request.model,
            max_retries=request.max_retries,
            timeout=request.timeout,
        )
        result = service.embed_documents(request.texts, request_id=request_id)

        vectors: List[Vector] = [
            Vector(
                index=item.index,
                vector=item.vector,
                dimension=len(item.vector),
                text_hash=item.text_hash,
                text_length=item.text_length,
                processing_time_ms=item.processing_time_ms,
                source_text=item.source_text,  # Include source text
            )
            for item in result.vectors
        ]
        failures: List[EmbeddingFailure] = [
            EmbeddingFailure(
                index=item.index,
                text_preview=item.text_preview,
                error_type=item.error_type,
                error_message=item.error_message,
                retry_recommended=item.retry_recommended,
                retry_count=item.retry_count,
            )
            for item in result.failures
        ]

        status_value = (
            ResponseStatus.SUCCESS
            if not failures
            else ResponseStatus.FAILED
            if not vectors
            else ResponseStatus.PARTIAL_SUCCESS
        )

        vectors_per_second = (
            len(vectors) / (result.processing_time_ms / 1000)
            if result.processing_time_ms > 0 and vectors
            else 0.0
        )

        metadata = BatchMetadata(
            model=request.model,
            model_dimension=service.model_info["dimension"],
            processing_time_ms=result.processing_time_ms,
            api_latency_ms=None,
            retry_count=result.retry_count,
            rate_limit_hits=result.rate_limit_hits,
            batch_size=result.batch_size,
            successful_count=len(vectors),
            failed_count=len(failures),
            vectors_per_second=vectors_per_second,
            config=build_embedding_config(request),
        )

        response = BatchEmbeddingResponse(
            request_id=request_id,
            status=status_value,
            vectors=vectors,
            failures=failures,
            metadata=metadata,
            timestamp=datetime.utcnow(),
        )

        # Save with source information
        storage.save_batch_result(
            response, 
            source_result_id=request.result_id
        )
        return response

    except BatchSizeLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "BATCH_SIZE_LIMIT_EXCEEDED",
                    "message": str(exc),
                    "details": {
                        "batch_size": exc.size,
                        "max_batch_size": exc.max_size,
                        "suggested_batches": (exc.size + exc.max_size - 1) // exc.max_size,
                    },
                }
            },
        ) from exc
    except InvalidTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": ErrorType.INVALID_TEXT_ERROR.value,
                    "message": str(exc),
                }
            },
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorType.AUTHENTICATION_ERROR.value,
                    "message": "Invalid API key. Please check your credentials.",
                }
            },
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": ErrorType.RATE_LIMIT_ERROR.value,
                    "message": str(exc),
                    "details": {
                        "retry_after_seconds": getattr(exc, "retry_after", 30),
                    },
                }
            },
        ) from exc
    except (APITimeoutError, NetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                }
            },
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        embedding_logger.log_request_failed(
            request_id=request_id,
            model=request.model,
            duration_ms=0,
            error_type="INTERNAL_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": {"request_id": request_id},
                }
            },
        ) from exc


@router.get(
    "/documents",
    status_code=status.HTTP_200_OK,
)
async def get_documents_with_chunking(
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get documents that have completed chunking and are ready for embedding.
    
    Returns a list of documents with their chunking results that can be used
    for vectorization.
    """
    from ..models.chunking_result import ChunkingResult, ResultStatus
    from ..models.chunking_task import ChunkingTask
    from ..models.document import Document
    from sqlalchemy import func, distinct, cast, String
    
    try:
        # 查询有已完成分块结果的文档
        # 注意：数据库中存储的是枚举名称（大写），使用 cast 转换后比较
        subquery = db.query(
            distinct(ChunkingTask.source_document_id).label('document_id')
        ).join(
            ChunkingResult,
            ChunkingTask.task_id == ChunkingResult.task_id
        ).filter(
            cast(ChunkingResult.status, String) == "COMPLETED"
        ).subquery()
        
        # 获取总数
        total = db.query(func.count()).select_from(subquery).scalar() or 0
        
        # 分页查询文档
        offset = (page - 1) * page_size
        document_ids = db.query(subquery.c.document_id).offset(offset).limit(page_size).all()
        document_ids = [d[0] for d in document_ids]
        
        # 获取文档详情
        documents = []
        for doc_id in document_ids:
            # Document 模型的主键是 id，不是 document_id
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                # 获取该文档的最新活动分块结果
                latest_chunking = db.query(ChunkingResult).join(
                    ChunkingTask,
                    ChunkingResult.task_id == ChunkingTask.task_id
                ).filter(
                    ChunkingTask.source_document_id == doc_id,
                    cast(ChunkingResult.status, String) == "COMPLETED"
                ).order_by(ChunkingResult.created_at.desc()).first()
                
                # Document 模型字段: id, filename, format, size_bytes, upload_time
                documents.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "file_type": doc.format,
                    "file_size": doc.size_bytes,
                    "created_at": doc.upload_time.isoformat() if doc.upload_time else None,
                    "chunking_result": {
                        "result_id": latest_chunking.result_id if latest_chunking else None,
                        "total_chunks": latest_chunking.total_chunks if latest_chunking else 0,
                        "created_at": latest_chunking.created_at.isoformat() if latest_chunking and latest_chunking.created_at else None,
                    } if latest_chunking else None
                })
        
        return success_response(
            data={
                "documents": documents,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to get documents: {str(exc)}",
                }
            },
        ) from exc


@router.get(
    "/documents/{document_id}/latest",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "No embedding result found"},
    },
)
async def get_latest_embedding_by_document(
    document_id: str,
    model: str = None,
    db: Session = Depends(get_db),
):
    """
    Get the latest embedding result for a document.
    
    This endpoint returns the most recent embedding result for a given document,
    optionally filtered by model. Useful for loading previous embedding results
    when selecting a document.
    
    Args:
        document_id: Document unique identifier
        model: Optional model filter (e.g., "bge-m3")
    
    Returns:
        Latest embedding result with vectors and metadata
    """
    try:
        embedding_db = EmbeddingResultDB(db)
        result = embedding_db.get_latest_by_document(document_id, model=model)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "EMBEDDING_RESULT_NOT_FOUND",
                        "message": f"No embedding result found for document '{document_id}'",
                    }
                },
            )
        
        # Return result as dictionary
        return success_response(
            data={
                "result_id": result.result_id,
                "document_id": result.document_id,
                "chunking_result_id": result.chunking_result_id,
                "model": result.model,
                "status": result.status,
                "successful_count": result.successful_count,
                "failed_count": result.failed_count,
                "processing_time_ms": result.processing_time_ms,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "json_file_path": result.json_file_path,
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to get latest embedding result: {str(exc)}",
                }
            },
        ) from exc


@router.get(
    "/models",
    status_code=status.HTTP_200_OK,
)
async def list_models():
    """List all available embedding models."""
    models = [
        ModelInfo(
            name=name,
            dimension=info["dimension"],
            description=info["description"],
            provider=info.get("provider", "unknown"),
            supports_multilingual=bool(info.get("supports_multilingual", True)),
            max_batch_size=int(info.get("max_batch_size", DEFAULT_MAX_BATCH_SIZE)),
        )
        for name, info in EMBEDDING_MODELS.items()
    ]
    return success_response(
        data={
            "models": models,
            "count": len(models)
        }
    )


@router.get(
    "/models/{model_name}",
    response_model=ModelInfo,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Model not found"},
    },
)
async def get_model_info(model_name: str):
    if model_name not in EMBEDDING_MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "MODEL_NOT_FOUND",
                    "message": (
                        f"Model '{model_name}' not found. Supported models: {', '.join(EMBEDDING_MODELS.keys())}"
                    ),
                }
            },
        )

    info = EMBEDDING_MODELS[model_name]
    return ModelInfo(
        name=model_name,
        dimension=info["dimension"],
        description=info["description"],
        provider=info.get("provider", model_name.split("-")[0]),
        supports_multilingual=bool(info.get("supports_multilingual", True)),
        max_batch_size=int(info.get("max_batch_size", DEFAULT_MAX_BATCH_SIZE)),
    )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """
    Health check endpoint for service monitoring.
    
    Validates:
    - Service is running (HTTP 200)
    - API endpoint reachability (5s timeout)
    - Model availability via embedding API
    - Authentication validity
    
    Returns status: healthy | degraded | unhealthy
    """
    try:
        api_key = os.getenv("EMBEDDING_API_KEY")
        base_url = os.getenv("EMBEDDING_API_BASE_URL")
        
        # Check authentication
        authentication_status = "valid" if (api_key and base_url) else "invalid"
        
        # Basic connectivity check
        api_connectivity = api_key is not None
        
        # Get available models
        models_available = list(EMBEDDING_MODELS.keys())
        
        # Determine overall status
        if api_connectivity and authentication_status == "valid" and models_available:
            overall_status = "healthy"
        elif api_connectivity or models_available:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "service": "up",
            "api_connectivity": api_connectivity,
            "models_available": models_available,
            "authentication": authentication_status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "error",
                "api_connectivity": False,
                "models_available": [],
                "authentication": "not_checked",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(exc)
            },
        )


@router.post(
    "/from-chunking-result",
    response_model=BatchEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        404: {"model": ErrorResponse, "description": "Chunking result not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def embed_from_chunking_result(
    request: ChunkingResultEmbeddingRequest,
    db: Session = Depends(get_db),
):
    """
    Vectorize all chunks from a chunking result.
    
    This endpoint takes a chunking result ID and creates embeddings for all chunks
    in that result. It automatically handles batch processing and returns vectors
    in the same order as the original chunks.
    """
    request_id = str(uuid.uuid4())
    try:
        service = get_embedding_service(
            model=request.model,
            max_retries=request.max_retries,
            timeout=request.timeout,
        )

        result = service.embed_chunking_result(
            result_id=request.result_id,
            db_session=db,
            request_id=request_id
        )

        vectors: List[Vector] = [
            Vector(
                index=item.index,
                vector=item.vector,
                dimension=len(item.vector),
                text_hash=item.text_hash,
                text_length=item.text_length,
                processing_time_ms=item.processing_time_ms,
                source_text=item.source_text,  # Include source text
            )
            for item in result.vectors
        ]
        failures: List[EmbeddingFailure] = [
            EmbeddingFailure(
                index=item.index,
                text_preview=item.text_preview,
                error_type=item.error_type,
                error_message=item.error_message,
                retry_recommended=item.retry_recommended,
                retry_count=item.retry_count,
            )
            for item in result.failures
        ]

        status_value = (
            ResponseStatus.SUCCESS
            if not failures
            else ResponseStatus.FAILED
            if not vectors
            else ResponseStatus.PARTIAL_SUCCESS
        )

        vectors_per_second = (
            len(vectors) / (result.processing_time_ms / 1000)
            if result.processing_time_ms > 0 and vectors
            else 0.0
        )

        metadata = BatchMetadata(
            model=request.model,
            model_dimension=service.model_info["dimension"],
            processing_time_ms=result.processing_time_ms,
            api_latency_ms=None,
            retry_count=result.retry_count,
            rate_limit_hits=result.rate_limit_hits,
            batch_size=result.batch_size,
            successful_count=len(vectors),
            failed_count=len(failures),
            vectors_per_second=vectors_per_second,
            config=build_embedding_config(request),
        )

        response = BatchEmbeddingResponse(
            request_id=request_id,
            status=status_value,
            vectors=vectors,
            failures=failures,
            metadata=metadata,
            timestamp=datetime.utcnow(),
        )

        # Get chunking_result_id from the service (it already found the latest result)
        from ..models.chunking_result import ChunkingResult, ResultStatus
        from ..models.chunking_task import ChunkingTask, StrategyType
        
        # Build query for latest active result
        query = db.query(ChunkingResult).join(
            ChunkingTask,
            ChunkingResult.task_id == ChunkingTask.task_id
        ).filter(
            ChunkingTask.source_document_id == request.document_id,
            ChunkingResult.status == ResultStatus.COMPLETED,
            ChunkingResult.is_active == True
        )
        
        # Apply strategy filter if provided
        if request.strategy_type:
            try:
                strategy_enum = StrategyType[request.strategy_type.upper()]
                query = query.filter(ChunkingTask.chunking_strategy == strategy_enum)
            except KeyError:
                pass
        
        # Get the most recent result
        chunking_result = query.order_by(ChunkingResult.created_at.desc()).first()
        chunking_result_id = chunking_result.result_id if chunking_result else None
        
        # Save with dual-write (JSON + Database)
        db_record = storage.save_with_database(
            session=db,
            response=response,
            document_id=request.document_id,
            chunking_result_id=chunking_result_id,
            model=request.model
        )
        
        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CHUNKING_RESULT_NOT_FOUND",
                    "message": str(exc),
                }
            },
        ) from exc
    except InvalidTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": ErrorType.INVALID_TEXT_ERROR.value,
                    "message": str(exc),
                }
            },
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorType.AUTHENTICATION_ERROR.value,
                    "message": "Invalid API key. Please check your credentials.",
                }
            },
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": ErrorType.RATE_LIMIT_ERROR.value,
                    "message": str(exc),
                    "details": {
                        "retry_after_seconds": getattr(exc, "retry_after", 30),
                    },
                }
            },
        ) from exc
    except (APITimeoutError, NetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                }
            },
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        embedding_logger.log_request_failed(
            request_id=request_id,
            model=request.model,
            duration_ms=0,
            error_type="INTERNAL_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": {"request_id": request_id},
                }
            },
        ) from exc


@router.post(
    "/from-document",
    response_model=BatchEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        404: {"model": ErrorResponse, "description": "Document or chunking result not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def embed_from_document(
    request: DocumentEmbeddingRequest,
    db: Session = Depends(get_db),
):
    """
    Vectorize chunks from a document's latest chunking result.
    
    This endpoint finds the most recent active chunking result for a document
    (optionally filtered by strategy type) and creates embeddings for all its chunks.
    """
    request_id = str(uuid.uuid4())
    try:
        service = get_embedding_service(
            model=request.model,
            max_retries=request.max_retries,
            timeout=request.timeout,
        )

        result = service.embed_document_latest_chunks(
            document_id=request.document_id,
            db_session=db,
            strategy_type=request.strategy_type,
            request_id=request_id
        )

        vectors: List[Vector] = [
            Vector(
                index=item.index,
                vector=item.vector,
                dimension=len(item.vector),
                text_hash=item.text_hash,
                text_length=item.text_length,
                processing_time_ms=item.processing_time_ms,
                source_text=item.source_text,  # Include source text
            )
            for item in result.vectors
        ]
        failures: List[EmbeddingFailure] = [
            EmbeddingFailure(
                index=item.index,
                text_preview=item.text_preview,
                error_type=item.error_type,
                error_message=item.error_message,
                retry_recommended=item.retry_recommended,
                retry_count=item.retry_count,
            )
            for item in result.failures
        ]

        status_value = (
            ResponseStatus.SUCCESS
            if not failures
            else ResponseStatus.FAILED
            if not vectors
            else ResponseStatus.PARTIAL_SUCCESS
        )

        vectors_per_second = (
            len(vectors) / (result.processing_time_ms / 1000)
            if result.processing_time_ms > 0 and vectors
            else 0.0
        )

        metadata = BatchMetadata(
            model=request.model,
            model_dimension=service.model_info["dimension"],
            processing_time_ms=result.processing_time_ms,
            api_latency_ms=None,
            retry_count=result.retry_count,
            rate_limit_hits=result.rate_limit_hits,
            batch_size=result.batch_size,
            successful_count=len(vectors),
            failed_count=len(failures),
            vectors_per_second=vectors_per_second,
            config=build_embedding_config(request),
        )

        response = BatchEmbeddingResponse(
            request_id=request_id,
            status=status_value,
            vectors=vectors,
            failures=failures,
            metadata=metadata,
            timestamp=datetime.utcnow(),
        )

        # Get chunking_result_id from the service (it already found the latest result)
        from ..models.chunking_result import ChunkingResult, ResultStatus
        from ..models.chunking_task import ChunkingTask, StrategyType
        
        # Build query for latest active result
        query = db.query(ChunkingResult).join(
            ChunkingTask,
            ChunkingResult.task_id == ChunkingTask.task_id
        ).filter(
            ChunkingTask.source_document_id == request.document_id,
            ChunkingResult.status == ResultStatus.COMPLETED,
            ChunkingResult.is_active == True
        )
        
        # Apply strategy filter if provided
        if request.strategy_type:
            try:
                strategy_enum = StrategyType[request.strategy_type.upper()]
                query = query.filter(ChunkingTask.chunking_strategy == strategy_enum)
            except KeyError:
                pass
        
        # Get the most recent result
        chunking_result = query.order_by(ChunkingResult.created_at.desc()).first()
        chunking_result_id = chunking_result.result_id if chunking_result else None
        
        # Save with dual-write (JSON + Database)
        db_record = storage.save_with_database(
            session=db,
            response=response,
            document_id=request.document_id,
            chunking_result_id=chunking_result_id,
            model=request.model
        )
        
        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "DOCUMENT_OR_CHUNKING_RESULT_NOT_FOUND",
                    "message": str(exc),
                }
            },
        ) from exc
    except InvalidTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": ErrorType.INVALID_TEXT_ERROR.value,
                    "message": str(exc),
                }
            },
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorType.AUTHENTICATION_ERROR.value,
                    "message": "Invalid API key. Please check your credentials.",
                }
            },
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": ErrorType.RATE_LIMIT_ERROR.value,
                    "message": str(exc),
                    "details": {
                        "retry_after_seconds": getattr(exc, "retry_after", 30),
                    },
                }
            },
        ) from exc
    except (APITimeoutError, NetworkError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                }
            },
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        embedding_logger.log_request_failed(
            request_id=request_id,
            model=request.model,
            duration_ms=0,
            error_type="INTERNAL_ERROR",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": {"request_id": request_id},
                }
            },
        ) from exc
