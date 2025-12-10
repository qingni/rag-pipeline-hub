"""Heading-based chunker implementation."""
from typing import List, Dict, Any
from .base_chunker import BaseChunker
from ...utils.chunking_helpers import HeadingDetector


class HeadingChunker(BaseChunker):
    """Chunker that splits text by heading structure."""
    
    def validate_params(self) -> None:
        """
        Validate heading chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        min_level = self.params.get('min_heading_level', 1)
        max_level = self.params.get('max_heading_level', 6)
        
        if not isinstance(min_level, int) or min_level < 1 or min_level > 6:
            raise ValueError("min_heading_level must be between 1 and 6")
        
        if not isinstance(max_level, int) or max_level < 1 or max_level > 6:
            raise ValueError("max_heading_level must be between 1 and 6")
        
        if min_level > max_level:
            raise ValueError("min_heading_level must be <= max_heading_level")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by headings.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        min_level = self.params.get('min_heading_level', 1)
        max_level = self.params.get('max_heading_level', 6)
        
        if not text or len(text) == 0:
            return []
        
        # Check if document has heading structure
        if not HeadingDetector.has_heading_structure(text, min_headings=2):
            # Fallback to paragraph chunking
            return self._fallback_to_paragraph(text)
        
        # Detect all headings
        all_headings = HeadingDetector.detect_headings(text)
        
        # Filter headings by level
        headings = [
            h for h in all_headings
            if min_level <= h[3] <= max_level
        ]
        
        if not headings:
            # No headings in range, fallback
            return self._fallback_to_paragraph(text)
        
        chunks = []
        chunk_index = 0
        
        for i, heading in enumerate(headings):
            start_pos, _, heading_text, level = heading
            
            # Find content end (next heading or end of text)
            if i < len(headings) - 1:
                end_pos = headings[i + 1][0]
            else:
                end_pos = len(text)
            
            # Extract content including heading
            content = text[start_pos:end_pos].strip()
            
            if content:
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    strategy="heading",
                    heading_text=heading_text,
                    heading_level=level,
                    min_level=min_level,
                    max_level=max_level
                )
                chunks.append(chunk)
                chunk_index += 1
        
        # If no chunks created, fallback
        if not chunks:
            return self._fallback_to_paragraph(text)
        
        return chunks
    
    def _fallback_to_paragraph(self, text: str) -> List[Dict[str, Any]]:
        """
        Fallback to paragraph-based chunking when no headings found.
        
        Args:
            text: Input text
        
        Returns:
            List of chunk dictionaries with fallback indicator
        """
        from .paragraph_chunker import ParagraphChunker
        
        # Use paragraph chunker with default params
        fallback_chunker = ParagraphChunker(
            min_chunk_size=100,
            max_chunk_size=1000
        )
        
        chunks = fallback_chunker.chunk(text)
        
        # Add fallback indicator to metadata
        for chunk in chunks:
            chunk['metadata']['fallback_strategy'] = 'paragraph'
            chunk['metadata']['fallback_reason'] = 'insufficient_heading_structure'
            chunk['metadata']['original_strategy'] = 'heading'
        
        return chunks
