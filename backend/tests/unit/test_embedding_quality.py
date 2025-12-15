"""Quality and documentation alignment tests for embedding module."""
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from src.models.embedding_models import (
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    BatchMetadata,
    EmbeddingConfig,
    EmbeddingMetadata,
    ResponseStatus,
    SingleEmbeddingRequest,
    SingleEmbeddingResponse,
    Vector,
    VectorDimensionMismatchError,
)
from src.services.embedding_service import EmbeddingService


class InstantEmbeddings:
    """Fake embeddings client that returns deterministic vectors instantly."""

    def embed_query(self, text: str):
        return [0.1, 0.2]


@pytest.fixture
def fast_service():
    service = EmbeddingService(
        api_key='test-key',
        model='bge-m3',
        max_retries=1,
        embeddings_client=InstantEmbeddings(),
    )
    service.model_info['dimension'] = 2
    return service


def test_single_embedding_meets_latency_budget(fast_service):
    result = fast_service.embed_query('性能测试')
    assert result.processing_time_ms < 2000
    assert result.text_length == len('性能测试')


def test_dimension_validation_detects_mismatch():
    service = EmbeddingService(
        api_key='test',
        model='bge-m3',
        embeddings_client=InstantEmbeddings(),
    )
    service.model_info['dimension'] = 3
    with pytest.raises(VectorDimensionMismatchError):
        service.embed_query('dimension mismatch')


def test_quickstart_payload_examples_validate_against_models():
    single_request = SingleEmbeddingRequest(
        text='人工智能是什么',
        model='qwen3-embedding-8b',
        max_retries=3,
        timeout=60,
    )
    assert single_request.model == 'qwen3-embedding-8b'

    single_response = SingleEmbeddingResponse(
        request_id='uuid-123',
        status=ResponseStatus.SUCCESS,
        vector=Vector(
            index=0,
            vector=[0.1, 0.2, 0.3],
            dimension=768,
            text_hash=Vector.create_text_hash('人工智能是什么'),
            text_length=6,
        ),
        metadata=EmbeddingMetadata(
            model='qwen3-embedding-8b',
            model_dimension=768,
            processing_time_ms=120.5,
            api_latency_ms=100.2,
            retry_count=0,
            rate_limit_hits=0,
            config=EmbeddingConfig(
                api_endpoint='http://localhost:8000/api/v1',
                max_retries=3,
                timeout_seconds=60,
                exponential_backoff=True,
                initial_delay_seconds=1.0,
                max_delay_seconds=32.0,
            ),
        ),
    )
    assert single_response.vector.text_length == 6

    batch_request = BatchEmbeddingRequest(
        texts=['人工智能', '机器学习'],
        model='bge-m3',
        max_retries=3,
        timeout=60,
    )
    assert len(batch_request.texts) == 2

    batch_response = BatchEmbeddingResponse(
        request_id='uuid-456',
        status=ResponseStatus.PARTIAL_SUCCESS,
        vectors=[
            Vector(
                index=0,
                vector=[0.1, 0.2, 0.3],
                dimension=768,
                text_hash=Vector.create_text_hash('人工智能'),
                text_length=4,
            )
        ],
        failures=[],
        metadata=BatchMetadata(
            model='bge-m3',
            model_dimension=768,
            processing_time_ms=250.0,
            api_latency_ms=200.0,
            retry_count=1,
            rate_limit_hits=0,
            batch_size=2,
            successful_count=1,
            failed_count=1,
            vectors_per_second=4.0,
            config=EmbeddingConfig(
                api_endpoint='http://localhost:8000/api/v1',
                max_retries=3,
                timeout_seconds=60,
                exponential_backoff=True,
                initial_delay_seconds=1.0,
                max_delay_seconds=32.0,
            ),
        ),
    )
    assert batch_response.metadata.successful_count + batch_response.metadata.failed_count == batch_response.metadata.batch_size
