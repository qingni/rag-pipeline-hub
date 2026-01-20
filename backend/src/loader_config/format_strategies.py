"""Format strategies and loader registry configuration.

This module defines the parsing strategies for each file format
and the registry of available loaders.
"""
from typing import Dict, List
from ..models.loader_config import LoaderConfig, FormatStrategy
from ..models.loading_result import ExtractionQuality


# Loader Registry - All available loaders and their configurations
LOADER_REGISTRY: Dict[str, LoaderConfig] = {
    "docling_serve": LoaderConfig(
        name="docling_serve",
        display_name="Docling Serve (HTTP)",
        supported_formats=["pdf", "docx", "xlsx", "pptx", "html", "md", "txt", "csv"],
        priority=0,  # Highest priority when available
        avg_speed="medium",
        quality_level=ExtractionQuality.HIGH,
        requires_installation=False,  # No local installation needed
        installation_command="./start_docling.sh",
        supports_tables=True,
        supports_images=True,
        supports_formulas=True,
        supports_ocr=True,
    ),
    "pymupdf": LoaderConfig(
        name="pymupdf",
        display_name="PyMuPDF",
        supported_formats=["pdf"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
        supports_images=True,
    ),
    "pypdf": LoaderConfig(
        name="pypdf",
        display_name="PyPDF",
        supported_formats=["pdf"],
        priority=3,
        avg_speed="fast",
        quality_level=ExtractionQuality.LOW,
    ),
    "docx": LoaderConfig(
        name="docx",
        display_name="python-docx",
        supported_formats=["docx"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "xlsx": LoaderConfig(
        name="xlsx",
        display_name="openpyxl",
        supported_formats=["xlsx", "xls"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
        supports_tables=True,
    ),
    "pptx": LoaderConfig(
        name="pptx",
        display_name="python-pptx",
        supported_formats=["pptx"],
        priority=2,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "html": LoaderConfig(
        name="html",
        display_name="BeautifulSoup",
        supported_formats=["html", "htm"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "csv": LoaderConfig(
        name="csv",
        display_name="pandas CSV",
        supported_formats=["csv"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
        supports_tables=True,
    ),
    "json": LoaderConfig(
        name="json",
        display_name="JSON Loader",
        supported_formats=["json"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "xml": LoaderConfig(
        name="xml",
        display_name="lxml",
        supported_formats=["xml"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "msg": LoaderConfig(
        name="msg",
        display_name="extract-msg",
        supported_formats=["msg"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "vtt": LoaderConfig(
        name="vtt",
        display_name="webvtt-py",
        supported_formats=["vtt"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "properties": LoaderConfig(
        name="properties",
        display_name="jproperties",
        supported_formats=["properties"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "text": LoaderConfig(
        name="text",
        display_name="Text Loader",
        supported_formats=["txt", "md", "markdown", "mdx", "rst", "log"],
        priority=1,
        avg_speed="fast",
        quality_level=ExtractionQuality.MEDIUM,
    ),
    "doc": LoaderConfig(
        name="doc",
        display_name="antiword",
        supported_formats=["doc"],
        priority=1,
        avg_speed="medium",
        quality_level=ExtractionQuality.LOW,
        requires_installation=True,
        installation_command="brew install antiword  # or apt-get install antiword",
    ),
    "unstructured": LoaderConfig(
        name="unstructured",
        display_name="Unstructured",
        supported_formats=["pdf", "docx", "xlsx", "pptx", "html", "msg"],
        priority=10,  # Universal fallback
        avg_speed="slow",
        quality_level=ExtractionQuality.MEDIUM,
        requires_installation=True,
        installation_command='pip install "unstructured[all-docs]"',
        supports_tables=True,
        supports_images=True,
    ),
}


# Format Strategy Mapping - Defines parsing strategy for each format
FORMAT_STRATEGIES: Dict[str, FormatStrategy] = {
    # First batch: PDF/DOCX/XLSX/PPTX
    "pdf": FormatStrategy(
        format="pdf",
        primary_loader="docling_serve",
        fallback_loaders=["pymupdf", "pypdf", "unstructured"],
        size_threshold_mb=20.0,
        fast_loader="pymupdf",
    ),
    "docx": FormatStrategy(
        format="docx",
        primary_loader="docling_serve",
        fallback_loaders=["docx", "unstructured"],
    ),
    "xlsx": FormatStrategy(
        format="xlsx",
        primary_loader="xlsx",  # 优先使用 openpyxl，保留完整的 Sheet 名称和元数据
        fallback_loaders=["docling_serve", "unstructured"],
    ),
    "xls": FormatStrategy(
        format="xls",
        primary_loader="xlsx",
        fallback_loaders=["unstructured"],
    ),
    "pptx": FormatStrategy(
        format="pptx",
        primary_loader="pptx",  # python-pptx 对 PPTX 的支持更好
        fallback_loaders=["docling_serve", "unstructured"],
    ),
    "ppt": FormatStrategy(
        format="ppt",
        primary_loader="docling_serve",  # 旧版 PPT 需要 Docling 转换
        fallback_loaders=["unstructured"],
    ),
    
    # Second batch: HTML/CSV/TXT/MD
    "html": FormatStrategy(
        format="html",
        primary_loader="html",
        fallback_loaders=["unstructured"],
    ),
    "htm": FormatStrategy(
        format="htm",
        primary_loader="html",
        fallback_loaders=["unstructured"],
    ),
    "csv": FormatStrategy(
        format="csv",
        primary_loader="csv",
        fallback_loaders=[],
    ),
    "json": FormatStrategy(
        format="json",
        primary_loader="json",
        fallback_loaders=[],
    ),
    "txt": FormatStrategy(
        format="txt",
        primary_loader="text",
        fallback_loaders=[],
    ),
    "md": FormatStrategy(
        format="md",
        primary_loader="text",
        fallback_loaders=[],
    ),
    "markdown": FormatStrategy(
        format="markdown",
        primary_loader="text",
        fallback_loaders=[],
    ),
    "mdx": FormatStrategy(
        format="mdx",
        primary_loader="text",
        fallback_loaders=[],
    ),
    
    # Third batch: Other formats
    "xml": FormatStrategy(
        format="xml",
        primary_loader="xml",
        fallback_loaders=["unstructured"],
    ),
    "msg": FormatStrategy(
        format="msg",
        primary_loader="msg",
        fallback_loaders=["unstructured"],
    ),
    "vtt": FormatStrategy(
        format="vtt",
        primary_loader="vtt",
        fallback_loaders=[],
    ),
    "properties": FormatStrategy(
        format="properties",
        primary_loader="properties",
        fallback_loaders=[],
    ),
    "doc": FormatStrategy(
        format="doc",
        primary_loader="doc",
        fallback_loaders=["unstructured"],
    ),
    "rst": FormatStrategy(
        format="rst",
        primary_loader="text",
        fallback_loaders=[],
    ),
    "log": FormatStrategy(
        format="log",
        primary_loader="text",
        fallback_loaders=[],
    ),
}


def get_loader_config(loader_name: str) -> LoaderConfig:
    """
    Get loader configuration by name.
    
    Args:
        loader_name: Name of the loader
        
    Returns:
        LoaderConfig instance
        
    Raises:
        KeyError: If loader not found
    """
    if loader_name not in LOADER_REGISTRY:
        raise KeyError(f"Unknown loader: {loader_name}")
    return LOADER_REGISTRY[loader_name]


def get_format_strategy(file_format: str) -> FormatStrategy:
    """
    Get format strategy by file format.
    
    Args:
        file_format: File format/extension (e.g., 'pdf', 'docx')
        
    Returns:
        FormatStrategy instance
        
    Raises:
        KeyError: If format not supported
    """
    format_lower = file_format.lower().lstrip('.')
    if format_lower not in FORMAT_STRATEGIES:
        raise KeyError(f"Unsupported format: {file_format}")
    return FORMAT_STRATEGIES[format_lower]


def get_supported_formats() -> List[str]:
    """Get list of all supported file formats."""
    return list(FORMAT_STRATEGIES.keys())


def get_available_loaders() -> List[LoaderConfig]:
    """Get list of all available loaders."""
    return list(LOADER_REGISTRY.values())


def is_format_supported(file_format: str) -> bool:
    """Check if a file format is supported."""
    return file_format.lower().lstrip('.') in FORMAT_STRATEGIES
