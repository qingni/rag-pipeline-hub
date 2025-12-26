"""
搜索查询数据模型

定义搜索历史和搜索配置的数据库模型
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import uuid

from ..storage.database import Base


def get_local_now():
    """获取当前本地时间"""
    return datetime.now()


class SearchHistory(Base):
    """搜索历史记录模型"""
    
    __tablename__ = "search_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_text = Column(Text, nullable=False)
    index_ids = Column(JSON, nullable=False)  # JSON array of index IDs
    config = Column(JSON, nullable=False)  # JSON object with top_k, threshold, metric_type
    result_count = Column(Integer, nullable=False, default=0)
    execution_time_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=get_local_now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "query_text": self.query_text,
            "index_ids": self.index_ids,
            "config": self.config,
            "result_count": self.result_count,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SearchConfig(Base):
    """搜索配置预设模型"""
    
    __tablename__ = "search_config"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    default_index_id = Column(String(36), nullable=True)
    default_top_k = Column(Integer, nullable=False, default=10)
    default_threshold = Column(Float, nullable=False, default=0.5)
    default_metric = Column(String(50), nullable=False, default="cosine")
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=get_local_now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "default_index_id": self.default_index_id,
            "default_top_k": self.default_top_k,
            "default_threshold": self.default_threshold,
            "default_metric": self.default_metric,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
