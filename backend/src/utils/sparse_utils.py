"""
稀疏向量工具函数

提供稀疏向量的验证、格式转换和空值检测功能。
用于混合检索中的稀疏向量处理。
"""
from typing import Dict, Optional, Union, Any
import logging

logger = logging.getLogger("sparse_utils")


def is_sparse_vector_valid(sparse_vector: Any) -> bool:
    """
    检测稀疏向量是否有效（非空且格式正确）
    
    Args:
        sparse_vector: 稀疏向量数据（期望 dict 格式 {index: weight}）
        
    Returns:
        True 如果稀疏向量有效
    """
    if sparse_vector is None:
        return False
    
    if not isinstance(sparse_vector, dict):
        return False
    
    if len(sparse_vector) == 0:
        return False
    
    # 检查是否所有权重为零
    if all(w == 0 for w in sparse_vector.values()):
        return False
    
    return True


def validate_sparse_vector(sparse_vector: Any) -> tuple:
    """
    验证稀疏向量格式并返回验证结果
    
    Args:
        sparse_vector: 待验证的稀疏向量
        
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if sparse_vector is None:
        return False, "稀疏向量为 None"
    
    if not isinstance(sparse_vector, dict):
        return False, f"稀疏向量格式错误：期望 dict，实际 {type(sparse_vector).__name__}"
    
    if len(sparse_vector) == 0:
        return False, "稀疏向量为空字典"
    
    # 检查 key 和 value 格式
    for key, value in sparse_vector.items():
        # key 应该是可转换为整数的
        try:
            int(key)
        except (ValueError, TypeError):
            return False, f"稀疏向量索引无效：{key}（应为整数或整数字符串）"
        
        # value 应该是数值
        if not isinstance(value, (int, float)):
            return False, f"稀疏向量权重无效：{value}（应为数值）"
        
        # 检查 NaN/Inf
        if isinstance(value, float) and (value != value or abs(value) == float('inf')):
            return False, f"稀疏向量包含无效值：NaN 或 Inf"
    
    # 检查是否所有权重为零
    if all(v == 0 for v in sparse_vector.values()):
        return False, "稀疏向量所有权重为零"
    
    return True, None


def convert_sparse_to_milvus_format(sparse_vector: Dict[str, float]) -> Dict[int, float]:
    """
    将稀疏向量转换为 Milvus 期望的格式
    
    Milvus SPARSE_FLOAT_VECTOR 要求 key 为 int 类型
    
    Args:
        sparse_vector: 稀疏向量 {str_index: weight}
        
    Returns:
        Milvus 格式的稀疏向量 {int_index: weight}
    """
    if not sparse_vector:
        return {}
    
    return {int(k): float(v) for k, v in sparse_vector.items() if float(v) != 0}


def convert_milvus_to_dict_format(milvus_sparse: Any) -> Dict[str, float]:
    """
    将 Milvus 返回的稀疏向量转换为标准 dict 格式
    
    Args:
        milvus_sparse: Milvus 返回的稀疏向量数据
        
    Returns:
        标准 dict 格式 {str_index: weight}
    """
    if milvus_sparse is None:
        return {}
    
    if isinstance(milvus_sparse, dict):
        return {str(k): float(v) for k, v in milvus_sparse.items()}
    
    # 如果是其他格式，尝试转换
    try:
        return {str(k): float(v) for k, v in dict(milvus_sparse).items()}
    except Exception as e:
        logger.warning(f"无法转换稀疏向量格式: {e}")
        return {}


def get_sparse_vector_stats(sparse_vector: Dict) -> Dict[str, Any]:
    """
    获取稀疏向量的统计信息
    
    Args:
        sparse_vector: 稀疏向量
        
    Returns:
        统计信息字典
    """
    if not sparse_vector or not isinstance(sparse_vector, dict):
        return {
            "nnz": 0,
            "min_weight": 0,
            "max_weight": 0,
            "avg_weight": 0,
            "is_valid": False
        }
    
    weights = [float(v) for v in sparse_vector.values()]
    non_zero_weights = [w for w in weights if w != 0]
    
    return {
        "nnz": len(non_zero_weights),
        "total_elements": len(weights),
        "min_weight": min(weights) if weights else 0,
        "max_weight": max(weights) if weights else 0,
        "avg_weight": sum(weights) / len(weights) if weights else 0,
        "is_valid": is_sparse_vector_valid(sparse_vector)
    }
