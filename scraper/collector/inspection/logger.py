import logging
import os
from logging.handlers import RotatingFileHandler

# Set up log folder relative to this script
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "collector.log")

# Setup logging configuration
logger = logging.getLogger("inspection_schedule_collector")
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if logger is imported multiple times
if not logger.handlers:
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (Rotating, max 10MB per file, keep 3 backup copies)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
