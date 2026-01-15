"""Fallback manager for document loading.

This module implements the multi-level fallback strategy for document parsing,
automatically switching to backup parsers when the primary parser fails.
"""
from typing import Dict, Any, Optional, List, Callable
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from ..models.loading_result import StandardDocumentResult, ExtractionQuality
from ..models.loader_config import FormatStrategy
from ..loader_config.format_strategies import (
    FORMAT_STRATEGIES,
    LOADER_REGISTRY,
    get_format_strategy,
    get_loader_config
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 超时配置（秒）- 参考业内 RAG 应用最佳实践
DEFAULT_TIMEOUT = 120.0  # 默认超时
LARGE_FILE_TIMEOUT = 600.0  # 10分钟，用于大文件或复杂文档

# Docling 超时配置（Docling 需要深度解析，耗时较长）
DOCLING_BASE_TIMEOUT = 300.0  # Docling 基础超时 5 分钟
DOCLING_TIMEOUT_PER_MB = 60.0  # Docling 每 MB 额外 60 秒
DOCLING_TIMEOUT_PER_PAGE = 5.0  # Docling 每页额外 5 秒（用于大页数文档）
DOCLING_MAX_TIMEOUT = 1800.0  # Docling 最大超时 30 分钟

# 文件大小阈值（MB）
LARGE_FILE_THRESHOLD_MB = 5.0  # 超过此大小视为大文件
VERY_LARGE_FILE_THRESHOLD_MB = 20.0  # 超过此大小直接使用快速加载器


class FallbackManager:
    """Manages fallback strategy for document loading."""
    
    def __init__(self):
        """Initialize fallback manager."""
        self._loaders: Dict[str, Any] = {}
        self._loader_availability: Dict[str, bool] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="loader")
    
    def register_loader(self, name: str, loader: Any) -> None:
        """
        Register a loader instance.
        
        Args:
            name: Loader name
            loader: Loader instance with extract_text method
        """
        # 跳过 None loader
        if loader is None:
            logger.warning(f"Skipping registration of None loader: {name}")
            return
        
        self._loaders[name] = loader
        
        # Check availability
        if hasattr(loader, 'is_available'):
            self._loader_availability[name] = loader.is_available()
        else:
            self._loader_availability[name] = True
        
        logger.info(f"Registered loader: {name} (available: {self._loader_availability[name]})")
    
    def is_loader_available(self, name: str) -> bool:
        """
        Check if a loader is available.
        
        对于支持动态检查的 loader（如 docling_serve），每次都重新检查可用性
        """
        loader = self._loaders.get(name)
        if not loader:
            return False
        
        # 如果 loader 有 is_available 方法，调用它进行实时检查
        if hasattr(loader, 'is_available'):
            return loader.is_available()
        
        # 否则使用缓存的结果
        return self._loader_availability.get(name, False)
    
    def get_loader(self, name: str) -> Optional[Any]:
        """Get a registered loader by name."""
        return self._loaders.get(name)
    
    def _calculate_timeout(
        self,
        loader_name: str,
        file_size_mb: float,
        base_timeout: float,
        page_count: int = 0
    ) -> float:
        """
        Calculate dynamic timeout based on loader type, file size and page count.
        
        Args:
            loader_name: Name of the loader
            file_size_mb: File size in MB
            base_timeout: Base timeout in seconds
            page_count: Number of pages (if known)
            
        Returns:
            Calculated timeout in seconds
        """
        # Docling Serve 需要更长的超时时间，特别是对于复杂文档
        if loader_name in ("docling_serve", "docling"):
            # 基础超时 + 每 MB 额外时间 + 每页额外时间
            timeout = DOCLING_BASE_TIMEOUT
            timeout += file_size_mb * DOCLING_TIMEOUT_PER_MB
            
            # 如果知道页数，按页数计算（大页数文档更耗时）
            if page_count > 0:
                timeout += page_count * DOCLING_TIMEOUT_PER_PAGE
            else:
                # 估算页数：假设每 MB 约 10 页
                estimated_pages = max(file_size_mb * 10, 1)
                timeout += estimated_pages * DOCLING_TIMEOUT_PER_PAGE
            
            # 限制最大超时
            return min(timeout, DOCLING_MAX_TIMEOUT)
        
        # Unstructured 也需要较长超时
        if loader_name == "unstructured":
            timeout = base_timeout + (file_size_mb * 30.0)
            return min(timeout, LARGE_FILE_TIMEOUT)
        
        # 大文件使用更长超时
        if file_size_mb > LARGE_FILE_THRESHOLD_MB:
            return max(base_timeout, LARGE_FILE_TIMEOUT)
        
        return base_timeout
    
    def _load_with_timeout(
        self,
        loader: Any,
        file_path: str,
        timeout: float
    ) -> Dict[str, Any]:
        """
        Execute loader with timeout protection.
        
        Args:
            loader: Loader instance
            file_path: Path to document
            timeout: Timeout in seconds
            
        Returns:
            Loading result or timeout error
        """
        try:
            future = self._executor.submit(loader.extract_text, file_path)
            result = future.result(timeout=timeout)
            return result
        except FuturesTimeoutError:
            return {
                "success": False,
                "loader": getattr(loader, 'name', 'unknown'),
                "error": f"Timeout after {timeout:.0f}s",
                "error_details": {
                    "timeout_seconds": timeout,
                    "suggestion": "Try using a faster loader (e.g., pymupdf for PDF)"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "loader": getattr(loader, 'name', 'unknown'),
                "error": str(e)
            }
    
    def load_with_fallback(
        self,
        file_path: str,
        file_format: str,
        file_size_bytes: int = 0,
        preferred_loader: Optional[str] = None,
        enable_fallback: bool = True,
        timeout: float = DEFAULT_TIMEOUT
    ) -> Dict[str, Any]:
        """
        Load document with automatic fallback strategy.
        
        Args:
            file_path: Path to the document file
            file_format: File format/extension
            file_size_bytes: File size in bytes (for intelligent selection)
            preferred_loader: Preferred loader to try first
            enable_fallback: Whether to enable fallback to other loaders
            timeout: Base timeout in seconds for each loader attempt
            
        Returns:
            Dictionary with loading result
        """
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # 对于超大文件，直接使用快速加载器
        if file_size_mb > VERY_LARGE_FILE_THRESHOLD_MB and not preferred_loader:
            logger.info(
                f"Very large file detected ({file_size_mb:.1f} MB), "
                f"using fast loader to avoid timeout"
            )
        
        # Get format strategy
        try:
            strategy = get_format_strategy(file_format)
        except KeyError:
            return {
                "success": False,
                "loader": "unknown",
                "error": f"Unsupported format: {file_format}",
                "error_details": {
                    "supported_formats": list(FORMAT_STRATEGIES.keys())
                }
            }
        
        # Build loader chain
        if preferred_loader:
            # 用户明确指定了加载器
            if not self.is_loader_available(preferred_loader):
                # 用户指定的加载器不可用，返回明确的错误
                loader = self._loaders.get(preferred_loader)
                reason = "Loader not registered"
                if loader and hasattr(loader, 'get_unavailable_reason'):
                    reason = loader.get_unavailable_reason()
                
                if not enable_fallback:
                    # 禁用 fallback 时直接报错
                    return {
                        "success": False,
                        "loader": preferred_loader,
                        "error": f"Specified loader '{preferred_loader}' is not available: {reason}",
                        "error_details": {
                            "preferred_loader": preferred_loader,
                            "reason": reason,
                            "suggestion": "Install the required library or choose another loader"
                        }
                    }
                else:
                    # 启用 fallback 时记录警告，继续使用其他加载器
                    logger.warning(
                        f"Preferred loader '{preferred_loader}' is not available ({reason}), "
                        f"falling back to other loaders"
                    )
            
            # Use preferred loader first, then fallback chain
            loader_chain = [preferred_loader]
            if enable_fallback:
                for loader in strategy.get_loader_chain(file_size_mb):
                    if loader not in loader_chain:
                        loader_chain.append(loader)
        else:
            loader_chain = strategy.get_loader_chain(file_size_mb)
        
        logger.info(f"Loader chain for {file_format}: {loader_chain}")
        
        # Log availability check for each loader
        for loader_name in loader_chain:
            is_avail = self.is_loader_available(loader_name)
            loader_obj = self._loaders.get(loader_name)
            logger.info(f"  - {loader_name}: available={is_avail}, registered={loader_obj is not None}")
        
        if not enable_fallback:
            loader_chain = loader_chain[:1]  # Only try first loader
        
        # Filter to available loaders
        available_chain = [
            loader for loader in loader_chain
            if self.is_loader_available(loader)
        ]
        
        logger.info(f"Available loader chain: {available_chain}")
        
        if not available_chain:
            return {
                "success": False,
                "loader": "none",
                "error": "No available loaders for this format",
                "error_details": {
                    "requested_loaders": loader_chain,
                    "available_loaders": [
                        name for name, available in self._loader_availability.items()
                        if available
                    ]
                }
            }
        
        # Try each loader in chain
        errors = {}
        original_parser = available_chain[0]
        
        for i, loader_name in enumerate(available_chain):
            loader = self.get_loader(loader_name)
            if not loader:
                errors[loader_name] = "Loader not registered"
                continue
            
            # Calculate dynamic timeout for this loader
            loader_timeout = self._calculate_timeout(loader_name, file_size_mb, timeout)
            
            logger.info(
                f"Trying loader: {loader_name} for {file_path} "
                f"(timeout: {loader_timeout:.0f}s, size: {file_size_mb:.1f}MB)"
            )
            
            try:
                start_time = time.time()
                
                # Use timeout-protected loading
                result = self._load_with_timeout(loader, file_path, loader_timeout)
                
                elapsed = time.time() - start_time
                
                # Validate result
                if self._is_valid_result(result):
                    # Add timing info
                    result["processing_time_seconds"] = elapsed
                    
                    # Mark fallback if not first loader
                    if i > 0:
                        result["fallback_used"] = True
                        result["fallback_reason"] = f"Primary parser ({original_parser}) failed: {errors.get(original_parser, 'Unknown error')}"
                        result["original_parser"] = original_parser
                        logger.info(f"Fallback to {loader_name} successful after {elapsed:.1f}s")
                    else:
                        result["fallback_used"] = False
                        logger.info(f"Loader {loader_name} completed in {elapsed:.1f}s")
                    
                    return result
                else:
                    error_msg = result.get("error", "Invalid result (empty or no content)")
                    errors[loader_name] = error_msg
                    logger.warning(f"Loader {loader_name} returned invalid result: {error_msg}")
                    
            except Exception as e:
                errors[loader_name] = str(e)
                logger.warning(f"Loader {loader_name} failed: {str(e)}")
        
        # All loaders failed
        return {
            "success": False,
            "loader": available_chain[-1] if available_chain else "none",
            "error": "All parsers failed",
            "error_details": {
                "attempted_parsers": available_chain,
                "errors": errors,
                "suggestion": "Try uploading a smaller file or using a different format"
            }
        }
    
    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """
        Check if a loading result is valid.
        
        Args:
            result: Loading result dictionary
            
        Returns:
            True if result is valid
        """
        if not result.get("success", False):
            return False
        
        # Check for content
        full_text = result.get("full_text", "")
        pages = result.get("pages", [])
        
        # Result is valid if we have text content
        if len(full_text) > 10:
            return True
        
        # Or if we have page content
        total_chars = sum(p.get("char_count", 0) for p in pages)
        if total_chars > 10:
            return True
        
        return False
    
    def get_recommended_loader(
        self,
        file_format: str,
        file_size_bytes: int = 0
    ) -> str:
        """
        Get recommended loader for a file.
        
        Args:
            file_format: File format/extension
            file_size_bytes: File size in bytes
            
        Returns:
            Recommended loader name
        """
        try:
            strategy = get_format_strategy(file_format)
            file_size_mb = file_size_bytes / (1024 * 1024)
            chain = strategy.get_loader_chain(file_size_mb)
            
            # Return first available loader
            for loader in chain:
                if self.is_loader_available(loader):
                    return loader
            
            return chain[0] if chain else "text"
            
        except KeyError:
            return "text"


# Global instance
fallback_manager = FallbackManager()
