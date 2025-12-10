"""Paragraph-based chunker implementation."""
from typing import List, Dict, Any
import re
from .base_chunker import BaseChunker


class ParagraphChunker(BaseChunker):
    """Chunker that splits text by paragraphs."""
    
    def validate_params(self) -> None:
        """
        Validate paragraph chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        min_chunk_size = self.params.get('min_chunk_size', 100)
        max_chunk_size = self.params.get('max_chunk_size', 1000)
        
        if not isinstance(min_chunk_size, int) or min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be a positive integer")
        
        if not isinstance(max_chunk_size, int) or max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be a positive integer")
        
        if min_chunk_size >= max_chunk_size:
            raise ValueError("min_chunk_size must be less than max_chunk_size")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by paragraphs.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        min_chunk_size = self.params.get('min_chunk_size', 100)
        max_chunk_size = self.params.get('max_chunk_size', 1000)
        
        if not text or len(text) == 0:
            return []
        
        # Split by double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            # If single paragraph exceeds max size, split it
            if para_length > max_chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    content = '\n\n'.join(current_chunk)
                    chunk = self._create_chunk(
                        content=content,
                        index=chunk_index,
                        start_pos=current_start,
                        end_pos=current_start + len(content),
                        strategy="paragraph",
                        paragraph_count=len(current_chunk)
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph by character
                para_chunks = self._split_large_paragraph(
                    para,
                    max_chunk_size,
                    current_start,
                    chunk_index
                )
                chunks.extend(para_chunks)
                chunk_index += len(para_chunks)
                current_start = text.find(para) + para_length
                continue
            
            # Check if adding this paragraph would exceed max size
            if current_length + para_length > max_chunk_size and current_chunk:
                # Save current chunk
                content = '\n\n'.join(current_chunk)
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=current_start,
                    end_pos=current_start + len(content),
                    strategy="paragraph",
                    paragraph_count=len(current_chunk)
                )
                chunks.append(chunk)
                chunk_index += 1
                current_chunk = []
                current_length = 0
                current_start = text.find(para)
            
            # Add paragraph to current chunk
            if not current_chunk:
                current_start = text.find(para, current_start)
            
            current_chunk.append(para)
            current_length += para_length
            
            # If chunk meets min size and is reasonably sized, save it
            if current_length >= min_chunk_size:
                content = '\n\n'.join(current_chunk)
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=current_start,
                    end_pos=current_start + len(content),
                    strategy="paragraph",
                    paragraph_count=len(current_chunk)
                )
                chunks.append(chunk)
                chunk_index += 1
                current_chunk = []
                current_length = 0
        
        # Save remaining paragraphs as final chunk
        if current_chunk:
            content = '\n\n'.join(current_chunk)
            chunk = self._create_chunk(
                content=content,
                index=chunk_index,
                start_pos=current_start,
                end_pos=current_start + len(content),
                strategy="paragraph",
                paragraph_count=len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_large_paragraph(
        self,
        paragraph: str,
        max_size: int,
        start_pos: int,
        start_index: int
    ) -> List[Dict[str, Any]]:
        """
        Split a large paragraph into smaller chunks.
        
        Args:
            paragraph: Paragraph text
            max_size: Maximum chunk size
            start_pos: Starting position in original text
            start_index: Starting chunk index
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        length = len(paragraph)
        pos = 0
        chunk_index = start_index
        
        while pos < length:
            end = min(pos + max_size, length)
            content = paragraph[pos:end].strip()
            
            if content:
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=start_pos + pos,
                    end_pos=start_pos + end,
                    strategy="paragraph",
                    paragraph_count=1,
                    split_from_large=True
                )
                chunks.append(chunk)
                chunk_index += 1
            
            pos = end
        
        return chunks
