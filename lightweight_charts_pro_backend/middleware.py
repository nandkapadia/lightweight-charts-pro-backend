"""Middleware for error handling, structured logging, and request tracking."""

# Standard Imports
import time
from collections.abc import Callable

# Third Party Imports
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

# Local Imports
from lightweight_charts_pro_backend.logging_config import (
    clear_request_id,
    get_logger,
    set_request_id,
)

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch exceptions and return structured JSON responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process a request and normalize any raised exceptions.

        Args:
            request (Request): Incoming HTTP request object.
            call_next (Callable): Next handler in the ASGI middleware chain.

        Returns:
            Response: Successful response or formatted error payload.
        """
        try:
            # Attempt to process the request normally
            response = await call_next(request)
            return response

        except ValidationError as exc:
            # Pydantic validation errors
            logger.warning(
                "Validation error",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "errors": exc.errors(),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation Error",
                    "detail": exc.errors(),
                    "message": "Request data validation failed",
                },
            )

        except SQLAlchemyError as exc:
            # Database errors
            logger.error(
                "Database error",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Database Error",
                    "message": "A database error occurred. Please try again later.",
                },
            )

        except ValueError as exc:
            # Value errors (often from validation)
            logger.warning(
                "Value error",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid Value",
                    "message": str(exc),
                },
            )

        except PermissionError as exc:
            # Permission/authorization errors
            logger.warning(
                "Permission error",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Permission Denied",
                    "message": str(exc),
                },
            )

        except Exception as exc:
            # Catch-all for unexpected errors
            logger.error(
                "Unhandled exception",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc),
                    "type": type(exc).__name__,
                },
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Please contact support.",
                },
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP request/response details and manage request IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process a request, logging lifecycle details and timing.

        Args:
            request (Request): Incoming HTTP request.
            call_next (Callable): Next middleware or route handler.

        Returns:
            Response: Response augmented with request ID headers.
        """
        # Generate and set request ID
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        finally:
            # Clear request ID from context
            clear_request_id()


class RateLimitExceededError(Exception):
    """Custom exception raised when rate limit thresholds are exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        """Initialize the exception with a user-friendly message.

        Args:
            message (str): Description of the rate limit violation.

        Returns:
            None: The message is stored on the instance.
        """
        self.message = message
        super().__init__(self.message)
