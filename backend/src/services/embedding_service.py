"""Embedding service with single and batch vectorization support."""
from __future__ import annotations

import hashlib
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple

from langchain_openai import OpenAIEmbeddings

from ..models.embedding_models import (
    APITimeoutError,
    AuthenticationError,
    BatchSizeLimitError,
    EmbeddingFailure,
    ErrorType,
    InvalidTextError,
    NetworkError,
    RateLimitError,
    VectorDimensionMismatchError,
)
from ..utils.logging_utils import embedding_logger
from ..utils.retry_utils import ExponentialBackoffRetry, detect_rate_limit_error

MAX_BATCH_SIZE = 1000


EMBEDDING_MODELS: Dict[str, Dict[str, object]] = {
    "bge-m3": {
        "name": "bge-m3",
        "dimension": 1024,
        "description": "BGE-M3 多语言模型，支持中英文，性能优秀",
        "provider": "bge",
        "supports_multilingual": True,
        "max_batch_size": 1000,
    },
    "qwen3-embedding-8b": {
        "name": "qwen3-embedding-8b",
        "dimension": 1536,
        "description": "通义千问 Embedding 模型，8B 参数",
        "provider": "qwen",
        "supports_multilingual": True,
        "max_batch_size": 1000,
    },
    "hunyuan-embedding": {
        "name": "hunyuan-embedding",
        "dimension": 1024,
        "description": "腾讯混元 Embedding 模型",
        "provider": "hunyuan",
        "supports_multilingual": True,
        "max_batch_size": 1000,
    },
    "jina-embeddings-v4": {
        "name": "jina-embeddings-v4",
        "dimension": 768,
        "description": "Jina AI Embeddings v4，多语言支持",
        "provider": "jina",
        "supports_multilingual": True,
        "max_batch_size": 1000,
    },
}


@dataclass
class SingleEmbeddingResult:
    """Outcome of a single text embedding call."""

    request_id: str
    vector: List[float]
    text_length: int
    api_latency_ms: float
    processing_time_ms: float
    retry_count: int
    rate_limit_hits: int


@dataclass
class DocumentVectorResult:
    """Successful document embedding result."""

    index: int
    vector: List[float]
    text_hash: str
    text_length: int
    processing_time_ms: float


@dataclass
class DocumentFailureResult:
    """Failed document embedding result."""

    index: int
    text_preview: str
    error_type: ErrorType
    error_message: str
    retry_recommended: bool
    retry_count: int


@dataclass
class BatchEmbeddingResult:
    """Outcome of a batch embedding request."""

    request_id: str
    batch_size: int
    vectors: List[DocumentVectorResult]
    failures: List[DocumentFailureResult]
    processing_time_ms: float
    retry_count: int
    rate_limit_hits: int


class EmbeddingService:
    """Vector embedding service built on OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str,
        model: Literal[
            "bge-m3",
            "qwen3-embedding-8b",
            "hunyuan-embedding",
            "jina-embeddings-v4",
        ] = "qwen3-embedding-8b",
        base_url: str = "http://dev.fit-ai.woa.com/api/llmproxy",
        max_retries: int = 3,
        request_timeout: int = 60,
        embeddings_client: Optional[OpenAIEmbeddings] = None,
        **kwargs,
    ) -> None:
        if model not in EMBEDDING_MODELS:
            raise ValueError(
                f"不支持的模型: {model}. 支持的模型: {', '.join(EMBEDDING_MODELS.keys())}"
            )

        self.model = model
        self.model_info = EMBEDDING_MODELS[model]
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.max_batch_size = int(
            min(MAX_BATCH_SIZE, self.model_info.get("max_batch_size", MAX_BATCH_SIZE))
        )

        self.retry_handler = ExponentialBackoffRetry(
            max_retries=max_retries,
            initial_delay=1.0,
            max_delay=32.0,
        )

        self.embeddings = embeddings_client or OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            max_retries=0,
            request_timeout=request_timeout,
            **kwargs,
        )

    def embed_query(self, text: str, request_id: Optional[str] = None) -> SingleEmbeddingResult:
        """Vectorize a single text with validation, retries, and logging."""
        if request_id is None:
            request_id = str(uuid.uuid4())

        validated_text = self._validate_text(text)
        embedding_logger.log_request_start(
            request_id=request_id,
            model=self.model,
            batch_size=1,
            is_single=True,
        )

        start_time = time.time()
        api_start = 0.0
        retry_count = 0
        rate_limit_hits = 0

        def _call_embedding() -> List[float]:
            nonlocal retry_count, rate_limit_hits, api_start
            api_start = time.time()
            try:
                return self.embeddings.embed_query(validated_text)
            except Exception as raw_error:  # pragma: no cover - defensive
                service_error = self._to_service_error(raw_error, request_id)
                if isinstance(service_error, (RateLimitError, APITimeoutError, NetworkError)):
                    retry_count += 1
                    if isinstance(service_error, RateLimitError):
                        rate_limit_hits += 1
                raise service_error

        try:
            vector = self.retry_handler.execute(
                _call_embedding,
                retryable_exceptions=(RateLimitError, APITimeoutError, NetworkError),
                on_retry=self._create_retry_callback(request_id),
            )
            vector = self._validate_vector_dimensions(vector, request_id)
            api_latency_ms = (time.time() - api_start) * 1000 if api_start else 0.0
            processing_time_ms = (time.time() - start_time) * 1000

            embedding_logger.log_request_complete(
                request_id=request_id,
                model=self.model,
                duration_ms=processing_time_ms,
                batch_size=1,
                successful_count=1,
                failed_count=0,
                retry_count=retry_count,
                rate_limit_hits=rate_limit_hits,
            )

            return SingleEmbeddingResult(
                request_id=request_id,
                vector=vector,
                text_length=len(validated_text),
                api_latency_ms=api_latency_ms,
                processing_time_ms=processing_time_ms,
                retry_count=retry_count,
                rate_limit_hits=rate_limit_hits,
            )
        except Exception as exc:  # pragma: no cover - defensive
            duration_ms = (time.time() - start_time) * 1000
            embedding_logger.log_request_failed(
                request_id=request_id,
                model=self.model,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
                retry_count=retry_count,
            )
            raise

    def embed_documents(
        self, texts: Sequence[str], request_id: Optional[str] = None
    ) -> BatchEmbeddingResult:
        """Vectorize multiple texts with partial failure handling."""
        if not texts:
            raise InvalidTextError("texts must contain at least 1 item")

        self._validate_batch_size(len(texts))
        batch_request_id = request_id or str(uuid.uuid4())
        embedding_logger.log_request_start(
            request_id=batch_request_id,
            model=self.model,
            batch_size=len(texts),
            is_single=False,
        )

        start_time = time.time()
        vectors: List[DocumentVectorResult] = []
        failures: List[DocumentFailureResult] = []
        total_retry_count = 0
        total_rate_limit_hits = 0

        for index, raw_text in enumerate(texts):
            try:
                validated_text = self._validate_text(raw_text)
            except InvalidTextError as err:
                failures.append(
                    self._build_failure(
                        index=index,
                        error_type=ErrorType.INVALID_TEXT_ERROR,
                        error_message=str(err),
                        retry_recommended=False,
                        retry_count=0,
                        text_preview=raw_text[:50],
                    )
                )
                continue

            doc_retry_count = 0
            doc_rate_limit_hits = 0
            doc_request_id = f"{batch_request_id}-{index}"

            def _embed_single_document() -> List[float]:
                nonlocal doc_retry_count, doc_rate_limit_hits
                try:
                    return self.embeddings.embed_query(validated_text)
                except Exception as raw_error:  # pragma: no cover - defensive
                    service_error = self._to_service_error(raw_error, doc_request_id)
                    if isinstance(service_error, (RateLimitError, APITimeoutError, NetworkError)):
                        doc_retry_count += 1
                        if isinstance(service_error, RateLimitError):
                            doc_rate_limit_hits += 1
                    raise service_error

            try:
                doc_start = time.time()
                vector = self.retry_handler.execute(
                    _embed_single_document,
                    retryable_exceptions=(RateLimitError, APITimeoutError, NetworkError),
                    on_retry=self._create_retry_callback(doc_request_id),
                )
                vector = self._validate_vector_dimensions(vector, batch_request_id)
                duration_ms = (time.time() - doc_start) * 1000
                vectors.append(
                    DocumentVectorResult(
                        index=index,
                        vector=vector,
                        text_hash=self._hash_text(validated_text),
                        text_length=len(validated_text),
                        processing_time_ms=duration_ms,
                    )
                )
                total_retry_count += doc_retry_count
                total_rate_limit_hits += doc_rate_limit_hits
            except (RateLimitError, APITimeoutError, NetworkError, AuthenticationError) as err:
                failures.append(
                    self._build_failure(
                        index=index,
                        error_type=self._map_error_type(err),
                        error_message=str(err),
                        retry_recommended=isinstance(
                            err, (RateLimitError, APITimeoutError, NetworkError)
                        ),
                        retry_count=doc_retry_count,
                        text_preview=validated_text[:50],
                    )
                )
                total_retry_count += doc_retry_count
                total_rate_limit_hits += doc_rate_limit_hits
            except Exception as err:  # pragma: no cover - defensive
                failures.append(
                    self._build_failure(
                        index=index,
                        error_type=ErrorType.UNKNOWN_ERROR,
                        error_message=str(err),
                        retry_recommended=False,
                        retry_count=doc_retry_count,
                        text_preview=validated_text[:50],
                    )
                )
                total_retry_count += doc_retry_count
                total_rate_limit_hits += doc_rate_limit_hits

        processing_time_ms = (time.time() - start_time) * 1000
        successful_count = len(vectors)
        failed_count = len(failures)

        embedding_logger.log_request_complete(
            request_id=batch_request_id,
            model=self.model,
            duration_ms=processing_time_ms,
            batch_size=len(texts),
            successful_count=successful_count,
            failed_count=failed_count,
            retry_count=total_retry_count,
            rate_limit_hits=total_rate_limit_hits,
        )

        if failed_count and successful_count:
            failure_summary = Counter(f.error_type for f in failures)
            embedding_logger.log_partial_success(
                request_id=batch_request_id,
                model=self.model,
                batch_size=len(texts),
                successful_count=successful_count,
                failed_count=failed_count,
                failure_types={k.value: v for k, v in failure_summary.items()},
            )
        elif failed_count and not successful_count:
            embedding_logger.log_request_failed(
                request_id=batch_request_id,
                model=self.model,
                duration_ms=processing_time_ms,
                error_type="BATCH_FAILED",
                error_message="All documents failed to embed",
                retry_count=total_retry_count,
            )

        return BatchEmbeddingResult(
            request_id=batch_request_id,
            batch_size=len(texts),
            vectors=vectors,
            failures=failures,
            processing_time_ms=processing_time_ms,
            retry_count=total_retry_count,
            rate_limit_hits=total_rate_limit_hits,
        )

    def get_model_info(self) -> Dict[str, object]:
        """Return configuration for current model."""
        return {
            "model": self.model,
            **self.model_info,
        }

    @staticmethod
    def list_available_models() -> Dict[str, Dict[str, object]]:
        """Return all supported embedding model configurations."""
        return EMBEDDING_MODELS

    def _validate_text(self, text: str) -> str:
        if not text or not text.strip():
            raise InvalidTextError("Text must contain non-whitespace characters")
        return text

    def _validate_vector_dimensions(
        self, vector: List[float], request_id: str
    ) -> List[float]:
        actual_dim = len(vector)
        expected_dim = int(self.model_info["dimension"])
        if actual_dim != expected_dim:
            embedding_logger.log_dimension_mismatch(
                request_id=request_id,
                model=self.model,
                expected_dimension=expected_dim,
                actual_dimension=actual_dim,
            )
            raise VectorDimensionMismatchError(
                expected=expected_dim,
                actual=actual_dim,
                model=self.model,
            )
        return vector

    def _validate_batch_size(self, batch_size: int) -> None:
        if batch_size > self.max_batch_size:
            raise BatchSizeLimitError(size=batch_size, max_size=self.max_batch_size)

    def _create_retry_callback(self, request_id: str) -> Callable[[Exception, int, float], None]:
        def _callback(error: Exception, attempt: int, delay_seconds: float) -> None:
            embedding_logger.log_retry_attempt(
                request_id=request_id,
                attempt=attempt,
                max_retries=self.max_retries,
                delay_ms=delay_seconds * 1000,
                error_type=type(error).__name__,
            )

        return _callback

    def _to_service_error(
        self, error: Exception, request_id: str
    ) -> Exception:  # pragma: no cover - defensive
        if isinstance(
            error, (RateLimitError, APITimeoutError, NetworkError, AuthenticationError)
        ):
            return error

        is_rate_limited, retry_after = detect_rate_limit_error(error)
        if is_rate_limited:
            embedding_logger.log_rate_limit_hit(
                request_id=request_id,
                model=self.model,
                retry_after_seconds=retry_after,
            )
            return RateLimitError(str(error), retry_after=retry_after)

        message = str(error).lower()
        if "timeout" in message or isinstance(error, TimeoutError):
            return APITimeoutError(str(error))
        if "connection" in message or "network" in message:
            return NetworkError(str(error))
        if "invalid api key" in message or "authentication" in message:
            return AuthenticationError(str(error))

        return error

    def _map_error_type(self, error: Exception) -> ErrorType:
        if isinstance(error, InvalidTextError):
            return ErrorType.INVALID_TEXT_ERROR
        if isinstance(error, RateLimitError):
            return ErrorType.RATE_LIMIT_ERROR
        if isinstance(error, APITimeoutError):
            return ErrorType.API_TIMEOUT_ERROR
        if isinstance(error, NetworkError):
            return ErrorType.NETWORK_ERROR
        if isinstance(error, AuthenticationError):
            return ErrorType.AUTHENTICATION_ERROR
        if isinstance(error, VectorDimensionMismatchError):
            return ErrorType.DIMENSION_MISMATCH_ERROR
        return ErrorType.UNKNOWN_ERROR

    def _build_failure(
        self,
        index: int,
        error_type: ErrorType,
        error_message: str,
        retry_recommended: bool,
        retry_count: int,
        text_preview: str,
    ) -> DocumentFailureResult:
        return DocumentFailureResult(
            index=index,
            text_preview=text_preview,
            error_type=error_type,
            error_message=error_message,
            retry_recommended=retry_recommended,
            retry_count=retry_count,
        )

    @staticmethod
    def _hash_text(text: str) -> str:
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    import os

    api_key = os.getenv("EMBEDDING_API_KEY", "test-key")
    service = EmbeddingService(api_key=api_key)
    print("Available models:")
    for name, info in EmbeddingService.list_available_models().items():
        print(f"- {name}: {info['dimension']} dims")

    try:
        result = service.embed_query("hello world")
        print(f"Single vector length: {len(result.vector)}")
    except Exception as exc:  # pragma: no cover - manual feedback
        print(f"Single embedding failed: {exc}")

    batch_result = service.embed_documents(["Doc 1", "", "Doc 3"])
    print(
        f"Batch success={len(batch_result.vectors)}, failures={len(batch_result.failures)}"
    )
