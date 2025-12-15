"""Unit tests for embedding batch logic."""
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from src.models.embedding_models import BatchSizeLimitError, ErrorType, RateLimitError
from src.services.embedding_service import EmbeddingService


class FakeEmbeddings:
    """Simple fake embeddings client for deterministic testing."""

    def __init__(self, failure_map=None):
        self.failure_map = failure_map or {}

    def embed_query(self, text: str):
        behavior = self.failure_map.get(text)
        if behavior == 'rate_limit':
            raise RateLimitError('rate limited')
        if behavior == 'value_error':
            raise ValueError('unexpected value')
        return [0.1, 0.2]


def create_service(failure_map=None):
    service = EmbeddingService(
        api_key='test-key',
        model='bge-m3',
        max_retries=1,
        embeddings_client=FakeEmbeddings(failure_map),
    )
    # Reduce expected dimension and batch size for tests
    service.model_info['dimension'] = 2
    service.max_batch_size = 5
    return service


def test_embed_documents_enforces_batch_limit():
    service = create_service()
    oversized = ['text'] * 6
    with pytest.raises(BatchSizeLimitError):
        service.embed_documents(oversized)


def test_embed_documents_partial_success_records_failures():
    service = create_service({'fail-item': 'rate_limit'})
    texts = ['doc-a', 'fail-item', 'doc-b']
    result = service.embed_documents(texts)

    assert len(result.vectors) == 2
    assert len(result.failures) == 1
    failure = result.failures[0]
    assert failure.index == 1
    assert failure.error_type == ErrorType.RATE_LIMIT_ERROR
    assert failure.retry_recommended is True
    assert result.batch_size == 3
    assert result.retry_count >= 1
    assert result.rate_limit_hits == 1
