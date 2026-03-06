"""Embedding service with single and batch vectorization support."""
from __future__ import annotations

import hashlib
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union

import httpx
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


# ============================================================================
# 通用文本 Embedding 模型
# ============================================================================
TEXT_EMBEDDING_MODELS: Dict[str, Dict[str, object]] = {
    "bge-m3": {
        "name": "bge-m3",
        "dimension": 1024,
        "max_sequence_length": 8192,
        "description": "BGE-M3 多语言模型，支持密集检索、多向量检索和稀疏检索",
        "provider": "bge",
        "supports_multilingual": True,
        "supports_instruction": False,
        "max_batch_size": 1000,
        "model_type": "text",
    },
    "qwen3-embedding-8b": {
        "name": "qwen3-embedding-8b",
        "dimension": 4096,
        "max_sequence_length": 32768,
        "description": "通义千问 Embedding 8B，高精度、长文本支持、动态维度输出",
        "provider": "qwen",
        "supports_multilingual": True,
        "supports_instruction": True,
        "max_batch_size": 1000,
        "model_type": "text",
    },
}

# ============================================================================
# 多模态 Embedding 模型
# ============================================================================
MULTIMODAL_EMBEDDING_MODELS: Dict[str, Dict[str, object]] = {
    "qwen3-vl-embedding-8b": {
        "name": "qwen3-vl-embedding-8b",
        "dimension": 4096,  # 支持自定义输出维度 (64 至 4096)
        "min_dimension": 64,
        "max_dimension": 4096,
        "max_sequence_length": 32768,
        "description": "通义千问多模态 Embedding 8B，支持文本、图像、截图、视频及任意多模态组合输入",
        "provider": "qwen",
        "supports_multilingual": True,
        "supports_instruction": True,
        "max_batch_size": 1000,
        "model_type": "multimodal",
        "supported_inputs": ["text", "image", "video", "text+image"],
        "core_features": [
            "统一语义空间中生成文本和视觉内容的向量表示",
            "实现高效的图文、文视频等多模态相似度计算与检索",
        ],
    },
}

# ============================================================================
# 合并所有 Embedding 模型 (保持向后兼容)
# ============================================================================
EMBEDDING_MODELS: Dict[str, Dict[str, object]] = {
    **TEXT_EMBEDDING_MODELS,
    **MULTIMODAL_EMBEDDING_MODELS,
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
    source_text: str  # Add original source text
    chunk_type: str = "text"  # 分块类型: text, table, image, code
    chunk_metadata: Optional[Dict[str, Any]] = None  # chunker 提取的结构化 metadata（heading_path, section_title 等）


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
            "qwen3-vl-embedding-8b",
        ] = "qwen3-embedding-8b",
        base_url: str = "",  # 必须通过参数传入，不提供默认值
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

        # 保存 API 配置用于多模态模型直接调用
        self._api_key = api_key
        self._base_url = base_url.rstrip('/') if base_url else ""
        
        # 多模态模型使用直接 HTTP 调用，文本模型使用 LangChain
        if self._is_multimodal_model():
            self.embeddings = None  # 多模态模型不使用 LangChain
        else:
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
                # 多模态模型使用专门的调用方法
                if self._is_multimodal_model():
                    return self._embed_query_multimodal(validated_text)
                else:
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
        self, texts: Sequence[str], request_id: Optional[str] = None,
        chunk_types: Optional[List[str]] = None,
        chunk_metadata_list: Optional[List[Optional[Dict[str, Any]]]] = None
    ) -> BatchEmbeddingResult:
        """Vectorize multiple texts with true batch API call for better performance.
        
        优化说明：
        - 使用 langchain OpenAIEmbeddings.embed_documents() 进行真正的批量 API 调用
        - 将 N 次串行请求减少为 1 次批量请求，大幅提升性能
        - 保留验证失败的文本记录，批量处理有效文本
        
        Args:
            texts: 要向量化的文本列表
            request_id: 请求ID
            chunk_types: 每个文本对应的分块类型列表 (text, table, image, code)
        """
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

        # 如果没有传入chunk_types，默认全部为text
        if chunk_types is None:
            chunk_types = ["text"] * len(texts)
        # 如果没有传入chunk_metadata_list，默认全部为None
        if chunk_metadata_list is None:
            chunk_metadata_list = [None] * len(texts)

        # 第一步：验证所有文本，分离有效和无效文本
        validated_texts: List[str] = []
        valid_indices: List[int] = []  # 记录有效文本的原始索引
        valid_chunk_types: List[str] = []  # 记录有效文本对应的chunk_type
        valid_chunk_metadata: List[Optional[Dict[str, Any]]] = []  # 记录有效文本对应的chunk_metadata
        
        for index, raw_text in enumerate(texts):
            try:
                validated_text = self._validate_text(raw_text)
                validated_texts.append(validated_text)
                valid_indices.append(index)
                valid_chunk_types.append(chunk_types[index] if index < len(chunk_types) else "text")
                valid_chunk_metadata.append(chunk_metadata_list[index] if index < len(chunk_metadata_list) else None)
            except InvalidTextError as err:
                failures.append(
                    self._build_failure(
                        index=index,
                        error_type=ErrorType.INVALID_TEXT_ERROR,
                        error_message=str(err),
                        retry_recommended=False,
                        retry_count=0,
                        text_preview=raw_text[:50] if raw_text else "",
                    )
                )

        # 第二步：如果有有效文本，使用批量 API 调用
        if validated_texts:
            def _embed_batch() -> List[List[float]]:
                nonlocal total_retry_count, total_rate_limit_hits
                try:
                    # 多模态模型使用专门的调用方法
                    if self._is_multimodal_model():
                        return self._embed_documents_multimodal(validated_texts)
                    else:
                        # 使用真正的批量 API：一次请求处理所有文本
                        return self.embeddings.embed_documents(validated_texts)
                except Exception as raw_error:  # pragma: no cover - defensive
                    service_error = self._to_service_error(raw_error, batch_request_id)
                    if isinstance(service_error, (RateLimitError, APITimeoutError, NetworkError)):
                        total_retry_count += 1
                        if isinstance(service_error, RateLimitError):
                            total_rate_limit_hits += 1
                    raise service_error

            try:
                batch_start = time.time()
                # 批量获取所有 embeddings
                all_vectors = self.retry_handler.execute(
                    _embed_batch,
                    retryable_exceptions=(RateLimitError, APITimeoutError, NetworkError),
                    on_retry=self._create_retry_callback(batch_request_id),
                )
                batch_duration_ms = (time.time() - batch_start) * 1000
                avg_duration_per_doc = batch_duration_ms / len(validated_texts) if validated_texts else 0

                # 处理批量结果，将向量与原始索引关联
                for i, (vector, original_index) in enumerate(zip(all_vectors, valid_indices)):
                    validated_text = validated_texts[i]
                    current_chunk_type = valid_chunk_types[i] if i < len(valid_chunk_types) else "text"
                    current_chunk_metadata = valid_chunk_metadata[i] if i < len(valid_chunk_metadata) else None
                    try:
                        vector = self._validate_vector_dimensions(vector, batch_request_id)
                        vectors.append(
                            DocumentVectorResult(
                                index=original_index,
                                vector=vector,
                                text_hash=self._hash_text(validated_text),
                                text_length=len(validated_text),
                                processing_time_ms=avg_duration_per_doc,
                                source_text=validated_text,
                                chunk_type=current_chunk_type,
                                chunk_metadata=current_chunk_metadata,
                            )
                        )
                    except VectorDimensionMismatchError as err:
                        failures.append(
                            self._build_failure(
                                index=original_index,
                                error_type=ErrorType.DIMENSION_MISMATCH_ERROR,
                                error_message=str(err),
                                retry_recommended=False,
                                retry_count=0,
                                text_preview=validated_text[:50],
                            )
                        )
            except (RateLimitError, APITimeoutError, NetworkError, AuthenticationError) as err:
                # 批量请求失败，将所有有效文本标记为失败
                for i, original_index in enumerate(valid_indices):
                    failures.append(
                        self._build_failure(
                            index=original_index,
                            error_type=self._map_error_type(err),
                            error_message=str(err),
                            retry_recommended=isinstance(
                                err, (RateLimitError, APITimeoutError, NetworkError)
                            ),
                            retry_count=total_retry_count,
                            text_preview=validated_texts[i][:50],
                        )
                    )
            except Exception as err:  # pragma: no cover - defensive
                # 未知错误，将所有有效文本标记为失败
                for i, original_index in enumerate(valid_indices):
                    failures.append(
                        self._build_failure(
                            index=original_index,
                            error_type=ErrorType.UNKNOWN_ERROR,
                            error_message=str(err),
                            retry_recommended=False,
                            retry_count=total_retry_count,
                            text_preview=validated_texts[i][:50],
                        )
                    )

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

    def _is_multimodal_model(self) -> bool:
        """Check if current model supports multimodal inputs."""
        return self.model in MULTIMODAL_EMBEDDING_MODELS

    def _build_multimodal_input(
        self,
        text: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        构建多模态模型的输入格式。
        
        根据 qwen3-vl-embedding-8b API 文档，输入格式为:
        [
            { "type": "image_url", "image_url": {"url": "..."} },  # 可选
            { "type": "text", "text": "..." }  # 必需
        ]
        
        Args:
            text: 文本内容（必需）
            image_url: 图片 URL（可选）
            image_base64: 图片 base64 编码（可选，会转换为 data URL）
            mime_type: 图片 MIME 类型（可选，默认 image/png）
            
        Returns:
            多模态输入列表
        """
        input_items: List[Dict[str, Any]] = []
        
        # 添加图片输入（如果有）
        if image_url:
            input_items.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
        elif image_base64:
            # 将 base64 转换为 data URL 格式
            # 使用传入的 MIME 类型，或根据常见格式默认为 image/png
            actual_mime_type = mime_type or "image/png"
            data_url = f"data:{actual_mime_type};base64,{image_base64}"
            input_items.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        
        # 添加文本输入（必需）
        input_items.append({
            "type": "text",
            "text": text
        })
        
        return input_items

    def _call_multimodal_embedding_api(
        self,
        inputs: List[Union[str, List[Dict[str, Any]]]],
        request_id: str,
    ) -> List[List[float]]:
        """
        直接调用多模态 embedding API。
        
        使用 OpenAI 兼容格式调用 qwen3-vl-embedding-8b:
        POST /embeddings
        {
            "model": "qwen3-vl-embedding-8b",
            "input": [...],  # 多模态输入格式
            "encoding_format": "float"
        }
        
        Args:
            inputs: 输入列表，每个元素是多模态格式的输入
            request_id: 请求 ID 用于日志
            
        Returns:
            向量列表
        """
        url = f"{self._base_url}/embeddings"
        
        # 构建请求体
        request_body = {
            "model": self.model,
            "input": inputs,
            "encoding_format": "float"
        }
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        
        # === DEBUG 日志：打印发送给API的输入结构 ===
        embedding_logger.logger.info(f"[DEBUG] Multimodal API call - request_id: {request_id}")
        embedding_logger.logger.info(f"[DEBUG] Number of inputs: {len(inputs)}")
        for idx, inp in enumerate(inputs):
            if isinstance(inp, list):
                # 多模态输入
                has_image = any(item.get("type") == "image_url" for item in inp)
                has_text = any(item.get("type") == "text" for item in inp)
                if has_image:
                    # 找到图片项
                    for item in inp:
                        if item.get("type") == "image_url":
                            image_url = item.get("image_url", {}).get("url", "")
                            if image_url.startswith("data:"):
                                # data URL 格式
                                mime_type = image_url.split(";")[0].split(":")[1] if ";" in image_url else "unknown"
                                base64_len = len(image_url.split(",")[1]) if "," in image_url else 0
                                embedding_logger.logger.info(
                                    f"[DEBUG] Input[{idx}]: MULTIMODAL (image + text), "
                                    f"mime_type={mime_type}, image_base64_len={base64_len}"
                                )
                            else:
                                embedding_logger.logger.info(
                                    f"[DEBUG] Input[{idx}]: MULTIMODAL (image URL + text), url={image_url[:100]}..."
                                )
                            break
                else:
                    text_content = ""
                    for item in inp:
                        if item.get("type") == "text":
                            text_content = item.get("text", "")[:100]
                            break
                    embedding_logger.logger.info(
                        f"[DEBUG] Input[{idx}]: TEXT ONLY in multimodal format, text={text_content}..."
                    )
            else:
                embedding_logger.logger.info(f"[DEBUG] Input[{idx}]: PLAIN TEXT, text={str(inp)[:100]}...")
        
        try:
            with httpx.Client(timeout=self.request_timeout) as client:
                response = client.post(url, json=request_body, headers=headers)
                
                if response.status_code == 429:
                    # 速率限制
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(
                        f"Rate limit exceeded: {response.text}",
                        retry_after=float(retry_after)
                    )
                elif response.status_code == 401:
                    raise AuthenticationError(f"Authentication failed: {response.text}")
                elif response.status_code >= 400:
                    # 其他错误
                    error_msg = f"API error {response.status_code}: {response.text}"
                    embedding_logger.logger.error(f"Multimodal API error: {error_msg}")
                    raise NetworkError(error_msg)
                
                result = response.json()
                
                # 提取向量
                vectors = []
                for item in result.get("data", []):
                    vectors.append(item.get("embedding", []))
                
                return vectors
                
        except httpx.TimeoutException as e:
            raise APITimeoutError(f"Request timeout: {str(e)}")
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {str(e)}")

    def _embed_query_multimodal(
        self,
        text: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> List[float]:
        """
        使用多模态模型进行单个文本/图文嵌入。
        
        Args:
            text: 文本内容
            image_url: 图片 URL（可选）
            image_base64: 图片 base64（可选）
            
        Returns:
            嵌入向量
        """
        multimodal_input = self._build_multimodal_input(text, image_url, image_base64)
        vectors = self._call_multimodal_embedding_api(
            inputs=[multimodal_input],
            request_id=str(uuid.uuid4())
        )
        return vectors[0] if vectors else []

    def _embed_documents_multimodal(
        self,
        texts: List[str],
        image_urls: Optional[List[Optional[str]]] = None,
        image_base64s: Optional[List[Optional[str]]] = None,
    ) -> List[List[float]]:
        """
        使用多模态模型进行批量文本/图文嵌入。
        
        Args:
            texts: 文本列表
            image_urls: 图片 URL 列表（可选，与 texts 长度对应）
            image_base64s: 图片 base64 列表（可选，与 texts 长度对应）
            
        Returns:
            嵌入向量列表
        """
        # 构建多模态输入列表
        inputs = []
        for i, text in enumerate(texts):
            img_url = image_urls[i] if image_urls and i < len(image_urls) else None
            img_b64 = image_base64s[i] if image_base64s and i < len(image_base64s) else None
            multimodal_input = self._build_multimodal_input(text, img_url, img_b64)
            inputs.append(multimodal_input)
        
        return self._call_multimodal_embedding_api(
            inputs=inputs,
            request_id=str(uuid.uuid4())
        )

    def _load_image_base64(self, image_path: str) -> Optional[str]:
        """
        Load original image from file path and convert to base64.
        
        This is called during embedding phase for image chunks when using
        multimodal models. The image data is loaded on-demand rather than
        being stored in the chunking result.
        
        Note: thumbnail_base64 in chunk metadata is only for preview purposes,
        the original image should be used for multimodal embedding to preserve
        full image quality and details.
        
        Args:
            image_path: Path to the image file (can be relative or absolute)
            
        Returns:
            Base64 encoded image string, or None if loading failed
        """
        import base64
        import os
        from pathlib import Path
        
        if not image_path:
            embedding_logger.logger.warning("Image path is empty")
            return None
        
        # 解析路径：处理相对路径和绝对路径
        resolved_path = self._resolve_image_path(image_path)
        
        if not resolved_path or not os.path.exists(resolved_path):
            embedding_logger.logger.warning(f"Image file not found: {image_path} (resolved: {resolved_path})")
            return None
        
        try:
            with open(resolved_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                embedding_logger.logger.info(
                    f"Loaded original image for multimodal embedding: {resolved_path} "
                    f"(size: {len(image_data)} chars)"
                )
                return image_data
        except Exception as e:
            embedding_logger.logger.warning(f"Failed to load image {resolved_path}: {e}")
            return None
    
    def _resolve_image_path(self, image_path: str) -> Optional[str]:
        """
        Resolve image path to absolute path.
        
        Handles multiple path formats:
        - Absolute paths: return as-is
        - Relative paths starting with '../uploads': resolve relative to backend/results
        - Other relative paths: try multiple base directories
        
        Args:
            image_path: Path to resolve
            
        Returns:
            Resolved absolute path, or None if invalid
        """
        import os
        from pathlib import Path
        
        if not image_path:
            return None
        
        # 如果已经是绝对路径且文件存在，直接返回
        if os.path.isabs(image_path):
            if os.path.exists(image_path):
                return image_path
            else:
                embedding_logger.logger.warning(f"Absolute path not found: {image_path}")
                return None
        
        # 获取项目根目录（backend 目录）
        # 当前文件在 backend/src/services/ 下，需要向上3级到达 backend/
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parent.parent.parent
        
        # 尝试多种路径解析策略
        possible_paths = []
        
        # 策略1：相对于 results 目录的路径（适用于 ../uploads/... 格式）
        if image_path.startswith('../'):
            possible_paths.append(backend_dir / 'results' / image_path)
            # 也尝试直接去掉 ../ 前缀
            clean_path = image_path.lstrip('../')
            possible_paths.append(backend_dir / clean_path)
        
        # 策略2：直接相对于 backend 目录
        possible_paths.append(backend_dir / image_path)
        
        # 策略3：如果路径包含 uploads/xx/figures，尝试替换为 figures
        # 因为有些系统可能将图片存储在不同的位置
        if 'uploads/' in image_path and '/figures/' in image_path:
            # 提取 figures 之后的部分
            figures_idx = image_path.find('/figures/')
            if figures_idx != -1:
                figures_path = image_path[figures_idx + 1:]  # 保留 'figures/...'
                possible_paths.append(backend_dir / figures_path)
        
        # 尝试所有可能的路径
        for path in possible_paths:
            resolved = path.resolve()
            if resolved.exists():
                embedding_logger.logger.debug(f"Resolved image path: {image_path} -> {resolved}")
                return str(resolved)
        
        # 记录所有尝试过的路径，方便调试
        tried_paths = [str(p.resolve()) for p in possible_paths]
        embedding_logger.logger.warning(
            f"Could not resolve image path: {image_path}. Tried: {tried_paths}"
        )
        return None

    def _prepare_chunk_for_embedding(
        self, 
        chunk, 
        is_multimodal: bool
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str]]:
        """
        Prepare a chunk for embedding, handling both text and image chunks.
        
        For multimodal models with image chunks:
        - Load original image base64 from file_path on demand (NOT thumbnail)
        - Use context information to enhance text description
        - Return both content and image_base64 for multimodal embedding
        
        Args:
            chunk: Chunk object from database
            is_multimodal: Whether using a multimodal embedding model
            
        Returns:
            Tuple of (text_content, chunk_type, image_base64, mime_type)
        """
        # 获取 chunk_type，如果是枚举类型则获取其 value
        # 注意：chunk_type 可能是 ChunkType 枚举对象（来自 Pydantic 模型）或字符串（来自数据库查询）
        # 枚举对象与字符串直接比较会返回 False，例如 ChunkType.IMAGE == 'image' 为 False
        # 因此需要统一转换为字符串进行后续的类型判断
        raw_chunk_type = chunk.chunk_type or 'text'
        if hasattr(raw_chunk_type, 'value'):
            chunk_type = raw_chunk_type.value  # 枚举类型，获取字符串值
        else:
            chunk_type = raw_chunk_type  # 已经是字符串
        
        text_content = chunk.content
        image_base64 = None
        mime_type = None
        
        # === DEBUG 日志：打印 chunk 基本信息 ===
        embedding_logger.logger.info(
            f"[DEBUG] _prepare_chunk_for_embedding: chunk_type={chunk_type}, "
            f"is_multimodal={is_multimodal}, content_preview={text_content[:50] if text_content else 'None'}..."
        )
        
        if is_multimodal and chunk_type == 'image':
            # For multimodal models, load original image data on demand
            # 注意：Chunk 模型的字段名是 chunk_metadata（JSON 字段），不是 metadata
            raw_metadata = getattr(chunk, 'chunk_metadata', None) or getattr(chunk, 'metadata', None) or {}
            
            # 处理 metadata 可能是字典或 Pydantic 对象的情况
            # 注意：从数据库查询返回的 chunk.chunk_metadata 可能是：
            # 1. dict 类型（SQLAlchemy 直接返回）
            # 2. Pydantic BaseModel 对象（通过 Pydantic 模型构造）
            # 3. Pydantic v2 的 BaseModel 对象（需要用 model_dump() 转换）
            # 由于 Pydantic 对象没有 .get() 方法，直接调用会报 "'MetaData' object has no attribute 'get'" 错误
            # 因此需要统一转换为字典格式
            if hasattr(raw_metadata, 'dict'):
                metadata = raw_metadata.dict()  # Pydantic v1 对象
            elif hasattr(raw_metadata, 'model_dump'):
                metadata = raw_metadata.model_dump()  # Pydantic v2 对象
            elif isinstance(raw_metadata, dict):
                metadata = raw_metadata  # 已经是字典
            else:
                metadata = {}  # 无法识别的类型，使用空字典
            
            image_path = metadata.get('image_path')
            mime_type = metadata.get('mime_type')
            
            # === DEBUG 日志：打印图片元数据 ===
            embedding_logger.logger.info(
                f"[DEBUG] Image chunk metadata: image_path={image_path}, mime_type={mime_type}, "
                f"has_thumbnail={bool(metadata.get('thumbnail_base64'))}, "
                f"context_before_len={len(metadata.get('context_before') or '')}, "
                f"context_after_len={len(metadata.get('context_after') or '')}"
            )
            
            if image_path:
                # 加载原始图片（不是缩略图 thumbnail_base64）
                image_base64 = self._load_image_base64(image_path)
                
                if image_base64:
                    # 构建增强的文本描述，包含图片上下文信息
                    text_content = self._build_image_text_description(metadata, chunk.content)
                    embedding_logger.logger.info(
                        f"[DEBUG] Image loaded successfully: path={image_path}, "
                        f"base64_len={len(image_base64)}, enhanced_text_len={len(text_content)}"
                    )
                else:
                    # 图片加载失败时，使用上下文信息作为降级文本
                    text_content = self._build_image_fallback_text(metadata, chunk.content)
                    embedding_logger.logger.warning(
                        f"[DEBUG] Image load failed, using fallback text: path={image_path}, "
                        f"fallback_text_len={len(text_content)}"
                    )
            else:
                embedding_logger.logger.warning(
                    f"[DEBUG] Image chunk has no image_path in metadata!"
                )
        
        return text_content, chunk_type, image_base64, mime_type
    
    def _build_image_text_description(self, metadata: dict, original_content: str) -> str:
        """
        Build enhanced text description for image chunk using context.
        
        This creates a richer text representation to pair with the image
        for better multimodal embedding quality.
        
        Args:
            metadata: Image chunk metadata containing context, alt_text, caption
            original_content: Original chunk content (usually "[Image: ...]")
            
        Returns:
            Enhanced text description
        """
        parts = []
        
        # 添加图片描述
        alt_text = metadata.get('alt_text')
        caption = metadata.get('caption')
        
        if caption:
            parts.append(f"图片标题: {caption}")
        if alt_text and alt_text != 'Image':
            parts.append(f"图片描述: {alt_text}")
        
        # 添加上下文信息（帮助模型理解图片在文档中的位置和语义）
        context_before = metadata.get('context_before')
        context_after = metadata.get('context_after')
        
        if context_before:
            # 截取上下文的最后部分，避免过长
            context_before = context_before[-200:] if len(context_before) > 200 else context_before
            parts.append(f"前文: {context_before}")
        
        if context_after:
            # 截取上下文的开始部分
            context_after = context_after[:200] if len(context_after) > 200 else context_after
            parts.append(f"后文: {context_after}")
        
        # 如果没有任何有用的信息，返回原始内容
        if not parts:
            return original_content
        
        return "\n".join(parts)
    
    def _build_image_fallback_text(self, metadata: dict, original_content: str) -> str:
        """
        Build fallback text description when image loading fails.
        
        Uses all available text information to create a reasonable
        text-only representation for embedding.
        
        Args:
            metadata: Image chunk metadata
            original_content: Original chunk content
            
        Returns:
            Fallback text for embedding
        """
        parts = []
        
        # 尽可能收集所有文本信息
        alt_text = metadata.get('alt_text')
        caption = metadata.get('caption')
        context_before = metadata.get('context_before', '')
        context_after = metadata.get('context_after', '')
        
        if caption:
            parts.append(caption)
        if alt_text and alt_text != 'Image':
            parts.append(alt_text)
        if context_before:
            parts.append(context_before[-150:])
        if context_after:
            parts.append(context_after[:150])
        
        if parts:
            return " ".join(parts)
        
        return original_content

    def _embed_chunks_multimodal(
        self,
        chunks: List[Any],
        request_id: Optional[str] = None
    ) -> BatchEmbeddingResult:
        """
        使用多模态模型对 chunks 进行批量嵌入。
        
        真正实现多模态向量化：
        - 图片块：从 image_path 加载图片数据，使用图文组合输入
        - 文本块：直接使用文本内容
        
        Args:
            chunks: Chunk 对象列表
            request_id: 请求 ID
            
        Returns:
            BatchEmbeddingResult 批量嵌入结果
        """
        if not chunks:
            raise InvalidTextError("chunks must contain at least 1 item")
        
        batch_request_id = request_id or str(uuid.uuid4())
        embedding_logger.log_request_start(
            request_id=batch_request_id,
            model=self.model,
            batch_size=len(chunks),
            is_single=False,
        )
        
        start_time = time.time()
        vectors: List[DocumentVectorResult] = []
        failures: List[DocumentFailureResult] = []
        total_retry_count = 0
        total_rate_limit_hits = 0
        
        # 准备多模态输入
        multimodal_inputs = []
        valid_indices = []
        chunk_texts = []  # 用于记录原始文本
        chunk_types_list = []  # 用于记录分块类型
        
        for index, chunk in enumerate(chunks):
            try:
                text_content, chunk_type, image_base64, mime_type = self._prepare_chunk_for_embedding(
                    chunk, is_multimodal=True
                )
                
                # 验证文本
                validated_text = self._validate_text(text_content)
                
                # 构建多模态输入
                if chunk_type == 'image' and image_base64:
                    # 图片块：使用图文组合输入（传入正确的MIME类型）
                    multimodal_input = self._build_multimodal_input(
                        text=validated_text,
                        image_base64=image_base64,
                        mime_type=mime_type
                    )
                    embedding_logger.logger.info(
                        f"Chunk {index}: Using multimodal input (image + text, mime: {mime_type})"
                    )
                else:
                    # 文本块：使用纯文本输入
                    multimodal_input = self._build_multimodal_input(text=validated_text)
                
                multimodal_inputs.append(multimodal_input)
                valid_indices.append(index)
                chunk_texts.append(validated_text)
                chunk_types_list.append(chunk_type or "text")  # 记录分块类型
                
            except InvalidTextError as err:
                failures.append(
                    self._build_failure(
                        index=index,
                        error_type=ErrorType.INVALID_TEXT_ERROR,
                        error_message=str(err),
                        retry_recommended=False,
                        retry_count=0,
                        text_preview=chunk.content[:50] if chunk.content else "",
                    )
                )
        
        # 批量调用多模态 API
        if multimodal_inputs:
            def _embed_multimodal_batch() -> List[List[float]]:
                nonlocal total_retry_count, total_rate_limit_hits
                try:
                    return self._call_multimodal_embedding_api(
                        inputs=multimodal_inputs,
                        request_id=batch_request_id
                    )
                except Exception as raw_error:
                    service_error = self._to_service_error(raw_error, batch_request_id)
                    if isinstance(service_error, (RateLimitError, APITimeoutError, NetworkError)):
                        total_retry_count += 1
                        if isinstance(service_error, RateLimitError):
                            total_rate_limit_hits += 1
                    raise service_error
            
            try:
                batch_start = time.time()
                all_vectors = self.retry_handler.execute(
                    _embed_multimodal_batch,
                    retryable_exceptions=(RateLimitError, APITimeoutError, NetworkError),
                    on_retry=self._create_retry_callback(batch_request_id),
                )
                batch_duration_ms = (time.time() - batch_start) * 1000
                avg_duration_per_doc = batch_duration_ms / len(multimodal_inputs) if multimodal_inputs else 0
                
                # 处理结果
                for i, (vector, original_index) in enumerate(zip(all_vectors, valid_indices)):
                    validated_text = chunk_texts[i]
                    current_chunk_type = chunk_types_list[i] if i < len(chunk_types_list) else "text"
                    try:
                        vector = self._validate_vector_dimensions(vector, batch_request_id)
                        vectors.append(
                            DocumentVectorResult(
                                index=original_index,
                                vector=vector,
                                text_hash=self._hash_text(validated_text),
                                text_length=len(validated_text),
                                processing_time_ms=avg_duration_per_doc,
                                source_text=validated_text,
                                chunk_type=current_chunk_type,
                            )
                        )
                    except VectorDimensionMismatchError as err:
                        failures.append(
                            self._build_failure(
                                index=original_index,
                                error_type=ErrorType.DIMENSION_MISMATCH_ERROR,
                                error_message=str(err),
                                retry_recommended=False,
                                retry_count=0,
                                text_preview=validated_text[:50],
                            )
                        )
            except (RateLimitError, APITimeoutError, NetworkError, AuthenticationError) as err:
                # 批量请求失败
                for i, original_index in enumerate(valid_indices):
                    failures.append(
                        self._build_failure(
                            index=original_index,
                            error_type=self._map_error_type(err),
                            error_message=str(err),
                            retry_recommended=isinstance(
                                err, (RateLimitError, APITimeoutError, NetworkError)
                            ),
                            retry_count=total_retry_count,
                            text_preview=chunk_texts[i][:50],
                        )
                    )
            except Exception as err:
                for i, original_index in enumerate(valid_indices):
                    failures.append(
                        self._build_failure(
                            index=original_index,
                            error_type=ErrorType.UNKNOWN_ERROR,
                            error_message=str(err),
                            retry_recommended=False,
                            retry_count=total_retry_count,
                            text_preview=chunk_texts[i][:50],
                        )
                    )
        
        processing_time_ms = (time.time() - start_time) * 1000
        successful_count = len(vectors)
        failed_count = len(failures)
        
        embedding_logger.log_request_complete(
            request_id=batch_request_id,
            model=self.model,
            duration_ms=processing_time_ms,
            batch_size=len(chunks),
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
                batch_size=len(chunks),
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
            batch_size=len(chunks),
            vectors=vectors,
            failures=failures,
            processing_time_ms=processing_time_ms,
            retry_count=total_retry_count,
            rate_limit_hits=total_rate_limit_hits,
        )

    def embed_chunking_result(
        self,
        result_id: str,
        db_session,
        request_id: Optional[str] = None
    ) -> BatchEmbeddingResult:
        """
        从分块结果ID获取所有chunks并进行向量化。
        
        改进：支持多模态模型处理图片块
        - 文本模型：跳过图片块或使用描述文本
        - 多模态模型：从 image_path 按需加载图片数据进行向量化
        """
        from ..models.chunking_result import ChunkingResult, ResultStatus
        from ..models.chunk import Chunk
        
        # 查询分块结果
        chunking_result = db_session.query(ChunkingResult).filter(
            ChunkingResult.result_id == result_id,
            ChunkingResult.status == ResultStatus.COMPLETED
        ).first()
        
        if not chunking_result:
            raise ValueError(f"Chunking result {result_id} not found or not completed")
        
        # 获取所有chunks
        chunks = db_session.query(Chunk).filter(
            Chunk.result_id == result_id
        ).order_by(Chunk.sequence_number).all()
        
        if not chunks:
            raise ValueError(f"No chunks found for result {result_id}")
        
        is_multimodal = self._is_multimodal_model()
        
        # === DEBUG 日志：打印模型和多模态判断信息 ===
        embedding_logger.logger.info(
            f"[DEBUG] embed_chunking_result: model={self.model}, "
            f"is_multimodal={is_multimodal}, num_chunks={len(chunks)}"
        )
        # 统计 chunk 类型
        chunk_types = {}
        for chunk in chunks:
            ct = chunk.chunk_type or 'text'
            chunk_types[ct] = chunk_types.get(ct, 0) + 1
        embedding_logger.logger.info(f"[DEBUG] Chunk types distribution: {chunk_types}")
        
        # 多模态模型使用专门的批量嵌入方法
        if is_multimodal:
            embedding_logger.logger.info("[DEBUG] Using multimodal embedding path")
            return self._embed_chunks_multimodal(chunks, request_id)
        
        embedding_logger.logger.info("[DEBUG] Using text-only embedding path")
        # 文本模型：使用普通的批量嵌入
        embedding_inputs = []
        chunk_types_list = []
        chunk_metadata_list = []
        for chunk in chunks:
            text_content, chunk_type, _, _ = self._prepare_chunk_for_embedding(
                chunk, is_multimodal=False
            )
            embedding_inputs.append(text_content)
            chunk_types_list.append(chunk_type or "text")
            raw_metadata = chunk.chunk_metadata if hasattr(chunk, 'chunk_metadata') else None
            if isinstance(raw_metadata, dict):
                chunk_metadata_list.append({
                    k: v for k, v in raw_metadata.items()
                    if k in ('heading_path', 'heading_text', 'section_title', 'parent_heading',
                             'heading_level', 'chunk_index', 'chunk_type',
                             'context_before', 'context_after')
                    and v is not None
                })
            else:
                chunk_metadata_list.append(None)
        
        # === Contextual Retrieval: 为每个 chunk 生成文档级上下文 ===
        from ..config import settings
        if getattr(settings, 'CONTEXTUAL_RETRIEVAL_ENABLED', False):
            embedding_inputs = self._apply_contextual_retrieval(
                chunking_result, embedding_inputs, db_session
            )
        
        return self.embed_documents(
            embedding_inputs, request_id=request_id,
            chunk_types=chunk_types_list,
            chunk_metadata_list=chunk_metadata_list
        )

    def _apply_contextual_retrieval(
        self,
        chunking_result,
        embedding_inputs: List[str],
        db_session,
    ) -> List[str]:
        """
        Contextual Retrieval: 加载完整文档，为每个 chunk 生成上下文描述并拼接。

        生成的上下文会被 prepend 到 chunk 文本前面，同时作用于
        embedding 向量和 BM25 稀疏向量（因为 source_text 取自 embedding 输入）。
        """
        from ..config import settings
        from .contextual_retrieval_service import ContextualRetrievalService

        try:
            # 1. 加载完整文档原文
            from .chunking_service import ChunkingService
            chunking_service = ChunkingService()
            full_doc_text, _, _ = chunking_service.load_source_document(
                chunking_result.document_id, db_session
            )

            if not full_doc_text or not full_doc_text.strip():
                embedding_logger.logger.warning(
                    f"[ContextualRetrieval] Empty document text for "
                    f"document_id={chunking_result.document_id}, skipping"
                )
                return embedding_inputs

            # 2. 过滤出纯文本 chunk 的内容（跳过图片块等）
            text_chunk_contents = [
                text for text in embedding_inputs if text and text.strip()
            ]

            if not text_chunk_contents:
                return embedding_inputs

            embedding_logger.logger.info(
                f"[ContextualRetrieval] Starting: document={chunking_result.document_name}, "
                f"doc_length={len(full_doc_text)}, chunks={len(text_chunk_contents)}"
            )

            # 3. 调用 LLM 为每个 chunk 生成上下文
            cr_service = ContextualRetrievalService(
                model=getattr(settings, "CONTEXTUAL_RETRIEVAL_MODEL", "qwen3.5-35b-a3b"),
                temperature=getattr(settings, "CONTEXTUAL_RETRIEVAL_TEMPERATURE", 0.0),
                max_tokens=getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_TOKENS", 128),
                request_timeout=getattr(settings, "CONTEXTUAL_RETRIEVAL_TIMEOUT", 30),
                max_workers=getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_WORKERS", 5),
                batch_size=getattr(settings, "CONTEXTUAL_RETRIEVAL_BATCH_SIZE", 10),
            )
            contexts = cr_service.generate_chunk_contexts(full_doc_text, text_chunk_contents)

            # 4. 将上下文 prepend 到 embedding 输入
            enriched_inputs = []
            context_idx = 0
            for original_text in embedding_inputs:
                if original_text and original_text.strip() and context_idx < len(contexts):
                    enriched = ContextualRetrievalService.prepend_context(
                        contexts[context_idx], original_text
                    )
                    enriched_inputs.append(enriched)
                    context_idx += 1
                else:
                    enriched_inputs.append(original_text)

            success_count = sum(1 for c in contexts if c)
            embedding_logger.logger.info(
                f"[ContextualRetrieval] Completed: {success_count}/{len(contexts)} "
                f"chunks enriched for document={chunking_result.document_name}"
            )

            return enriched_inputs

        except Exception as e:
            embedding_logger.logger.error(
                f"[ContextualRetrieval] Failed for document={chunking_result.document_name}: {e}. "
                f"Falling back to original chunks."
            )
            return embedding_inputs

    def embed_document_latest_chunks(
        self,
        document_id: str,
        db_session,
        strategy_type: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> BatchEmbeddingResult:
        """
        从文档ID获取最新的分块结果并进行向量化。
        
        改进：支持多模态模型处理图片块
        - 文本模型：跳过图片块或使用描述文本
        - 多模态模型：从 image_path 按需加载图片数据进行向量化
        """
        from ..models.chunking_result import ChunkingResult, ResultStatus
        from ..models.chunking_task import ChunkingTask, StrategyType
        from ..models.chunk import Chunk
        
        # 构建查询：获取文档的最新完成的分块结果
        query = db_session.query(ChunkingResult).join(
            ChunkingTask,
            ChunkingResult.task_id == ChunkingTask.task_id
        ).filter(
            ChunkingTask.source_document_id == document_id,
            ChunkingResult.status == ResultStatus.COMPLETED,
            ChunkingResult.is_active == True
        )
        
        # 如果指定了策略类型，添加过滤
        if strategy_type:
            try:
                strategy_enum = StrategyType[strategy_type.upper()]
                query = query.filter(ChunkingTask.chunking_strategy == strategy_enum)
            except KeyError:
                raise ValueError(f"Invalid strategy type: {strategy_type}")
        
        # 获取最新的结果
        chunking_result = query.order_by(ChunkingResult.created_at.desc()).first()
        
        if not chunking_result:
            error_msg = f"No completed chunking result found for document {document_id}"
            if strategy_type:
                error_msg += f" with strategy {strategy_type}"
            raise ValueError(error_msg)
        
        # 获取所有chunks
        chunks = db_session.query(Chunk).filter(
            Chunk.result_id == chunking_result.result_id
        ).order_by(Chunk.sequence_number).all()
        
        if not chunks:
            raise ValueError(f"No chunks found for result {chunking_result.result_id}")
        
        is_multimodal = self._is_multimodal_model()
        
        # 多模态模型使用专门的批量嵌入方法
        if is_multimodal:
            return self._embed_chunks_multimodal(chunks, request_id)
        
        # 文本模型：使用普通的批量嵌入
        embedding_inputs = []
        chunk_types_list = []  # 收集每个chunk的类型
        chunk_metadata_list = []  # 收集每个chunk的结构化metadata
        for chunk in chunks:
            text_content, chunk_type, _, _ = self._prepare_chunk_for_embedding(
                chunk, is_multimodal=False
            )
            # 文本模型：所有块都使用文本内容
            embedding_inputs.append(text_content)
            chunk_types_list.append(chunk_type or "text")
            # 收集 chunk 的结构化 metadata
            raw_metadata = chunk.chunk_metadata if hasattr(chunk, 'chunk_metadata') else None
            if isinstance(raw_metadata, dict):
                chunk_metadata_list.append({
                    k: v for k, v in raw_metadata.items()
                    if k in ('heading_path', 'heading_text', 'section_title', 'parent_heading',
                             'heading_level', 'chunk_index', 'chunk_type',
                             'context_before', 'context_after')
                    and v is not None
                })
            else:
                chunk_metadata_list.append(None)

        # === Contextual Retrieval: 为每个 chunk 生成文档级上下文 ===
        from ..config import settings
        if getattr(settings, 'CONTEXTUAL_RETRIEVAL_ENABLED', False):
            embedding_inputs = self._apply_contextual_retrieval(
                chunking_result, embedding_inputs, db_session
            )
        
        return self.embed_documents(
            embedding_inputs, request_id=request_id,
            chunk_types=chunk_types_list,
            chunk_metadata_list=chunk_metadata_list
        )


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
