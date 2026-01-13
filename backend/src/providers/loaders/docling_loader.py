"""Docling document loader.

Docling is IBM's enterprise-grade document parsing tool designed for generative AI.
It provides high-accuracy table extraction (97.9%) and structured output.
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, Future

from .base_loader import BaseLoader
from ...models.loading_result import ExtractionQuality

logger = logging.getLogger(__name__)

# Check if docling is available
DOCLING_AVAILABLE = False
DOCLING_UNAVAILABLE_REASON = None

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError as e:
    DOCLING_UNAVAILABLE_REASON = f"Docling not installed: {str(e)}. Install with: pip install docling"
except Exception as e:
    DOCLING_UNAVAILABLE_REASON = f"Docling initialization error: {str(e)}"


class DoclingLoader(BaseLoader):
    """Load documents using IBM Docling library.
    
    Docling provides:
    - High-accuracy table extraction (97.9%)
    - Structured content output (tables, images, formulas)
    - Support for PDF, DOCX, XLSX, PPTX, HTML
    - Optional OCR for scanned documents
    """
    
    def __init__(self):
        """Initialize Docling loader."""
        super().__init__(name="docling", quality_level=ExtractionQuality.HIGH)
        self._converter = None
        self._converter_future: Optional[Future] = None
        self._initialization_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="docling-init")
    
    def _initialize_converter_async(self):
        """Initialize DocumentConverter in background thread."""
        try:
            logger.info("Starting Docling DocumentConverter initialization...")
            converter = DocumentConverter()
            logger.info("Docling DocumentConverter initialization completed")
            return converter
        except Exception as e:
            logger.error(f"Failed to initialize Docling DocumentConverter: {str(e)}")
            raise
    
    def _get_converter(self):
        """Get or create DocumentConverter instance with async initialization."""
        if not DOCLING_AVAILABLE:
            raise RuntimeError(DOCLING_UNAVAILABLE_REASON)
        
        with self._initialization_lock:
            # If converter is already initialized, return it
            if self._converter is not None:
                return self._converter
            
            # If initialization is in progress, wait for it
            if self._converter_future is not None:
                logger.info("Waiting for Docling initialization to complete...")
                try:
                    self._converter = self._converter_future.result(timeout=120)  # 2 minutes timeout
                    return self._converter
                except Exception as e:
                    logger.error(f"Docling initialization failed: {str(e)}")
                    self._converter_future = None
                    raise RuntimeError(f"Docling initialization failed: {str(e)}")
            
            # Start initialization
            logger.info("Starting Docling initialization in background...")
            self._converter_future = self._executor.submit(self._initialize_converter_async)
            
            # Wait for initialization to complete
            try:
                self._converter = self._converter_future.result(timeout=120)  # 2 minutes timeout
                return self._converter
            except Exception as e:
                logger.error(f"Docling initialization failed: {str(e)}")
                self._converter_future = None
                raise RuntimeError(f"Docling initialization failed: {str(e)}")
    
    def is_initializing(self) -> bool:
        """Check if Docling is currently initializing."""
        return (self._converter_future is not None and 
                not self._converter_future.done() and 
                self._converter is None)
    
    def is_ready(self) -> bool:
        """Check if Docling is ready to use."""
        return self._converter is not None
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and structured content using Docling.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Dictionary with extracted content and metadata
        """
        if not DOCLING_AVAILABLE:
            return {
                "success": False,
                "loader": self.name,
                "error": DOCLING_UNAVAILABLE_REASON
            }
        
        try:
            converter = self._get_converter()
            result = converter.convert(file_path)
            
            # Get document
            doc = result.document
            
            # Extract full text as markdown
            full_text = doc.export_to_markdown()
            
            # Extract pages
            pages = []
            tables = []
            images = []
            formulas = []
            
            table_index = 0
            image_index = 0
            formula_index = 0
            
            # Process document elements
            for page_num, page in enumerate(doc.pages, start=1):
                page_text_parts = []
                
                for element in page.elements:
                    element_type = getattr(element, 'type', None) or getattr(element, 'label', 'text')
                    
                    if element_type == 'table':
                        # Extract table
                        table_data = self._extract_table(element, page_num, table_index)
                        if table_data:
                            tables.append(table_data)
                            table_index += 1
                    elif element_type == 'picture' or element_type == 'figure':
                        # Extract image info
                        image_data = self._extract_image(element, page_num, image_index)
                        if image_data:
                            images.append(image_data)
                            image_index += 1
                    elif element_type == 'formula' or element_type == 'equation':
                        # Extract formula
                        formula_data = self._extract_formula(element, page_num, formula_index)
                        if formula_data:
                            formulas.append(formula_data)
                            formula_index += 1
                    else:
                        # Text content
                        text = getattr(element, 'text', str(element))
                        if text:
                            page_text_parts.append(text)
                
                page_text = '\n'.join(page_text_parts)
                pages.append({
                    "page_number": page_num,
                    "text": page_text,
                    "char_count": len(page_text)
                })
            
            # Extract metadata
            metadata = self._extract_metadata(doc, file_path)
            
            return {
                "success": True,
                "loader": self.name,
                "metadata": metadata,
                "pages": pages,
                "tables": tables,
                "images": images,
                "formulas": formulas,
                "full_text": full_text,
                "total_pages": len(pages),
                "total_chars": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Docling extraction failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _extract_table(self, element, page_num: int, table_index: int) -> Optional[Dict[str, Any]]:
        """Extract table data from element."""
        try:
            # Try to get table data
            if hasattr(element, 'data'):
                data = element.data
                if hasattr(data, 'to_dataframe'):
                    df = data.to_dataframe()
                    return {
                        "page_number": page_num,
                        "table_index": table_index,
                        "headers": list(df.columns),
                        "rows": df.values.tolist(),
                        "caption": getattr(element, 'caption', None),
                        "row_count": len(df),
                        "col_count": len(df.columns)
                    }
            
            # Fallback: try to extract as text
            if hasattr(element, 'text'):
                return {
                    "page_number": page_num,
                    "table_index": table_index,
                    "headers": [],
                    "rows": [[element.text]],
                    "caption": None,
                    "row_count": 1,
                    "col_count": 1
                }
                
        except Exception as e:
            logger.warning(f"Failed to extract table: {str(e)}")
        
        return None
    
    def _extract_image(self, element, page_num: int, image_index: int) -> Optional[Dict[str, Any]]:
        """Extract image information from element."""
        try:
            return {
                "page_number": page_num,
                "image_index": image_index,
                "caption": getattr(element, 'caption', None),
                "alt_text": getattr(element, 'alt_text', None),
                "bbox": getattr(element, 'bbox', None)
            }
        except Exception as e:
            logger.warning(f"Failed to extract image: {str(e)}")
        
        return None
    
    def _extract_formula(self, element, page_num: int, formula_index: int) -> Optional[Dict[str, Any]]:
        """Extract formula from element."""
        try:
            latex = getattr(element, 'latex', None) or getattr(element, 'text', '')
            return {
                "page_number": page_num,
                "formula_index": formula_index,
                "latex": latex,
                "text_representation": getattr(element, 'text', None)
            }
        except Exception as e:
            logger.warning(f"Failed to extract formula: {str(e)}")
        
        return None
    
    def _extract_metadata(self, doc, file_path: str) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {}
        
        try:
            if hasattr(doc, 'meta'):
                meta = doc.meta
                metadata = {
                    "title": getattr(meta, 'title', None),
                    "author": getattr(meta, 'author', None),
                    "subject": getattr(meta, 'subject', None),
                    "creator": getattr(meta, 'creator', None),
                }
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {str(e)}")
        
        # Add file info
        path = Path(file_path)
        metadata["filename"] = path.name
        metadata["format"] = path.suffix.lstrip('.').lower()
        
        return metadata
    
    def is_available(self) -> bool:
        """Check if Docling is available."""
        return DOCLING_AVAILABLE
    
    def get_unavailable_reason(self) -> Optional[str]:
        """Get reason why Docling is unavailable."""
        return DOCLING_UNAVAILABLE_REASON


# Global instance
docling_loader = DoclingLoader()
