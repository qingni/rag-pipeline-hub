"""
Database query layer for embedding results.

Implements high-performance queries for embedding metadata with proper indexing.
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session

from ..models.embedding_models import EmbeddingResult


class EmbeddingResultDB:
    """
    Database access layer for EmbeddingResult queries.
    
    Implements:
    - FR-025: Query by result_id
    - FR-026: Query latest by document_id (with model filter)
    - FR-027: List with pagination and filters
    - FR-028: Performance indexes for <100ms queries
    """
    
    def __init__(self, session: Session):
        """
        Initialize database query layer.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    def get_by_result_id(self, result_id: str) -> Optional[EmbeddingResult]:
        """
        Query embedding result by unique result_id.
        
        Implements FR-025: GET /embedding/results/{result_id}
        
        Performance: O(1) lookup via primary key, <10ms
        
        Args:
            result_id: Unique embedding result identifier
            
        Returns:
            EmbeddingResult or None if not found
        """
        stmt = select(EmbeddingResult).where(
            EmbeddingResult.result_id == result_id
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_latest_by_document(
        self,
        document_id: str,
        model: Optional[str] = None
    ) -> Optional[EmbeddingResult]:
        """
        Get the latest embedding result for a document.
        
        Implements FR-026: GET /embedding/results/by-document/{document_id}?model=xxx
        
        Performance: <100ms with 10k records via idx_doc_model composite index
        
        Args:
            document_id: Document identifier
            model: Optional model filter (e.g., "bge-m3")
            
        Returns:
            Latest EmbeddingResult or None if not found
        """
        # Build query with document_id filter
        stmt = select(EmbeddingResult).where(
            EmbeddingResult.document_id == document_id
        )
        
        # Add model filter if provided
        if model:
            stmt = stmt.where(EmbeddingResult.model == model)
        
        # Order by created_at DESC to get latest
        # Uses idx_created_at index for efficient sorting
        stmt = stmt.order_by(desc(EmbeddingResult.created_at)).limit(1)
        
        return self.session.execute(stmt).scalar_one_or_none()
    
    def list_results(
        self,
        filters: Optional[dict] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[EmbeddingResult], int]:
        """
        List embedding results with pagination and filtering.
        
        Implements FR-027: GET /embedding/results?page=1&page_size=20&...
        
        Performance: <200ms for paginated queries via appropriate indexes
        
        Supported filters:
        - document_id: Filter by document
        - model: Filter by embedding model
        - status: Filter by processing status (SUCCESS, FAILED, PARTIAL_SUCCESS)
        - date_from: Filter by created_at >= date_from
        - date_to: Filter by created_at <= date_to
        
        Args:
            filters: Dictionary of filter conditions
            page: Page number (1-indexed)
            page_size: Results per page (max 100)
            
        Returns:
            Tuple of (results list, total count)
        """
        if filters is None:
            filters = {}
        
        # Validate page_size
        page_size = min(page_size, 100)
        page = max(page, 1)
        
        # Build base query
        stmt = select(EmbeddingResult)
        count_stmt = select(func.count()).select_from(EmbeddingResult)
        
        # Apply filters
        conditions = []
        
        if 'document_id' in filters and filters['document_id']:
            conditions.append(EmbeddingResult.document_id == filters['document_id'])
        
        if 'model' in filters and filters['model']:
            conditions.append(EmbeddingResult.model == filters['model'])
        
        if 'status' in filters and filters['status']:
            # Uses idx_status index for efficient filtering
            conditions.append(EmbeddingResult.status == filters['status'])
        
        if 'date_from' in filters and filters['date_from']:
            # Uses idx_created_at index
            conditions.append(EmbeddingResult.created_at >= filters['date_from'])
        
        if 'date_to' in filters and filters['date_to']:
            # Uses idx_created_at index
            conditions.append(EmbeddingResult.created_at <= filters['date_to'])
        
        if 'chunking_result_id' in filters and filters['chunking_result_id']:
            conditions.append(
                EmbeddingResult.chunking_result_id == filters['chunking_result_id']
            )
        
        # Apply all conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        
        # Order by created_at DESC (latest first)
        stmt = stmt.order_by(desc(EmbeddingResult.created_at))
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Execute queries
        results = list(self.session.execute(stmt).scalars().all())
        total_count = self.session.execute(count_stmt).scalar()
        
        return results, total_count
    
    def count_by_status(self, document_id: Optional[str] = None) -> dict:
        """
        Count embedding results grouped by status.
        
        Useful for dashboard statistics and health monitoring.
        
        Args:
            document_id: Optional filter by document
            
        Returns:
            Dictionary mapping status -> count
            Example: {"SUCCESS": 150, "FAILED": 5, "PARTIAL_SUCCESS": 3}
        """
        stmt = select(
            EmbeddingResult.status,
            func.count(EmbeddingResult.result_id)
        ).group_by(EmbeddingResult.status)
        
        if document_id:
            stmt = stmt.where(EmbeddingResult.document_id == document_id)
        
        results = self.session.execute(stmt).all()
        return {status: count for status, count in results}
    
    def count_by_model(self, document_id: Optional[str] = None) -> dict:
        """
        Count embedding results grouped by model.
        
        Useful for understanding model usage patterns.
        
        Args:
            document_id: Optional filter by document
            
        Returns:
            Dictionary mapping model -> count
            Example: {"bge-m3": 100, "qwen3-embedding-8b": 50}
        """
        stmt = select(
            EmbeddingResult.model,
            func.count(EmbeddingResult.result_id)
        ).group_by(EmbeddingResult.model)
        
        if document_id:
            stmt = stmt.where(EmbeddingResult.document_id == document_id)
        
        results = self.session.execute(stmt).all()
        return {model: count for model, count in results}
    
    def get_recent_results(
        self,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[EmbeddingResult]:
        """
        Get most recent embedding results.
        
        Useful for dashboard "recent activity" views.
        
        Args:
            limit: Maximum results to return (default 10, max 100)
            status: Optional status filter
            
        Returns:
            List of recent EmbeddingResult records
        """
        limit = min(limit, 100)
        
        stmt = select(EmbeddingResult).order_by(
            desc(EmbeddingResult.created_at)
        ).limit(limit)
        
        if status:
            stmt = stmt.where(EmbeddingResult.status == status)
        
        return list(self.session.execute(stmt).scalars().all())
    
    def get_processing_stats(
        self,
        model: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> dict:
        """
        Get aggregate processing statistics.
        
        Useful for performance monitoring and optimization.
        
        Args:
            model: Optional model filter
            date_from: Optional start date filter
            date_to: Optional end date filter
            
        Returns:
            Dictionary with statistics:
            - total_count: Total embedding operations
            - successful_count: Total successful vectors
            - failed_count: Total failed chunks
            - avg_processing_time_ms: Average processing time
            - max_processing_time_ms: Maximum processing time
            - min_processing_time_ms: Minimum processing time
        """
        conditions = []
        
        if model:
            conditions.append(EmbeddingResult.model == model)
        if date_from:
            conditions.append(EmbeddingResult.created_at >= date_from)
        if date_to:
            conditions.append(EmbeddingResult.created_at <= date_to)
        
        stmt = select(
            func.count(EmbeddingResult.result_id).label('total_count'),
            func.sum(EmbeddingResult.successful_count).label('successful_count'),
            func.sum(EmbeddingResult.failed_count).label('failed_count'),
            func.avg(EmbeddingResult.processing_time_ms).label('avg_processing_time_ms'),
            func.max(EmbeddingResult.processing_time_ms).label('max_processing_time_ms'),
            func.min(EmbeddingResult.processing_time_ms).label('min_processing_time_ms')
        )
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        result = self.session.execute(stmt).one()
        
        return {
            'total_count': result.total_count or 0,
            'successful_count': result.successful_count or 0,
            'failed_count': result.failed_count or 0,
            'avg_processing_time_ms': round(result.avg_processing_time_ms, 2) if result.avg_processing_time_ms else 0,
            'max_processing_time_ms': result.max_processing_time_ms or 0,
            'min_processing_time_ms': result.min_processing_time_ms or 0
        }
    
    def delete_old_results(
        self,
        before_date: datetime,
        dry_run: bool = True
    ) -> int:
        """
        Delete embedding results older than a specified date.
        
        CAUTION: This does NOT delete the corresponding JSON files.
        JSON files must be cleaned separately to avoid orphaned files.
        
        Args:
            before_date: Delete results created before this date
            dry_run: If True, only count (don't delete). Default: True
            
        Returns:
            Number of results that would be/were deleted
        """
        stmt = select(func.count()).select_from(EmbeddingResult).where(
            EmbeddingResult.created_at < before_date
        )
        count = self.session.execute(stmt).scalar()
        
        if not dry_run and count > 0:
            delete_stmt = EmbeddingResult.__table__.delete().where(
                EmbeddingResult.created_at < before_date
            )
            self.session.execute(delete_stmt)
            self.session.commit()
        
        return count
    
    def delete_result(self, result_id: str) -> bool:
        """
        Delete a single embedding result by result_id.
        
        Args:
            result_id: Unique embedding result identifier
            
        Returns:
            True if deleted, False if not found
        """
        stmt = EmbeddingResult.__table__.delete().where(
            EmbeddingResult.result_id == result_id
        )
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.rowcount > 0


def get_embedding_db(session: Session) -> EmbeddingResultDB:
    """
    Factory function for dependency injection.
    
    Args:
        session: SQLAlchemy database session
        
    Returns:
        EmbeddingResultDB instance
    """
    return EmbeddingResultDB(session)
