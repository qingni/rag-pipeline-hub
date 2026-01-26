"""
Task Queue Service - 支持多任务并行处理的异步任务队列服务

功能：
1. 多任务并行处理（线程池 + 进程池）
2. 任务状态管理和查询
3. 加载器分类调度
4. 任务优先级支持
5. 批量任务状态查询（减少轮询开销）
"""
import logging
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import OrderedDict

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"          # 等待执行
    QUEUED = "queued"            # 已加入队列
    RUNNING = "running"          # 正在执行
    SUCCESS = "success"          # 执行成功
    FAILURE = "failure"          # 执行失败
    CANCELLED = "cancelled"      # 已取消
    TIMEOUT = "timeout"          # 超时


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class LoaderCategory(str, Enum):
    """加载器分类 - 用于任务调度"""
    LOCAL_FAST = "local_fast"       # 快速本地加载器（text, csv, json）
    LOCAL_MEDIUM = "local_medium"   # 中等本地加载器（pymupdf, docx）
    LOCAL_HEAVY = "local_heavy"     # 重型本地加载器（unstructured）
    REMOTE = "remote"               # 远程服务（docling_serve）


# 加载器分类映射
LOADER_CATEGORY_MAP = {
    # 快速加载器 - 使用线程池
    "text": LoaderCategory.LOCAL_FAST,
    "csv": LoaderCategory.LOCAL_FAST,
    "json": LoaderCategory.LOCAL_FAST,
    "xml": LoaderCategory.LOCAL_FAST,
    "html": LoaderCategory.LOCAL_FAST,
    
    # 中等加载器 - 使用线程池
    "pymupdf": LoaderCategory.LOCAL_MEDIUM,
    "pypdf": LoaderCategory.LOCAL_MEDIUM,
    "docx": LoaderCategory.LOCAL_MEDIUM,
    "xlsx": LoaderCategory.LOCAL_MEDIUM,
    "pptx": LoaderCategory.LOCAL_MEDIUM,
    
    # 重型加载器 - 使用进程池
    "unstructured": LoaderCategory.LOCAL_HEAVY,
    
    # 远程服务 - 使用异步 HTTP
    "docling_serve": LoaderCategory.REMOTE,
    "docling": LoaderCategory.REMOTE,
}


@dataclass
class QueueTask:
    """队列任务"""
    task_id: str
    document_id: str
    loader_name: str
    file_path: str
    file_format: str
    file_size_bytes: int
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    future: Optional[Future] = None
    
    @property
    def category(self) -> LoaderCategory:
        """获取加载器分类"""
        return LOADER_CATEGORY_MAP.get(self.loader_name, LoaderCategory.LOCAL_MEDIUM)
    
    @property
    def processing_time(self) -> Optional[float]:
        """计算处理时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "document_id": self.document_id,
            "loader_name": self.loader_name,
            "file_format": self.file_format,
            "file_size_bytes": self.file_size_bytes,
            "priority": self.priority.value,
            "status": self.status.value,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
            "category": self.category.value,
        }


class TaskQueueService:
    """
    任务队列服务
    
    特性：
    1. 分类执行器：线程池（快速/中等）、进程池（重型）、远程服务
    2. 任务优先级：支持 4 级优先级
    3. 并发控制：可配置最大并发数
    4. 任务跟踪：完整的生命周期管理
    """
    
    def __init__(
        self,
        thread_pool_size: int = 4,
        process_pool_size: int = 2,
        max_remote_concurrent: int = 4,
        task_timeout: float = 1800.0,  # 30 分钟
        cleanup_interval: int = 300,  # 5 分钟清理一次过期任务
    ):
        """
        初始化任务队列服务
        
        Args:
            thread_pool_size: 线程池大小（用于快速/中等加载器）
            process_pool_size: 进程池大小（用于重型加载器）
            max_remote_concurrent: 最大远程并发数
            task_timeout: 任务超时时间（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self._thread_pool = ThreadPoolExecutor(
            max_workers=thread_pool_size,
            thread_name_prefix="loader_thread"
        )
        
        # 进程池用于 CPU 密集型任务（如 unstructured）
        # 注意：进程池在某些环境下可能有问题，这里先用线程池替代
        self._heavy_pool = ThreadPoolExecutor(
            max_workers=process_pool_size,
            thread_name_prefix="loader_heavy"
        )
        
        self._max_remote_concurrent = max_remote_concurrent
        self._remote_semaphore = threading.Semaphore(max_remote_concurrent)
        
        self._task_timeout = task_timeout
        self._cleanup_interval = cleanup_interval
        
        # 任务存储（使用 OrderedDict 保持插入顺序）
        self._tasks: Dict[str, QueueTask] = OrderedDict()
        self._lock = threading.RLock()
        
        # 任务完成回调
        self._completion_callbacks: Dict[str, List[Callable]] = {}
        
        # 启动清理线程
        self._shutdown = False
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="task_cleanup"
        )
        self._cleanup_thread.start()
        
        logger.info(
            f"TaskQueueService initialized: "
            f"thread_pool={thread_pool_size}, "
            f"heavy_pool={process_pool_size}, "
            f"remote_concurrent={max_remote_concurrent}"
        )
    
    def submit_task(
        self,
        document_id: str,
        loader_name: str,
        file_path: str,
        file_format: str,
        file_size_bytes: int,
        load_func: Callable,
        priority: TaskPriority = TaskPriority.NORMAL,
        on_complete: Optional[Callable] = None,
    ) -> str:
        """
        提交加载任务
        
        Args:
            document_id: 文档 ID
            loader_name: 加载器名称
            file_path: 文件路径
            file_format: 文件格式
            file_size_bytes: 文件大小
            load_func: 加载函数（接收 file_path 参数）
            priority: 任务优先级
            on_complete: 完成回调
        
        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        
        task = QueueTask(
            task_id=task_id,
            document_id=document_id,
            loader_name=loader_name,
            file_path=file_path,
            file_format=file_format,
            file_size_bytes=file_size_bytes,
            priority=priority,
            status=TaskStatus.QUEUED,
        )
        
        with self._lock:
            self._tasks[task_id] = task
            if on_complete:
                self._completion_callbacks[task_id] = [on_complete]
        
        # 根据加载器分类选择执行器
        category = task.category
        
        if category == LoaderCategory.REMOTE:
            # 远程服务使用信号量控制并发
            future = self._thread_pool.submit(
                self._execute_remote_task,
                task,
                load_func
            )
        elif category == LoaderCategory.LOCAL_HEAVY:
            # 重型任务使用专用线程池
            future = self._heavy_pool.submit(
                self._execute_task,
                task,
                load_func
            )
        else:
            # 快速/中等任务使用普通线程池
            future = self._thread_pool.submit(
                self._execute_task,
                task,
                load_func
            )
        
        task.future = future
        
        logger.info(
            f"Task submitted: {task_id}, "
            f"document={document_id}, "
            f"loader={loader_name}, "
            f"category={category.value}"
        )
        
        return task_id
    
    def _execute_task(self, task: QueueTask, load_func: Callable) -> None:
        """执行本地任务"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            logger.info(f"Task started: {task.task_id}")
            
            # 执行加载
            result = load_func(task.file_path)
            
            task.completed_at = datetime.now()
            
            if result.get("success"):
                task.status = TaskStatus.SUCCESS
                task.result = result
                task.progress = 100
                logger.info(
                    f"Task completed: {task.task_id}, "
                    f"time={task.processing_time:.1f}s"
                )
            else:
                task.status = TaskStatus.FAILURE
                task.error_message = result.get("error", "Unknown error")
                logger.warning(
                    f"Task failed: {task.task_id}, "
                    f"error={task.error_message}"
                )
            
            # 调用完成回调
            self._call_completion_callbacks(task)
            
        except Exception as e:
            task.status = TaskStatus.FAILURE
            task.error_message = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task exception: {task.task_id}, error={e}", exc_info=True)
            self._call_completion_callbacks(task)
    
    def _execute_remote_task(self, task: QueueTask, load_func: Callable) -> None:
        """执行远程任务（带信号量控制并发）"""
        with self._remote_semaphore:
            self._execute_task(task, load_func)
    
    def _call_completion_callbacks(self, task: QueueTask) -> None:
        """调用任务完成回调"""
        callbacks = self._completion_callbacks.pop(task.task_id, [])
        for callback in callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Callback error for task {task.task_id}: {e}")
    
    def get_task(self, task_id: str) -> Optional[QueueTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_batch_status(self, task_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取任务状态
        
        Args:
            task_ids: 任务 ID 列表
        
        Returns:
            任务 ID -> 状态字典 的映射
        """
        result = {}
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task:
                result[task_id] = task.to_dict()
        return result
    
    def get_document_tasks(self, document_id: str) -> List[Dict[str, Any]]:
        """获取文档的所有任务"""
        return [
            task.to_dict()
            for task in self._tasks.values()
            if task.document_id == document_id
        ]
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取所有活跃任务（pending, queued, running）"""
        active_statuses = {TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING}
        return [
            task.to_dict()
            for task in self._tasks.values()
            if task.status in active_statuses
        ]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        status_counts = {}
        category_counts = {}
        
        for task in self._tasks.values():
            # 按状态统计
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # 按分类统计
            category = task.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "total_tasks": len(self._tasks),
            "status_counts": status_counts,
            "category_counts": category_counts,
            "thread_pool_size": self._thread_pool._max_workers,
            "heavy_pool_size": self._heavy_pool._max_workers,
            "max_remote_concurrent": self._max_remote_concurrent,
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
        
        Returns:
            是否成功取消
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # 只能取消未完成的任务
        if task.status in {TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED}:
            return False
        
        # 尝试取消 Future
        if task.future and not task.future.done():
            cancelled = task.future.cancel()
            if cancelled:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                logger.info(f"Task cancelled: {task_id}")
                return True
        
        # 如果无法取消 Future，标记为取消（任务可能正在执行）
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        logger.info(f"Task marked as cancelled: {task_id}")
        return True
    
    def _cleanup_loop(self) -> None:
        """清理过期任务的后台线程"""
        while not self._shutdown:
            try:
                time.sleep(self._cleanup_interval)
                self._cleanup_completed_tasks()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def _cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """
        清理已完成的过期任务
        
        Args:
            max_age_hours: 最大保留时间（小时）
        
        Returns:
            清理的任务数量
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        completed_statuses = {TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED}
        
        to_remove = []
        
        with self._lock:
            for task_id, task in self._tasks.items():
                if task.status in completed_statuses:
                    if task.completed_at and task.completed_at < cutoff:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} expired tasks")
        
        return len(to_remove)
    
    def shutdown(self, wait: bool = True) -> None:
        """关闭服务"""
        self._shutdown = True
        self._thread_pool.shutdown(wait=wait)
        self._heavy_pool.shutdown(wait=wait)
        logger.info("TaskQueueService shutdown")


# 全局实例
task_queue_service = TaskQueueService()
