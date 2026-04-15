"""
Logging configuration using loguru
"""

import os
import sys
from loguru import logger
from datetime import datetime

# Configure loguru
def setup_logger():
    """Setup application logging"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Add file handler
    log_file = os.path.join(log_dir, f"scrapmaster_{datetime.now().strftime('%Y%m%d')}.log")
    logger.add(
        log_file,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    logger.info("ScrapMaster Desktop logging initialized")
    return logger

def get_logger():
    """Get the logger instance"""
    return logger