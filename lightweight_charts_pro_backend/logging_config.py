"""Structured logging helpers with request correlation support."""

# Standard Imports
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

# Third Party Imports
from pythonjsonlogger import jsonlogger

# Local Imports
from lightweight_charts_pro_backend.config import Settings

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that enriches log records with request context."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Augment log records with timestamps, levels, and request IDs.

        Args:
            log_record (dict[str, Any]): Mutable log dictionary to enrich.
            record (logging.LogRecord): Original log record emitted by logger.
            message_dict (dict[str, Any]): Structured message payload if provided.

        Returns:
            None: The log record dictionary is mutated in place.
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = self.formatTime(record, self.datefmt)

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add request ID from context if available
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)


def setup_logging(settings: Settings) -> None:
    """Configure structured logging based on runtime environment.

    Args:
        settings (Settings): Application settings controlling log behavior.

    Returns:
        None: Logging handlers and formatters are configured globally.
    """
    # Determine log format based on environment
    if settings.is_production:
        # Use JSON logging for production
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Use human-readable logging for development
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers
    root_logger.handlers = []

    # Add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set specific log levels for libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Log startup message
    root_logger.info(
        "Logging configured",
        extra={
            "environment": settings.environment,
            "log_level": settings.log_level,
            "format": "json" if settings.is_production else "text",
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger by name.

    Args:
        name (str): Logger name, typically ``__name__`` from the caller.

    Returns:
        logging.Logger: Logger instance honoring the configured handlers.
    """
    return logging.getLogger(name)


def set_request_id(request_id: str | None = None) -> str:
    """Store a request ID in context for correlation across log records.

    Args:
        request_id (str | None): Optional existing request identifier; generates a UUID when ``None``.

    Returns:
        str: Request identifier that was set in the context.
    """
    # Generate a UUID when the caller does not provide an ID
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """Retrieve the current request ID stored in context.

    Returns:
        str: Request identifier or empty string when unset.
    """
    return request_id_var.get()


def clear_request_id() -> None:
    """Remove any request ID stored in context to avoid leakage across requests.

    Returns:
        None: This function is executed for its side effects only.
    """
    request_id_var.set("")
