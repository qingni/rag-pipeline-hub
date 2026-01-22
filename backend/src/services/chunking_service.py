"""Chunking service for document chunking operations."""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from ..storage.database import get_db
from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..models.chunking_strategy import ChunkingStrategy
from ..models.chunking_result import ChunkingResult, ResultStatus
from ..models.chunking_task import ChunkingTask, TaskStatus
from ..models.chunk import Chunk
from ..models.parent_chunk import ParentChunk
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
            "semantic": ChunkingParameterValidator.validate_semantic_params,
            "parent_child": ChunkingParameterValidator.validate_parent_child_params,
            "multimodal": ChunkingParameterValidator.validate_multimodal_params,
            "hybrid": ChunkingParameterValidator.validate_hybrid_params
        }
    
    def load_source_document(self, document_id: str, db: Session) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Load source document text, page metadata, and images for chunking.
        Supports loaded documents (load -> chunk workflow).
        Compatible with multiple loaders: docling_serve, xlsx, unstructured.
        
        图片处理策略（占位符+结构化元数据方案）：
        - 文本中保留图片占位符 [IMAGE_N: 描述]，保持文档结构清晰
        - images 数组包含图片完整数据（file_path用于展示，base64_data用于多模态嵌入）
        - 分块器根据占位符关联图片数据，生成图片块的结构化元数据
        
        Args:
            document_id: Document ID
            db: Database session
            
        Returns:
            Tuple of (full_text, pages_metadata, images)
            - pages_metadata: page_number, sheet_name, char_count for each page
            - images: 图片数组，包含 file_path, base64_data, context_before/after 等
            
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
        
        loader_type = load_data.get("loader", "")
        
        # Extract text and metadata from pages - support multiple formats
        text_parts = []
        pages_metadata = []
        
        # New StandardDocumentResult format: content.pages
        if "content" in load_data and "pages" in load_data["content"]:
            pages = load_data["content"]["pages"]
            for page in pages:
                page_text = page.get("text", "")
                text_parts.append(page_text)
                pages_metadata.append({
                    "page_number": page.get("page_number"),
                    "sheet_name": page.get("sheet_name"),
                    "char_count": page.get("char_count"),
                    "text": page_text,  # Include text for page-based chunking
                })
        # Old format: pages directly at root level
        elif "pages" in load_data:
            pages = load_data.get("pages", [])
            
            # For native XLSX loader: extract sheet_name from text or tables
            if loader_type == "xlsx":
                tables = load_data.get("tables", [])
                # Build page_number -> sheet_name mapping from tables.caption
                page_to_sheet = {}
                for table in tables:
                    page_num = table.get("page_number")
                    caption = table.get("caption")
                    if page_num and caption:
                        page_to_sheet[page_num] = caption
                
                for page in pages:
                    page_text = page.get("text", "")
                    text_parts.append(page_text)
                    
                    # Try to extract sheet name from text header (e.g., "Sheet: xxx\n...")
                    sheet_name = None
                    if page_text.startswith("Sheet: "):
                        first_line = page_text.split('\n')[0]
                        sheet_name = first_line.replace("Sheet: ", "").strip()
                    
                    # Fallback to tables[].caption mapping
                    if not sheet_name:
                        sheet_name = page_to_sheet.get(page.get("page_number"))
                    
                    pages_metadata.append({
                        "page_number": page.get("page_number"),
                        "sheet_name": sheet_name,
                        "char_count": page.get("char_count"),
                        "text": page_text,  # Include text for page-based chunking
                    })
            
            # For Docling loader: sheet_name directly in page
            elif loader_type == "docling_serve":
                for page in pages:
                    page_text = page.get("text", "")
                    text_parts.append(page_text)
                    pages_metadata.append({
                        "page_number": page.get("page_number"),
                        "sheet_name": page.get("sheet_name"),
                        "char_count": page.get("char_count"),
                        "text": page_text,  # Include text for page-based chunking
                    })
            
            # For Unstructured or other loaders: no sheet_name available
            else:
                for page in pages:
                    page_text = page.get("text", "")
                    text_parts.append(page_text)
                    pages_metadata.append({
                        "page_number": page.get("page_number"),
                        "sheet_name": None,
                        "char_count": page.get("char_count"),
                        "text": page_text,  # Include text for page-based chunking
                    })
        
        # Fallback: try full_text directly (no metadata available)
        elif "full_text" in load_data:
            return load_data["full_text"], [], []
        elif "content" in load_data and "full_text" in load_data["content"]:
            return load_data["content"]["full_text"], [], []
        
        # 提取图片数据（用于多模态分块）
        images = load_data.get("images", [])
        
        return "\n\n".join(text_parts), pages_metadata, images
    
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
            
            # Load source document with page metadata and images
            text, pages_metadata, images = self.load_source_document(task.source_document_id, db)
            
            # Build document-level metadata for chunking (used by multimodal chunker)
            doc_metadata = {
                "pages": pages_metadata,
                "images": images,  # 图片数据传递给分块器
                "document_id": task.source_document_id
            }
            
            # Get strategy info - query by strategy_type, not strategy_id
            strategy = db.query(ChunkingStrategy).filter(
                ChunkingStrategy.strategy_type == task.chunking_strategy,
                ChunkingStrategy.is_enabled == True
            ).first()
            
            if not strategy:
                raise ValueError(f"Strategy {task.chunking_strategy.value} not found or disabled")
            
            # Ensure chunking_params is a dict (not None)
            params = task.chunking_params if task.chunking_params else {}
            
            # Get chunker and process
            chunker = self.get_chunker(task.chunking_strategy.value, params)
            
            # Check if this is parent-child chunking
            is_parent_child = task.chunking_strategy.value == 'parent_child'
            
            if is_parent_child:
                # Use special method for parent-child chunking
                chunk_result = chunker.chunk(text, metadata=doc_metadata)
                parent_chunks = chunk_result.get('parent_chunks', [])
                child_chunks = chunk_result.get('child_chunks', [])
                
                # Save result with parent chunks
                result = self.save_parent_child_result(
                    task_id=task.task_id,
                    document_id=task.source_document_id,
                    strategy_id=strategy.strategy_id,
                    strategy_type=task.chunking_strategy.value,
                    parameters=params,
                    parent_chunks=parent_chunks,
                    child_chunks=child_chunks,
                    db=db,
                    version=version,
                    previous_version_id=previous_version_id,
                    replacement_reason=replacement_reason
                )
            else:
                # Standard chunking (pass metadata for multimodal chunker)
                chunks = chunker.chunk(text, metadata=doc_metadata)
                
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
            # Get chunk type from chunk_data, default to TEXT
            from ..models.chunk import ChunkType
            chunk_type_str = chunk_data.get("chunk_type", "text")
            try:
                chunk_type = ChunkType(chunk_type_str)
            except ValueError:
                chunk_type = ChunkType.TEXT
            
            chunk = Chunk(
                result_id=result.result_id,
                sequence_number=i,
                content=chunk_data["content"],
                chunk_type=chunk_type,
                chunk_metadata=chunk_data["metadata"],
                start_position=chunk_data["metadata"].get("start_position", 0),
                end_position=chunk_data["metadata"].get("end_position", 0),
                token_count=chunk_data["metadata"].get("char_count", 0)
            )
            db.add(chunk)
        
        db.commit()
        db.refresh(result)
        
        return result
    
    def save_parent_child_result(
        self,
        task_id: str,
        document_id: str,
        strategy_id: str,
        strategy_type: str,
        parameters: Dict[str, Any],
        parent_chunks: List[Dict[str, Any]],
        child_chunks: List[Dict[str, Any]],
        db: Session,
        version: int = 1,
        previous_version_id: str = None,
        replacement_reason: str = None
    ) -> ChunkingResult:
        """
        Save parent-child chunking result to database and file.
        
        Args:
            task_id: Task ID
            document_id: Document ID
            strategy_id: Strategy ID
            strategy_type: Strategy type
            parameters: Chunking parameters used
            parent_chunks: List of parent chunk data
            child_chunks: List of child chunk data
            db: Session
            version: Version number
            previous_version_id: Previous version ID (if replacing)
            replacement_reason: Reason for replacement
            
        Returns:
            Created ChunkingResult
        """
        from ..utils.chunking_helpers import ChunkStatistics
        from ..models.chunking_task import StrategyType
        from ..models.chunk import ChunkType
        from datetime import datetime
        import time
        
        # Get document info
        document = db.query(Document).filter(Document.id == document_id).first()
        
        # Calculate statistics for child chunks (these are used for retrieval)
        statistics = ChunkStatistics.calculate_statistics(child_chunks)
        statistics['parent_count'] = len(parent_chunks)
        statistics['child_count'] = len(child_chunks)
        statistics['avg_children_per_parent'] = len(child_chunks) / len(parent_chunks) if parent_chunks else 0
        
        # Create result directory if needed
        from pathlib import Path
        from ..config import settings
        
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
            "total_chunks": len(child_chunks),
            "total_parent_chunks": len(parent_chunks),
            "statistics": statistics,
            "parent_chunks": parent_chunks,
            "chunks": child_chunks,
            "created_at": datetime.now().isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(file_path)
        
        # Store relative path in database
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
            total_chunks=len(child_chunks),
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
        
        # Create a mapping from old parent_id to new parent_id
        parent_id_mapping = {}
        
        # Save parent chunks to database
        for i, parent_data in enumerate(parent_chunks):
            old_parent_id = parent_data['metadata'].get('chunk_id')
            
            parent_chunk = ParentChunk(
                result_id=result.result_id,
                sequence_number=i,
                content=parent_data['content'],
                start_position=parent_data['metadata'].get('start_position', 0),
                end_position=parent_data['metadata'].get('end_position', 0),
                child_count=parent_data['metadata'].get('child_count', 0),
                metadata={
                    'char_count': parent_data['metadata'].get('char_count', 0),
                    'word_count': parent_data['metadata'].get('word_count', 0),
                    'child_ids': parent_data['metadata'].get('child_ids', [])
                }
            )
            db.add(parent_chunk)
            db.flush()
            
            # Map old parent_id to new database parent_id
            parent_id_mapping[old_parent_id] = parent_chunk.id
        
        # Save child chunks to database
        for i, chunk_data in enumerate(child_chunks):
            old_parent_id = chunk_data.get('parent_id')
            new_parent_id = parent_id_mapping.get(old_parent_id)
            
            chunk = Chunk(
                result_id=result.result_id,
                sequence_number=i,
                content=chunk_data["content"],
                chunk_type=ChunkType.TEXT,
                parent_id=new_parent_id,
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
