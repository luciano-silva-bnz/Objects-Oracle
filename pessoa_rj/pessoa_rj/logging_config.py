from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock

from .config import LOG_FILE

_LOG_LOCK = Lock()
_INITIALIZED = False


def _ensure_configured() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    with _LOG_LOCK:
        if _INITIALIZED:
            return
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)

        logger = logging.getLogger("pessoa_rj")
        logger.setLevel(logging.INFO)
        if not any(
            isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(LOG_FILE)
            for h in logger.handlers
        ):
            logger.addHandler(handler)

        _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    _ensure_configured()
    full_name = f"pessoa_rj.{name}" if not name.startswith("pessoa_rj") else name
    return logging.getLogger(full_name)


def get_log_path() -> Path:
    _ensure_configured()
    return LOG_FILE
