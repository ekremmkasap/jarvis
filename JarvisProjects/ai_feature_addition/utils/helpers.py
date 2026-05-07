import logging
import datetime
import os

def setup_logging(log_file_path: str = "project.log", level: int = logging.INFO) -> None:
    """
    Configures the root logger for the project, directing output to both a file and the console.

    Args:
        log_file_path: The path to the log file. Defaults to "project.log".
        level: The minimum logging level to capture. Defaults to logging.INFO.
               Common levels: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL.
    """
    # Ensure the directory for the log file exists
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )

def generate_timestamp(format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Generates a current timestamp string in a specified format.

    Args:
        format_string: The desired format string for the timestamp.
                       Defaults to "%Y-%m-%d %H:%M:%S".
                       See datetime.strftime for format codes.

    Returns:
        A string representing the current time formatted according to format_string.
    """
    return datetime.datetime.now().strftime(format_string)