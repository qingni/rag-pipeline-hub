"""Multimodal chunker for handling tables, images, and code blocks."""
import re
import uuid
import base64
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .base_chunker import BaseChunker
from .image_extractor import ImageExtractor
from ...models.chunk_metadata import (
    ChunkTypeEnum,
    create_chunk_metadata
)


class MultimodalChunker(BaseChunker):
    """
    Chunker that extracts and processes multimodal content (tables, images, code blocks)
    from documents, generating separate chunks for each content type.
    
    This chunker:
    1. Extracts tables (Markdown format) as independent chunks
    2. Extracts images (with base64 or path) as independent chunks  
    3. Extracts code blocks as independent chunks
    4. Chunks remaining text using a configurable text strategy
    
    Image extraction is handled by the unified ImageExtractor module for consistency
    across different chunking strategies.
    """
    
    # Regex patterns for content extraction
    # Fixed: last row may not end with \n, so use \n? at the end
    TABLE_PATTERN = re.compile(
        r'(\|[^\n]+\|(?:\n\|[-:| ]+\|)?(?:\n\|[^\n]+\|)*)',
        re.MULTILINE
    )
    
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?\n([\s\S]*?)```',
        re.MULTILINE
    )
    
    def __init__(self, **params):
        """
        Initialize multimodal chunker.
        
        Args:
            include_tables: Whether to extract tables (default: True)
            include_images: Whether to extract images (default: True)
            include_code: Whether to extract code blocks (default: True)
            text_strategy: Strategy for text chunks ('character', 'paragraph') (default: 'character')
            text_chunk_size: Size for text chunks (default: 500)
            text_overlap: Overlap for text chunks (default: 50)
            min_table_rows: Minimum rows for table extraction (default: 2)
            min_code_lines: Minimum lines for code extraction (default: 3)
            image_base_path: Base path for resolving relative image paths
        """
        # Initialize image extractor placeholder before parent init
        # (will be properly set up in validate_params called by parent)
        self._image_extractor: Optional[ImageExtractor] = None
        super().__init__(**params)
    
    def validate_params(self) -> None:
        """Validate chunking parameters."""
        # Boolean parameters
        self.include_tables = self.params.get('include_tables', True)
        self.include_images = self.params.get('include_images', True)
        self.include_code = self.params.get('include_code', True)
        
        # Text chunking parameters
        self.text_strategy = self.params.get('text_strategy', 'character')
        if self.text_strategy not in ('character', 'paragraph', 'none'):
            raise ValueError(f"Invalid text_strategy: {self.text_strategy}")
        
        self.text_chunk_size = self.params.get('text_chunk_size', 500)
        if not 100 <= self.text_chunk_size <= 5000:
            raise ValueError("text_chunk_size must be between 100 and 5000")
        
        self.text_overlap = self.params.get('text_overlap', 50)
        if self.text_overlap >= self.text_chunk_size:
            raise ValueError("text_overlap must be less than text_chunk_size")
        
        # Extraction thresholds
        self.min_table_rows = self.params.get('min_table_rows', 2)
        self.min_code_lines = self.params.get('min_code_lines', 3)
        
        # Image processing
        self.image_base_path = self.params.get('image_base_path', None)
        
        # Initialize unified image extractor
        self._image_extractor = ImageExtractor(
            image_base_path=self.image_base_path,
            include_images=self.include_images
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text with multimodal content extraction.
        
        For Excel files with page metadata, each sheet is processed independently
        to ensure proper sheet_name association.
        
        Args:
            text: Input text with potential tables, images, and code
            metadata: Optional metadata about the source document
                     Expected format: {"pages": [{"page_number": 1, "sheet_name": "xxx", "text": "...", ...}], ...}
        
        Returns:
            List of chunks with appropriate types (text, table, image, code)
        """
        metadata = metadata or {}
        pages = metadata.get("pages", [])
        
        # Check if we have page-level data with sheet_name (Excel files)
        # If so, process each page independently to preserve sheet boundaries
        has_sheet_pages = pages and any(p.get("sheet_name") for p in pages)
        
        if has_sheet_pages:
            return self._chunk_by_pages(pages, metadata)
        else:
            return self._chunk_full_text(text, metadata)
    
    def _chunk_by_pages(
        self, 
        pages: List[Dict[str, Any]], 
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk document by pages, treating each page/sheet as an independent unit.
        This ensures Excel sheet boundaries are preserved.
        
        Args:
            pages: List of page data with text, sheet_name, etc.
            metadata: Document metadata
            
        Returns:
            List of chunks with proper sheet_name in metadata
        """
        all_chunks = []
        global_offset = 0
        
        for page in pages:
            page_text = page.get("text", "")
            sheet_name = page.get("sheet_name")
            page_number = page.get("page_number")
            
            if not page_text.strip():
                global_offset += len(page_text) + 2  # +2 for separator
                continue
            
            # Create page-specific metadata
            page_metadata = {
                **metadata,
                "current_sheet_name": sheet_name,
                "current_page_number": page_number
            }
            
            # Check if the content is a TSV table (openpyxl format)
            # TSV tables have tab-separated values
            is_tsv_table = self._is_tsv_table(page_text)
            
            if is_tsv_table and self.include_tables:
                # Treat entire page as a single table chunk
                chunk = self._create_tsv_table_chunk(
                    page_text, 
                    global_offset, 
                    sheet_name, 
                    page_number,
                    len(all_chunks)
                )
                all_chunks.append(chunk)
            else:
                # Process page with standard multimodal extraction
                page_chunks = self._chunk_single_page(
                    page_text, 
                    global_offset, 
                    sheet_name,
                    page_number,
                    page_metadata
                )
                all_chunks.extend(page_chunks)
            
            global_offset += len(page_text) + 2  # +2 for "\n\n" separator
        
        # Reassign global chunk indices
        for idx, chunk in enumerate(all_chunks):
            chunk['metadata']['chunk_index'] = idx
        
        return all_chunks
    
    def _is_tsv_table(self, text: str) -> bool:
        """
        Check if text is a TSV (Tab-Separated Values) table.
        TSV tables from openpyxl have tab-separated columns.
        """
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Check if most lines have tabs (indicating TSV format)
        tab_lines = sum(1 for line in lines if '\t' in line)
        return tab_lines >= len(lines) * 0.5  # At least 50% lines have tabs
    
    def _create_tsv_table_chunk(
        self, 
        text: str, 
        offset: int, 
        sheet_name: Optional[str],
        page_number: Optional[int],
        chunk_index: int
    ) -> Dict[str, Any]:
        """Create a table chunk from TSV formatted text."""
        lines = text.strip().split('\n')
        
        # Skip "Sheet: xxx" header line if present
        data_lines = []
        for line in lines:
            if line.startswith("Sheet:"):
                continue
            data_lines.append(line)
        
        # Count rows and columns
        row_count = len(data_lines)
        col_count = max(len(line.split('\t')) for line in data_lines) if data_lines else 0
        
        # Extract headers (first data row with tabs)
        headers = []
        for line in data_lines:
            if '\t' in line:
                headers = [h.strip() for h in line.split('\t')]
                break
        
        table_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.TABLE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=text,
            start_position=offset,
            end_position=offset + len(text),
            table_markdown=text,
            row_count=row_count,
            column_count=col_count,
            headers=headers,
            has_header=True,
            sheet_name=sheet_name
        )
        
        # Add page_number to metadata
        if page_number is not None:
            table_metadata['page_number'] = page_number
        
        return {
            'content': text,
            'chunk_type': ChunkTypeEnum.TABLE.value,
            'parent_id': None,
            'metadata': table_metadata
        }
    
    def _chunk_single_page(
        self, 
        text: str, 
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk a single page with multimodal content extraction.
        All chunks from this page will inherit the sheet_name.
        """
        chunks = []
        extracted_regions: List[Tuple[int, int, str]] = []
        
        # Extract Markdown tables
        if self.include_tables:
            table_chunks, table_regions = self._extract_tables_from_page(
                text, global_offset, sheet_name, page_number, metadata
            )
            chunks.extend(table_chunks)
            extracted_regions.extend(table_regions)
        
        # Extract code blocks  
        if self.include_code:
            code_chunks, code_regions = self._extract_code_from_page(
                text, global_offset, sheet_name, page_number, metadata
            )
            chunks.extend(code_chunks)
            extracted_regions.extend(code_regions)
        
        # Extract images using unified ImageExtractor
        if self.include_images:
            image_chunks, image_regions = self._image_extractor.extract_images(
                text=text,
                metadata=metadata,
                global_offset=global_offset,
                sheet_name=sheet_name,
                page_number=page_number
            )
            chunks.extend(image_chunks)
            extracted_regions.extend(image_regions)
        
        # Extract remaining text
        if self.text_strategy != 'none':
            text_chunks = self._extract_text_from_page(
                text, global_offset, extracted_regions, sheet_name, page_number, metadata
            )
            chunks.extend(text_chunks)
        
        return chunks
    
    def _extract_tables_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract Markdown tables from a single page."""
        chunks = []
        regions = []
        
        for match in self.TABLE_PATTERN.finditer(text):
            table_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            rows = [r.strip() for r in table_text.split('\n') if r.strip()]
            if len(rows) < self.min_table_rows:
                continue
            
            # Parse headers
            headers = self._parse_table_headers(rows[0]) if rows else []
            
            # Check for separator row
            has_separator = len(rows) > 1 and re.match(r'^\|[-:| ]+\|$', rows[1])
            data_row_count = len(rows) - (2 if has_separator else 1)
            
            table_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.TABLE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=table_text,
                start_position=global_offset + start_pos,
                end_position=global_offset + end_pos,
                table_markdown=table_text,
                row_count=data_row_count,
                column_count=len(headers),
                headers=headers,
                has_header=True,
                sheet_name=sheet_name
            )
            
            if page_number is not None:
                table_metadata['page_number'] = page_number
            
            chunks.append({
                'content': table_text,
                'chunk_type': ChunkTypeEnum.TABLE.value,
                'parent_id': None,
                'metadata': table_metadata
            })
            
            regions.append((start_pos, end_pos, 'table'))
        
        return chunks, regions
    
    def _parse_table_headers(self, header_row: str) -> List[str]:
        """
        Parse headers from a Markdown table header row.
        
        Args:
            header_row: The first row of a Markdown table (e.g., "| Col1 | Col2 |")
            
        Returns:
            List of header strings
        """
        if not header_row:
            return []
        
        # Remove leading/trailing pipes and split by pipe
        headers = []
        parts = header_row.strip().strip('|').split('|')
        for part in parts:
            header = part.strip()
            if header:
                headers.append(header)
        
        return headers
    
    def _extract_code_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract code blocks from a single page."""
        chunks = []
        regions = []
        
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            lines = code_content.split('\n')
            if len(lines) < self.min_code_lines:
                continue
            
            # Detect function/class names
            function_name = None
            class_name = None
            
            func_match = re.search(r'def\s+(\w+)\s*\(', code_content)
            if func_match:
                function_name = func_match.group(1)
            
            class_match = re.search(r'class\s+(\w+)[\s:(]', code_content)
            if class_match:
                class_name = class_match.group(1)
            
            code_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.CODE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=code_content,
                start_position=global_offset + start_pos,
                end_position=global_offset + end_pos,
                language=language,
                start_line=1,
                end_line=len(lines),
                function_name=function_name,
                class_name=class_name,
                is_complete_block=True
            )
            
            if sheet_name:
                code_metadata['sheet_name'] = sheet_name
            if page_number is not None:
                code_metadata['page_number'] = page_number
            
            chunks.append({
                'content': code_content,
                'chunk_type': ChunkTypeEnum.CODE.value,
                'parent_id': None,
                'metadata': code_metadata
            })
            
            regions.append((start_pos, end_pos, 'code'))
        
        return chunks, regions
    
    def _extract_text_from_page(
        self,
        text: str,
        global_offset: int,
        extracted_regions: List[Tuple[int, int, str]],
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract text chunks from a single page, excluding already extracted regions."""
        chunks = []
        
        # Sort regions by start position
        sorted_regions = sorted(extracted_regions, key=lambda r: r[0])
        
        # Find text segments
        text_segments = []
        current_pos = 0
        
        for start, end, _ in sorted_regions:
            if current_pos < start:
                text_segments.append((current_pos, start))
            current_pos = max(current_pos, end)
        
        if current_pos < len(text):
            text_segments.append((current_pos, len(text)))
        
        # Chunk each text segment
        for seg_start, seg_end in text_segments:
            segment_text = text[seg_start:seg_end].strip()
            if not segment_text:
                continue
            
            if self.text_strategy == 'character':
                segment_chunks = self._chunk_text_by_character_with_sheet(
                    segment_text, global_offset + seg_start, sheet_name, page_number, metadata
                )
            else:  # paragraph
                segment_chunks = self._chunk_text_by_paragraph_with_sheet(
                    segment_text, global_offset + seg_start, sheet_name, page_number, metadata
                )
            
            chunks.extend(segment_chunks)
        
        return chunks
    
    def _chunk_text_by_character_with_sheet(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text by character with sheet_name support."""
        chunks = []
        step = self.text_chunk_size - self.text_overlap
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + self.text_chunk_size]
            if not chunk_text.strip():
                continue
            
            chunk = self._create_chunk_with_sheet(
                content=chunk_text,
                index=len(chunks),
                start_pos=offset + i,
                end_pos=offset + i + len(chunk_text),
                chunk_type=ChunkTypeEnum.TEXT.value,
                sheet_name=sheet_name,
                page_number=page_number
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_text_by_paragraph_with_sheet(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text by paragraph with sheet_name support."""
        chunks = []
        
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_pos = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                current_pos += 2
                continue
            
            para_start = text.find(para, current_pos)
            if para_start == -1:
                para_start = current_pos
            
            para_end = para_start + len(para)
            
            chunk = self._create_chunk_with_sheet(
                content=para,
                index=len(chunks),
                start_pos=offset + para_start,
                end_pos=offset + para_end,
                chunk_type=ChunkTypeEnum.TEXT.value,
                sheet_name=sheet_name,
                page_number=page_number
            )
            chunks.append(chunk)
            
            current_pos = para_end
        
        return chunks
    
    def _create_chunk_with_sheet(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        chunk_type: str,
        sheet_name: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a chunk with sheet_name in metadata."""
        chunk_metadata = create_chunk_metadata(
            chunk_type=chunk_type,
            chunk_id=str(uuid.uuid4()),
            chunk_index=index,
            content=content,
            start_position=start_pos,
            end_position=end_pos
        )
        
        if sheet_name:
            chunk_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            chunk_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': chunk_type,
            'parent_id': None,
            'metadata': chunk_metadata
        }
    
    def _chunk_full_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Original chunking logic for documents without page/sheet structure.
        """
        chunks = []
        
        # Build position-to-sheet mapping for Excel files (legacy support)
        sheet_position_map = self._build_position_to_sheet_map(text, metadata.get("pages", []))
        
        # Track extracted regions to avoid double-processing
        extracted_regions: List[Tuple[int, int, str]] = []
        
        # Extract tables (with sheet_name support)
        if self.include_tables:
            table_chunks, table_regions = self._extract_tables(text, metadata, sheet_position_map)
            chunks.extend(table_chunks)
            extracted_regions.extend(table_regions)
        
        # Extract code blocks
        if self.include_code:
            code_chunks, code_regions = self._extract_code_blocks(text, metadata)
            chunks.extend(code_chunks)
            extracted_regions.extend(code_regions)
        
        # Extract images using unified ImageExtractor
        if self.include_images:
            image_chunks, image_regions = self._image_extractor.extract_images(
                text=text,
                metadata=metadata,
                global_offset=0
            )
            chunks.extend(image_chunks)
            extracted_regions.extend(image_regions)
        
        # Extract remaining text
        if self.text_strategy != 'none':
            text_chunks = self._extract_text(text, extracted_regions, metadata)
            chunks.extend(text_chunks)
        
        # Sort all chunks by position
        chunks.sort(key=lambda c: c['metadata'].get('start_position', 0))
        
        # Reassign sequence numbers
        for idx, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = idx
        
        return chunks
    
    def _build_position_to_sheet_map(
        self, 
        text: str, 
        pages: List[Dict[str, Any]]
    ) -> List[Tuple[int, int, Optional[str]]]:
        """
        Build a map of text position ranges to sheet names.
        
        Args:
            text: Full document text
            pages: List of page metadata with sheet_name info
        
        Returns:
            List of (start_pos, end_pos, sheet_name) tuples
        """
        if not pages:
            return []
        
        position_map = []
        current_pos = 0
        
        for page in pages:
            sheet_name = page.get("sheet_name")
            char_count = page.get("char_count", 0)
            
            if not sheet_name:
                # Skip pages without sheet_name, but update position
                current_pos += char_count + 2  # +2 for "\n\n" separator
                continue
            
            # Calculate page boundaries based on char_count
            page_start = current_pos
            page_end = current_pos + char_count
            
            position_map.append((page_start, page_end, sheet_name))
            current_pos = page_end + 2  # +2 for "\n\n" separator
        
        return position_map
    
    def _get_sheet_name_for_position(
        self, 
        position: int, 
        sheet_map: List[Tuple[int, int, Optional[str]]]
    ) -> Optional[str]:
        """Get sheet name for a given position in text."""
        for start, end, sheet_name in sheet_map:
            if start <= position < end:
                return sheet_name
        return None
    
    def _extract_tables(
        self, 
        text: str, 
        metadata: Dict[str, Any],
        sheet_position_map: List[Tuple[int, int, Optional[str]]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """
        Extract table chunks from text.
        
        Args:
            text: Input text
            metadata: Document metadata
            sheet_position_map: Mapping of positions to sheet names for Excel files
        """
        chunks = []
        regions = []
        sheet_position_map = sheet_position_map or []
        
        for match in self.TABLE_PATTERN.finditer(text):
            table_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Parse table structure
            rows = [r.strip() for r in table_text.split('\n') if r.strip()]
            
            # Skip separator rows for counting
            data_rows = [r for r in rows if not re.match(r'^\|[-:| ]+\|$', r)]
            
            if len(data_rows) < self.min_table_rows:
                continue
            
            # Count columns
            first_row = data_rows[0] if data_rows else ""
            column_count = first_row.count('|') - 1 if first_row else 0
            
            # Check for header (presence of separator row)
            has_header = any(re.match(r'^\|[-:| ]+\|$', r) for r in rows)
            
            # Determine sheet_name based on position
            sheet_name = self._get_sheet_name_for_position(start_pos, sheet_position_map)
            
            # Create table chunk
            table_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.TABLE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=table_text,
                start_position=start_pos,
                end_position=end_pos,
                table_index=len([c for c in chunks if c.get('chunk_type') == 'table']),
                row_count=len(data_rows),
                column_count=column_count,
                has_header=has_header,
                table_markdown=table_text,
                page_number=metadata.get('page_number'),
                sheet_name=sheet_name  # Include sheet_name for Excel files
            )
            
            chunks.append({
                'content': table_text,
                'chunk_type': ChunkTypeEnum.TABLE.value,
                'parent_id': None,
                'metadata': table_metadata
            })
            
            regions.append((start_pos, end_pos, 'table'))
        
        return chunks, regions
    
    def _extract_code_blocks(
        self, 
        text: str, 
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract code block chunks from text."""
        chunks = []
        regions = []
        
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Check minimum lines
            lines = code_content.split('\n')
            if len(lines) < self.min_code_lines:
                continue
            
            # Detect function/class names (basic detection)
            function_name = None
            class_name = None
            
            # Python detection
            func_match = re.search(r'def\s+(\w+)\s*\(', code_content)
            if func_match:
                function_name = func_match.group(1)
            
            class_match = re.search(r'class\s+(\w+)[\s:(]', code_content)
            if class_match:
                class_name = class_match.group(1)
            
            # Create code chunk
            code_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.CODE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=code_content,
                start_position=start_pos,
                end_position=end_pos,
                language=language,
                start_line=1,
                end_line=len(lines),
                function_name=function_name,
                class_name=class_name,
                is_complete_block=True
            )
            
            chunks.append({
                'content': code_content,
                'chunk_type': ChunkTypeEnum.CODE.value,
                'parent_id': None,
                'metadata': code_metadata
            })
            
            regions.append((start_pos, end_pos, 'code'))
        
        return chunks, regions
    
    def _extract_text(
        self, 
        text: str, 
        extracted_regions: List[Tuple[int, int, str]],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract text chunks from regions not covered by other content types."""
        chunks = []
        
        # Sort regions by start position
        sorted_regions = sorted(extracted_regions, key=lambda r: r[0])
        
        # Find text segments
        text_segments = []
        current_pos = 0
        
        for start, end, _ in sorted_regions:
            if current_pos < start:
                text_segments.append((current_pos, start))
            current_pos = max(current_pos, end)
        
        # Add final segment
        if current_pos < len(text):
            text_segments.append((current_pos, len(text)))
        
        # Chunk each text segment
        for seg_start, seg_end in text_segments:
            segment_text = text[seg_start:seg_end].strip()
            if not segment_text:
                continue
            
            if self.text_strategy == 'character':
                segment_chunks = self._chunk_text_by_character(
                    segment_text, seg_start, metadata
                )
            else:  # paragraph
                segment_chunks = self._chunk_text_by_paragraph(
                    segment_text, seg_start, metadata
                )
            
            chunks.extend(segment_chunks)
        
        return chunks
    
    def _chunk_text_by_character(
        self, 
        text: str, 
        offset: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text using character-based splitting."""
        chunks = []
        step = self.text_chunk_size - self.text_overlap
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + self.text_chunk_size]
            if not chunk_text.strip():
                continue
            
            chunk = self._create_chunk(
                content=chunk_text,
                index=len(chunks),
                start_pos=offset + i,
                end_pos=offset + i + len(chunk_text),
                chunk_type=ChunkTypeEnum.TEXT.value
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_text_by_paragraph(
        self, 
        text: str, 
        offset: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text by paragraphs."""
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_pos = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                current_pos += 2  # Skip empty paragraph
                continue
            
            # Find actual position in original text
            para_start = text.find(para, current_pos)
            if para_start == -1:
                para_start = current_pos
            
            para_end = para_start + len(para)
            
            chunk = self._create_chunk(
                content=para,
                index=len(chunks),
                start_pos=offset + para_start,
                end_pos=offset + para_end,
                chunk_type=ChunkTypeEnum.TEXT.value
            )
            chunks.append(chunk)
            
            current_pos = para_end
        
        return chunks
    
    def get_supported_types(self) -> List[str]:
        """Get list of content types this chunker can extract."""
        types = []
        if self.include_tables:
            types.append(ChunkTypeEnum.TABLE.value)
        if self.include_images:
            types.append(ChunkTypeEnum.IMAGE.value)
        if self.include_code:
            types.append(ChunkTypeEnum.CODE.value)
        if self.text_strategy != 'none':
            types.append(ChunkTypeEnum.TEXT.value)
        return types
