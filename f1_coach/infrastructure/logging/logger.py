"""Centralised logging configuration for KOACH.

Every module obtains its logger via:
    from f1_coach.infrastructure.logging.logger import get_logger
    logger = get_logger(__name__)

Log format:  [YYYY-MM-DD HH:MM:SS] [LEVEL] [module.path] message
Destinations: terminal (stdout) + daily rotating file under data/logs/
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_FORMATTER = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_LOG_DIR = Path("data/logs")
_initialized = False


def _initialize() -> None:
    global _initialized
    if _initialized:
        return

    # Ensure stdout handles UTF-8 on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("f1_coach")
    root.setLevel(logging.INFO)

    # Terminal handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(_FORMATTER)
    root.addHandler(stream_handler)

    # Daily rotating file handler — keeps all old files (no backupCount limit)
    file_handler = TimedRotatingFileHandler(
        filename=_LOG_DIR / "f1_coach.log",
        when="midnight",
        interval=1,
        backupCount=0,        # never auto-delete old logs
        encoding="utf-8",
        utc=False,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(_FORMATTER)
    root.addHandler(file_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-specific logger, ensuring global logging is initialised."""
    _initialize()
    return logging.getLogger(name)
