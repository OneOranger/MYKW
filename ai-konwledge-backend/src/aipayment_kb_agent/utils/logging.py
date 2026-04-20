from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aipayment_kb_agent.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    log_dir: Path = settings.log_path
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root.addHandler(stream)
    root.addHandler(file_handler)
