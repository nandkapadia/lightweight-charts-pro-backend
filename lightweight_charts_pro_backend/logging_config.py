"""Structured logging configuration for the application.

This module sets up JSON-formatted logging for production environments
with request correlation IDs and contextual information.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from pythonjsonlogger import jsonlogger

from lightweight_charts_pro_backend.config import Settings

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds request context to log records."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record.

        Args:
            log_record: Dictionary to add fields to.
            record: Original log record.
            message_dict: Dictionary from the log message.
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
    """Configure structured logging for the application.

    Sets up JSON logging for production and human-readable logging
    for development. Configures log levels and formatters.

    Args:
        settings: Application settings containing log configuration.
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
    """Get a logger with the specified name.

    Args:
        name: Logger name (usually __name__).

    Returns:
        logging.Logger: Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", extra={"chart_id": "chart1"})
    """
    return logging.getLogger(name)


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID in context for log correlation.

    Args:
        request_id: Optional request ID. If None, generates a new UUID.

    Returns:
        str: The request ID that was set.

    Example:
        >>> request_id = set_request_id()
        >>> logger.info("Processing request")  # Will include request_id
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """Get current request ID from context.

    Returns:
        str: Current request ID or empty string if not set.
    """
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear request ID from context.

    Should be called at the end of request processing.
    """
    request_id_var.set("")
