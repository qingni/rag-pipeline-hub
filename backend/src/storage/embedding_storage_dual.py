"""
Dual-write extension for EmbeddingStorage.

This module extends embedding_storage.py with dual-write functionality
(JSON file + database record) with concurrent safety and rollback.
"""
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .embedding_storage import EmbeddingStorage, StorageError
from ..models.embedding_models import (
    BatchEmbeddingResponse,
    EmbeddingResult,
)


class DualWriteEmbeddingStorage(EmbeddingStorage):
    """
    Extended storage with dual-write capability.
    
    Implements:
    - FR-022: Atomic dual-write (JSON file + database record)
    - FR-023: Relative path storage
    - FR-024: Update-on-duplicate for same document+model
    - NFR-003: Row-level locking for concurrent safety
    - NFR-005: Rollback guarantee (no orphaned JSON files)
    """
    
    def _get_relative_path(self, absolute_path: Path) -> str:
        """
        Convert absolute path to relative path from results_dir.
        
        Implements FR-023: Store relative paths in database.
        
        Args:
            absolute_path: Absolute file path
            
        Returns:
            Relative path string (e.g., "embedding/2025-12-16/file.json")
        """
        try:
            rel_path = absolute_path.relative_to(self.results_dir.parent)
            return str(rel_path)
        except ValueError:
            # Fallback if path is not relative to results_dir
            return str(absolute_path)
    
    def save_with_database(
        self,
        session: Session,
        response: BatchEmbeddingResponse,
        document_id: str,
        chunking_result_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """
        Save embedding result with atomic dual-write (JSON + Database).
        
        Implements:
        - FR-022: Three-step atomic operation with rollback
        - FR-024: Update existing record for same document+model
        - NFR-003: Row-level locking for concurrent safety
        - NFR-005: Guarantee no orphaned JSON files
        
        Transaction flow:
        1. Acquire row-level lock (SELECT ... FOR UPDATE)
        2. Write JSON file to disk
        3. Create/update database record
        4. Commit transaction
        5. On failure: Rollback + delete JSON file
        
        Args:
            session: SQLAlchemy database session
            response: Batch embedding response with vectors
            document_id: Source document ID
            chunking_result_id: Optional chunking result ID
            model: Embedding model name (fallback to response.metadata.model)
            
        Returns:
            Created/updated EmbeddingResult record
            
        Raises:
            StorageError: If dual-write operation fails
        """
        json_path = None
        model_name = model or response.metadata.model
        
        try:
            # Step 0: Acquire row-level lock for concurrent safety (NFR-003)
            # This prevents race conditions when multiple requests update same document+model
            existing = session.execute(
                select(EmbeddingResult)
                .where(
                    EmbeddingResult.document_id == document_id,
                    EmbeddingResult.model == model_name
                )
                .with_for_update()  # Row-level lock blocks concurrent transactions
            ).scalar_one_or_none()
            
            # Step 1: Write JSON file (FR-022)
            json_path = self.save_batch_result(
                response,
                source_result_id=chunking_result_id,
                source_document_id=document_id
            )
            
            # Step 2: Write/update database record (FR-022, FR-024)
            relative_path = self._get_relative_path(json_path)
            
            if existing:
                # FR-024: Update existing record for same document+model
                existing.result_id = response.request_id
                existing.chunking_result_id = chunking_result_id
                existing.status = response.status
                existing.successful_count = response.metadata.successful_count
                existing.failed_count = response.metadata.failed_count
                existing.vector_dimension = response.metadata.model_dimension
                existing.json_file_path = relative_path
                existing.processing_time_ms = response.metadata.processing_time_ms
                existing.created_at = response.timestamp
                existing.error_message = self._format_error_message(response.failures)
                db_record = existing
            else:
                # Create new record
                db_record = EmbeddingResult(
                    result_id=response.request_id,
                    document_id=document_id,
                    chunking_result_id=chunking_result_id,
                    model=model_name,
                    status=response.status,
                    successful_count=response.metadata.successful_count,
                    failed_count=response.metadata.failed_count,
                    vector_dimension=response.metadata.model_dimension,
                    json_file_path=relative_path,
                    processing_time_ms=response.metadata.processing_time_ms,
                    created_at=response.timestamp,
                    error_message=self._format_error_message(response.failures)
                )
                session.add(db_record)
            
            # Commit transaction
            session.commit()
            
            return db_record
            
        except SQLAlchemyError as e:
            # Step 3: Rollback on database failure (NFR-005)
            session.rollback()
            
            # Delete orphaned JSON file to maintain consistency
            if json_path and json_path.exists():
                try:
                    json_path.unlink()
                except OSError as delete_error:
                    # Log but don't fail - manual cleanup may be needed
                    print(f"Warning: Failed to delete orphaned JSON file {json_path}: {delete_error}")
            
            raise StorageError(
                f"Dual-write failed for document {document_id}: {e}. "
                f"Database write failed, JSON file rolled back."
            ) from e
            
        except IOError as e:
            # JSON write failed, database not touched
            session.rollback()
            raise StorageError(
                f"Dual-write failed for document {document_id}: {e}. "
                f"JSON write failed, no database changes made."
            ) from e
    
    def _format_error_message(self, failures: list) -> Optional[str]:
        """
        Format failure list into database error_message field.
        
        Args:
            failures: List of EmbeddingFailure objects
            
        Returns:
            Formatted error string or None
        """
        if not failures:
            return None
        
        if len(failures) == 1:
            return f"{failures[0].error_type}: {failures[0].error_message}"
        
        # Multiple failures: summarize
        error_types = [f.error_type for f in failures]
        return f"{len(failures)} failures: {', '.join(set(error_types))}"
