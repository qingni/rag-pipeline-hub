"""Document loaders package."""
from .pymupdf_loader import pymupdf_loader
from .pypdf_loader import pypdf_loader
from .unstructured_loader import unstructured_loader
from .text_loader import text_loader
from .docx_loader import docx_loader
from .doc_loader import doc_loader

__all__ = [
    'pymupdf_loader',
    'pypdf_loader',
    'unstructured_loader',
    'text_loader',
    'docx_loader',
    'doc_loader'
]
