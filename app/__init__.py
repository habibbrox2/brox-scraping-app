"""
ScrapMaster Desktop Application
A production-ready desktop web scraping application with modern GUI.
"""

__version__ = "1.0.0"
__author__ = "ScrapMaster Team"

import sys
import os

# Add the application root to path
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_ROOT)

# Initialize logging
from app.utils.logger import setup_logger
logger = setup_logger()

# Initialize database
from app.database.db import init_database, get_session
init_database()