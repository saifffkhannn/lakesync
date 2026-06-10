import logging
import os
from datetime import datetime

logger = None
logger_file_path = None


def get_log_file_path():
    return logger_file_path


def start_new_log_file():
    global logger, logger_file_path

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")

    active_logger = get_logger()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    for handler in list(active_logger.handlers):
        if isinstance(handler, logging.FileHandler):
            active_logger.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    active_logger.addHandler(file_handler)
    logger_file_path = log_file

    return log_file

def get_logger():
    """
    Initializes and returns a singleton logger instance.
    - Creates logs directory if not present
    - Logs to both file and console
    - Uses timestamped log file for each run
    """

    global logger, logger_file_path

    # --------------------------------------------------
    # Return existing logger (singleton pattern)
    # --------------------------------------------------
    if logger:
        return logger

    try:
        # --------------------------------------------------
        # Determine base directory of project
        # --------------------------------------------------
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # --------------------------------------------------
        # Create logs directory if not exists
        # --------------------------------------------------
        log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        # --------------------------------------------------
        # Create unique log file using timestamp
        # --------------------------------------------------
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")
        logger_file_path = log_file

        # --------------------------------------------------
        # Initialize logger
        # --------------------------------------------------
        logger = logging.getLogger("pipeline_logger")
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers if function is called multiple times
        if logger.handlers:
            return logger

        # --------------------------------------------------
        # Define log format
        # --------------------------------------------------
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        # --------------------------------------------------
        # File handler (writes logs to file)
        # --------------------------------------------------
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"⚠️ Failed to create file handler | Error: {str(e)}")
            # Do not stop execution — fallback to console logging

        # --------------------------------------------------
        # Console handler (prints logs to terminal)
        # --------------------------------------------------
        try:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        except Exception as e:
            print(f"⚠️ Failed to create console handler | Error: {str(e)}")

        return logger

    except Exception as e:
        # Critical failure — logger itself failed
        print(f"❌ Logger initialization failed: {str(e)}")
        raise
