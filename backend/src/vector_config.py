"""
向量索引配置类

提供 Milvus 的配置管理
"""
from dataclasses import dataclass
from typing import Optional
import os


# 默认向量数据库提供者（仅支持 milvus）
DEFAULT_VECTOR_PROVIDER = "milvus"

# 默认 Collection 配置
DEFAULT_COLLECTION_NAME = os.getenv("DEFAULT_COLLECTION_NAME", "default_collection")
DEFAULT_COLLECTION_DESCRIPTION = "默认知识库 Collection，用于存储所有文档的向量数据"

# 物理 Collection 命名模板（Dify 方案：按维度拆分物理 Collection）
# 格式: {逻辑知识库名}_{dim}{维度数}，如 default_collection_dim1024
PHYSICAL_COLLECTION_TEMPLATE = os.getenv("PHYSICAL_COLLECTION_TEMPLATE", "{collection_name}_dim{dimension}")


def get_physical_collection_name(logical_name: str, dimension: int) -> str:
    """
    根据逻辑知识库名和向量维度生成物理 Collection 名称
    
    参考 Dify 方案：一个逻辑知识库按「知识库 + 维度」拆分为多个物理 Collection，
    从根源解决 Milvus 不支持同一 Collection 存储不同维度向量的问题。
    
    Args:
        logical_name: 逻辑知识库名称（如 default_collection）
        dimension: 向量维度（如 1024, 2048, 4096）
        
    Returns:
        物理 Collection 名称（如 default_collection_dim1024）
    """
    return PHYSICAL_COLLECTION_TEMPLATE.format(
        collection_name=logical_name,
        dimension=dimension
    )


def parse_physical_collection_name(physical_name: str) -> tuple:
    """
    从物理 Collection 名称解析出逻辑名和维度
    
    Args:
        physical_name: 物理 Collection 名称（如 default_collection_dim1024）
        
    Returns:
        (logical_name, dimension) 元组，解析失败返回 (physical_name, None)
    """
    import re
    match = re.match(r'^(.+)_dim(\d+)$', physical_name)
    if match:
        return match.group(1), int(match.group(2))
    return physical_name, None


@dataclass
class MilvusConfig:
    """Milvus 配置类"""
    
    host: str = "localhost"
    port: int = 19530
    user: str = ""
    password: str = ""
    timeout: int = 30
    default_collection_name: str = DEFAULT_COLLECTION_NAME
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
        default_collection_name: Optional[str] = None
    ):
        """从环境变量或参数初始化配置"""
        self.host = host or os.getenv("MILVUS_HOST", "localhost")
        self.port = port or int(os.getenv("MILVUS_PORT", "19530"))
        self.user = user or os.getenv("MILVUS_USER", "")
        self.password = password or os.getenv("MILVUS_PASSWORD", "")
        self.timeout = timeout or int(os.getenv("MILVUS_TIMEOUT", "30"))
        self.default_collection_name = default_collection_name or os.getenv(
            "DEFAULT_COLLECTION_NAME", DEFAULT_COLLECTION_NAME
        )
