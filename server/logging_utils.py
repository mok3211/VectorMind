from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from server.config import settings

_CONFIGURED = False
_MODULE_HANDLER_NAMES: set[str] = set()


def _level() -> int:
    name = (settings.log_level or "INFO").strip().upper()
    return getattr(logging, name, logging.INFO)


def _formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _new_file_handler(path: Path) -> TimedRotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        filename=str(path),
        when="midnight",
        interval=1,
        backupCount=max(1, int(settings.log_retention_days or 5)),
        encoding="utf-8",
    )
    handler.setLevel(_level())
    handler.setFormatter(_formatter())
    return handler


def _module_log_path(name: str) -> Path:
    safe_name = (name or "app").replace("/", ".").replace("\\", ".")
    safe_name = safe_name.replace(":", ".").replace(" ", "_")
    return Path(settings.log_dir) / f"{safe_name}.log"


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(_level())
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(_level())
    console.setFormatter(_formatter())
    root.addHandler(console)

    root.addHandler(_new_file_handler(log_dir / "app.log"))

    logging.captureWarnings(True)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    logger = logging.getLogger(name)
    logger.setLevel(_level())

    handler_name = f"module-file:{name}"
    if handler_name not in _MODULE_HANDLER_NAMES:
        handler = _new_file_handler(_module_log_path(name))
        handler.set_name(handler_name)
        logger.addHandler(handler)
        logger.propagate = True
        _MODULE_HANDLER_NAMES.add(handler_name)

    return logger
