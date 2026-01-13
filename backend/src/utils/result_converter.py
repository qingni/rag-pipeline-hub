"""Result converter utilities.

This module provides utilities for converting between different result formats,
ensuring compatibility between legacy loaders and the new StandardDocumentResult format.
"""
from typing import Dict, Any, Optional
import logging

from ..models.loading_result import (
    StandardDocumentResult,
    DocumentMetadata,
    DocumentContent,
    ProcessingStatistics,
    PageContent,
    TableContent,
    ImageContent,
    FormulaContent,
    ExtractionQuality
)

logger = logging.getLogger(__name__)


def convert_legacy_result(
    result: Dict[str, Any],
    file_size: int = 0,
    file_format: str = "",
    processing_time: float = 0.0,
    quality_level: ExtractionQuality = ExtractionQuality.MEDIUM
) -> StandardDocumentResult:
    """
    Convert legacy loader result to StandardDocumentResult.
    
    Args:
        result: Legacy result dictionary from loader.extract_text()
        file_size: File size in bytes
        file_format: File format/extension
        processing_time: Processing time in seconds
        quality_level: Quality level of the loader
        
    Returns:
        StandardDocumentResult instance
    """
    if not result.get('success', False):
        return StandardDocumentResult.create_error(
            loader=result.get('loader', 'unknown'),
            error=result.get('error', 'Unknown error'),
            error_details=result.get('error_details')
        )
    
    # Parse metadata
    raw_metadata = result.get('metadata', {})
    extraction_quality = _calculate_quality(result, quality_level)
    
    metadata = DocumentMetadata(
        title=raw_metadata.get('title'),
        author=raw_metadata.get('author'),
        page_count=result.get('total_pages', 0),
        file_size=file_size,
        format=file_format,
        created_time=raw_metadata.get('created_time'),
        modified_time=raw_metadata.get('modified_time'),
        extraction_quality=extraction_quality,
        quality_level=quality_level
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
            caption=table_data.get('caption'),
            row_count=table_data.get('row_count', 0),
            col_count=table_data.get('col_count', 0)
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
    
    # Parse formulas
    formulas = []
    for formula_data in result.get('formulas', []):
        formulas.append(FormulaContent(
            page_number=formula_data.get('page_number', 1),
            formula_index=formula_data.get('formula_index', 0),
            latex=formula_data.get('latex', ''),
            text_representation=formula_data.get('text_representation')
        ))
    
    # Create content
    content = DocumentContent(
        full_text=result.get('full_text', ''),
        pages=pages,
        tables=tables,
        images=images,
        formulas=formulas
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
        formula_count=len(formulas)
    )
    
    return StandardDocumentResult(
        success=True,
        loader=result.get('loader', 'unknown'),
        metadata=metadata,
        content=content,
        statistics=statistics
    )


def convert_standard_to_legacy(result: StandardDocumentResult) -> Dict[str, Any]:
    """
    Convert StandardDocumentResult to legacy format.
    
    This is useful for backward compatibility with existing code.
    
    Args:
        result: StandardDocumentResult instance
        
    Returns:
        Legacy result dictionary
    """
    if not result.success:
        return {
            "success": False,
            "loader": result.loader,
            "error": result.error,
            "error_details": result.error_details
        }
    
    return {
        "success": True,
        "loader": result.loader,
        "metadata": result.metadata.to_dict(),
        "pages": [p.to_dict() for p in result.content.pages],
        "tables": [t.to_dict() for t in result.content.tables],
        "images": [i.to_dict() for i in result.content.images],
        "formulas": [f.to_dict() for f in result.content.formulas],
        "full_text": result.content.full_text,
        "total_pages": result.statistics.total_pages,
        "total_chars": result.statistics.total_chars,
        "fallback_used": result.statistics.fallback_used,
        "fallback_reason": result.statistics.fallback_reason,
        "original_parser": result.statistics.original_parser
    }


def _calculate_quality(result: Dict[str, Any], quality_level: ExtractionQuality) -> float:
    """
    Calculate extraction quality score.
    
    Args:
        result: Extraction result
        quality_level: Base quality level of the loader
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    # Base quality from loader type
    base_quality = {
        ExtractionQuality.HIGH: 0.9,
        ExtractionQuality.MEDIUM: 0.75,
        ExtractionQuality.LOW: 0.6,
        ExtractionQuality.MINIMAL: 0.4
    }.get(quality_level, 0.75)
    
    # Adjust based on content
    full_text = result.get('full_text', '')
    total_chars = len(full_text)
    
    if total_chars == 0:
        return 0.0
    
    # Bonus for structured content
    has_tables = len(result.get('tables', [])) > 0
    has_images = len(result.get('images', [])) > 0
    has_formulas = len(result.get('formulas', [])) > 0
    
    quality = base_quality
    if has_tables:
        quality = min(1.0, quality + 0.05)
    if has_images:
        quality = min(1.0, quality + 0.02)
    if has_formulas:
        quality = min(1.0, quality + 0.03)
    
    return round(quality, 2)


def merge_results(results: list) -> Optional[StandardDocumentResult]:
    """
    Merge multiple parsing results into one.
    
    This can be useful when combining results from different parsers
    for different aspects of a document.
    
    Args:
        results: List of StandardDocumentResult instances
        
    Returns:
        Merged StandardDocumentResult or None if all failed
    """
    successful = [r for r in results if r.success]
    
    if not successful:
        return None
    
    # Use first successful result as base
    base = successful[0]
    
    # Merge tables, images, formulas from other results
    all_tables = list(base.content.tables)
    all_images = list(base.content.images)
    all_formulas = list(base.content.formulas)
    
    for result in successful[1:]:
        # Add unique tables
        for table in result.content.tables:
            if not any(
                t.page_number == table.page_number and t.table_index == table.table_index
                for t in all_tables
            ):
                all_tables.append(table)
        
        # Add unique images
        for image in result.content.images:
            if not any(
                i.page_number == image.page_number and i.image_index == image.image_index
                for i in all_images
            ):
                all_images.append(image)
        
        # Add unique formulas
        for formula in result.content.formulas:
            if not any(
                f.page_number == formula.page_number and f.formula_index == formula.formula_index
                for f in all_formulas
            ):
                all_formulas.append(formula)
    
    # Update content
    base.content.tables = all_tables
    base.content.images = all_images
    base.content.formulas = all_formulas
    
    # Update statistics
    base.statistics.table_count = len(all_tables)
    base.statistics.image_count = len(all_images)
    base.statistics.formula_count = len(all_formulas)
    
    return base
