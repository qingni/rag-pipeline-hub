"""
向量索引配置类

提供 Milvus 的配置管理
"""
from dataclasses import dataclass
from typing import Optional
import os


# 默认向量数据库提供者（仅支持 milvus）
DEFAULT_VECTOR_PROVIDER = "milvus"


@dataclass
class MilvusConfig:
    """Milvus 配置类"""
    
    host: str = "localhost"
    port: int = 19530
    user: str = ""
    password: str = ""
    timeout: int = 30
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """从环境变量或参数初始化配置"""
        self.host = host or os.getenv("MILVUS_HOST", "localhost")
        self.port = port or int(os.getenv("MILVUS_PORT", "19530"))
        self.user = user or os.getenv("MILVUS_USER", "")
        self.password = password or os.getenv("MILVUS_PASSWORD", "")
        self.timeout = timeout or int(os.getenv("MILVUS_TIMEOUT", "30"))
