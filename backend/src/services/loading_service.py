"""Document loading service with Docling integration and fallback strategy.

This service provides document loading capabilities with:
- Docling as the primary parser for high-quality extraction
- Multi-level fallback strategy for reliability
- Intelligent loader selection based on file size and format
- Unified output format (StandardDocumentResult)
- Async loading support for large files via Docling Serve
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import time
import logging

from ..models.document import Document
from ..models.processing_result import ProcessingResult
from ..models.loading_result import StandardDocumentResult, ExtractionQuality
from ..models.loader_config import LoaderConfig, FormatStrategy
from ..models.loading_task import LoadingTask, LoadingTaskStatus
from ..loader_config.format_strategies import (
    FORMAT_STRATEGIES,
    LOADER_REGISTRY,
    get_format_strategy,
    get_loader_config,
    get_supported_formats,
    is_format_supported
)
from ..providers.loaders import (
    LOADER_INSTANCES,
    get_loader,
    pymupdf_loader,
    pypdf_loader,
    unstructured_loader,
    text_loader,
    docx_loader,
    doc_loader,
    docling_serve_loader
)
from ..services.fallback_manager import fallback_manager
from ..storage.json_storage import json_storage
from ..utils.error_handlers import NotFoundError, ProcessingError
from ..utils.result_converter import convert_legacy_result

logger = logging.getLogger(__name__)


class LoadingService:
    """Service for loading and parsing documents into processable text data."""
    
    def __init__(self):
        """Initialize loading service with available loaders."""
        # Register all loaders with fallback manager
        self._register_loaders()
        
        # Legacy format to loader mapping (for backward compatibility)
        self.format_loader_map = {
            fmt: strategy.primary_loader
            for fmt, strategy in FORMAT_STRATEGIES.items()
        }
        
        # Reference to loaders for direct access
        self.loaders = LOADER_INSTANCES
    
    def _register_loaders(self):
        """Register all available loaders with the fallback manager."""
        for name, loader in LOADER_INSTANCES.items():
            fallback_manager.register_loader(name, loader)
    
    def load_document(
        self,
        db: Session,
        document_id: str,
        loader_type: Optional[str] = None,
        enable_fallback: bool = True
    ) -> ProcessingResult:
        """
        Load and parse document using specified or auto-selected loader.
        
        Supports parsing multiple document formats with:
        - Docling as primary parser for PDF, DOCX, XLSX, PPTX
        - Automatic fallback to backup parsers on failure
        - Intelligent selection based on file size
        - Unified output format
        
        Args:
            db: Database session
            document_id: Document identifier
            loader_type: Type of loader to use. If None, auto-selects based on file format.
            enable_fallback: Whether to enable fallback to other loaders
            
        Returns:
            ProcessingResult instance with loading results
            
        Raises:
            NotFoundError: If document not found
            ProcessingError: If loading fails
        """
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise NotFoundError("Document", document_id)
        
        file_format = document.format.lower().lstrip('.')
        file_path = document.storage_path
        
        # Edge Case: Check if file exists (T059)
        if not Path(file_path).exists():
            raise ProcessingError(
                f"Source file not found: {document.filename}",
                {"file_path": file_path, "hint": "The file may have been deleted or moved"}
            )
        
        # Check if format is supported
        if not is_format_supported(file_format):
            raise ProcessingError(
                f"Unsupported file format: {document.format}",
                {"supported_formats": get_supported_formats()}
            )
        
        # Get file size
        try:
            file_size = Path(file_path).stat().st_size
        except Exception:
            file_size = 0
        
        # Edge Case: Large file warning (T060)
        MAX_FILE_SIZE_MB = 100
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            logger.warning(
                f"Large file detected: {document.filename} ({file_size / 1024 / 1024:.1f} MB). "
                f"Processing may take longer and use more memory."
            )
        
        logger.info(
            f"Starting document loading: {document_id} "
            f"(format: {file_format}, size: {file_size / 1024:.1f} KB, "
            f"loader: {loader_type or 'auto'})"
        )
        
        # Update document status
        document.status = "processing"
        db.commit()
        
        # Create processing result
        processing_result = ProcessingResult(
            document_id=document_id,
            processing_type="load",
            provider=loader_type or "auto",
            result_path="",
            status="running"
        )
        db.add(processing_result)
        db.commit()
        db.refresh(processing_result)
        
        start_time = time.time()
        
        try:
            # Load document with fallback strategy
            result_data = fallback_manager.load_with_fallback(
                file_path=file_path,
                file_format=file_format,
                file_size_bytes=file_size,
                preferred_loader=loader_type,
                enable_fallback=enable_fallback
            )
            
            processing_time = time.time() - start_time
            
            if not result_data.get("success"):
                error_msg = result_data.get("error", "Unknown error")
                error_details = result_data.get("error_details", {})
                logger.error(f"Loading failed for {document_id}: {error_msg}")
                raise ProcessingError(f"Loading failed: {error_msg}", error_details)
            
            # Extract statistics
            total_pages = result_data.get("total_pages", 0)
            total_chars = result_data.get("total_chars", 0)
            actual_loader = result_data.get("loader", loader_type or "unknown")
            fallback_used = result_data.get("fallback_used", False)
            
            logger.info(
                f"Successfully loaded {document_id}: "
                f"{total_pages} pages, {total_chars} characters, "
                f"loader: {actual_loader}, fallback: {fallback_used}"
            )
            
            # Add processing time to result
            result_data["processing_time"] = processing_time
            
            # Save result as JSON
            result_path = json_storage.save_result(
                document.filename,
                "load",
                result_data
            )
            
            # Update processing result
            processing_result.result_path = result_path
            processing_result.status = "completed"
            processing_result.provider = actual_loader
            processing_result.extra_metadata = {
                "total_pages": total_pages,
                "total_chars": total_chars,
                "loader_type": actual_loader,
                "file_format": document.format,
                "processing_time": processing_time,
                "fallback_used": fallback_used,
                "fallback_reason": result_data.get("fallback_reason"),
                "original_parser": result_data.get("original_parser"),
                "table_count": len(result_data.get("tables", [])),
                "image_count": len(result_data.get("images", [])),
            }
            
            # Update document status
            document.status = "ready"
            
            db.commit()
            db.refresh(processing_result)
            
            logger.info(f"Document loading completed: {document_id}")
            return processing_result
            
        except ProcessingError:
            processing_result.status = "failed"
            processing_result.error_message = str(ProcessingError)
            document.status = "error"
            db.commit()
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error during loading: {str(e)}"
            logger.error(f"Loading failed for {document_id}: {error_msg}", exc_info=True)
            
            processing_result.status = "failed"
            processing_result.error_message = error_msg
            document.status = "error"
            db.commit()
            
            raise ProcessingError(error_msg)
    
    def get_loading_result(
        self,
        db: Session,
        document_id: str,
        loader_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get loading result for a document.
        
        Args:
            db: Database session
            document_id: Document identifier
            loader_type: Optional specific loader type to retrieve
            
        Returns:
            Loading result data or None if not found
        """
        query = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == document_id,
            ProcessingResult.processing_type == "load"
        )
        
        if loader_type:
            query = query.filter(ProcessingResult.provider == loader_type)
        
        result = query.order_by(ProcessingResult.created_time.desc()).first()
        
        if not result or not result.result_path:
            return None
        
        try:
            return json_storage.load_result(result.result_path)
        except Exception as e:
            logger.error(f"Failed to load result from {result.result_path}: {str(e)}")
            return None
    
    def get_available_loaders(self) -> List[Dict[str, Any]]:
        """
        Get list of available loaders with their configurations.
        
        Returns:
            List of loader configuration dictionaries
        """
        loaders = []
        for name, config in LOADER_REGISTRY.items():
            loader_info = config.to_dict()
            # Check actual availability
            loader_instance = get_loader(name)
            if loader_instance and hasattr(loader_instance, 'is_available'):
                loader_info['is_available'] = loader_instance.is_available()
                if not loader_info['is_available']:
                    loader_info['unavailable_reason'] = loader_instance.get_unavailable_reason()
            loaders.append(loader_info)
        return loaders
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.
        
        Returns:
            List of supported file extensions
        """
        return get_supported_formats()
    
    def get_format_strategies(self) -> List[Dict[str, Any]]:
        """
        Get list of format strategies.
        
        Returns:
            List of format strategy dictionaries
        """
        return [strategy.to_dict() for strategy in FORMAT_STRATEGIES.values()]
    
    def get_loader_for_format(self, file_format: str) -> Optional[str]:
        """
        Get recommended loader for a specific file format.
        
        Args:
            file_format: File format/extension (e.g., 'pdf', 'docx')
            
        Returns:
            Loader name or None if format not supported
        """
        try:
            strategy = get_format_strategy(file_format)
            return strategy.primary_loader
        except KeyError:
            return None
    
    def get_recommended_loader(
        self,
        file_format: str,
        file_size_bytes: int = 0
    ) -> str:
        """
        Get recommended loader based on format and file size.
        
        Args:
            file_format: File format/extension
            file_size_bytes: File size in bytes
            
        Returns:
            Recommended loader name
        """
        return fallback_manager.get_recommended_loader(file_format, file_size_bytes)
    
    # ==================== 异步加载方法 ====================
    
    def should_use_async(
        self,
        file_format: str,
        file_size_bytes: int,
        loader_name: Optional[str] = None
    ) -> bool:
        """
        判断是否应该使用异步加载
        
        Args:
            file_format: 文件格式
            file_size_bytes: 文件大小（字节）
            loader_name: 指定的加载器名称
        
        Returns:
            是否应该使用异步加载
        """
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Docling Serve 始终推荐使用异步（处理较慢）
        if loader_name in ("docling_serve", "docling"):
            return True
        
        # 自动选择模式下，复杂格式的大文件使用异步
        if loader_name is None:
            complex_formats = {"pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls"}
            if file_format.lower() in complex_formats and file_size_mb > 2:
                return True
        
        return False
    
    def submit_async_load(
        self,
        db: Session,
        document_id: str,
        loader_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提交异步加载任务
        
        Args:
            db: 数据库会话
            document_id: 文档 ID
            loader_type: 加载器类型（目前仅支持 docling_serve）
        
        Returns:
            Dict: {
                "task_id": str,
                "status": str,
                "document_id": str
            }
        """
        # 获取文档
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise NotFoundError("Document", document_id)
        
        file_path = document.storage_path
        
        # 检查文件是否存在
        if not Path(file_path).exists():
            raise ProcessingError(
                f"Source file not found: {document.filename}",
                {"file_path": file_path}
            )
        
        # 目前异步加载仅支持 Docling Serve
        actual_loader = loader_type or "docling_serve"
        if actual_loader not in ("docling_serve", "docling"):
            raise ProcessingError(
                f"Async loading only supports docling_serve, got: {actual_loader}"
            )
        
        # 检查 Docling Serve 是否可用
        if not docling_serve_loader or not docling_serve_loader.is_available():
            reason = docling_serve_loader.get_unavailable_reason() if docling_serve_loader else "Loader not initialized"
            raise ProcessingError(f"Docling Serve is not available: {reason}")
        
        # 提交异步任务到 Docling Serve
        submit_result = docling_serve_loader.submit_async_convert(file_path)
        
        if not submit_result.get("success"):
            raise ProcessingError(
                f"Failed to submit async task: {submit_result.get('error')}"
            )
        
        external_task_id = submit_result.get("task_id")
        
        # 创建本地任务记录
        loading_task = LoadingTask(
            document_id=document_id,
            external_task_id=external_task_id,
            loader_type=actual_loader,
            status=LoadingTaskStatus.PENDING,
            started_at=datetime.utcnow()  # 任务提交后立即开始计时
        )
        db.add(loading_task)
        
        # 更新文档状态
        document.status = "processing"
        
        db.commit()
        db.refresh(loading_task)
        
        logger.info(
            f"Async loading task submitted: task_id={loading_task.id}, "
            f"external_task_id={external_task_id}, document_id={document_id}"
        )
        
        return {
            "task_id": loading_task.id,
            "external_task_id": external_task_id,
            "status": loading_task.status,
            "document_id": document_id,
            "loader_type": actual_loader
        }
    
    def get_async_task_status(
        self,
        db: Session,
        task_id: str
    ) -> Dict[str, Any]:
        """
        获取异步任务状态
        
        会同时查询 Docling Serve 的最新状态并更新本地记录。
        
        Args:
            db: 数据库会话
            task_id: 本地任务 ID
        
        Returns:
            Dict: {
                "task_id": str,
                "status": str,
                "progress": int,
                "document_id": str
            }
        """
        # 查找本地任务
        task = db.query(LoadingTask).filter(LoadingTask.id == task_id).first()
        if not task:
            raise NotFoundError("LoadingTask", task_id)
        
        # 如果任务已完成或失败，直接返回本地状态
        if task.status in (LoadingTaskStatus.SUCCESS, LoadingTaskStatus.FAILURE, LoadingTaskStatus.CANCELLED):
            return {
                "task_id": task.id,
                "status": task.status,
                "progress": task.progress,
                "document_id": task.document_id,
                "error_message": task.error_message,
                "processing_time": task.processing_time
            }
        
        # 查询 Docling Serve 的最新状态
        if task.external_task_id and docling_serve_loader:
            poll_result = docling_serve_loader.poll_task_status(task.external_task_id)
            
            if poll_result.get("success"):
                new_status = poll_result.get("status")
                new_progress = poll_result.get("progress", 0)
                
                # 更新本地状态
                if new_status != task.status:
                    task.status = new_status
                    if new_status == LoadingTaskStatus.STARTED and not task.started_at:
                        task.started_at = datetime.utcnow()
                    elif new_status in (LoadingTaskStatus.SUCCESS, LoadingTaskStatus.FAILURE):
                        task.completed_at = datetime.utcnow()
                        # 计算处理时间：优先使用 started_at，否则使用 created_at
                        start_time = task.started_at or task.created_at
                        if start_time:
                            task.processing_time = (task.completed_at - start_time).total_seconds()
                
                task.progress = new_progress
                db.commit()
                
                # 如果任务成功，自动获取并保存结果
                if new_status == LoadingTaskStatus.SUCCESS:
                    self._save_async_task_result(db, task)
            else:
                # 轮询失败，记录错误但不改变状态
                logger.warning(f"Failed to poll task status: {poll_result.get('error')}")
        
        return {
            "task_id": task.id,
            "status": task.status,
            "progress": task.progress,
            "document_id": task.document_id,
            "error_message": task.error_message,
            "processing_time": task.processing_time
        }
    
    def _save_async_task_result(self, db: Session, task: LoadingTask) -> None:
        """
        保存异步任务结果
        
        从 Docling Serve 获取结果并保存到本地。
        """
        if not task.external_task_id or not docling_serve_loader:
            return
        
        try:
            # 先获取文档信息（用于传递文件名和格式）
            document = db.query(Document).filter(Document.id == task.document_id).first()
            if not document:
                return
            
            # 获取结果（传入文件名和格式，以便正确提取格式特定的元数据）
            result_data = docling_serve_loader.get_task_result(
                task.external_task_id,
                filename=document.filename,
                file_format=document.format
            )
            
            if not result_data.get("success"):
                task.status = LoadingTaskStatus.FAILURE
                task.error_message = result_data.get("error", "Failed to get result")
                db.commit()
                return
            
            # 添加处理时间
            result_data["processing_time"] = task.processing_time
            result_data["async_mode"] = True
            
            # 保存结果到 JSON
            result_path = json_storage.save_result(
                document.filename,
                "load",
                result_data
            )
            
            task.result_path = result_path
            
            # 创建 ProcessingResult 记录
            processing_result = ProcessingResult(
                document_id=task.document_id,
                processing_type="load",
                provider=task.loader_type,
                result_path=result_path,
                status="completed",
                extra_metadata={
                    "total_pages": result_data.get("total_pages", 0),
                    "total_chars": result_data.get("total_chars", 0),
                    "loader_type": task.loader_type,
                    "file_format": document.format,
                    "processing_time": task.processing_time,
                    "async_mode": True,
                    "table_count": len(result_data.get("tables", [])),
                    "image_count": len(result_data.get("images", []))
                }
            )
            db.add(processing_result)
            
            # 更新文档状态
            document.status = "ready"
            
            db.commit()
            
            logger.info(f"Async task result saved: task_id={task.id}, result_path={result_path}")
            
        except Exception as e:
            logger.error(f"Failed to save async task result: {e}", exc_info=True)
            task.status = LoadingTaskStatus.FAILURE
            task.error_message = str(e)
            db.commit()
    
    def get_async_task_result(
        self,
        db: Session,
        task_id: str
    ) -> Dict[str, Any]:
        """
        获取异步任务结果
        
        Args:
            db: 数据库会话
            task_id: 本地任务 ID
        
        Returns:
            完整的加载结果，格式与同步加载一致
        """
        # 查找本地任务
        task = db.query(LoadingTask).filter(LoadingTask.id == task_id).first()
        if not task:
            raise NotFoundError("LoadingTask", task_id)
        
        # 检查任务状态
        if task.status != LoadingTaskStatus.SUCCESS:
            if task.status == LoadingTaskStatus.FAILURE:
                raise ProcessingError(
                    f"Task failed: {task.error_message}",
                    {"task_id": task_id, "status": task.status}
                )
            else:
                raise ProcessingError(
                    f"Task not completed yet, current status: {task.status}",
                    {"task_id": task_id, "status": task.status}
                )
        
        # 查找对应的 ProcessingResult 记录
        processing_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == task.document_id,
            ProcessingResult.processing_type == "load",
            ProcessingResult.result_path == task.result_path
        ).first()
        
        if not processing_result:
            # 如果没有找到 ProcessingResult，尝试从 JSON 加载并构建响应
            if not task.result_path:
                raise ProcessingError("Task result path not found")
            
            try:
                result_data = json_storage.load_result(task.result_path)
                # 构建与 ProcessingResult 格式一致的响应
                return {
                    "id": task.id,
                    "document_id": task.document_id,
                    "processing_type": "load",
                    "provider": task.loader_type,
                    "status": "completed",
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "result_path": task.result_path,
                    "extra_metadata": {
                        "total_pages": result_data.get("total_pages", 0),
                        "total_chars": result_data.get("total_chars", 0),
                        "loader_type": task.loader_type,
                        "processing_time": task.processing_time,
                        "async_mode": True
                    },
                    "result_data": result_data,
                    "task_id": task.id
                }
            except Exception as e:
                raise ProcessingError(f"Failed to load result: {e}")
        
        # 加载 JSON 结果数据
        try:
            result_data = json_storage.load_result(processing_result.result_path)
        except Exception as e:
            logger.warning(f"Failed to load result JSON: {e}")
            result_data = None
        
        # 返回与同步加载一致的格式
        return {
            "id": processing_result.id,
            "document_id": processing_result.document_id,
            "processing_type": processing_result.processing_type,
            "provider": processing_result.provider,
            "status": processing_result.status,
            "created_at": processing_result.created_at.isoformat() if processing_result.created_at else None,
            "result_path": processing_result.result_path,
            "extra_metadata": processing_result.extra_metadata,
            "result_data": result_data,
            "task_id": task.id
        }
    
    def cancel_async_task(
        self,
        db: Session,
        task_id: str
    ) -> Dict[str, Any]:
        """
        取消异步任务
        
        Args:
            db: 数据库会话
            task_id: 本地任务 ID
        
        Returns:
            取消结果
        """
        task = db.query(LoadingTask).filter(LoadingTask.id == task_id).first()
        if not task:
            raise NotFoundError("LoadingTask", task_id)
        
        # 只能取消未完成的任务
        if task.status in (LoadingTaskStatus.SUCCESS, LoadingTaskStatus.FAILURE):
            return {
                "task_id": task.id,
                "cancelled": False,
                "reason": f"Task already {task.status}"
            }
        
        # 更新状态
        task.status = LoadingTaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        
        # 恢复文档状态
        document = db.query(Document).filter(Document.id == task.document_id).first()
        if document and document.status == "processing":
            document.status = "uploaded"
        
        db.commit()
        
        logger.info(f"Async task cancelled: task_id={task_id}")
        
        return {
            "task_id": task.id,
            "cancelled": True,
            "status": task.status
        }
    
    def list_async_tasks(
        self,
        db: Session,
        document_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        列出异步任务
        
        Args:
            db: 数据库会话
            document_id: 按文档 ID 过滤
            status: 按状态过滤
            limit: 最大返回数量
        
        Returns:
            任务列表
        """
        query = db.query(LoadingTask)
        
        if document_id:
            query = query.filter(LoadingTask.document_id == document_id)
        
        if status:
            query = query.filter(LoadingTask.status == status)
        
        tasks = query.order_by(LoadingTask.created_at.desc()).limit(limit).all()
        
        return [task.to_dict() for task in tasks]


# Global instance
loading_service = LoadingService()
