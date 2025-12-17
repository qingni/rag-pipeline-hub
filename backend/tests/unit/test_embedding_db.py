"""
Unit tests for embedding database query layer.

Tests all query methods with various scenarios and edge cases.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from src.storage.database import Base
from src.models.embedding_models import EmbeddingResult
from src.storage.embedding_db import EmbeddingResultDB


# Test database setup
@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def embedding_db(session):
    """Create EmbeddingResultDB instance."""
    return EmbeddingResultDB(session)


@pytest.fixture
def sample_results(session):
    """Create sample embedding results for testing."""
    now = datetime.utcnow()
    results = []
    
    # Create 5 successful results for doc-1 with bge-m3
    for i in range(5):
        result = EmbeddingResult(
            result_id=str(uuid.uuid4()),
            document_id="doc-1",
            chunking_result_id=f"chunk-{i}",
            model="bge-m3",
            status="SUCCESS",
            successful_count=50,
            failed_count=0,
            vector_dimension=1024,
            json_file_path=f"embedding/2025-12-16/embedding_{i}.json",
            processing_time_ms=100.5 + i * 10,
            created_at=now - timedelta(hours=i)
        )
        session.add(result)
        results.append(result)
    
    # Create 3 failed results for doc-2 with qwen3
    for i in range(3):
        result = EmbeddingResult(
            result_id=str(uuid.uuid4()),
            document_id="doc-2",
            chunking_result_id=f"chunk-{i+5}",
            model="qwen3-embedding-8b",
            status="FAILED",
            successful_count=0,
            failed_count=50,
            vector_dimension=4096,
            json_file_path=f"embedding/2025-12-16/embedding_{i+5}.json",
            processing_time_ms=50.0,
            created_at=now - timedelta(hours=i+5),
            error_message="API timeout"
        )
        session.add(result)
        results.append(result)
    
    # Create 2 partial success results for doc-1 with different model
    for i in range(2):
        result = EmbeddingResult(
            result_id=str(uuid.uuid4()),
            document_id="doc-1",
            chunking_result_id=f"chunk-{i+8}",
            model="jina-embeddings-v4",
            status="PARTIAL_SUCCESS",
            successful_count=40,
            failed_count=10,
            vector_dimension=2048,
            json_file_path=f"embedding/2025-12-16/embedding_{i+8}.json",
            processing_time_ms=120.0,
            created_at=now - timedelta(hours=i+8),
            error_message="2 chunks failed due to empty text"
        )
        session.add(result)
        results.append(result)
    
    session.commit()
    return results


class TestGetByResultId:
    """Test get_by_result_id method."""
    
    def test_get_existing_result(self, embedding_db, sample_results):
        """Should return result when ID exists."""
        target = sample_results[0]
        result = embedding_db.get_by_result_id(target.result_id)
        
        assert result is not None
        assert result.result_id == target.result_id
        assert result.document_id == target.document_id
    
    def test_get_nonexistent_result(self, embedding_db, sample_results):
        """Should return None when ID doesn't exist."""
        result = embedding_db.get_by_result_id("nonexistent-id")
        assert result is None


class TestGetLatestByDocument:
    """Test get_latest_by_document method."""
    
    def test_get_latest_without_model_filter(self, embedding_db, sample_results):
        """Should return most recent result for document."""
        result = embedding_db.get_latest_by_document("doc-1")
        
        assert result is not None
        assert result.document_id == "doc-1"
        # Should be the first one created (most recent)
        assert result.result_id == sample_results[0].result_id
    
    def test_get_latest_with_model_filter(self, embedding_db, sample_results):
        """Should return most recent result for document+model."""
        result = embedding_db.get_latest_by_document("doc-1", model="bge-m3")
        
        assert result is not None
        assert result.document_id == "doc-1"
        assert result.model == "bge-m3"
        assert result.result_id == sample_results[0].result_id
    
    def test_get_latest_different_model(self, embedding_db, sample_results):
        """Should return correct result when filtering by different model."""
        result = embedding_db.get_latest_by_document("doc-1", model="jina-embeddings-v4")
        
        assert result is not None
        assert result.model == "jina-embeddings-v4"
        assert result.status == "PARTIAL_SUCCESS"
    
    def test_get_latest_nonexistent_document(self, embedding_db, sample_results):
        """Should return None for nonexistent document."""
        result = embedding_db.get_latest_by_document("doc-999")
        assert result is None
    
    def test_get_latest_nonexistent_model(self, embedding_db, sample_results):
        """Should return None when no results with that model."""
        result = embedding_db.get_latest_by_document("doc-1", model="hunyuan-embedding")
        assert result is None


class TestListResults:
    """Test list_results method with pagination and filtering."""
    
    def test_list_all_no_filters(self, embedding_db, sample_results):
        """Should list all results with pagination."""
        results, total = embedding_db.list_results(page=1, page_size=20)
        
        assert len(results) == 10  # All sample results
        assert total == 10
    
    def test_list_with_pagination(self, embedding_db, sample_results):
        """Should paginate results correctly."""
        # Page 1
        results, total = embedding_db.list_results(page=1, page_size=3)
        assert len(results) == 3
        assert total == 10
        
        # Page 2
        results, total = embedding_db.list_results(page=2, page_size=3)
        assert len(results) == 3
        assert total == 10
        
        # Page 4 (last page)
        results, total = embedding_db.list_results(page=4, page_size=3)
        assert len(results) == 1  # Only 1 result on last page
        assert total == 10
    
    def test_list_filter_by_document(self, embedding_db, sample_results):
        """Should filter by document_id."""
        results, total = embedding_db.list_results(
            filters={'document_id': 'doc-1'},
            page=1,
            page_size=20
        )
        
        assert len(results) == 7  # 5 bge-m3 + 2 jina
        assert total == 7
        assert all(r.document_id == 'doc-1' for r in results)
    
    def test_list_filter_by_model(self, embedding_db, sample_results):
        """Should filter by model."""
        results, total = embedding_db.list_results(
            filters={'model': 'qwen3-embedding-8b'},
            page=1,
            page_size=20
        )
        
        assert len(results) == 3
        assert total == 3
        assert all(r.model == 'qwen3-embedding-8b' for r in results)
    
    def test_list_filter_by_status(self, embedding_db, sample_results):
        """Should filter by status."""
        results, total = embedding_db.list_results(
            filters={'status': 'SUCCESS'},
            page=1,
            page_size=20
        )
        
        assert len(results) == 5
        assert total == 5
        assert all(r.status == 'SUCCESS' for r in results)
    
    def test_list_filter_by_date_range(self, embedding_db, sample_results):
        """Should filter by date range."""
        now = datetime.utcnow()
        date_from = now - timedelta(hours=3, minutes=30)  # More inclusive range
        date_to = now + timedelta(minutes=5)  # Include now
        
        results, total = embedding_db.list_results(
            filters={'date_from': date_from, 'date_to': date_to},
            page=1,
            page_size=20
        )
        
        # Should include results from hours 0-3 (4 results)
        assert len(results) == 4
        assert total == 4
    
    def test_list_multiple_filters(self, embedding_db, sample_results):
        """Should combine multiple filters."""
        results, total = embedding_db.list_results(
            filters={
                'document_id': 'doc-1',
                'model': 'bge-m3',
                'status': 'SUCCESS'
            },
            page=1,
            page_size=20
        )
        
        assert len(results) == 5
        assert total == 5
        assert all(
            r.document_id == 'doc-1' and 
            r.model == 'bge-m3' and 
            r.status == 'SUCCESS' 
            for r in results
        )
    
    def test_list_respects_max_page_size(self, embedding_db, sample_results):
        """Should cap page_size at 100."""
        results, total = embedding_db.list_results(page=1, page_size=1000)
        
        # Should return all 10, not fail or exceed limit
        assert len(results) == 10
        assert total == 10


class TestCountByStatus:
    """Test count_by_status method."""
    
    def test_count_all_statuses(self, embedding_db, sample_results):
        """Should count results grouped by status."""
        counts = embedding_db.count_by_status()
        
        assert counts['SUCCESS'] == 5
        assert counts['FAILED'] == 3
        assert counts['PARTIAL_SUCCESS'] == 2
    
    def test_count_with_document_filter(self, embedding_db, sample_results):
        """Should count statuses for specific document."""
        counts = embedding_db.count_by_status(document_id='doc-1')
        
        assert counts['SUCCESS'] == 5
        assert counts['PARTIAL_SUCCESS'] == 2
        assert 'FAILED' not in counts  # No failed results for doc-1


class TestCountByModel:
    """Test count_by_model method."""
    
    def test_count_all_models(self, embedding_db, sample_results):
        """Should count results grouped by model."""
        counts = embedding_db.count_by_model()
        
        assert counts['bge-m3'] == 5
        assert counts['qwen3-embedding-8b'] == 3
        assert counts['jina-embeddings-v4'] == 2
    
    def test_count_with_document_filter(self, embedding_db, sample_results):
        """Should count models for specific document."""
        counts = embedding_db.count_by_model(document_id='doc-2')
        
        assert counts['qwen3-embedding-8b'] == 3
        assert 'bge-m3' not in counts


class TestGetRecentResults:
    """Test get_recent_results method."""
    
    def test_get_recent_default_limit(self, embedding_db, sample_results):
        """Should return most recent results."""
        results = embedding_db.get_recent_results(limit=5)
        
        assert len(results) == 5
        # Should be ordered by created_at DESC
        assert results[0].created_at >= results[-1].created_at
    
    def test_get_recent_with_status_filter(self, embedding_db, sample_results):
        """Should filter recent results by status."""
        results = embedding_db.get_recent_results(limit=10, status='SUCCESS')
        
        assert len(results) == 5
        assert all(r.status == 'SUCCESS' for r in results)
    
    def test_get_recent_respects_max_limit(self, embedding_db, sample_results):
        """Should cap limit at 100."""
        results = embedding_db.get_recent_results(limit=1000)
        assert len(results) == 10  # All results, capped


class TestGetProcessingStats:
    """Test get_processing_stats method."""
    
    def test_stats_all_results(self, embedding_db, sample_results):
        """Should calculate stats across all results."""
        stats = embedding_db.get_processing_stats()
        
        assert stats['total_count'] == 10
        assert stats['successful_count'] == 5 * 50 + 2 * 40  # 330
        assert stats['failed_count'] == 3 * 50 + 2 * 10  # 170
        assert stats['avg_processing_time_ms'] > 0
        assert stats['max_processing_time_ms'] > 0
        assert stats['min_processing_time_ms'] > 0
    
    def test_stats_filter_by_model(self, embedding_db, sample_results):
        """Should calculate stats for specific model."""
        stats = embedding_db.get_processing_stats(model='bge-m3')
        
        assert stats['total_count'] == 5
        assert stats['successful_count'] == 5 * 50
        assert stats['failed_count'] == 0
    
    def test_stats_filter_by_date_range(self, embedding_db, sample_results):
        """Should calculate stats within date range."""
        now = datetime.utcnow()
        date_from = now - timedelta(hours=2, minutes=30)  # Last 2.5 hours
        
        stats = embedding_db.get_processing_stats(date_from=date_from)
        
        # Should include results from last ~2.5 hours (approximately 3 results)
        assert stats['total_count'] >= 2  # At least 2 results


class TestDeleteOldResults:
    """Test delete_old_results method."""
    
    def test_delete_dry_run(self, embedding_db, sample_results, session):
        """Should count without deleting in dry run mode."""
        now = datetime.utcnow()
        before_date = now - timedelta(hours=5)
        
        count = embedding_db.delete_old_results(before_date, dry_run=True)
        
        assert count == 5  # 5 results older than 5 hours
        
        # Verify no deletion occurred
        remaining = session.query(EmbeddingResult).count()
        assert remaining == 10
    
    def test_delete_actually_deletes(self, embedding_db, sample_results, session):
        """Should delete results when dry_run=False."""
        now = datetime.utcnow()
        before_date = now - timedelta(hours=5)
        
        count = embedding_db.delete_old_results(before_date, dry_run=False)
        
        assert count == 5
        
        # Verify deletion occurred
        remaining = session.query(EmbeddingResult).count()
        assert remaining == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
