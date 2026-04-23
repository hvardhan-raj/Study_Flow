from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .settings import settings


def configure_logging() -> logging.Logger:
    """Configure application logging once for both console and file output."""
    settings.ensure_directories()

    logger = logging.getLogger()
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.debug("Logging configured")
    return logger

