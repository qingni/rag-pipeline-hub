"""
智能分块参数配置模块

基于业界 RAG 最佳实践，根据文档类型、长度、Embedding 模型等特征
动态推荐最优的分块参数配置。

设计原则:
1. 文档格式决定基础参数 - 结构化数据、长文档、演示文稿等有不同的最优配置
2. 文档长度调整参数 - 短文档用小块提高精度，长文档用大块保留上下文
3. Embedding 模型影响语义分块 - 不同模型有不同的最优相似度阈值
4. 策略类型决定专用参数 - 每种策略有其特定的参数集合
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum


class DocumentLength(Enum):
    """文档长度分类"""
    SHORT = "short"      # < 2000 字符
    MEDIUM = "medium"    # 2000 - 50000 字符
    LONG = "long"        # > 50000 字符


class DocumentCategory(Enum):
    """文档类型分类"""
    STRUCTURED = "structured"      # 结构化数据 (CSV/XLSX/JSON)
    LONG_FORM = "long_form"       # 长篇文档 (PDF/DOCX)
    TECHNICAL = "technical"        # 技术文档 (MD/代码)
    PRESENTATION = "presentation"  # 演示文稿 (PPTX)
    EBOOK = "ebook"               # 电子书 (EPUB)
    WEB = "web"                   # 网页内容 (HTML)
    PLAIN = "plain"               # 纯文本 (TXT)


# ============================================================================
# 核心配置表
# ============================================================================

# 按文档格式的基础文本分块参数
# 设计原理：
# - 结构化数据：每行独立记录，overlap=0 避免切断数据
# - 长篇文档：连续叙事文本，需要 15%-20% 重叠保持语义连贯
# - 演示文稿：每页独立，小块精确检索
# - 电子书：章节很长，需要充分重叠
FORMAT_BASE_PARAMS = {
    # ===== 结构化数据（行级独立语义）=====
    "csv": {
        "chunk_size": 500,
        "overlap": 0,
        "category": DocumentCategory.STRUCTURED,
        "description": "CSV 数据每行是独立记录，无需重叠"
    },
    "xlsx": {
        "chunk_size": 500,
        "overlap": 0,
        "category": DocumentCategory.STRUCTURED,
        "description": "Excel 表格数据按行组织，无需重叠"
    },
    "xls": {
        "chunk_size": 500,
        "overlap": 0,
        "category": DocumentCategory.STRUCTURED,
        "description": "Excel 97-2003 格式"
    },
    "json": {
        "chunk_size": 600,
        "overlap": 0,
        "category": DocumentCategory.STRUCTURED,
        "description": "JSON 结构化数据，按对象边界分块"
    },
    
    # ===== 长篇文档（需要上下文连贯）=====
    "pdf": {
        "chunk_size": 800,
        "overlap": 150,
        "category": DocumentCategory.LONG_FORM,
        "description": "PDF 通常是长篇文档，需要较多上下文重叠"
    },
    "docx": {
        "chunk_size": 800,
        "overlap": 150,
        "category": DocumentCategory.LONG_FORM,
        "description": "Word 文档内容连贯，适当重叠保持语义"
    },
    "doc": {
        "chunk_size": 800,
        "overlap": 150,
        "category": DocumentCategory.LONG_FORM,
        "description": "Word 97-2003 格式"
    },
    
    # ===== 技术文档 =====
    "txt": {
        "chunk_size": 600,
        "overlap": 100,
        "category": DocumentCategory.PLAIN,
        "description": "纯文本根据内容长度动态调整"
    },
    "md": {
        "chunk_size": 600,
        "overlap": 100,
        "category": DocumentCategory.TECHNICAL,
        "description": "Markdown 技术文档，保持段落完整性"
    },
    
    # ===== 网页内容 =====
    "html": {
        "chunk_size": 700,
        "overlap": 100,
        "category": DocumentCategory.WEB,
        "description": "HTML 内容提取后通常需要上下文"
    },
    "htm": {
        "chunk_size": 700,
        "overlap": 100,
        "category": DocumentCategory.WEB,
        "description": "HTML 内容"
    },
    
    # ===== 演示文稿 =====
    "pptx": {
        "chunk_size": 400,
        "overlap": 50,
        "category": DocumentCategory.PRESENTATION,
        "description": "PPT 每页内容相对独立，较小块精确检索"
    },
    "ppt": {
        "chunk_size": 400,
        "overlap": 50,
        "category": DocumentCategory.PRESENTATION,
        "description": "PPT 97-2003 格式"
    },
    
    # ===== 默认 =====
    "default": {
        "chunk_size": 600,
        "overlap": 100,
        "category": DocumentCategory.PLAIN,
        "description": "通用默认配置"
    }
}


# 按文档长度的调整系数
LENGTH_ADJUSTMENTS = {
    DocumentLength.SHORT: {
        "size_multiplier": 0.6,
        "overlap_multiplier": 0.5,
        "min_chunk_size": 150,
        "max_chunk_size": 500,
        "description": "短文档用小块提高精度"
    },
    DocumentLength.MEDIUM: {
        "size_multiplier": 1.0,
        "overlap_multiplier": 1.0,
        "min_chunk_size": 200,
        "max_chunk_size": 1500,
        "description": "中等文档使用标准配置"
    },
    DocumentLength.LONG: {
        "size_multiplier": 1.5,
        "overlap_multiplier": 1.5,
        "min_chunk_size": 300,
        "max_chunk_size": 2000,
        "description": "长文档用大块保留上下文"
    }
}


# Embedding 模型特定的语义分块参数
# 不同模型的向量空间分布不同，需要不同的相似度阈值
EMBEDDING_MODEL_PARAMS = {
    "bge-m3": {
        "similarity_threshold": 0.55,
        "min_chunk_size": 200,
        "max_chunk_size": 1000,
        "dimension": 1024,
        "max_context": 8192,
        "description": "BGE-M3 多语言模型，1024维，速度快"
    },
    "qwen3-embedding-8b": {
        "similarity_threshold": 0.45,
        "min_chunk_size": 300,
        "max_chunk_size": 1500,
        "dimension": 4096,
        "max_context": 32768,
        "description": "Qwen3 高精度模型，4096维，32K上下文"
    },
    "default": {
        "similarity_threshold": 0.5,
        "min_chunk_size": 200,
        "max_chunk_size": 1200,
        "dimension": 1024,
        "max_context": 8192,
        "description": "默认 Embedding 参数"
    }
}


# ============================================================================
# 策略专用参数配置
# ============================================================================

# 混合分块策略参数（合并了原 multimodal 的功能）
HYBRID_STRATEGY_PARAMS = {
    # 正文分块策略参数
    "text": {
        "semantic": {
            "similarity_threshold": 0.5,
            "min_chunk_size": 200,
            "max_chunk_size": 1200,
            "use_embedding": True,
            "embedding_model": "bge-m3"
        },
        "paragraph": {
            "min_chunk_size": 150,
            "max_chunk_size": 1500
        },
        "character": {
            "chunk_size": 600,
            "overlap": 100
        },
        "heading": {
            "min_heading_level": 1,
            "max_heading_level": 3
        },
        "none": {
            "description": "不分块文本（仅提取表格、图片、代码）"
        }
    },
    # 代码分块策略参数
    "code": {
        "lines": {
            "lines_per_chunk": 50,
            "overlap_lines": 8,
            "description": "按行数分块，保持函数/类完整性"
        },
        "character": {
            "chunk_size": 800,
            "overlap": 100,
            "description": "按字符分块"
        },
        "none": {
            "description": "不分块（保持代码块完整）"
        }
    },
    # 表格处理
    "table": {
        "strategy": "independent",
        "min_rows": 2
    },
    # 图片处理
    "image": {
        "strategy": "independent"
    },
    # 内容提取阈值（从 multimodal 合并）
    "extraction": {
        "min_table_rows": 2,
        "min_code_lines": 3,
        "include_tables": True,
        "include_images": True,
        "include_code": True
    }
}


# 父子分块策略参数
PARENT_CHILD_STRATEGY_PARAMS = {
    # 按文档长度调整
    DocumentLength.SHORT: {
        "parent_size": 1200,
        "child_size": 300,
        "parent_overlap": 100,
        "child_overlap": 30,
        "description": "短文档：较小的父块和子块"
    },
    DocumentLength.MEDIUM: {
        "parent_size": 2000,
        "child_size": 400,
        "parent_overlap": 200,
        "child_overlap": 50,
        "description": "中等文档：标准配置"
    },
    DocumentLength.LONG: {
        "parent_size": 2500,
        "child_size": 500,
        "parent_overlap": 300,
        "child_overlap": 75,
        "description": "长文档：较大的父块和子块"
    }
}


# 标题分块策略参数
HEADING_STRATEGY_PARAMS = {
    "default": {
        "min_heading_level": 1,
        "max_heading_level": 3,
        "description": "默认使用 H1-H3"
    },
    # 技术文档通常有更深的标题层级
    DocumentCategory.TECHNICAL: {
        "min_heading_level": 1,
        "max_heading_level": 4,
        "description": "技术文档使用 H1-H4"
    },
    # 电子书章节结构深
    DocumentCategory.EBOOK: {
        "min_heading_level": 1,
        "max_heading_level": 4,
        "description": "电子书使用 H1-H4"
    }
}


# 段落分块策略参数
PARAGRAPH_STRATEGY_PARAMS = {
    DocumentLength.SHORT: {
        "min_chunk_size": 100,
        "max_chunk_size": 800,
        "description": "短文档：允许较小的段落块"
    },
    DocumentLength.MEDIUM: {
        "min_chunk_size": 150,
        "max_chunk_size": 1500,
        "description": "中等文档：标准段落范围"
    },
    DocumentLength.LONG: {
        "min_chunk_size": 200,
        "max_chunk_size": 2000,
        "description": "长文档：允许较大的段落块"
    }
}


# ============================================================================
# 智能参数计算函数
# ============================================================================

def get_document_length_category(char_count: int) -> DocumentLength:
    """根据字符数判断文档长度分类"""
    if char_count < 2000:
        return DocumentLength.SHORT
    elif char_count <= 50000:
        return DocumentLength.MEDIUM
    else:
        return DocumentLength.LONG


def get_format_category(doc_format: str) -> DocumentCategory:
    """获取文档格式对应的分类"""
    fmt = doc_format.lower() if doc_format else "default"
    config = FORMAT_BASE_PARAMS.get(fmt, FORMAT_BASE_PARAMS["default"])
    return config.get("category", DocumentCategory.PLAIN)


def get_base_text_params(doc_format: str) -> Dict[str, Any]:
    """
    获取基于文档格式的基础文本分块参数
    
    Args:
        doc_format: 文档格式（如 'pdf', 'csv', 'docx'）
        
    Returns:
        包含 chunk_size, overlap, description 的字典
    """
    fmt = doc_format.lower() if doc_format else "default"
    config = FORMAT_BASE_PARAMS.get(fmt, FORMAT_BASE_PARAMS["default"])
    return {
        "chunk_size": config["chunk_size"],
        "overlap": config["overlap"],
        "description": config.get("description", "")
    }


def get_adaptive_text_params(
    doc_format: str, 
    char_count: int
) -> Dict[str, Any]:
    """
    根据文档格式和长度自适应调整文本分块参数
    
    Args:
        doc_format: 文档格式
        char_count: 文档字符数
        
    Returns:
        自适应调整后的分块参数
    """
    base = get_base_text_params(doc_format)
    length_cat = get_document_length_category(char_count)
    adjustment = LENGTH_ADJUSTMENTS[length_cat]
    
    # 计算调整后的参数
    chunk_size = int(base["chunk_size"] * adjustment["size_multiplier"])
    overlap = int(base["overlap"] * adjustment["overlap_multiplier"])
    
    # 确保在合理范围内
    chunk_size = max(adjustment["min_chunk_size"], 
                     min(chunk_size, adjustment["max_chunk_size"]))
    overlap = min(overlap, int(chunk_size * 0.3))  # 重叠不超过 30%
    
    return {
        "chunk_size": chunk_size,
        "overlap": overlap,
        "length_category": length_cat.value,
        "adjustment_reason": adjustment["description"],
        "base_description": base.get("description", "")
    }


def get_semantic_params(
    embedding_model: str = "bge-m3",
    doc_format: Optional[str] = None,
    char_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    获取语义分块参数，结合 Embedding 模型和文档特征
    
    Args:
        embedding_model: Embedding 模型名称
        doc_format: 可选的文档格式
        char_count: 可选的文档字符数
        
    Returns:
        语义分块参数配置
    """
    model_params = EMBEDDING_MODEL_PARAMS.get(
        embedding_model, 
        EMBEDDING_MODEL_PARAMS["default"]
    )
    
    result = {
        "similarity_threshold": model_params["similarity_threshold"],
        "min_chunk_size": model_params["min_chunk_size"],
        "max_chunk_size": model_params["max_chunk_size"],
        "use_embedding": True,
        "embedding_model": embedding_model,
        "model_description": model_params.get("description", "")
    }
    
    # 如果提供了文档长度，进一步调整
    if char_count is not None:
        length_cat = get_document_length_category(char_count)
        length_adj = LENGTH_ADJUSTMENTS[length_cat]
        
        result["min_chunk_size"] = int(
            result["min_chunk_size"] * length_adj["size_multiplier"]
        )
        result["max_chunk_size"] = int(
            result["max_chunk_size"] * length_adj["size_multiplier"]
        )
        result["length_adjustment"] = length_adj["description"]
    
    return result


def get_hybrid_params(
    doc_format: str = "default",
    char_count: int = 10000,
    code_block_ratio: float = 0.0,
    embedding_model: str = "bge-m3",
    has_tables: bool = True,
    has_images: bool = True,
    has_code: bool = False,
    # 新增：用于智能推荐正文分块策略的参数
    has_table_layout: bool = True,
    is_flattened_tabular: bool = False,
    is_log_like: bool = False,
    is_slide_like: bool = False,
    has_clear_structure: bool = False,
    heading_count: int = 0
) -> Dict[str, Any]:
    """
    获取混合分块策略参数（合并了原 multimodal 的功能）
    
    现在包含智能正文策略推荐，根据文档特征自动选择最佳的正文分块策略。
    
    Args:
        doc_format: 文档格式
        char_count: 文档字符数
        code_block_ratio: 代码块占比
        embedding_model: Embedding 模型
        has_tables: 是否包含表格
        has_images: 是否包含图片
        has_code: 是否包含代码块
        has_table_layout: 表格是否保留了布局（Markdown 表格格式）
        is_flattened_tabular: 是否是扁平化的表格数据
        is_log_like: 是否是日志类文本
        is_slide_like: 是否是幻灯片类文档
        has_clear_structure: 是否有清晰的标题结构
        heading_count: 标题数量
        
    Returns:
        混合分块策略的完整参数配置，包含推荐的正文策略及理由
    """
    # 获取基础文本参数
    text_params = get_adaptive_text_params(doc_format, char_count)
    
    # 获取语义分块参数（用于正文语义分块）
    semantic_params = get_semantic_params(embedding_model, doc_format, char_count)
    
    # 获取提取阈值配置
    extraction = HYBRID_STRATEGY_PARAMS["extraction"]
    
    # 根据代码占比调整代码分块参数
    code_lines = HYBRID_STRATEGY_PARAMS["code"]["lines"]["lines_per_chunk"]
    code_overlap = HYBRID_STRATEGY_PARAMS["code"]["lines"]["overlap_lines"]
    
    if code_block_ratio > 0.4:
        # 代码占比高时，增大每块行数
        code_lines = 80
        code_overlap = 10
    elif code_block_ratio > 0.2:
        code_lines = 50
        code_overlap = 8
    
    # ========== 智能推荐正文分块策略 ==========
    text_strategy, text_strategy_reason = _recommend_text_strategy(
        doc_format=doc_format,
        has_table_layout=has_table_layout,
        is_flattened_tabular=is_flattened_tabular,
        is_log_like=is_log_like,
        is_slide_like=is_slide_like,
        has_clear_structure=has_clear_structure,
        heading_count=heading_count
    )
    
    return {
        # 正文策略参数
        "text_strategy": text_strategy,
        "text_strategy_reason": text_strategy_reason,
        "text_chunk_size": text_params["chunk_size"],
        "text_overlap": text_params["overlap"],
        "similarity_threshold": semantic_params["similarity_threshold"],
        "use_embedding": True,
        "embedding_model": embedding_model,
        
        # 代码策略参数
        "code_strategy": "lines",
        "code_chunk_lines": code_lines,
        "code_overlap_lines": code_overlap,
        
        # 表格策略
        "table_strategy": "independent",
        
        # 内容提取设置（合并自 multimodal）
        "include_tables": has_tables,
        "include_images": has_images,
        "include_code": has_code or code_block_ratio > 0,
        
        # 提取阈值（合并自 multimodal）
        "min_table_rows": extraction["min_table_rows"],
        "min_code_lines": extraction["min_code_lines"],
        
        # 元信息
        "format_adjustment": text_params.get("base_description", ""),
        "length_adjustment": text_params.get("adjustment_reason", "")
    }


def _recommend_text_strategy(
    doc_format: str,
    has_table_layout: bool = True,
    is_flattened_tabular: bool = False,
    is_log_like: bool = False,
    is_slide_like: bool = False,
    has_clear_structure: bool = False,
    heading_count: int = 0
) -> Tuple[str, str]:
    """
    根据文档特征推荐混合分块的正文策略
    
    推荐优先级：
    1. 扁平化表格数据 -> 段落分块（保持每行记录完整）
    2. 日志类文本 -> 段落分块（保持每条日志完整）
    3. 幻灯片类文档 -> 段落分块（保持每页内容完整）
    4. 结构化数据格式（JSON/CSV）无表格布局 -> 段落分块
    5. 有清晰标题结构 -> 标题分块
    6. 默认 -> 语义分块（通用策略）
    
    Args:
        doc_format: 文档格式
        has_table_layout: 是否有表格布局
        is_flattened_tabular: 是否是扁平化表格
        is_log_like: 是否是日志类文本
        is_slide_like: 是否是幻灯片类
        has_clear_structure: 是否有清晰结构
        heading_count: 标题数量
        
    Returns:
        (strategy, reason) - 推荐的策略和理由
    """
    fmt = doc_format.lower() if doc_format else ""
    
    # 1. 扁平化表格数据 -> 段落分块
    if is_flattened_tabular:
        return (
            "paragraph",
            "检测到表格数据（布局已扁平化），按段落分块可保持每行记录的完整性"
        )
    
    # 2. 表格类格式但没有表格布局 -> 段落分块
    if fmt in ("xlsx", "xls", "csv") and not has_table_layout:
        return (
            "paragraph",
            f"{fmt.upper()} 文件表格布局未保留，推荐按段落分块保持数据行完整"
        )
    
    # 3. 日志类文本 -> 段落分块
    if is_log_like:
        return (
            "paragraph",
            "检测到日志格式文本，按段落分块可保持每条日志记录的完整性"
        )
    
    # 4. 幻灯片类文档 -> 段落分块
    if is_slide_like or fmt in ("pptx", "ppt"):
        return (
            "paragraph",
            "演示文稿每页内容相对独立，按段落分块可保持幻灯片内容的完整性"
        )
    
    # 5. JSON 格式 -> 段落分块
    if fmt == "json":
        return (
            "paragraph",
            "JSON 结构化数据按段落分块可保持每条记录的完整性"
        )
    
    # 6. 有清晰标题结构 -> 标题分块
    if has_clear_structure and heading_count >= 5:
        return (
            "heading",
            f"文档有清晰的标题层级结构（{heading_count}个标题），按标题分块可保持章节完整性"
        )
    
    # 7. 默认 -> 语义分块
    return (
        "semantic",
        "连续叙事文本，语义分块可自动识别自然语义边界"
    )


def get_parent_child_params(
    char_count: int = 10000,
    doc_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取父子分块策略参数
    
    Args:
        char_count: 文档字符数
        doc_format: 可选的文档格式
        
    Returns:
        父子分块策略的参数配置
    """
    length_cat = get_document_length_category(char_count)
    params = PARENT_CHILD_STRATEGY_PARAMS[length_cat]
    
    return {
        "parent_chunk_size": params["parent_size"],
        "child_chunk_size": params["child_size"],
        "parent_overlap": params["parent_overlap"],
        "child_overlap": params["child_overlap"],
        "length_category": length_cat.value,
        "adjustment_reason": params["description"]
    }


def get_heading_params(
    doc_format: str = "default",
    heading_count: int = 0
) -> Dict[str, Any]:
    """
    获取标题分块策略参数
    
    Args:
        doc_format: 文档格式
        heading_count: 标题数量
        
    Returns:
        标题分块策略的参数配置
    """
    category = get_format_category(doc_format)
    
    # 优先使用格式类别的配置，否则使用默认
    if category in HEADING_STRATEGY_PARAMS:
        params = HEADING_STRATEGY_PARAMS[category]
    else:
        params = HEADING_STRATEGY_PARAMS["default"]
    
    return {
        "min_heading_level": params["min_heading_level"],
        "max_heading_level": params["max_heading_level"],
        "description": params["description"]
    }


def get_paragraph_params(char_count: int = 10000) -> Dict[str, Any]:
    """
    获取段落分块策略参数
    
    Args:
        char_count: 文档字符数
        
    Returns:
        段落分块策略的参数配置
    """
    length_cat = get_document_length_category(char_count)
    params = PARAGRAPH_STRATEGY_PARAMS[length_cat]
    
    return {
        "min_chunk_size": params["min_chunk_size"],
        "max_chunk_size": params["max_chunk_size"],
        "length_category": length_cat.value,
        "adjustment_reason": params["description"]
    }


def get_character_params(
    doc_format: str = "default",
    char_count: int = 10000
) -> Dict[str, Any]:
    """
    获取字符分块策略参数
    
    Args:
        doc_format: 文档格式
        char_count: 文档字符数
        
    Returns:
        字符分块策略的参数配置
    """
    return get_adaptive_text_params(doc_format, char_count)


# ============================================================================
# 统一的智能参数获取接口
# ============================================================================

def get_smart_params(
    strategy_type: str,
    doc_format: str = "default",
    char_count: int = 10000,
    embedding_model: str = "bge-m3",
    code_block_ratio: float = 0.0,
    table_count: int = 0,
    image_count: int = 0,
    heading_count: int = 0,
    # 新增：用于智能推荐正文策略的参数
    has_table_layout: bool = True,
    is_flattened_tabular: bool = False,
    is_log_like: bool = False,
    is_slide_like: bool = False,
    has_clear_structure: bool = False
) -> Dict[str, Any]:
    """
    统一的智能参数获取接口
    
    根据策略类型和文档特征，返回最优的分块参数配置
    
    Args:
        strategy_type: 策略类型 (character, paragraph, heading, semantic, 
                       parent_child, hybrid)
        doc_format: 文档格式
        char_count: 文档字符数
        embedding_model: Embedding 模型（用于语义相关策略）
        code_block_ratio: 代码块占比（用于混合策略）
        table_count: 表格数量
        image_count: 图片数量
        heading_count: 标题数量
        has_table_layout: 是否有表格布局
        is_flattened_tabular: 是否是扁平化表格
        is_log_like: 是否是日志类文本
        is_slide_like: 是否是幻灯片类
        has_clear_structure: 是否有清晰结构
        
    Returns:
        策略对应的智能参数配置
    """
    if strategy_type == "character":
        return get_character_params(doc_format, char_count)
    
    elif strategy_type == "paragraph":
        return get_paragraph_params(char_count)
    
    elif strategy_type == "heading":
        return get_heading_params(doc_format, heading_count)
    
    elif strategy_type == "semantic":
        return get_semantic_params(embedding_model, doc_format, char_count)
    
    elif strategy_type == "parent_child":
        return get_parent_child_params(char_count, doc_format)
    
    elif strategy_type == "hybrid":
        return get_hybrid_params(
            doc_format=doc_format,
            char_count=char_count,
            code_block_ratio=code_block_ratio,
            embedding_model=embedding_model,
            has_tables=table_count > 0,
            has_images=image_count > 0,
            has_code=code_block_ratio > 0,
            has_table_layout=has_table_layout,
            is_flattened_tabular=is_flattened_tabular,
            is_log_like=is_log_like,
            is_slide_like=is_slide_like,
            has_clear_structure=has_clear_structure,
            heading_count=heading_count
        )
    
    else:
        # 默认返回字符分块参数
        return get_character_params(doc_format, char_count)


def get_all_format_params() -> Dict[str, Dict[str, Any]]:
    """获取所有文档格式的基础参数配置（用于 API 查询）"""
    return {
        fmt: {
            "chunk_size": config["chunk_size"],
            "overlap": config["overlap"],
            "category": config["category"].value if isinstance(config["category"], DocumentCategory) else config["category"],
            "description": config["description"]
        }
        for fmt, config in FORMAT_BASE_PARAMS.items()
    }


def get_all_embedding_params() -> Dict[str, Dict[str, Any]]:
    """获取所有 Embedding 模型的语义分块参数（用于 API 查询）"""
    return EMBEDDING_MODEL_PARAMS
