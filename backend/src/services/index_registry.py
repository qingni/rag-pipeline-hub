"""
Index Registry Module

This module provides a registry for managing multiple vector indexes.
"""

import logging
from typing import Dict, Optional, List, Any
from threading import RLock

from ..models.vector_index import VectorIndex, IndexProvider
from .providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class IndexRegistry:
    """
    Registry for managing vector index instances
    
    Implements the Registry pattern for centralized index management
    with lazy loading and caching.
    """
    
    _instance: Optional["IndexRegistry"] = None
    _lock: RLock = RLock()
    
    def __init__(self):
        """Initialize the registry"""
        self._indexes: Dict[str, VectorIndex] = {}
        self._providers: Dict[str, BaseProvider] = {}
        self._instance_lock = RLock()
    
    def register_provider(self, provider_name: str, provider: BaseProvider):
        """
        Register a provider by name
        
        Args:
            provider_name: Name of the provider (e.g., 'faiss', 'milvus')
            provider: Provider instance
        """
        with self._instance_lock:
            self._providers[provider_name] = provider
            logger.info(f"Registered provider: {provider_name}")
    
    @classmethod
    def get_instance(cls) -> "IndexRegistry":
        """
        Get the singleton registry instance
        
        Returns:
            IndexRegistry instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close_all()
            cls._instance = None
    
    def register_index(self, index: VectorIndex, provider: BaseProvider):
        """
        Register an index with its provider
        
        Args:
            index: VectorIndex model
            provider: Provider instance
        """
        with self._instance_lock:
            self._indexes[index.name] = index
            self._providers[index.name] = provider
            logger.info(f"Registered index: {index.name} (provider: {index.provider})")
    
    def unregister_index(self, index_name: str):
        """
        Unregister an index
        
        Args:
            index_name: Name of the index to unregister
        """
        with self._instance_lock:
            if index_name in self._providers:
                self._providers[index_name].close()
                del self._providers[index_name]
            
            if index_name in self._indexes:
                del self._indexes[index_name]
                logger.info(f"Unregistered index: {index_name}")
    
    def get_index(self, index_name: str) -> Optional[VectorIndex]:
        """
        Get an index by name
        
        Args:
            index_name: Name of the index
            
        Returns:
            VectorIndex or None if not found
        """
        return self._indexes.get(index_name)
    
    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """
        Get a provider instance by name (provider name or index name)
        
        Args:
            name: Name of the provider or index
            
        Returns:
            BaseProvider or None if not found
        """
        # First try to get by provider name directly
        if name in self._providers:
            return self._providers[name]
        
        # Then try by index name (for backward compatibility)
        for idx_name, provider in self._providers.items():
            if idx_name == name:
                return provider
        
        return None
    
    def list_indexes(
        self,
        provider: Optional[IndexProvider] = None,
        namespace: Optional[str] = None
    ) -> List[VectorIndex]:
        """
        List all registered indexes with optional filtering
        
        Args:
            provider: Filter by provider type
            namespace: Filter by namespace
            
        Returns:
            List of VectorIndex models
        """
        indexes = list(self._indexes.values())
        
        if provider is not None:
            indexes = [idx for idx in indexes if idx.provider == provider]
        
        if namespace is not None:
            indexes = [idx for idx in indexes if idx.namespace == namespace]
        
        return indexes
    
    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index is registered
        
        Args:
            index_name: Name of the index
            
        Returns:
            True if exists
        """
        return index_name in self._indexes
    
    def get_index_count(self) -> int:
        """
        Get the total number of registered indexes
        
        Returns:
            Index count
        """
        return len(self._indexes)
    
    def close_all(self):
        """Close all provider connections"""
        with self._instance_lock:
            for provider in self._providers.values():
                try:
                    provider.close()
                except Exception as e:
                    logger.error(f"Error closing provider: {e}")
            
            self._providers.clear()
            self._indexes.clear()
            logger.info("Closed all index providers")
    
    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all registered indexes
        
        Returns:
            Dictionary mapping index names to health status
        """
        results = {}
        
        for index_name, provider in self._providers.items():
            try:
                results[index_name] = provider.health_check()
            except Exception as e:
                results[index_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return results
    
    def __len__(self) -> int:
        """Get the number of registered indexes"""
        return len(self._indexes)
    
    def __contains__(self, index_name: str) -> bool:
        """Check if an index is registered"""
        return index_name in self._indexes


# Convenience functions for global registry access

def get_registry() -> IndexRegistry:
    """Get the global index registry"""
    return IndexRegistry.get_instance()


def register_index(index: VectorIndex, provider: BaseProvider):
    """Register an index in the global registry"""
    get_registry().register_index(index, provider)


def get_index(index_name: str) -> Optional[VectorIndex]:
    """Get an index from the global registry"""
    return get_registry().get_index(index_name)


def get_provider(index_name: str) -> Optional[BaseProvider]:
    """Get a provider from the global registry"""
    return get_registry().get_provider(index_name)
