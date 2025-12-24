"""
索引操作日志工具

记录索引创建、更新、删除、查询等关键操作
日志格式：时间戳、操作类型、索引ID、用户ID、耗时、结果状态

2024-12-24 创建 (T010a)
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager
import time

from ..models.vector_index import IndexOperationLog
from ..utils.logger import get_logger

logger = get_logger("index_logging")


class OperationType:
    """操作类型常量"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"
    BATCH_SEARCH = "BATCH_SEARCH"
    PERSIST = "PERSIST"
    RECOVER = "RECOVER"
    ADD_VECTORS = "ADD_VECTORS"
    DELETE_VECTORS = "DELETE_VECTORS"
    UPDATE_VECTORS = "UPDATE_VECTORS"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"


class OperationStatus:
    """操作状态常量"""
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class IndexOperationLogger:
    """索引操作日志记录器"""
    
    def __init__(self, db_session: Session):
        """
        初始化日志记录器
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
    
    def log_operation(
        self,
        operation_type: str,
        index_id: Optional[int] = None,
        user_id: Optional[str] = None,
        status: str = OperationStatus.STARTED,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> IndexOperationLog:
        """
        记录操作日志
        
        Args:
            operation_type: 操作类型
            index_id: 索引ID
            user_id: 用户ID
            status: 操作状态
            details: 详细信息
            error_message: 错误信息
            duration_ms: 耗时（毫秒）
            
        Returns:
            IndexOperationLog 对象
        """
        try:
            log_entry = IndexOperationLog(
                index_id=index_id,
                operation_type=operation_type,
                user_id=user_id,
                status=status,
                details=details or {},
                error_message=error_message,
                duration_ms=duration_ms,
                started_at=datetime.now(),
                completed_at=datetime.now() if status != OperationStatus.STARTED else None
            )
            
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            
            logger.info(
                f"Operation logged: {operation_type} | "
                f"index_id={index_id} | user={user_id} | "
                f"status={status} | duration={duration_ms}ms"
            )
            
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to log operation: {str(e)}")
            self.db.rollback()
            raise
    
    def update_operation_status(
        self,
        log_id: int,
        status: str,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[IndexOperationLog]:
        """
        更新操作状态
        
        Args:
            log_id: 日志ID
            status: 新状态
            error_message: 错误信息
            duration_ms: 耗时
            details: 更新的详细信息
            
        Returns:
            更新后的 IndexOperationLog 对象
        """
        try:
            log_entry = self.db.query(IndexOperationLog).filter(
                IndexOperationLog.id == log_id
            ).first()
            
            if log_entry:
                log_entry.status = status
                log_entry.completed_at = datetime.now()
                
                if error_message:
                    log_entry.error_message = error_message
                
                if duration_ms is not None:
                    log_entry.duration_ms = duration_ms
                
                if details:
                    existing_details = log_entry.details or {}
                    existing_details.update(details)
                    log_entry.details = existing_details
                
                self.db.commit()
                self.db.refresh(log_entry)
                
                logger.info(
                    f"Operation status updated: id={log_id} | "
                    f"status={status} | duration={duration_ms}ms"
                )
                
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to update operation status: {str(e)}")
            self.db.rollback()
            raise
    
    @contextmanager
    def track_operation(
        self,
        operation_type: str,
        index_id: Optional[int] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        上下文管理器：自动跟踪操作的开始和结束
        
        Usage:
            with logger.track_operation("CREATE", index_id=1) as log:
                # 执行操作
                pass
            # 自动更新状态和耗时
        
        Args:
            operation_type: 操作类型
            index_id: 索引ID
            user_id: 用户ID
            details: 详细信息
            
        Yields:
            IndexOperationLog 对象
        """
        start_time = time.time()
        log_entry = None
        
        try:
            # 记录开始
            log_entry = self.log_operation(
                operation_type=operation_type,
                index_id=index_id,
                user_id=user_id,
                status=OperationStatus.STARTED,
                details=details
            )
            
            yield log_entry
            
            # 记录成功
            duration_ms = (time.time() - start_time) * 1000
            self.update_operation_status(
                log_id=log_entry.id,
                status=OperationStatus.SUCCESS,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            # 记录失败
            duration_ms = (time.time() - start_time) * 1000
            if log_entry:
                self.update_operation_status(
                    log_id=log_entry.id,
                    status=OperationStatus.FAILED,
                    error_message=str(e),
                    duration_ms=duration_ms
                )
            raise
    
    def get_operation_history(
        self,
        index_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        获取操作历史
        
        Args:
            index_id: 筛选特定索引
            operation_type: 筛选特定操作类型
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            IndexOperationLog 列表
        """
        query = self.db.query(IndexOperationLog)
        
        if index_id is not None:
            query = query.filter(IndexOperationLog.index_id == index_id)
        
        if operation_type is not None:
            query = query.filter(IndexOperationLog.operation_type == operation_type)
        
        return query.order_by(IndexOperationLog.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def get_operation_stats(
        self,
        index_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取操作统计信息
        
        Args:
            index_id: 筛选特定索引
            hours: 统计时间范围（小时）
            
        Returns:
            统计信息字典
        """
        from sqlalchemy import func as sql_func
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = self.db.query(IndexOperationLog).filter(
            IndexOperationLog.created_at >= cutoff_time
        )
        
        if index_id is not None:
            query = query.filter(IndexOperationLog.index_id == index_id)
        
        logs = query.all()
        
        # 统计各操作类型的数量
        operation_counts = {}
        status_counts = {
            OperationStatus.SUCCESS: 0,
            OperationStatus.FAILED: 0,
            OperationStatus.STARTED: 0
        }
        total_duration_ms = 0
        completed_count = 0
        
        for log in logs:
            # 操作类型统计
            if log.operation_type not in operation_counts:
                operation_counts[log.operation_type] = 0
            operation_counts[log.operation_type] += 1
            
            # 状态统计
            if log.status in status_counts:
                status_counts[log.status] += 1
            
            # 耗时统计
            if log.duration_ms is not None:
                total_duration_ms += log.duration_ms
                completed_count += 1
        
        avg_duration_ms = total_duration_ms / completed_count if completed_count > 0 else 0
        
        return {
            "time_range_hours": hours,
            "total_operations": len(logs),
            "operation_counts": operation_counts,
            "status_counts": status_counts,
            "avg_duration_ms": round(avg_duration_ms, 2),
            "success_rate": round(
                status_counts[OperationStatus.SUCCESS] / len(logs) * 100, 2
            ) if logs else 0
        }


def get_operation_logger(db_session: Session) -> IndexOperationLogger:
    """
    获取操作日志记录器实例
    
    Args:
        db_session: 数据库会话
        
    Returns:
        IndexOperationLogger 实例
    """
    return IndexOperationLogger(db_session)
