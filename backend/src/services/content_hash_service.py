"""
Content hash service for incremental embedding and caching.

Provides content hashing for:
- Incremental embedding (detect changed chunks)
- Vector caching (content-based cache keys)
"""
import hashlib
from typing import List, Dict, Any, Optional, Tuple


class ContentHashService:
    """
    Service for computing content hashes.
    
    Uses SHA-256 for secure, collision-resistant hashing.
    """
    
    HASH_PREFIX = "sha256:"
    
    def __init__(self):
        pass
    
    def compute_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content.
        
        Args:
            content: Text content to hash
            
        Returns:
            Hash string with prefix (e.g., "sha256:abc123...")
        """
        if not content:
            return f"{self.HASH_PREFIX}{'0' * 64}"
        
        hash_bytes = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return f"{self.HASH_PREFIX}{hash_bytes}"
    
    def compute_hash_raw(self, content: str) -> str:
        """
        Compute raw SHA-256 hash without prefix.
        
        Args:
            content: Text content to hash
            
        Returns:
            64-character hex string
        """
        if not content:
            return '0' * 64
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def compute_batch_hashes(self, contents: List[str]) -> List[str]:
        """
        Compute hashes for multiple contents.
        
        Args:
            contents: List of text contents
            
        Returns:
            List of hash strings
        """
        return [self.compute_hash(content) for content in contents]
    
    def make_cache_key(self, content: str, model: str) -> str:
        """
        Make cache key from content and model.
        
        Format: {hash_prefix}:{model}
        where hash_prefix is first 16 chars of content hash
        
        Args:
            content: Text content
            model: Model name
            
        Returns:
            Cache key string
        """
        content_hash = self.compute_hash_raw(content)
        return f"{content_hash[:16]}:{model}"
    
    def detect_changes(
        self,
        current_chunks: List[Dict[str, Any]],
        previous_hashes: Dict[str, str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        """
        Detect changes between current chunks and previous hashes.
        
        Args:
            current_chunks: List of current chunks with 'id' and 'content'
            previous_hashes: Dict mapping chunk_id to content_hash
            
        Returns:
            Tuple of (new_chunks, modified_chunks, unchanged_ids)
        """
        new_chunks = []
        modified_chunks = []
        unchanged_ids = []
        
        for chunk in current_chunks:
            chunk_id = chunk.get('id', chunk.get('chunk_id'))
            content = chunk.get('content', '')
            current_hash = self.compute_hash(content)
            
            if chunk_id not in previous_hashes:
                # New chunk
                new_chunks.append(chunk)
            elif previous_hashes[chunk_id] != current_hash:
                # Modified chunk
                modified_chunks.append(chunk)
            else:
                # Unchanged chunk
                unchanged_ids.append(chunk_id)
        
        return new_chunks, modified_chunks, unchanged_ids
    
    def build_hash_map(self, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Build a hash map from chunks.
        
        Args:
            chunks: List of chunks with 'id' and 'content'
            
        Returns:
            Dict mapping chunk_id to content_hash
        """
        hash_map = {}
        for chunk in chunks:
            chunk_id = chunk.get('id', chunk.get('chunk_id'))
            content = chunk.get('content', '')
            hash_map[chunk_id] = self.compute_hash(content)
        return hash_map
    
    def verify_hash(self, content: str, expected_hash: str) -> bool:
        """
        Verify content matches expected hash.
        
        Args:
            content: Text content to verify
            expected_hash: Expected hash string
            
        Returns:
            True if hashes match
        """
        computed = self.compute_hash(content)
        return computed == expected_hash
    
    def get_hash_prefix(self, content_hash: str, length: int = 16) -> str:
        """
        Get prefix of hash for cache key.
        
        Args:
            content_hash: Full hash string (with or without prefix)
            length: Prefix length
            
        Returns:
            Hash prefix
        """
        # Remove sha256: prefix if present
        if content_hash.startswith(self.HASH_PREFIX):
            content_hash = content_hash[len(self.HASH_PREFIX):]
        
        return content_hash[:length]


# Global instance for convenience
_default_service = None


def get_content_hash_service() -> ContentHashService:
    """Get default content hash service instance."""
    global _default_service
    if _default_service is None:
        _default_service = ContentHashService()
    return _default_service


def compute_content_hash(content: str) -> str:
    """
    Compute hash of content using default service.
    
    Args:
        content: Text content
        
    Returns:
        Hash string
    """
    return get_content_hash_service().compute_hash(content)


def make_cache_key(content: str, model: str) -> str:
    """
    Make cache key from content and model using default service.
    
    Args:
        content: Text content
        model: Model name
        
    Returns:
        Cache key string
    """
    return get_content_hash_service().make_cache_key(content, model)
