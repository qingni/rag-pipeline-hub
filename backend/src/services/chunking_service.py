"""Chunking service for document chunking operations."""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..storage.database import get_db
from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..models.chunking_strategy import ChunkingStrategy
from ..models.chunking_result import ChunkingResult, ResultStatus
from ..models.chunking_task import ChunkingTask, TaskStatus
from ..models.chunk import Chunk
from ..utils.chunking_validators import ChunkingParameterValidator
import json
import os
from datetime import datetime


class ChunkingService:
    """Service for managing document chunking operations."""
    
    def __init__(self):
        """Initialize chunking service."""
        self.validators = {
            "character": ChunkingParameterValidator.validate_character_params,
            "paragraph": ChunkingParameterValidator.validate_paragraph_params,
            "heading": ChunkingParameterValidator.validate_heading_params,
            "semantic": ChunkingParameterValidator.validate_semantic_params
        }
    
    def load_source_document(self, document_id: str, db: Session) -> str:
        """
        Load source document text for chunking.
        Supports loaded documents (load -> chunk workflow).
        
        Args:
            document_id: Document ID
            db: Database session
            
        Returns:
            Document text content
            
        Raises:
            ValueError: If document or processing result not found
        """
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get loading result
        loading_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == document_id,
            ProcessingResult.processing_type == "load",
            ProcessingResult.status == "completed"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        if not loading_result:
            raise ValueError(f"No processing result found for document {document_id}. Document must be loaded first.")
        
        # Load JSON result
        if not os.path.exists(loading_result.result_path):
            raise ValueError(f"Processing result file not found: {loading_result.result_path}")
        
        with open(loading_result.result_path, 'r', encoding='utf-8') as f:
            load_data = json.load(f)
        
        # Extract text from pages - support both old and new formats
        text_parts = []
        
        # New StandardDocumentResult format: content.pages
        if "content" in load_data and "pages" in load_data["content"]:
            for page in load_data["content"]["pages"]:
                text_parts.append(page.get("text", ""))
        # Old format: pages directly at root level
        elif "pages" in load_data:
            for page in load_data.get("pages", []):
                text_parts.append(page.get("text", ""))
        # Fallback: try full_text directly
        elif "full_text" in load_data:
            return load_data["full_text"]
        elif "content" in load_data and "full_text" in load_data["content"]:
            return load_data["content"]["full_text"]
        
        return "\n\n".join(text_parts)
    
    def validate_strategy_parameters(self, strategy_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize strategy parameters.
        
        Args:
            strategy_type: Strategy type identifier
            parameters: Input parameters
            
        Returns:
            Validated parameters
            
        Raises:
            ValueError: If parameters are invalid
        """
        validator = self.validators.get(strategy_type)
        if not validator:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        return validator(parameters)
    
    def get_chunker(self, strategy_type: str, parameters: Dict[str, Any]):
        """
        Get chunker instance for strategy type.
        
        Args:
            strategy_type: Strategy type identifier
            parameters: Chunking parameters
            
        Returns:
            Chunker instance
            
        Raises:
            ValueError: If strategy type unknown
        """
        from ..providers.chunkers import get_chunker
        return get_chunker(strategy_type, **parameters)
    
    def process_chunking_task(
        self, 
        task_id: str, 
        db: Session,
        version: int = 1,
        previous_version_id: str = None,
        replacement_reason: str = None
    ) -> ChunkingResult:
        """
        Process a chunking task.
        
        Args:
            task_id: Task ID to process
            db: Database session
            version: Version number for this result
            previous_version_id: ID of previous version (if replacing)
            replacement_reason: Reason for replacing previous version
            
        Returns:
            ChunkingResult
            
        Raises:
            ValueError: If task not found or processing fails
        """
        from ..models.chunking_task import ChunkingTask
        from datetime import datetime
        
        # Get task
        task = db.query(ChunkingTask).filter(ChunkingTask.task_id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            db.commit()
            
            # Load source document
            text = self.load_source_document(task.source_document_id, db)
            
            # Get strategy info
            strategy = db.query(ChunkingStrategy).filter(
                ChunkingStrategy.strategy_id == task.chunking_strategy.value
            ).first()
            
            if not strategy:
                raise ValueError(f"Strategy {task.chunking_strategy.value} not found")
            
            # Ensure chunking_params is a dict (not None)
            params = task.chunking_params if task.chunking_params else {}
            
            # Get chunker and process
            chunker = self.get_chunker(task.chunking_strategy.value, params)
            chunks = chunker.chunk(text)
            
            # Save result
            result = self.save_chunking_result(
                task_id=task.task_id,
                document_id=task.source_document_id,
                strategy_id=strategy.strategy_id,
                strategy_type=task.chunking_strategy.value,
                parameters=params,
                chunks=chunks,
                db=db,
                version=version,
                previous_version_id=previous_version_id,
                replacement_reason=replacement_reason
            )
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            db.commit()
            
            return result
            
        except Exception as e:
            # Update task with error
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            db.commit()
            raise
    
    def save_chunking_result(
        self,
        task_id: str,
        document_id: str,
        strategy_id: str,
        strategy_type: str,
        parameters: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        db: Session,
        version: int = 1,
        previous_version_id: str = None,
        replacement_reason: str = None
    ) -> ChunkingResult:
        """
        Save chunking result to database and file.
        
        Args:
            task_id: Task ID
            document_id: Document ID
            strategy_id: Strategy ID
            strategy_type: Strategy type
            parameters: Chunking parameters used
            chunks: List of chunk data
            db: Session
            version: Version number
            previous_version_id: Previous version ID (if replacing)
            replacement_reason: Reason for replacement
            
        Returns:
            Created ChunkingResult
        """
        from ..utils.chunking_helpers import ChunkStatistics
        from ..models.chunking_task import StrategyType
        from datetime import datetime
        import time
        
        # Get document info
        document = db.query(Document).filter(Document.id == document_id).first()
        
        # Calculate statistics
        statistics = ChunkStatistics.calculate_statistics(chunks)
        
        # Create result directory if needed (relative to backend directory)
        from pathlib import Path
        from ..config import settings
        
        # RESULTS_DIR now points to ./results (backend/results)
        result_dir = Path(settings.RESULTS_DIR) / "chunking"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate result file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = result_dir / f"{document_id}_{strategy_type}_{timestamp}.json"
        
        # Save JSON result
        result_data = {
            "task_id": task_id,
            "document_id": document_id,
            "strategy_type": strategy_type,
            "parameters": parameters,
            "total_chunks": len(chunks),
            "statistics": statistics,
            "chunks": chunks,
            "created_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(file_path)
        
        # Store relative path in database (relative to backend directory)
        relative_path = f"results/chunking/{file_path.name}"
        
        # Get task for timing
        task = db.query(ChunkingTask).filter(ChunkingTask.task_id == task_id).first()
        processing_time = 0
        if task and task.started_at:
            processing_time = (datetime.now() - task.started_at).total_seconds()
        
        # Create database record
        result = ChunkingResult(
            task_id=task_id,
            document_id=document_id,
            document_name=document.filename if document else "Unknown",
            source_file=document.storage_path if document else "",
            total_chunks=len(chunks),
            chunking_strategy=StrategyType[strategy_type.upper()],
            chunking_params=parameters,
            status=ResultStatus.COMPLETED,
            processing_time=processing_time,
            statistics=statistics,
            json_file_path=relative_path,
            file_size=file_size,
            version=version,
            previous_version_id=previous_version_id,
            is_active=True,
            replacement_reason=replacement_reason
        )
        
        db.add(result)
        db.flush()
        
        # Save individual chunks to database
        for i, chunk_data in enumerate(chunks):
            chunk = Chunk(
                result_id=result.result_id,
                sequence_number=i,
                content=chunk_data["content"],
                chunk_metadata=chunk_data["metadata"],
                start_position=chunk_data["metadata"].get("start_position", 0),
                end_position=chunk_data["metadata"].get("end_position", 0),
                token_count=chunk_data["metadata"].get("char_count", 0)
            )
            db.add(chunk)
        
        db.commit()
        db.refresh(result)
        
        return result


# Singleton instance
chunking_service = ChunkingService()
