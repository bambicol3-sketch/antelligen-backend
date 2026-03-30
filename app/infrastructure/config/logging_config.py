import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with console + daily rotating file handlers.

    Log files are written to <project_root>/logs/ with daily rotation
    and 30-day retention.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # File handler — rotates daily at midnight, keeps 30 days
    # Naming: logs/app.log (current), logs/2026-03-30-app.log (rotated)
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y%m%d"
    file_handler.namer = lambda name: os.path.join(
        os.path.dirname(name),
        os.path.basename(name).replace("app.log.", "") + "-app.log",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
