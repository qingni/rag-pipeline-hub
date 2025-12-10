"""Helper utilities for chunking operations."""
import re
from typing import List, Tuple, Dict, Any


class HeadingDetector:
    """Utility class for detecting headings in text."""
    
    # Markdown headings: # H1, ## H2, ### H3, etc.
    MD_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # HTML headings: <h1>, <h2>, etc.
    HTML_HEADING_PATTERN = re.compile(r'<h([1-6])>(.*?)</h\1>', re.IGNORECASE)
    
    @staticmethod
    def detect_headings(text: str) -> List[Tuple[int, int, str, int]]:
        """
        Detect headings in text.
        
        Args:
            text: Input text
        
        Returns:
            List of tuples: (start_pos, end_pos, heading_text, level)
        """
        headings = []
        
        # Detect Markdown headings
        for match in HeadingDetector.MD_HEADING_PATTERN.finditer(text):
            level = len(match.group(1))  # Number of #
            heading_text = match.group(2).strip()
            headings.append((match.start(), match.end(), heading_text, level))
        
        # Detect HTML headings
        for match in HeadingDetector.HTML_HEADING_PATTERN.finditer(text):
            level = int(match.group(1))
            heading_text = match.group(2).strip()
            headings.append((match.start(), match.end(), heading_text, level))
        
        # Sort by position
        return sorted(headings, key=lambda x: x[0])
    
    @staticmethod
    def has_heading_structure(text: str, min_headings: int = 2) -> bool:
        """
        Check if document has sufficient heading structure.
        
        Args:
            text: Input text
            min_headings: Minimum number of headings required
        
        Returns:
            True if document has sufficient headings
        """
        headings = HeadingDetector.detect_headings(text)
        return len(headings) >= min_headings


class ChunkStatistics:
    """Utility class for calculating chunk statistics."""
    
    @staticmethod
    def calculate_statistics(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics for a list of chunks.
        
        Args:
            chunks: List of chunk dictionaries
        
        Returns:
            Statistics dictionary with avg_chunk_size, max_chunk_size, etc.
        """
        if not chunks:
            return {
                'avg_chunk_size': 0,
                'max_chunk_size': 0,
                'min_chunk_size': 0,
                'total_characters': 0
            }
        
        chunk_sizes = [chunk['metadata']['char_count'] for chunk in chunks]
        total_chars = sum(chunk_sizes)
        
        return {
            'avg_chunk_size': total_chars / len(chunks) if chunks else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0,
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'total_characters': total_chars
        }


class TextUtils:
    """General text processing utilities."""
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Input text
        
        Returns:
            List of sentences
        """
        # Simple sentence splitting for Chinese and English
        sentences = re.split(r'[。！？.!?]\s*', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text (handles both English and Chinese).
        
        Args:
            text: Input text
        
        Returns:
            Word count
        """
        # For English, split by whitespace
        # For Chinese, count characters (approximate)
        words = text.split()
        total = len(words)
        
        # Add Chinese character count
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total += chinese_chars
        
        return total
