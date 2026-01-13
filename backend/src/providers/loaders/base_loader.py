"""Base loader interface for document loaders.

All document loaders should inherit from this base class to ensure
consistent interface and output format.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import time
import logging

from ...models.loading_result import (
    StandardDocumentResult,
    DocumentMetadata,
    DocumentContent,
    ProcessingStatistics,
    PageContent,
    TableContent,
    ImageContent,
    ExtractionQuality
)

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for document loaders."""
    
    def __init__(self, name: str, quality_level: ExtractionQuality = ExtractionQuality.MEDIUM):
        """
        Initialize base loader.
        
        Args:
            name: Loader name identifier
            quality_level: Default quality level for this loader
        """
        self.name = name
        self.quality_level = quality_level
    
    @abstractmethod
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and content from document.
        
        This is the main method that subclasses must implement.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with extraction results in legacy format for compatibility.
            Should include:
            - success: bool
            - loader: str
            - full_text: str
            - pages: List[Dict]
            - total_pages: int
            - total_chars: int
            - metadata: Dict (optional)
            - error: str (if success=False)
        """
        pass
    
    def load(self, file_path: str) -> StandardDocumentResult:
        """
        Load document and return standardized result.
        
        This method wraps extract_text and converts the result to
        StandardDocumentResult format.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            StandardDocumentResult instance
        """
        start_time = time.time()
        
        try:
            # Get file info
            path = Path(file_path)
            file_size = path.stat().st_size if path.exists() else 0
            file_format = path.suffix.lstrip('.').lower()
            
            # Extract content
            result = self.extract_text(file_path)
            processing_time = time.time() - start_time
            
            if not result.get('success', False):
                return StandardDocumentResult.create_error(
                    loader=self.name,
                    error=result.get('error', 'Unknown error'),
                    error_details=result.get('error_details')
                )
            
            # Convert to StandardDocumentResult
            return self._convert_to_standard_result(
                result=result,
                file_size=file_size,
                file_format=file_format,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Loader {self.name} failed: {str(e)}", exc_info=True)
            return StandardDocumentResult.create_error(
                loader=self.name,
                error=str(e)
            )
    
    def _convert_to_standard_result(
        self,
        result: Dict[str, Any],
        file_size: int,
        file_format: str,
        processing_time: float
    ) -> StandardDocumentResult:
        """
        Convert legacy result format to StandardDocumentResult.
        
        Args:
            result: Legacy result dictionary
            file_size: File size in bytes
            file_format: File format/extension
            processing_time: Processing time in seconds
            
        Returns:
            StandardDocumentResult instance
        """
        # Parse metadata
        raw_metadata = result.get('metadata', {})
        metadata = DocumentMetadata(
            title=raw_metadata.get('title'),
            author=raw_metadata.get('author'),
            page_count=result.get('total_pages', 0),
            file_size=file_size,
            format=file_format,
            created_time=raw_metadata.get('created_time'),
            modified_time=raw_metadata.get('modified_time'),
            extraction_quality=self._calculate_quality(result),
            quality_level=self.quality_level
        )
        
        # Parse pages
        pages = []
        for page_data in result.get('pages', []):
            pages.append(PageContent(
                page_number=page_data.get('page_number', 0),
                text=page_data.get('text', ''),
                char_count=page_data.get('char_count', len(page_data.get('text', ''))),
                paragraphs=page_data.get('paragraphs', []),
                headings=page_data.get('headings', [])
            ))
        
        # Parse tables
        tables = []
        for table_data in result.get('tables', []):
            tables.append(TableContent(
                page_number=table_data.get('page_number', 1),
                table_index=table_data.get('table_index', 0),
                headers=table_data.get('headers', []),
                rows=table_data.get('rows', []),
                caption=table_data.get('caption')
            ))
        
        # Parse images
        images = []
        for image_data in result.get('images', []):
            images.append(ImageContent(
                page_number=image_data.get('page_number', 1),
                image_index=image_data.get('image_index', 0),
                caption=image_data.get('caption'),
                alt_text=image_data.get('alt_text'),
                bbox=image_data.get('bbox')
            ))
        
        # Create content
        content = DocumentContent(
            full_text=result.get('full_text', ''),
            pages=pages,
            tables=tables,
            images=images
        )
        
        # Create statistics
        statistics = ProcessingStatistics(
            total_pages=result.get('total_pages', len(pages)),
            total_chars=result.get('total_chars', len(result.get('full_text', ''))),
            processing_time=processing_time,
            fallback_used=result.get('fallback_used', False),
            fallback_reason=result.get('fallback_reason'),
            original_parser=result.get('original_parser'),
            table_count=len(tables),
            image_count=len(images),
            formula_count=len(result.get('formulas', []))
        )
        
        return StandardDocumentResult(
            success=True,
            loader=self.name,
            metadata=metadata,
            content=content,
            statistics=statistics
        )
    
    def _calculate_quality(self, result: Dict[str, Any]) -> float:
        """
        Calculate extraction quality score.
        
        Args:
            result: Extraction result
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        # Base quality from loader type
        base_quality = {
            ExtractionQuality.HIGH: 0.9,
            ExtractionQuality.MEDIUM: 0.75,
            ExtractionQuality.LOW: 0.6,
            ExtractionQuality.MINIMAL: 0.4
        }.get(self.quality_level, 0.75)
        
        # Adjust based on content
        full_text = result.get('full_text', '')
        total_chars = len(full_text)
        
        if total_chars == 0:
            return 0.0
        
        # Bonus for structured content
        has_tables = len(result.get('tables', [])) > 0
        has_images = len(result.get('images', [])) > 0
        
        quality = base_quality
        if has_tables:
            quality = min(1.0, quality + 0.05)
        if has_images:
            quality = min(1.0, quality + 0.02)
        
        return round(quality, 2)
    
    def is_available(self) -> bool:
        """
        Check if this loader is available (dependencies installed).
        
        Returns:
            True if loader can be used
        """
        return True
    
    def get_unavailable_reason(self) -> Optional[str]:
        """
        Get reason why loader is unavailable.
        
        Returns:
            Reason string or None if available
        """
        return None
