"""FastAPI routes for embedding operations."""
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

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
)
from ..services.embedding_service import EmbeddingService, EMBEDDING_MODELS
from ..storage.embedding_storage import EmbeddingStorage
from ..utils.logging_utils import embedding_logger

router = APIRouter(prefix="/embedding", tags=["embedding"])
storage = EmbeddingStorage(
    results_dir=os.getenv("EMBEDDING_RESULTS_DIR", "results/embedding")
)
DEFAULT_MAX_BATCH_SIZE = 1000


def build_embedding_config(request) -> EmbeddingConfig:
    return EmbeddingConfig(
        api_endpoint=os.getenv("EMBEDDING_API_BASE_URL", "http://dev.fit-ai.woa.com/api/llmproxy"),
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

    base_url = os.getenv("EMBEDDING_API_BASE_URL", "http://dev.fit-ai.woa.com/api/llmproxy")
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

        storage.save_batch_result(response)
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
    "/models",
    response_model=ModelsListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_models():
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
    return ModelsListResponse(models=models, count=len(models))


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
    try:
        api_key = os.getenv("EMBEDDING_API_KEY")
        api_connectivity = api_key is not None
        return {
            "status": "healthy" if api_connectivity else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "api_connectivity": api_connectivity,
        }
    except Exception:  # pragma: no cover - defensive
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "api_connectivity": False,
            },
        )
