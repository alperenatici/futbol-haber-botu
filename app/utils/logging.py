"""Logging utilities for the football news bot."""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

from app.config import settings

# Install rich traceback handler
install(show_locals=True)

console = Console()


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rich_console: bool = True
) -> logging.Logger:
    """Setup logging configuration."""
    
    # Create logger
    logger = logging.getLogger("futbot")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Add console handler
    if rich_console:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = settings.logs_dir / log_file
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "futbot") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


# Default logger
logger = setup_logging(log_file="futbot.log")
