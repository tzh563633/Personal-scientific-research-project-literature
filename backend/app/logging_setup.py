from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import settings


def configure_logging() -> None:
    log_path = settings.storage_path / "logs" / "app.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(formatter)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(stream)
        root.addHandler(file_handler)
