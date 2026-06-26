"""
logger.py — Per-run file logger with optional GUI callback.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

LOG_DIR = Path(__file__).parent.parent / "logs"


def get_run_logger(
    name: str = "GeminiArtworkStudio",
    log_lines: list[str] | None = None,
    callback: Callable[[str], None] | None = None,
) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{timestamp}_{name}.log"

    logger = logging.getLogger(f"{name}_{timestamp}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_lines is not None:
        class _ListHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                log_lines.append(self.format(record))
        lh = _ListHandler()
        lh.setFormatter(fmt)
        logger.addHandler(lh)

    if callback is not None:
        class _CallbackHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                callback(self.format(record))
        cbh = _CallbackHandler()
        cbh.setFormatter(fmt)
        logger.addHandler(cbh)

    return logger