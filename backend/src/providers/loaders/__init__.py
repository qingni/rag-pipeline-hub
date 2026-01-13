"""Document loaders package.

This package provides document loaders for various file formats.
All loaders follow a consistent interface and output format.
"""
from .base_loader import BaseLoader
from .pymupdf_loader import pymupdf_loader
from .pypdf_loader import pypdf_loader
from .unstructured_loader import unstructured_loader
from .text_loader import text_loader
from .docx_loader import docx_loader
from .doc_loader import doc_loader
from .docling_loader import docling_loader
from .html_loader import html_loader
from .csv_loader import csv_loader
from .json_loader import json_loader
from .xml_loader import xml_loader
from .xlsx_loader import xlsx_loader
from .pptx_loader import pptx_loader
from .epub_loader import epub_loader
from .email_loader import email_loader
from .msg_loader import msg_loader
from .vtt_loader import vtt_loader
from .properties_loader import properties_loader

# Loader registry - maps loader names to instances
LOADER_INSTANCES = {
    # PDF loaders
    'pymupdf': pymupdf_loader,
    'pypdf': pypdf_loader,
    
    # Document loaders
    'docx': docx_loader,
    'doc': doc_loader,
    'xlsx': xlsx_loader,
    'pptx': pptx_loader,
    
    # Web/markup loaders
    'html': html_loader,
    'xml': xml_loader,
    
    # Data format loaders
    'csv': csv_loader,
    'json': json_loader,
    
    # Text loaders
    'text': text_loader,
    
    # Email loaders
    'email': email_loader,
    'msg': msg_loader,
    
    # Ebook loaders
    'epub': epub_loader,
    
    # Specialized loaders
    'vtt': vtt_loader,
    'properties': properties_loader,
    
    # Advanced loaders
    'docling': docling_loader,
    'unstructured': unstructured_loader,
}


def get_loader(name: str):
    """
    Get a loader instance by name.
    
    Args:
        name: Loader name
        
    Returns:
        Loader instance or None if not found
    """
    return LOADER_INSTANCES.get(name)


def get_available_loaders():
    """
    Get list of available loader names.
    
    Returns:
        List of loader names
    """
    return list(LOADER_INSTANCES.keys())


def get_available_loader_instances():
    """
    Get list of available loader instances that are actually usable.
    
    Returns:
        Dictionary of loader name to instance for available loaders
    """
    available = {}
    for name, loader in LOADER_INSTANCES.items():
        if hasattr(loader, 'is_available'):
            if loader.is_available():
                available[name] = loader
        else:
            available[name] = loader
    return available


def register_loader(name: str, loader):
    """
    Register a new loader.
    
    Args:
        name: Loader name
        loader: Loader instance
    """
    LOADER_INSTANCES[name] = loader


def check_loader_availability():
    """
    Check availability of all loaders.
    
    Returns:
        Dictionary of loader name to (available, reason) tuples
    """
    status = {}
    for name, loader in LOADER_INSTANCES.items():
        if hasattr(loader, 'is_available'):
            available = loader.is_available()
            reason = None
            if not available and hasattr(loader, 'get_unavailable_reason'):
                reason = loader.get_unavailable_reason()
            status[name] = (available, reason)
        else:
            status[name] = (True, None)
    return status


__all__ = [
    'BaseLoader',
    'pymupdf_loader',
    'pypdf_loader',
    'unstructured_loader',
    'text_loader',
    'docx_loader',
    'doc_loader',
    'docling_loader',
    'html_loader',
    'csv_loader',
    'json_loader',
    'xml_loader',
    'xlsx_loader',
    'pptx_loader',
    'epub_loader',
    'email_loader',
    'msg_loader',
    'vtt_loader',
    'properties_loader',
    'LOADER_INSTANCES',
    'get_loader',
    'get_available_loaders',
    'get_available_loader_instances',
    'register_loader',
    'check_loader_availability',
]
