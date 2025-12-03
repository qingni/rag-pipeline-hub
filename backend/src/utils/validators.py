"""Validation utilities."""
from typing import BinaryIO
from pathlib import Path
from .error_handlers import ValidationError
from ..config import settings


# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}

# Max file size (50MB)
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE


def validate_file_upload(file: BinaryIO, filename: str) -> None:
    """
    Validate uploaded file.
    
    Args:
        file: File object
        filename: Original filename
        
    Raises:
        ValidationError: If validation fails
    """
    # Check file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format: {file_ext}",
            {
                "allowed_formats": list(ALLOWED_EXTENSIONS),
                "received_format": file_ext
            }
        )
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File size exceeds limit: {file_size} bytes",
            {
                "max_size": MAX_FILE_SIZE,
                "file_size": file_size,
                "max_size_mb": MAX_FILE_SIZE / (1024 * 1024)
            }
        )
    
    if file_size == 0:
        raise ValidationError("Empty file not allowed")


def validate_document_id(document_id: str) -> None:
    """
    Validate document ID format.
    
    Args:
        document_id: Document identifier
        
    Raises:
        ValidationError: If invalid
    """
    if not document_id or len(document_id) != 36:
        raise ValidationError(
            "Invalid document ID format",
            {"document_id": document_id}
        )


def validate_processing_type(processing_type: str) -> None:
    """
    Validate processing type.
    
    Args:
        processing_type: Type of processing
        
    Raises:
        ValidationError: If invalid
    """
    allowed_types = {"load", "parse", "chunk", "embed", "index", "generate"}
    if processing_type not in allowed_types:
        raise ValidationError(
            f"Invalid processing type: {processing_type}",
            {"allowed_types": list(allowed_types)}
        )


def validate_chunk_parameters(chunk_size: int, chunk_overlap: int) -> None:
    """
    Validate chunking parameters.
    
    Args:
        chunk_size: Size of chunks
        chunk_overlap: Overlap between chunks
        
    Raises:
        ValidationError: If invalid
    """
    if not (100 <= chunk_size <= 5000):
        raise ValidationError(
            f"Chunk size must be between 100 and 5000, got {chunk_size}"
        )
    
    if not (0 <= chunk_overlap <= 1000):
        raise ValidationError(
            f"Chunk overlap must be between 0 and 1000, got {chunk_overlap}"
        )
    
    if chunk_overlap >= chunk_size:
        raise ValidationError(
            f"Chunk overlap ({chunk_overlap}) must be less than chunk size ({chunk_size})"
        )


def validate_search_query(query_text: str, top_k: int) -> None:
    """
    Validate search query parameters.
    
    Args:
        query_text: Query string
        top_k: Number of results
        
    Raises:
        ValidationError: If invalid
    """
    if not query_text or len(query_text) < 1:
        raise ValidationError("Query text cannot be empty")
    
    if len(query_text) > 500:
        raise ValidationError(
            f"Query text too long: {len(query_text)} characters (max 500)"
        )
    
    if not (1 <= top_k <= 100):
        raise ValidationError(
            f"top_k must be between 1 and 100, got {top_k}"
        )


def validate_generation_parameters(temperature: float, max_tokens: int, top_p: float) -> None:
    """
    Validate text generation parameters.
    
    Args:
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        
    Raises:
        ValidationError: If invalid
    """
    if not (0 <= temperature <= 2):
        raise ValidationError(
            f"Temperature must be between 0 and 2, got {temperature}"
        )
    
    if not (1 <= max_tokens <= 4000):
        raise ValidationError(
            f"max_tokens must be between 1 and 4000, got {max_tokens}"
        )
    
    if not (0 <= top_p <= 1):
        raise ValidationError(
            f"top_p must be between 0 and 1, got {top_p}"
        )
