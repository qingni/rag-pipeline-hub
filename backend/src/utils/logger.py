"""
Logging Configuration for Vector Index Module

This module provides logging configuration specific to the vector index functionality.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_vector_index_logger(
    name: str = "vector_index",
    log_level: str = "INFO",
    log_dir: str = "./logs",
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup logger for vector index module
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_console: Enable console logging
        log_to_file: Enable file logging
        max_file_size_mb: Maximum size of each log file in MB
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        log_file = log_path / f"{name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info(f"Logger '{name}' initialized (level: {log_level})")
    return logger


def get_vector_index_logger(name: str = "vector_index") -> logging.Logger:
    """
    Get or create a vector index logger
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up
    if not logger.handlers:
        return setup_vector_index_logger(name)
    
    return logger


# Setup default logger for the module
default_logger = setup_vector_index_logger()


# Alias for convenience
get_logger = get_vector_index_logger
