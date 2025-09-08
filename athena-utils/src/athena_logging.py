"""
Lightweight, reusable logging utilities for Athena services.

Usage:
  from athena_logging import configure_logging, get_logger, log_exceptions,
      set_request_context, clear_request_context

Then in app startup (once):
  configure_logging()

In code:
  logger = get_logger(__name__)
  logger.info("Hello")

Environment variables (optional):
  ATHENA_LOG_LEVEL   -> DEBUG | INFO | WARNING | ERROR | CRITICAL
  ATHENA_LOG_FORMAT  -> text | json
  ATHENA_LOG_SERVICE -> service name string
  ATHENA_LOG_FILE    -> absolute or relative log file path
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    FileHandler,
    Filter,
    Formatter,
    Logger,
    StreamHandler,
    getLogger,
)

# Type aliases to keep annotations short and readable
LogCallable = Callable[..., object]
LogDecorator = Callable[
    [LogCallable],
    LogCallable,
]
# Default log level
DEFAULT_LOG_LEVEL = INFO


_is_configured: bool = False

# Context variables to enrich log records across threads/async tasks
_request_id_var: ContextVar[Optional[str]] = ContextVar(
    "athena_request_id",
    default=None,
)
_user_id_var: ContextVar[Optional[str]] = ContextVar(
    "athena_user_id",
    default=None,
)
_service_name_default: str = "athena"


def _coerce_level(level_str: Optional[str]) -> int:
    if not level_str:
        return INFO
    value = str(level_str).strip().upper()
    return {
        "DEBUG": DEBUG,
        "INFO": INFO,
        "WARNING": WARNING,
        "ERROR": ERROR,
        "CRITICAL": CRITICAL,
    }.get(value, INFO)


class _ContextFilter(Filter):
    """Inject contextual fields on LogRecord so formatters can rely on them.

    This ensures fields like service name, request id and user id are
    always present, even if not explicitly set by the caller.
    """

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record):  # noqa: D401
        # Service name is always present
        if not hasattr(record, "service_name"):
            record.service_name = self.service_name

        # Context fields are optional but should always exist for formatting
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_var.get() or "-"
        if not hasattr(record, "user_id"):
            record.user_id = _user_id_var.get() or "-"
        return True


class _JsonFormatter(Formatter):
    """Tiny JSON formatter to avoid extra dependencies."""

    def format(self, record) -> str:  # noqa: D401
        base: Dict[str, object] = {
            "ts": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(
                record,
                "service_name",
                _service_name_default,
            ),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def _ensure_parent_dir(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def configure_logging(
    *,
    level: Optional[str] = None,
    json_format: Optional[bool] = None,
    service_name: Optional[str] = None,
    log_file: Optional[str] = None,
    force: bool = False,
) -> None:
    """Configure global logging for Athena apps.

    Reads defaults from environment if parameters are not provided.
    Safe to call multiple times; pass force=True to reconfigure.
    """

    global _is_configured, _service_name_default
    if _is_configured and not force:
        return

    env_level = os.getenv("ATHENA_LOG_LEVEL")
    env_format = os.getenv("ATHENA_LOG_FORMAT")
    env_service = os.getenv("ATHENA_LOG_SERVICE")
    env_file = os.getenv("ATHENA_LOG_FILE")

    effective_level = _coerce_level(level or env_level)
    use_json = (
        json_format
        if json_format is not None
        else (
            str(env_format).lower() == "json" if env_format else False
        )
    )
    _service_name_default = (
        service_name or env_service or _service_name_default
    )
    target_file = (
        Path(log_file or env_file) if (log_file or env_file) else None
    )

    root = getLogger()

    # Remove existing handlers when forcing reconfiguration
    if force:
        for handler in list(root.handlers):
            root.removeHandler(handler)

    root.setLevel(effective_level)

    # Common filter for all handlers
    ctx_filter = _ContextFilter(_service_name_default)

    # Console handler
    console_handler = StreamHandler(stream=sys.stdout)
    console_handler.setLevel(effective_level)
    console_handler.addFilter(ctx_filter)
    if use_json:
        console_handler.setFormatter(_JsonFormatter())
    else:
        # Timestamp, level, service, context, logger and message
        fmt = (
            "%(asctime)s %(levelname)s %(service_name)s "
            "[rid=%(request_id)s uid=%(user_id)s] "
            "%(name)s:%(lineno)d - %(message)s"
        )
        datefmt = "%Y-%m-%dT%H:%M:%S%z"
        console_handler.setFormatter(
            Formatter(fmt=fmt, datefmt=datefmt)
        )
    root.addHandler(console_handler)

    # Optional file handler
    if target_file is not None:
        _ensure_parent_dir(target_file)
        file_handler = FileHandler(target_file, encoding="utf-8")
        file_handler.setLevel(effective_level)
        file_handler.addFilter(ctx_filter)
        if use_json:
            file_handler.setFormatter(_JsonFormatter())
        else:
            fmt = (
                "%(asctime)s %(levelname)s %(service_name)s "
                "[rid=%(request_id)s uid=%(user_id)s] "
                "%(name)s:%(lineno)d - %(message)s"
            )
            datefmt = "%Y-%m-%dT%H:%M:%S%z"
            file_handler.setFormatter(
                Formatter(fmt=fmt, datefmt=datefmt)
            )
        root.addHandler(file_handler)

    _is_configured = True


def get_logger(name: Optional[str] = None) -> Logger:
    """Return a logger, ensuring base configuration exists."""
    if not _is_configured:
        configure_logging()
    return getLogger(name or _service_name_default)


def set_request_context(
    *,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Bind request-scoped fields that will automatically appear in logs."""
    if request_id is not None:
        _request_id_var.set(request_id)
    if user_id is not None:
        _user_id_var.set(user_id)


def get_request_context() -> Dict[str, Optional[str]]:
    """Return the current request context values."""
    return {
        "request_id": _request_id_var.get(),
        "user_id": _user_id_var.get(),
    }


def clear_request_context() -> None:
    """Clear the request context fields."""
    _request_id_var.set(None)
    _user_id_var.set(None)


def log_exceptions(
    *,
    message: str = "Unhandled exception",
    level: int = ERROR,
    logger: Optional[Logger] = None,
) -> LogDecorator:
    """Decorator to log exceptions and re-raise.

    Errors are never swallowed; they are logged and re-raised.
    """

    def _decorator(func: LogCallable) -> LogCallable:
        from functools import wraps

        @wraps(func)
        def _wrapper(*args: object, **kwargs: object) -> object:
            log = logger or get_logger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                log.log(
                    level,
                    f"{message}: {exc}",
                    exc_info=True,
                )
                raise

        return _wrapper

    return _decorator


@contextmanager
def capture_exceptions(
    *,
    message: str = "Unhandled exception",
    level: int = ERROR,
    logger: Optional[Logger] = None,
):
    """Context manager to log exceptions and re-raise.

    Example:
        with capture_exceptions(message="processing failed"):
            do_work()
    """

    log = logger or get_logger(__name__)
    try:
        yield
    except Exception as exc:  # noqa: BLE001
        log.log(level, f"{message}: {exc}", exc_info=True)
        raise


__all__ = [
    "configure_logging",
    "get_logger",
    "set_request_context",
    "get_request_context",
    "clear_request_context",
    "log_exceptions",
    "capture_exceptions",
]
