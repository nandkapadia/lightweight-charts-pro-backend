"""Centralized validation logic for identifiers, timestamps, and data points.

This module consolidates validation logic used across REST and WebSocket handlers,
ensuring consistent behavior and preventing code duplication. All validators
use typed exceptions for clear error handling.
"""

import math
import re
from typing import Any

from lightweight_charts_pro_backend.exceptions import (
    DuplicateTimestampError,
    InvalidDataError,
    InvalidTimestampError,
    ValidationError,
)

# Validation constants
MAX_ID_LENGTH = 128
ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
MAX_HISTORY_COUNT = 10000


def validate_identifier(value: str | None, field_name: str) -> str:
    """Validate an identifier (chart_id, series_id, etc.) for security and correctness.

    Args:
        value: Identifier string to validate; may be None.
        field_name: Human-readable field name for error reporting.

    Returns:
        str: Validated identifier.

    Raises:
        ValidationError: When the identifier is None, empty, too long, contains
            unsafe characters, or attempts path traversal.
    """
    if value is None:
        raise ValidationError(f"{field_name} cannot be None", field=field_name)

    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} must be a string, got {type(value).__name__}", field=field_name
        )

    if not value:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)

    if len(value) > MAX_ID_LENGTH:
        raise ValidationError(
            f"{field_name} cannot exceed {MAX_ID_LENGTH} characters",
            field=field_name,
        )

    if not ID_PATTERN.match(value):
        raise ValidationError(
            f"{field_name} contains invalid characters. Only alphanumeric, underscore, hyphen, and dot allowed.",
            field=field_name,
        )

    # Prevent path traversal
    if ".." in value or value.startswith(("/", "\\")):
        raise ValidationError(
            f"Invalid {field_name} format - path traversal detected", field=field_name
        )

    return value


def validate_pane_id(value: int | None) -> int:
    """Validate the pane ID parameter.

    Args:
        value: Pane identifier to validate.

    Returns:
        int: Validated pane identifier; defaults to 0 when None.

    Raises:
        ValidationError: When paneId is not an integer or falls outside allowed range.
    """
    if value is None:
        return 0

    if not isinstance(value, int):
        raise ValidationError(
            f"paneId must be an integer, got {type(value).__name__}", field="paneId"
        )

    if value < 0 or value > 100:
        raise ValidationError("paneId must be between 0 and 100", field="paneId")

    return value


def validate_count(value: int | None) -> int:
    """Validate the count used when paging historical data.

    Args:
        value: Requested number of items.

    Returns:
        int: Validated count with default applied when None.

    Raises:
        ValidationError: When count is not an integer or outside valid range.
    """
    if value is None:
        return 500

    if not isinstance(value, int):
        raise ValidationError(
            f"count must be an integer, got {type(value).__name__}", field="count"
        )

    if value <= 0 or value > MAX_HISTORY_COUNT:
        raise ValidationError(f"count must be between 1 and {MAX_HISTORY_COUNT}", field="count")

    return value


def validate_before_time(value: int | float | None) -> int | float | None:
    """Validate the beforeTime parameter used for history pagination.

    Preserves the original numeric type (int or float) to avoid truncating
    millisecond/sub-second timestamps used in high-frequency data.

    Args:
        value: Timestamp value to validate.

    Returns:
        int | float | None: Validated timestamp preserving original type, or None when not provided.

    Raises:
        ValidationError: When the provided timestamp is invalid.
    """
    if value is None:
        return None

    if not isinstance(value, (int, float)):
        raise ValidationError(
            f"beforeTime must be a number, got {type(value).__name__}",
            field="beforeTime",
        )

    if value < 0:
        raise ValidationError("beforeTime must be >= 0", field="beforeTime")

    # For large datasets, ensure timestamp is within reasonable bounds (Unix epoch to year 2100)
    if value > 4102444800:  # Year 2100
        raise ValidationError("beforeTime exceeds maximum allowed timestamp", field="beforeTime")

    # Preserve original type - don't truncate float timestamps to int
    return value


def validate_timestamp(value: Any, index: int | None = None) -> int | float:
    """Validate a single timestamp value from a data point.

    This is critical for preventing lookahead bias in backtesting.
    Any invalid timestamp fails fast to avoid silent data corruption.

    Accepts both second and millisecond Unix timestamps, with automatic detection.
    Also accepts NumPy scalar types (int64, float64, etc.) commonly used in pandas.

    Args:
        value: Timestamp value to validate. Can be int, float, or NumPy scalar.
        index: Optional index of the data point for error reporting.

    Returns:
        int | float: Validated timestamp (normalized to seconds for consistency).

    Raises:
        InvalidTimestampError: When timestamp is missing, NaN, infinite, or invalid type.
    """
    if value is None:
        raise InvalidTimestampError(
            "Timestamp is None (missing required 'time' field)", index=index, value=value
        )

    # Accept NumPy scalar types (common from pandas DataFrames)
    try:
        import numpy as np

        if isinstance(value, np.generic):
            value = value.item()  # Convert to Python native type
    except ImportError:
        pass  # NumPy not installed, skip conversion

    # Accept int or float for timestamps
    if not isinstance(value, (int, float)):
        raise InvalidTimestampError(
            f"Timestamp must be numeric (int or float), got {type(value).__name__}",
            index=index,
            value=value,
        )

    # Check for NaN
    if isinstance(value, float) and math.isnan(value):
        raise InvalidTimestampError("Timestamp is NaN", index=index, value=value)

    # Check for infinity
    if isinstance(value, float) and math.isinf(value):
        raise InvalidTimestampError("Timestamp is infinite", index=index, value=value)

    # Validate reasonable range - handle both seconds and milliseconds
    if value < 0:
        raise InvalidTimestampError("Timestamp cannot be negative", index=index, value=value)

    # Auto-detect millisecond vs second timestamps
    # Millisecond timestamps are > year 2100 in seconds (4102444800)
    # But reasonable in milliseconds (< year 2286: 10000000000000)
    if value > 10000000000000:  # Year 2286 in milliseconds - unreasonable
        raise InvalidTimestampError(
            f"Timestamp {value} exceeds maximum allowed value (year 2286 in milliseconds)",
            index=index,
            value=value,
        )

    # Normalize milliseconds to seconds for internal consistency
    # Threshold: year 2100 in seconds = 4102444800
    # Any timestamp > this is assumed to be milliseconds
    if value > 4102444800:
        # Likely milliseconds - convert to seconds
        value = value / 1000.0

    return value


def validate_numeric_value(
    value: Any, field: str, index: int | None = None, allow_none: bool = False
) -> float | None:
    """Validate a numeric field (open, high, low, close, value, etc.).

    Accepts NumPy scalar types (int64, float64, etc.) commonly used in pandas DataFrames.

    Args:
        value: Numeric value to validate. Can be int, float, or NumPy scalar.
        field: Field name for error reporting.
        index: Optional index of the data point.
        allow_none: Whether to allow None values (for optional fields).

    Returns:
        float | None: Validated numeric value.

    Raises:
        InvalidDataError: When value is NaN, infinite, or invalid type.
    """
    if value is None:
        if allow_none:
            return None
        raise InvalidDataError(
            f"Field '{field}' is None (required field missing)", field=field, index=index
        )

    # Accept NumPy scalar types (common from pandas DataFrames)
    try:
        import numpy as np

        if isinstance(value, np.generic):
            value = value.item()  # Convert to Python native type
    except ImportError:
        pass  # NumPy not installed, skip conversion

    if not isinstance(value, (int, float)):
        raise InvalidDataError(
            f"Field '{field}' must be numeric, got {type(value).__name__}",
            field=field,
            index=index,
        )

    if isinstance(value, float) and math.isnan(value):
        raise InvalidDataError(f"Field '{field}' is NaN", field=field, index=index)

    if isinstance(value, float) and math.isinf(value):
        raise InvalidDataError(f"Field '{field}' is infinite", field=field, index=index)

    return float(value)


def validate_series_data(
    data: list[dict[str, Any]],
    series_type: str,
    check_duplicates: bool = True,
    enforce_sorted: bool = False,
) -> list[dict[str, Any]]:
    """Validate series data points for timestamp integrity and required fields.

    This function performs comprehensive validation to prevent lookahead bias
    and data corruption in backtesting scenarios.

    Args:
        data: List of data points to validate.
        series_type: Type of series (line, candlestick, etc.) to determine required fields.
        check_duplicates: Whether to check for duplicate timestamps (default True).
        enforce_sorted: Whether to enforce monotonic non-decreasing timestamps.
            If True, rejects out-of-order data instead of allowing silent reordering.
            Recommended for production backtests to catch data quality issues.

    Returns:
        list[dict[str, Any]]: Validated data (same as input if validation passes).

    Raises:
        InvalidTimestampError: When any timestamp is invalid or out of order (if enforce_sorted=True).
        InvalidDataError: When required fields are missing or invalid.
        DuplicateTimestampError: When duplicate timestamps are detected.
    """
    if not isinstance(data, list):
        raise InvalidDataError(f"data must be a list, got {type(data).__name__}")

    if not data:
        return data  # Empty data is allowed

    # Track timestamps for duplicate detection and ordering
    # Use dict to map timestamp -> first index seen for O(n) duplicate detection
    # Previously used O(n²) scan on duplicate found - now we track indices as we go
    seen_timestamps: dict[int | float, int] = {} if check_duplicates else {}
    last_timestamp: int | float | None = None

    # Define required fields by series type
    required_fields = _get_required_fields(series_type)

    for i, point in enumerate(data):
        if not isinstance(point, dict):
            raise InvalidDataError(
                f"Data point must be a dict, got {type(point).__name__}", index=i
            )

        # Validate timestamp (critical for preventing lookahead bias)
        time_value = point.get("time")
        validated_time = validate_timestamp(time_value, index=i)

        # Check monotonic ordering if enforce_sorted is enabled
        if enforce_sorted and last_timestamp is not None:
            if validated_time < last_timestamp:
                raise InvalidTimestampError(
                    f"Timestamps are not monotonic: {validated_time} < {last_timestamp}. "
                    "Data must be sorted in ascending order when enforce_sorted=True.",
                    index=i,
                    value=validated_time,
                )

        last_timestamp = validated_time

        # O(n) duplicate detection - track first index for each timestamp
        if check_duplicates:
            if validated_time in seen_timestamps:
                # Duplicate found - we know first index from dict, current is i
                first_index = seen_timestamps[validated_time]
                raise DuplicateTimestampError(timestamp=validated_time, indices=[first_index, i])
            seen_timestamps[validated_time] = i

        # Validate required fields based on series type
        for field in required_fields:
            if field == "time":
                continue  # Already validated
            value = point.get(field)
            validate_numeric_value(value, field, index=i, allow_none=False)

        # OHLC sanity checks for candlestick/bar series
        if series_type.lower() in ["candlestick", "bar"]:
            _validate_ohlc_sanity(point, i)

    return data


def _validate_ohlc_sanity(point: dict[str, Any], index: int) -> None:
    """Validate OHLC sanity checks for candlestick/bar data.

    Ensures that low <= open <= high and low <= close <= high.

    Args:
        point: Data point containing OHLC fields.
        index: Index of the data point for error reporting.

    Raises:
        InvalidDataError: When OHLC values violate sanity constraints.
    """
    open_val = point.get("open", 0)
    high_val = point.get("high", 0)
    low_val = point.get("low", 0)
    close_val = point.get("close", 0)

    # Check: low <= high
    if low_val > high_val:
        raise InvalidDataError(
            f"Invalid OHLC: low ({low_val}) > high ({high_val})",
            field="low/high",
            index=index,
        )

    # Check: low <= open <= high
    if not (low_val <= open_val <= high_val):
        raise InvalidDataError(
            f"Invalid OHLC: open ({open_val}) outside range [low={low_val}, high={high_val}]",
            field="open",
            index=index,
        )

    # Check: low <= close <= high
    if not (low_val <= close_val <= high_val):
        raise InvalidDataError(
            f"Invalid OHLC: close ({close_val}) outside range [low={low_val}, high={high_val}]",
            field="close",
            index=index,
        )


def _get_required_fields(series_type: str) -> list[str]:
    """Get required fields for a given series type.

    Args:
        series_type: The series type (line, candlestick, etc.).

    Returns:
        list[str]: List of required field names.
    """
    # Map series types to required fields
    required_fields_map = {
        "line": ["time", "value"],
        "area": ["time", "value"],
        "baseline": ["time", "value"],
        "histogram": ["time", "value"],
        "bar": ["time", "open", "high", "low", "close"],
        "candlestick": ["time", "open", "high", "low", "close"],
    }

    # Default to requiring time + value for unknown types
    return required_fields_map.get(series_type.lower(), ["time", "value"])
