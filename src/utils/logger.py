"""Utilitaire de logging centralisé.

Ce module configure un logging JSON avec rotation et fournit des helpers pour
enrichir automatiquement les logs avec du contexte (job, durée, module).

Exemple d'utilisation::

    from utils.logger import configure_logging, get_logger, log_execution

    configure_logging()
    LOGGER = get_logger(__name__, job_name="my_job")

    with log_execution(LOGGER, "Traitement", extra={"step": 1}):
        ...
        LOGGER.info("Action terminée", extra={"job_name": "my_job"})
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_FILENAME = "app.log"


@dataclass
class LoggingSettings:
    """Paramètres du système de logs."""

    env: str = "dev"
    level: str = "INFO"
    log_dir: str = "logs"
    filename: str = DEFAULT_FILENAME
    max_bytes: int = DEFAULT_MAX_BYTES
    backup_count: int = DEFAULT_BACKUP_COUNT


class JsonFormatter(logging.Formatter):
    """Formatter JSON compact pour faciliter le parsing."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "job_name": getattr(record, "job_name", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "pid": record.process,
        }
        standard = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }
        for key, value in record.__dict__.items():
            if key in standard or key in log_record:
                continue
            log_record[key] = self._serialize(value)

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        clean_record = {k: v for k, v in log_record.items() if v is not None}
        return json.dumps(clean_record, ensure_ascii=False)

    @staticmethod
    def _serialize(value: Any) -> Any:
        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value)


class DevFormatter(logging.Formatter):
    """Formatter lisible pour le développement."""

    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s.%03d"

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        time_str = self.formatTime(record, self.datefmt)
        job = getattr(record, "job_name", None)
        duration = getattr(record, "duration_ms", None)
        parts = [
            time_str,
            f"{record.levelname:<8}",
            record.name,
            record.funcName,
        ]
        if job:
            parts.append(f"job={job}")
        if duration is not None:
            parts.append(f"duration_ms={duration}")
        message = " | ".join(parts)
        return f"{message} | {record.getMessage()}"


_CONFIGURED = False


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Configure le logging global (idempotent).

    Args:
        config: dictionnaire de configuration (config.yaml -> logging).
    """

    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return

    settings = LoggingSettings(**(config or {}))
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / settings.filename

    level = getattr(logging, settings.level.upper(), logging.INFO)
    console_handler = logging.StreamHandler()
    if settings.env == "prod":
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(DevFormatter())

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.max_bytes,
        backupCount=settings.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())

    logging.basicConfig(level=level, handlers=[console_handler, file_handler], force=True)
    _CONFIGURED = True


def get_logger(name: str, job_name: Optional[str] = None, **extra: Any) -> logging.LoggerAdapter:
    """Retourne un LoggerAdapter enrichi avec le contexte fourni."""

    context = {"job_name": job_name}
    context.update(extra)
    # Remove None to avoid noisy JSON
    context = {k: v for k, v in context.items() if v is not None}
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, context)


@contextmanager
def log_execution(
    logger: logging.Logger, action: str, job_name: Optional[str] = None, **extra: Any
):
    """Context manager pour tracer la durée d'une action."""

    start = time.perf_counter()
    context = {"job_name": job_name, **extra}
    context = {k: v for k, v in context.items() if v is not None}
    logger.info("%s démarré", action, extra=context)
    try:
        yield
    except Exception:  # pragma: no cover - propagation
        context["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        logger.error("%s échoué", action, extra=context, exc_info=True)
        raise
    else:
        context["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        logger.info("%s terminé", action, extra=context)


__all__ = ["configure_logging", "get_logger", "log_execution", "LoggingSettings"]
