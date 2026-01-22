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
        
        # Check if text is structured data (each line is a record)
        # Detect by checking if text has single newlines but no double newlines,
        # or if each line looks like a key:value pair
        is_structured = self._is_structured_text(text)
        
        if is_structured:
            # For structured data, split by single newline to keep each record intact
            paragraphs = [line.strip() for line in text.split('\n') if line.strip()]
        else:
            # Standard paragraph splitting by double newlines
            paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0
        chunk_index = 0
        
        # For structured data, try to keep each record as its own chunk
        if is_structured:
            return self._chunk_structured_data(paragraphs, text, min_chunk_size, max_chunk_size)
        
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
    
    def _is_structured_text(self, text: str) -> bool:
        """
        Detect if text is structured data (each line is a complete record).
        
        Args:
            text: Input text
            
        Returns:
            True if text appears to be structured data
        """
        # Check if no double newlines exist (all single-line records)
        if '\n\n' not in text and '\n' in text:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if len(lines) >= 2:
                # Check if most lines look like key:value pairs
                # Pattern matches: "Key: Value" or "Key Name: Value Description"
                # Allow multiple colons in a line (e.g., "Game: Title: Description")
                kv_pattern = re.compile(r'^[^:]{2,100}:\s*.+$')
                kv_count = sum(1 for line in lines if kv_pattern.match(line))
                if kv_count / len(lines) > 0.5:
                    return True
                
                # Also check if lines have consistent length (structured data often does)
                # and each line is a complete record (no continuation indicators)
                avg_len = sum(len(l) for l in lines) / len(lines)
                if avg_len > 50 and all(len(l) > 30 for l in lines):
                    # Lines are substantial and uniform - likely structured records
                    return True
        return False
    
    def _chunk_structured_data(
        self, 
        records: List[str], 
        original_text: str,
        min_chunk_size: int,
        max_chunk_size: int
    ) -> List[Dict[str, Any]]:
        """
        Chunk structured data, keeping each record intact.
        
        For structured data like JSON key-value pairs, each line/record
        should be kept as a complete unit. Only merge records if they're
        very short, and never split a record in the middle.
        
        Args:
            records: List of record strings (one per line)
            original_text: Original text for position tracking
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        chunk_index = 0
        current_pos = 0
        
        for record in records:
            if not record:
                continue
            
            # Find position in original text
            start_pos = original_text.find(record, current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(record)
            
            # Create chunk for this record (one record = one chunk for structured data)
            chunk = self._create_chunk(
                content=record,
                index=chunk_index,
                start_pos=start_pos,
                end_pos=end_pos,
                strategy="paragraph",
                paragraph_count=1,
                is_structured_record=True
            )
            chunks.append(chunk)
            chunk_index += 1
            current_pos = end_pos
        
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
