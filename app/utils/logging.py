"""Application-wide structured logging setup (loguru based)."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.config.settings import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=False,
        diagnose=False,
    )
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "app.log",
        level=settings.log_level,
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
    )
    _CONFIGURED = True


def get_logger(name: str):
    configure_logging()
    return logger.bind(module=name)
