import logging
import os
import sys

def setup_logging():
    """Configures logging to both console and a file in the project root."""
    # Find project root (one level up from qatrackplus_manager_windows)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(project_root, "logs")
    
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            # Fallback to current directory if we can't create logs in root
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "manager.log")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # We don't add a Console Handler here because the CLI uses 'rich'
    # which has its own console handling. 
    # But we can add a simple one if needed, or let rich handle it.
    
    logging.info("--- Logging Initialized ---")
    logging.info(f"Log file: {log_file}")
    logging.info(f"Platform: {sys.platform}")
    logging.info(f"Python Version: {sys.version}")

def get_logger(name):
    return logging.getLogger(name)
