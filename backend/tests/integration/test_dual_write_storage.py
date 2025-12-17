"""
Integration test for dual-write storage.

Tests the complete dual-write flow: JSON file + database record.
"""
import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import json

from src.storage.database import Base
from src.models.embedding_models import (
    EmbeddingResult,
    BatchEmbeddingResponse,
    BatchMetadata,
    EmbeddingConfig,
    Vector,
)
from src.storage.embedding_storage_dual import DualWriteEmbeddingStorage


@pytest.fixture
def engine():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def storage(tmp_path):
    """Create storage instance with temporary directory."""
    results_dir = tmp_path / "results" / "embedding"
    return DualWriteEmbeddingStorage(results_dir=str(results_dir))


@pytest.fixture
def sample_response():
    """Create sample batch embedding response."""
    config = EmbeddingConfig(
        api_endpoint="http://test.api.com/v1/embeddings",
        max_retries=3,
        timeout_seconds=60
    )
    
    metadata = BatchMetadata(
        model="bge-m3",
        model_dimension=1024,
        batch_size=2,
        successful_count=2,
        failed_count=0,
        processing_time_ms=150.5,
        api_latency_ms=120.0,
        config=config
    )
    
    vectors = [
        Vector(
            index=0,
            vector=[0.1] * 1024,
            dimension=1024,
            text_hash="sha256:abc123",
            text_length=100,
            processing_time_ms=75.0
        ),
        Vector(
            index=1,
            vector=[0.2] * 1024,
            dimension=1024,
            text_hash="sha256:def456",
            text_length=150,
            processing_time_ms=75.5
        ),
    ]
    
    return BatchEmbeddingResponse(
        request_id=str(uuid.uuid4()),
        status="SUCCESS",
        vectors=vectors,
        failures=[],
        metadata=metadata,
        timestamp=datetime.utcnow()
    )


class TestDualWrite:
    """Test dual-write functionality."""
    
    def test_successful_dual_write(self, storage, session, sample_response):
        """Should create both JSON file and database record."""
        document_id = "test-doc-1"
        chunking_result_id = "test-chunk-1"
        
        # Perform dual-write
        db_record = storage.save_with_database(
            session=session,
            response=sample_response,
            document_id=document_id,
            chunking_result_id=chunking_result_id
        )
        
        # Verify database record
        assert db_record.result_id == sample_response.request_id
        assert db_record.document_id == document_id
        assert db_record.chunking_result_id == chunking_result_id
        assert db_record.model == "bge-m3"
        assert db_record.status == "SUCCESS"
        assert db_record.successful_count == 2
        assert db_record.failed_count == 0
        assert db_record.vector_dimension == 1024
        
        # Verify JSON file exists
        json_path = Path(db_record.json_file_path)
        # Since path is relative, need to resolve from storage base dir
        full_path = storage.results_dir.parent / json_path
        assert full_path.exists(), f"JSON file not found at {full_path}"
        
        # Verify JSON content
        with open(full_path, 'r') as f:
            json_data = json.load(f)
        
        assert json_data['request_id'] == sample_response.request_id
        assert json_data['status'] == 'SUCCESS'
        assert len(json_data['vectors']) == 2
        assert json_data['source']['document_id'] == document_id
        assert json_data['source']['chunking_result_id'] == chunking_result_id
    
    def test_update_existing_record(self, storage, session, sample_response):
        """Should update existing record for same document+model."""
        document_id = "test-doc-2"
        model = "bge-m3"
        
        # First write
        first_record = storage.save_with_database(
            session=session,
            response=sample_response,
            document_id=document_id,
            model=model
        )
        
        # Second write with different result_id
        sample_response.request_id = str(uuid.uuid4())
        sample_response.metadata.successful_count = 3
        
        second_record = storage.save_with_database(
            session=session,
            response=sample_response,
            document_id=document_id,
            model=model
        )
        
        # Should be same database record (updated)
        assert first_record.document_id == second_record.document_id
        assert first_record.model == second_record.model
        
        # But with new values
        assert second_record.result_id == sample_response.request_id
        assert second_record.successful_count == 3
        
        # Verify only one record exists
        all_records = session.query(EmbeddingResult).filter_by(
            document_id=document_id,
            model=model
        ).all()
        assert len(all_records) == 1
    
    def test_concurrent_safety_simulation(self, storage, session, sample_response):
        """Test row-level locking prevents duplicates."""
        document_id = "test-doc-3"
        model = "qwen3-embedding-8b"
        
        # Simulate concurrent requests by making multiple writes
        # In real concurrent scenario, row lock would serialize these
        results = []
        for i in range(3):
            sample_response.request_id = str(uuid.uuid4())
            result = storage.save_with_database(
                session=session,
                response=sample_response,
                document_id=document_id,
                model=model
            )
            results.append(result)
        
        # Verify only one record exists (all updates should have modified same record)
        all_records = session.query(EmbeddingResult).filter_by(
            document_id=document_id,
            model=model
        ).all()
        
        assert len(all_records) == 1, "Should have exactly one record due to update-on-duplicate"
        assert all_records[0].result_id == results[-1].result_id  # Latest request_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
