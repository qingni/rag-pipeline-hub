"""
Unified image extraction module for all chunking strategies.

This module provides consistent image extraction capabilities that can be reused
across different chunkers (multimodal, hybrid, etc.) to ensure:
1. Consistent image detection (placeholder, Markdown, HTML formats)
2. Proper metadata association from document loading stage
3. Standardized image chunk creation for multimodal retrieval
"""
import re
import uuid
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ...models.chunk_metadata import ChunkTypeEnum, create_chunk_metadata

logger = logging.getLogger(__name__)


class ImageExtractor:
    """
    Unified image extractor that supports multiple image formats.
    
    Supported formats:
    1. Placeholder format: [IMAGE_N: description] - Generated during document loading
    2. Markdown format: ![alt](path)
    3. HTML format: <img src="..." />
    
    Key features:
    - Associates placeholder images with metadata.images data
    - Supports base64 data for multimodal embedding
    - Provides consistent image chunk creation across all chunkers
    """
    
    # Regex patterns for different image formats
    # Placeholder format from document loading: [IMAGE_N: description]
    PLACEHOLDER_IMAGE_PATTERN = re.compile(
        r'\[IMAGE_(\d+):\s*([^\]]*)\]',
        re.MULTILINE
    )
    
    # Markdown image format: ![alt](path)
    MARKDOWN_IMAGE_PATTERN = re.compile(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        re.MULTILINE
    )
    
    # HTML image format: <img src="..." />
    HTML_IMAGE_PATTERN = re.compile(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*/?>',
        re.IGNORECASE
    )
    
    def __init__(
        self,
        image_base_path: Optional[str] = None,
        include_images: bool = True
    ):
        """
        Initialize image extractor.
        
        Args:
            image_base_path: Base path for resolving relative image paths
            include_images: Whether to extract images (default: True)
        """
        self.image_base_path = image_base_path
        self.include_images = include_images
    
    def extract_images(
        self,
        text: str,
        metadata: Dict[str, Any],
        global_offset: int = 0,
        sheet_name: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """
        Extract images from text and return image chunks and processed regions.
        
        This is the main entry point for image extraction, supporting all three
        image formats in priority order:
        1. Placeholder format (highest priority - has full metadata)
        2. Markdown format
        3. HTML format
        
        Args:
            text: Input text containing potential images
            metadata: Document metadata containing 'images' array from loading stage
            global_offset: Offset to add to all positions (for page-based processing)
            sheet_name: Optional sheet name for Excel files
            page_number: Optional page number
            
        Returns:
            Tuple of (image_chunks, extracted_regions)
            - image_chunks: List of image chunk dictionaries
            - extracted_regions: List of (start, end, 'image') tuples for processed areas
        """
        if not self.include_images:
            return [], []
        
        chunks = []
        regions = []
        
        # Get pre-loaded image data from document loading stage
        images_data = metadata.get("images", [])
        
        # Method 1: Extract placeholder format [IMAGE_N: description]
        placeholder_chunks, placeholder_regions = self._extract_placeholder_images(
            text=text,
            images_data=images_data,
            global_offset=global_offset,
            sheet_name=sheet_name,
            page_number=page_number,
            chunk_start_index=len(chunks)
        )
        chunks.extend(placeholder_chunks)
        regions.extend(placeholder_regions)
        
        # Method 2: Extract Markdown format ![alt](path)
        markdown_chunks, markdown_regions = self._extract_markdown_images(
            text=text,
            metadata=metadata,
            global_offset=global_offset,
            sheet_name=sheet_name,
            page_number=page_number,
            existing_regions=regions,
            chunk_start_index=len(chunks)
        )
        chunks.extend(markdown_chunks)
        regions.extend(markdown_regions)
        
        # Method 3: Extract HTML format <img src="..." />
        html_chunks, html_regions = self._extract_html_images(
            text=text,
            metadata=metadata,
            global_offset=global_offset,
            sheet_name=sheet_name,
            page_number=page_number,
            existing_regions=regions,
            chunk_start_index=len(chunks)
        )
        chunks.extend(html_chunks)
        regions.extend(html_regions)
        
        logger.debug(f"Extracted {len(chunks)} images from text")
        return chunks, regions
    
    def _extract_placeholder_images(
        self,
        text: str,
        images_data: List[Dict[str, Any]],
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        chunk_start_index: int
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract images using placeholder format [IMAGE_N: description]."""
        chunks = []
        regions = []
        
        for match in self.PLACEHOLDER_IMAGE_PATTERN.finditer(text):
            image_index = int(match.group(1))
            placeholder_text = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Find corresponding image data from loading stage
            image_info = self._find_image_by_index(images_data, image_index, page_number)
            
            if image_info:
                # Create image chunk with full metadata
                image_chunk = self._create_image_chunk_from_data(
                    image_info=image_info,
                    placeholder_text=placeholder_text,
                    start_pos=global_offset + start_pos,
                    end_pos=global_offset + end_pos,
                    chunk_index=chunk_start_index + len(chunks),
                    sheet_name=sheet_name,
                    page_number=page_number
                )
            else:
                # Create basic image chunk (no metadata available)
                image_chunk = self._create_placeholder_image_chunk(
                    placeholder_text=placeholder_text,
                    image_index=image_index,
                    start_pos=global_offset + start_pos,
                    end_pos=global_offset + end_pos,
                    chunk_index=chunk_start_index + len(chunks),
                    sheet_name=sheet_name,
                    page_number=page_number
                )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        return chunks, regions
    
    def _extract_markdown_images(
        self,
        text: str,
        metadata: Dict[str, Any],
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        existing_regions: List[Tuple[int, int, str]],
        chunk_start_index: int
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract images using Markdown format ![alt](path)."""
        chunks = []
        regions = []
        
        for match in self.MARKDOWN_IMAGE_PATTERN.finditer(text):
            start_pos = match.start()
            
            # Skip if already matched by placeholder
            if self._position_in_regions(start_pos, existing_regions):
                continue
            
            alt_text = match.group(1)
            image_path = match.group(2)
            end_pos = match.end()
            
            image_chunk = self._create_image_chunk(
                image_path=image_path,
                alt_text=alt_text,
                start_pos=global_offset + start_pos,
                end_pos=global_offset + end_pos,
                chunk_index=chunk_start_index + len(chunks),
                sheet_name=sheet_name,
                page_number=page_number,
                metadata=metadata
            )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        return chunks, regions
    
    def _extract_html_images(
        self,
        text: str,
        metadata: Dict[str, Any],
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        existing_regions: List[Tuple[int, int, str]],
        chunk_start_index: int
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract images using HTML format <img src="..." />."""
        chunks = []
        regions = []
        
        for match in self.HTML_IMAGE_PATTERN.finditer(text):
            start_pos = match.start()
            
            # Skip if already matched by other patterns
            if self._position_in_regions(start_pos, existing_regions):
                continue
            
            image_path = match.group(1)
            alt_text = match.group(2) if match.lastindex >= 2 else ''
            end_pos = match.end()
            
            image_chunk = self._create_image_chunk(
                image_path=image_path,
                alt_text=alt_text or '',
                start_pos=global_offset + start_pos,
                end_pos=global_offset + end_pos,
                chunk_index=chunk_start_index + len(chunks),
                sheet_name=sheet_name,
                page_number=page_number,
                metadata=metadata
            )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        return chunks, regions
    
    def _position_in_regions(
        self,
        position: int,
        regions: List[Tuple[int, int, str]]
    ) -> bool:
        """Check if a position is within any existing region."""
        return any(r[0] <= position < r[1] for r in regions)
    
    def _find_image_by_index(
        self,
        images_data: List[Dict[str, Any]],
        image_index: int,
        page_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find image data by index from the loading stage images array.
        
        Args:
            images_data: List of image data from document loading
            image_index: Image index from placeholder
            page_number: Optional page number for precise matching
            
        Returns:
            Matching image data dictionary or None
        """
        for img in images_data:
            if img.get("image_index") == image_index:
                # If page number specified, verify it matches
                if page_number is not None:
                    img_page = img.get("page_number")
                    if img_page is not None and img_page != page_number:
                        continue
                return img
        return None
    
    def _create_image_chunk_from_data(
        self,
        image_info: Dict[str, Any],
        placeholder_text: str,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> Dict[str, Any]:
        """
        Create image chunk from loading stage data.
        
        This creates a rich image chunk with full metadata from document loading,
        including file path, thumbnail, dimensions, etc.
        
        Design decision: Delayed loading
        - Only save file_path and thumbnail_base64 at chunking stage
        - Full base64_data loaded on-demand during vectorization (only needed for multimodal models)
        - Reduces storage size of chunking results
        """
        # Determine image description
        alt_text = image_info.get("alt_text") or image_info.get("caption") or placeholder_text
        content = f"[Image: {alt_text}]" if alt_text else "[Image]"
        
        # Extract image properties (don't load full base64 at chunking stage)
        file_path = image_info.get("file_path")
        thumbnail_base64 = image_info.get("thumbnail_base64")
        mime_type = image_info.get("mime_type")
        width = image_info.get("width")
        height = image_info.get("height")
        original_size = image_info.get("original_size")
        context_before = image_info.get("context_before")
        context_after = image_info.get("context_after")
        
        # Infer format from file path or mime type
        img_format = None
        if mime_type:
            img_format = mime_type.split('/')[-1] if '/' in mime_type else mime_type
        elif file_path:
            img_format = Path(file_path).suffix.lstrip('.').lower()
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            # Core image data
            image_path=file_path,               # For display and vectorization
            thumbnail_base64=thumbnail_base64,  # For quick preview
            alt_text=alt_text,
            caption=image_info.get("caption"),
            width=width,
            height=height,
            original_size=original_size,
            format=img_format,
            mime_type=mime_type,
            # Image context (improves retrieval relevance)
            context_before=context_before,
            context_after=context_after,
            # Original image index
            image_index=image_info.get("image_index")
        )
        
        # Add sheet and page info
        if sheet_name:
            image_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            image_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    def _create_placeholder_image_chunk(
        self,
        placeholder_text: str,
        image_index: int,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> Dict[str, Any]:
        """
        Create image chunk from placeholder when no metadata is available.
        
        This is a fallback when the image data wasn't found in metadata.images.
        """
        content = f"[Image: {placeholder_text}]" if placeholder_text else "[Image]"
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            alt_text=placeholder_text,
            image_index=image_index
        )
        
        if sheet_name:
            image_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            image_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    def _create_image_chunk(
        self,
        image_path: str,
        alt_text: str,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create image chunk from Markdown/HTML image reference.
        
        Note: No base64 embedding at chunking stage - will be loaded during vectorization.
        """
        img_format = None
        
        if image_path:
            # Resolve relative path if base path is provided
            if self.image_base_path and not Path(image_path).is_absolute():
                if not image_path.startswith(('http://', 'https://', 'data:')):
                    resolved_path = str(Path(self.image_base_path) / image_path)
                else:
                    resolved_path = image_path
            else:
                resolved_path = image_path
            
            img_format = Path(image_path).suffix.lstrip('.').lower()
        else:
            resolved_path = image_path
        
        content = f"[Image: {alt_text}]" if alt_text else f"[Image: {image_path}]"
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            image_path=resolved_path,  # For vectorization stage
            alt_text=alt_text,
            caption=alt_text,
            format=img_format
        )
        
        if sheet_name:
            image_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            image_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    @staticmethod
    def load_image_as_base64(
        image_path: str,
        image_base_path: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """
        Load image and convert to base64 for multimodal embedding support.
        
        This is a utility method that can be called during vectorization stage
        to load full image data when needed for multimodal models.
        
        Supports:
        - Local file paths (absolute and relative)
        - HTTP/HTTPS URLs (with fetch)
        - Data URLs (extract existing base64)
        
        Args:
            image_path: Path or URL to the image
            image_base_path: Base path for resolving relative paths
        
        Returns:
            Tuple of (base64_string, width, height, format) or (None, None, None, None)
        """
        try:
            # Handle data URLs
            if image_path.startswith('data:'):
                return ImageExtractor._extract_data_url_base64(image_path)
            
            # Handle HTTP/HTTPS URLs
            if image_path.startswith(('http://', 'https://')):
                return ImageExtractor._fetch_url_image_base64(image_path)
            
            # Handle local file paths
            return ImageExtractor._load_local_image_base64(image_path, image_base_path)
            
        except Exception as e:
            logger.warning(f"Failed to load image {image_path}: {e}")
            return None, None, None, None
    
    @staticmethod
    def _extract_data_url_base64(
        data_url: str
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """Extract base64 from data URL."""
        # Parse data URL: data:image/png;base64,xxxxx
        match = re.match(r'data:image/(\w+);base64,(.+)', data_url)
        if not match:
            return None, None, None, None
        
        img_format = match.group(1)
        base64_str = match.group(2)
        
        # Try to get dimensions
        width, height = ImageExtractor._get_base64_image_dimensions(base64_str)
        
        return base64_str, width, height, img_format
    
    @staticmethod
    def _fetch_url_image_base64(
        url: str
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """Fetch image from URL and convert to base64."""
        try:
            import requests
            from io import BytesIO
            
            # Fetch with timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            base64_str = base64.b64encode(image_data).decode('utf-8')
            
            # Detect format from content-type or URL
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                img_format = 'png'
            elif 'gif' in content_type:
                img_format = 'gif'
            elif 'webp' in content_type:
                img_format = 'webp'
            else:
                img_format = 'jpeg'  # Default
            
            # Try to get dimensions
            width, height = None, None
            try:
                from PIL import Image
                img = Image.open(BytesIO(image_data))
                width, height = img.size
            except ImportError:
                pass
            
            return base64_str, width, height, img_format
            
        except Exception:
            return None, None, None, None
    
    @staticmethod
    def _load_local_image_base64(
        image_path: str,
        image_base_path: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """Load local image file and convert to base64."""
        # Resolve relative path
        if image_base_path and not Path(image_path).is_absolute():
            full_path = Path(image_base_path) / image_path
        else:
            full_path = Path(image_path)
        
        if not full_path.exists():
            return None, None, None, None
        
        # Read and encode image
        with open(full_path, 'rb') as f:
            image_data = f.read()
        
        base64_str = base64.b64encode(image_data).decode('utf-8')
        img_format = full_path.suffix.lstrip('.').lower()
        
        # Try to get dimensions
        width, height = None, None
        try:
            from PIL import Image
            img = Image.open(full_path)
            width, height = img.size
        except ImportError:
            pass
        
        return base64_str, width, height, img_format
    
    @staticmethod
    def _get_base64_image_dimensions(
        base64_str: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """Get dimensions from base64 encoded image."""
        try:
            from PIL import Image
            from io import BytesIO
            
            image_data = base64.b64decode(base64_str)
            img = Image.open(BytesIO(image_data))
            return img.size
        except Exception:
            return None, None
