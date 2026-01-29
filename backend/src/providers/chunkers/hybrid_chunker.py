"""Hybrid chunker that applies different strategies to different content types."""
from typing import List, Dict, Any, Optional
import re
import logging
from .base_chunker import BaseChunker
from .image_extractor import ImageExtractor

logger = logging.getLogger(__name__)

# 支持的 Embedding 模型列表（与 SemanticChunker 保持一致）
SUPPORTED_EMBEDDING_MODELS = ['bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding']


class HybridChunker(BaseChunker):
    """
    Hybrid chunker that applies different chunking strategies to different content types.
    
    Supports:
    - Text content: semantic, paragraph, or character chunking
    - Code blocks: line-based chunking
    - Tables: independent chunks (preserve as Markdown)
    - Images: independent chunks (using unified ImageExtractor for multimodal retrieval)
    
    When text_strategy is 'semantic', supports embedding models:
    - bge-m3: 1024维，8K上下文，多语言，速度快（推荐）
    - qwen3-embedding-8b: 4096维，32K上下文，高精度
    - hunyuan-embedding: 1024维，腾讯混元
    
    Image extraction uses the same unified ImageExtractor as MultimodalChunker,
    ensuring consistent image handling across all chunking strategies for multimodal retrieval.
    """
    
    def __init__(self, **params):
        """
        Initialize hybrid chunker with content-type specific strategies.
        
        Supported params:
        - text_strategy: Strategy for text content ('semantic', 'paragraph', 'character', 'heading')
        - embedding_model: Model for semantic chunking (default: 'bge-m3')
        - use_embedding: Enable/disable embedding for semantic (default: True)
        - code_strategy: Strategy for code blocks ('lines', 'character', 'none')
        - table_strategy: Strategy for tables ('independent', 'merge_with_text')
        - include_images: Whether to extract images using unified ImageExtractor (default: True)
        - image_base_path: Base path for resolving relative image paths
        """
        super().__init__(**params)
        self._sub_chunkers = {}
        
        # Store embedding params for semantic text chunking
        self._embedding_model = params.get('embedding_model', 'bge-m3')
        self._use_embedding = params.get('use_embedding', True)
        
        # Image extraction params
        self._include_images = params.get('include_images', True)
        self._image_base_path = params.get('image_base_path')
        self._image_extractor: Optional[ImageExtractor] = None
    
    def validate_params(self) -> None:
        """
        Validate hybrid chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Text strategy
        text_strategy = self.params.get('text_strategy', 'semantic')
        if text_strategy not in ['semantic', 'paragraph', 'character', 'heading']:
            raise ValueError(f"Invalid text_strategy: {text_strategy}")
        
        # Code strategy
        code_strategy = self.params.get('code_strategy', 'lines')
        if code_strategy not in ['lines', 'character', 'none']:
            raise ValueError(f"Invalid code_strategy: {code_strategy}")
        
        # Table strategy
        table_strategy = self.params.get('table_strategy', 'independent')
        if table_strategy not in ['independent', 'merge_with_text']:
            raise ValueError(f"Invalid table_strategy: {table_strategy}")
        
        # Validate size parameters
        text_chunk_size = self.params.get('text_chunk_size', 500)
        if not isinstance(text_chunk_size, int) or text_chunk_size < 100:
            raise ValueError("text_chunk_size must be >= 100")
        
        code_chunk_lines = self.params.get('code_chunk_lines', 50)
        if not isinstance(code_chunk_lines, int) or code_chunk_lines < 10:
            raise ValueError("code_chunk_lines must be >= 10")
        
        # Initialize unified image extractor if images are enabled
        self._include_images = self.params.get('include_images', True)
        self._image_base_path = self.params.get('image_base_path')
        
        if self._include_images:
            self._image_extractor = ImageExtractor(
                image_base_path=self._image_base_path,
                include_images=self._include_images
            )
    
    def _get_text_chunker(self):
        """Get or create the text chunker based on configuration."""
        if 'text' not in self._sub_chunkers:
            from . import get_chunker
            
            text_strategy = self.params.get('text_strategy', 'semantic')
            text_params = {
                'chunk_size': self.params.get('text_chunk_size', 500),
                'overlap': self.params.get('text_overlap', 50),
            }
            
            # Strategy-specific params
            if text_strategy == 'semantic':
                text_params['similarity_threshold'] = self.params.get('similarity_threshold', 0.5)
                text_params['min_chunk_size'] = self.params.get('text_chunk_size', 500)
                text_params['max_chunk_size'] = self.params.get('text_chunk_size', 500) * 3
                # Pass embedding params from HybridChunker
                text_params['use_embedding'] = self._use_embedding
                text_params['embedding_model'] = self._embedding_model
                text_params['embedding_similarity_threshold'] = self.params.get(
                    'embedding_similarity_threshold', 0.7
                )
            elif text_strategy == 'paragraph':
                text_params['min_chunk_size'] = self.params.get('text_chunk_size', 500) // 2
                text_params['max_chunk_size'] = self.params.get('text_chunk_size', 500) * 2
            elif text_strategy == 'heading':
                text_params['min_heading_level'] = self.params.get('min_heading_level', 1)
                text_params['max_heading_level'] = self.params.get('max_heading_level', 3)
            
            self._sub_chunkers['text'] = get_chunker(text_strategy, **text_params)
        
        return self._sub_chunkers['text']
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text using hybrid strategy based on content type.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
                     Expected to contain 'images' array from document loading for image extraction
        
        Returns:
            List of chunk dictionaries with content type markers
        """
        if not text or len(text) == 0:
            return []
        
        metadata = metadata or {}
        chunks = []
        chunk_index = 0
        
        # First, extract images using unified ImageExtractor if enabled
        # This ensures consistent image handling with MultimodalChunker
        image_regions = []
        if self._include_images and self._image_extractor:
            image_chunks, image_regions = self._image_extractor.extract_images(
                text=text,
                metadata=metadata,
                global_offset=0
            )
            chunks.extend(image_chunks)
            chunk_index += len(image_chunks)
        
        # Extract different content types (excluding already processed image regions)
        content_segments = self._segment_content(text, image_regions)
        
        for segment in content_segments:
            segment_type = segment['type']
            segment_content = segment['content']
            segment_start = segment['start_pos']
            
            if segment_type == 'code':
                # Chunk code blocks
                code_chunks = self._chunk_code(segment_content, segment_start, chunk_index)
                chunks.extend(code_chunks)
                chunk_index += len(code_chunks)
                
            elif segment_type == 'table':
                # Handle tables as independent chunks
                table_strategy = self.params.get('table_strategy', 'independent')
                
                if table_strategy == 'independent':
                    table_chunk = self._create_chunk(
                        content=segment_content,
                        index=chunk_index,
                        start_pos=segment_start,
                        end_pos=segment_start + len(segment_content),
                        chunk_type='table',
                        strategy='hybrid',
                        content_type='table',
                        table_rows=segment.get('rows', 0),
                        table_cols=segment.get('cols', 0)
                    )
                    chunks.append(table_chunk)
                    chunk_index += 1
                # else: merge_with_text - will be handled with surrounding text
                
            elif segment_type == 'text':
                # Chunk regular text
                text_chunks = self._chunk_text(segment_content, segment_start, chunk_index)
                chunks.extend(text_chunks)
                chunk_index += len(text_chunks)
        
        # Ensure sequential chunk_index
        for i, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = i
        
        logger.info(f"Hybrid chunking produced {len(chunks)} chunks")
        return chunks
    
    def _segment_content(
        self,
        text: str,
        exclude_regions: List[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Segment content into different types (text, code, table).
        
        Note: Images are now handled separately by ImageExtractor before this method.
        This method only handles code blocks and tables.
        
        Args:
            text: Input text
            exclude_regions: List of (start, end, type) tuples to exclude (e.g., image regions)
        
        Returns:
            List of content segments with type and position
        """
        segments = []
        exclude_regions = exclude_regions or []
        
        # Pattern to match code blocks (fenced or indented)
        code_pattern = r'```[\w]*\n[\s\S]*?```|`{3,}[\s\S]*?`{3,}'
        
        # Pattern to match Markdown tables
        table_pattern = r'(?:^\|.+\|$\n)+(?:^\|[-:| ]+\|$\n)(?:^\|.+\|$\n?)+'
        
        # Combine patterns (excluding images - now handled by ImageExtractor)
        combined_pattern = f'({code_pattern})|({table_pattern})'
        
        # Track all non-text regions
        non_text_regions = list(exclude_regions)  # Start with excluded regions
        
        # Find code and table matches
        for match in re.finditer(combined_pattern, text, re.MULTILINE):
            match_start = match.start()
            match_end = match.end()
            matched_text = match.group()
            
            # Skip if overlaps with excluded regions
            if any(r[0] <= match_start < r[1] or r[0] < match_end <= r[1]
                   for r in exclude_regions):
                continue
            
            # Determine segment type
            if match.group(1):  # Code block
                segments.append({
                    'type': 'code',
                    'content': matched_text,
                    'start_pos': match_start,
                    'end_pos': match_end,
                    'language': self._extract_code_language(matched_text)
                })
                non_text_regions.append((match_start, match_end, 'code'))
            elif match.group(2):  # Table
                rows, cols = self._count_table_dimensions(matched_text)
                segments.append({
                    'type': 'table',
                    'content': matched_text,
                    'start_pos': match_start,
                    'end_pos': match_end,
                    'rows': rows,
                    'cols': cols
                })
                non_text_regions.append((match_start, match_end, 'table'))
        
        # Extract text segments (excluding all non-text regions)
        text_segments = self._extract_text_segments(text, non_text_regions)
        segments.extend(text_segments)
        
        # Sort segments by position
        segments.sort(key=lambda x: x['start_pos'])
        
        # If no special content found, treat entire text as text
        if not segments:
            segments.append({
                'type': 'text',
                'content': text,
                'start_pos': 0
            })
        
        return segments
    
    def _extract_text_segments(
        self,
        text: str,
        non_text_regions: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Extract text segments that are not covered by non-text regions.
        
        Args:
            text: Full text
            non_text_regions: List of (start, end, type) tuples
            
        Returns:
            List of text segment dictionaries
        """
        segments = []
        
        # Sort regions by start position
        sorted_regions = sorted(non_text_regions, key=lambda r: r[0])
        
        current_pos = 0
        for start, end, _ in sorted_regions:
            if current_pos < start:
                text_content = text[current_pos:start]
                if text_content.strip():
                    segments.append({
                        'type': 'text',
                        'content': text_content,
                        'start_pos': current_pos
                    })
            current_pos = max(current_pos, end)
        
        # Add remaining text
        if current_pos < len(text):
            remaining = text[current_pos:]
            if remaining.strip():
                segments.append({
                    'type': 'text',
                    'content': remaining,
                    'start_pos': current_pos
                })
        
        return segments
    
    def _extract_code_language(self, code_block: str) -> str:
        """Extract programming language from code fence."""
        match = re.match(r'```(\w+)', code_block)
        return match.group(1) if match else 'unknown'
    
    def _count_table_dimensions(self, table: str) -> tuple:
        """Count rows and columns in a Markdown table."""
        lines = [l for l in table.strip().split('\n') if l.strip()]
        rows = len(lines)
        
        if lines:
            # Count columns by counting | separators in first row
            first_row = lines[0]
            cols = first_row.count('|') - 1  # Subtract 1 for leading |
            if cols <= 0:
                cols = 1
        else:
            cols = 0
        
        return rows, cols
    
    def _chunk_text(
        self, 
        text: str, 
        base_pos: int, 
        start_index: int
    ) -> List[Dict[str, Any]]:
        """
        Chunk text content using configured text strategy.
        
        Args:
            text: Text content
            base_pos: Base position in original document
            start_index: Starting chunk index
        
        Returns:
            List of text chunks
        """
        if not text.strip():
            return []
        
        text_chunker = self._get_text_chunker()
        raw_chunks = text_chunker.chunk(text)
        
        # Adjust positions and add hybrid metadata
        chunks = []
        for i, raw_chunk in enumerate(raw_chunks):
            chunk = self._create_chunk(
                content=raw_chunk['content'],
                index=start_index + i,
                start_pos=base_pos + raw_chunk['metadata'].get('start_position', 0),
                end_pos=base_pos + raw_chunk['metadata'].get('end_position', len(raw_chunk['content'])),
                chunk_type='text',
                strategy='hybrid',
                content_type='text',
                sub_strategy=self.params.get('text_strategy', 'semantic')
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_code(
        self, 
        code: str, 
        base_pos: int, 
        start_index: int
    ) -> List[Dict[str, Any]]:
        """
        Chunk code content.
        
        Args:
            code: Code content (may include fences)
            base_pos: Base position in original document
            start_index: Starting chunk index
        
        Returns:
            List of code chunks
        """
        code_strategy = self.params.get('code_strategy', 'lines')
        
        if code_strategy == 'none':
            # Keep as single chunk
            return [self._create_chunk(
                content=code,
                index=start_index,
                start_pos=base_pos,
                end_pos=base_pos + len(code),
                chunk_type='code',
                strategy='hybrid',
                content_type='code',
                language=self._extract_code_language(code)
            )]
        
        # Extract code content from fences
        match = re.match(r'```(\w*)\n([\s\S]*?)```', code)
        if match:
            language = match.group(1) or 'unknown'
            code_content = match.group(2)
        else:
            language = 'unknown'
            code_content = code
        
        if code_strategy == 'lines':
            return self._chunk_code_by_lines(
                code_content, language, base_pos, start_index
            )
        else:  # character
            return self._chunk_code_by_chars(
                code_content, language, base_pos, start_index
            )
    
    def _chunk_code_by_lines(
        self,
        code: str,
        language: str,
        base_pos: int,
        start_index: int
    ) -> List[Dict[str, Any]]:
        """Chunk code by number of lines."""
        lines_per_chunk = self.params.get('code_chunk_lines', 50)
        overlap_lines = self.params.get('code_overlap_lines', 5)
        
        lines = code.split('\n')
        chunks = []
        
        i = 0
        while i < len(lines):
            end = min(i + lines_per_chunk, len(lines))
            chunk_lines = lines[i:end]
            content = '\n'.join(chunk_lines)
            
            # Calculate position
            start_char = sum(len(l) + 1 for l in lines[:i])
            end_char = start_char + len(content)
            
            chunk = self._create_chunk(
                content=f"```{language}\n{content}\n```",
                index=start_index + len(chunks),
                start_pos=base_pos + start_char,
                end_pos=base_pos + end_char,
                chunk_type='code',
                strategy='hybrid',
                content_type='code',
                language=language,
                line_start=i + 1,
                line_end=end,
                total_lines=len(lines)
            )
            chunks.append(chunk)
            
            i = end - overlap_lines if end < len(lines) else end
        
        return chunks
    
    def _chunk_code_by_chars(
        self,
        code: str,
        language: str,
        base_pos: int,
        start_index: int
    ) -> List[Dict[str, Any]]:
        """Chunk code by character count."""
        chunk_size = self.params.get('code_chunk_size', 1000)
        overlap = self.params.get('code_overlap', 100)
        
        chunks = []
        start = 0
        
        while start < len(code):
            end = min(start + chunk_size, len(code))
            content = code[start:end]
            
            chunk = self._create_chunk(
                content=f"```{language}\n{content}\n```",
                index=start_index + len(chunks),
                start_pos=base_pos + start,
                end_pos=base_pos + end,
                chunk_type='code',
                strategy='hybrid',
                content_type='code',
                language=language
            )
            chunks.append(chunk)
            
            start = end - overlap if end < len(code) else end
        
        return chunks
