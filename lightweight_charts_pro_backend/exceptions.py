"""Typed exception hierarchy for consistent error handling across the application.

This module defines custom exceptions that map to specific HTTP status codes
and provide structured error responses. Using typed exceptions instead of
returning error dictionaries ensures compile-time safety and consistent
error handling across REST and WebSocket endpoints.
"""

from typing import Any


class DatafeedException(Exception):
    """Base exception for all datafeed-related errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code for REST endpoints (None for WebSocket).
        error_code: Machine-readable error code for client handling.
    """

    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        """Initialize datafeed exception with error details.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code (defaults to 500 if None).
            error_code: Optional machine-readable error code.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code or 500
        self.error_code = error_code or self.__class__.__name__


class ChartNotFoundError(DatafeedException):
    """Raised when a requested chart does not exist."""

    def __init__(self, chart_id: str):
        """Initialize chart not found error.

        Args:
            chart_id: The chart identifier that was not found.
        """
        super().__init__(
            message=f"Chart '{chart_id}' not found",
            status_code=404,
            error_code="CHART_NOT_FOUND",
        )
        self.chart_id = chart_id


class SeriesNotFoundError(DatafeedException):
    """Raised when a requested series does not exist."""

    def __init__(self, chart_id: str, pane_id: int, series_id: str):
        """Initialize series not found error.

        Args:
            chart_id: The chart identifier.
            pane_id: The pane index.
            series_id: The series identifier that was not found.
        """
        super().__init__(
            message=f"Series '{series_id}' not found in pane {pane_id} of chart '{chart_id}'",
            status_code=404,
            error_code="SERIES_NOT_FOUND",
        )
        self.chart_id = chart_id
        self.pane_id = pane_id
        self.series_id = series_id


class InvalidTimestampError(DatafeedException):
    """Raised when timestamp data is invalid, missing, or causes lookahead bias.

    This exception is critical for preventing lookahead bias in backtesting.
    Any data point with missing, NaN, or invalid timestamps must fail fast
    to avoid silent data corruption that would invalidate backtest results.
    """

    def __init__(self, message: str, index: int | None = None, value: Any | None = None):
        """Initialize invalid timestamp error.

        Args:
            message: Description of the timestamp validation failure.
            index: Optional index of the problematic data point.
            value: Optional problematic timestamp value for debugging.
        """
        detail = message
        if index is not None:
            detail += f" at index {index}"
        if value is not None:
            detail += f" (value: {value!r})"

        super().__init__(
            message=detail,
            status_code=400,
            error_code="INVALID_TIMESTAMP",
        )
        self.index = index
        self.value = value


class InvalidDataError(DatafeedException):
    """Raised when data points contain invalid values (NaN, missing required fields, etc.)."""

    def __init__(self, message: str, field: str | None = None, index: int | None = None):
        """Initialize invalid data error.

        Args:
            message: Description of the data validation failure.
            field: Optional field name that failed validation.
            index: Optional index of the problematic data point.
        """
        detail = message
        if field:
            detail += f" (field: {field})"
        if index is not None:
            detail += f" at index {index}"

        super().__init__(
            message=detail,
            status_code=400,
            error_code="INVALID_DATA",
        )
        self.field = field
        self.index = index


class DuplicateTimestampError(DatafeedException):
    """Raised when duplicate timestamps are detected in series data.

    For quantitative trading, duplicate timestamps can indicate data quality
    issues (e.g., duplicate bars from data provider, multiple exchanges).
    This exception enforces explicit handling rather than silent merging.
    """

    def __init__(self, timestamp: int | float, indices: list[int]):
        """Initialize duplicate timestamp error.

        Args:
            timestamp: The duplicated timestamp value.
            indices: List of indices where the timestamp appears.
        """
        super().__init__(
            message=f"Duplicate timestamp {timestamp} found at indices {indices}",
            status_code=400,
            error_code="DUPLICATE_TIMESTAMP",
        )
        self.timestamp = timestamp
        self.indices = indices


class ValidationError(DatafeedException):
    """Raised when input validation fails (invalid IDs, parameters, etc.)."""

    def __init__(self, message: str, field: str | None = None):
        """Initialize validation error.

        Args:
            message: Description of the validation failure.
            field: Optional field name that failed validation.
        """
        detail = message
        if field:
            detail = f"{field}: {message}"

        super().__init__(
            message=detail,
            status_code=400,
            error_code="VALIDATION_ERROR",
        )
        self.field = field
