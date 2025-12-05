"""Pydantic models for chart API requests and responses.

This module defines validation models using Pydantic for all chart-related
API requests and responses. These models ensure type safety, automatic
validation, and clear API documentation through FastAPI's integration
with Pydantic.
"""

# Standard Imports
from typing import Any

# Third Party Imports
from pydantic import BaseModel, Field, field_validator


class SetSeriesDataRequest(BaseModel):
    """Request model for setting series data on a chart.

    This model validates incoming requests to set or update series data
    on a chart. It supports multiple series types and allows optional
    configuration through the options field.

    Attributes:
        pane_id: Pane index where the series should be displayed.
            Defaults to 0 (main pane). Must be non-negative integer.
            Charts can have multiple panes for indicators, volume, etc.
        series_type: Type of series to create or update. Common types include
            'line', 'area', 'bar', 'candlestick', 'histogram', 'baseline'.
            This determines how the data is visually represented.
        data: List of data points for the series. Each data point should be
            a dictionary containing at minimum a 'time' key (Unix timestamp
            or date string) and a value key ('value' for line/area, 'open',
            'high', 'low', 'close' for candlestick, etc.).
        options: Optional configuration dictionary for series appearance and
            behavior. Can include color, line width, price format, etc.
            Structure depends on the series_type.

    Example:
        >>> request = SetSeriesDataRequest(
        ...     pane_id=0,
        ...     series_type="candlestick",
        ...     data=[
        ...         {"time": 1609459200, "open": 100, "high": 105, "low": 99, "close": 103},
        ...         {"time": 1609545600, "open": 103, "high": 108, "low": 102, "close": 107}
        ...     ],
        ...     options={"upColor": "#26a69a", "downColor": "#ef5350"}
        ... )
    """

    # Pane index - default to main pane (0), must be non-negative
    pane_id: int = Field(default=0, ge=0, description="Pane index")

    # Series type - required field that determines visualization type
    series_type: str = Field(..., min_length=1, description="Series type")

    # Data points - required field containing the actual chart data
    data: list[dict[str, Any]] = Field(..., description="Series data points")

    # Optional series configuration for customizing appearance and behavior
    options: dict[str, Any] | None = Field(default=None, description="Series options")

    @field_validator("series_type")
    @classmethod
    def validate_series_type(cls, v: str) -> str:
        """Validate series type is a known type.

        This validator checks if the provided series type is one of the
        standard TradingView Lightweight Charts series types. Unknown types
        are allowed for extensibility (custom series implementations).

        Args:
            v: The series type string to validate.

        Returns:
            str: The validated series type (unchanged).

        Note:
            This validator currently allows all types for extensibility.
            Future versions may add warnings for unknown types.
        """
        # Define the standard TradingView Lightweight Charts series types
        valid_types = {"line", "area", "bar", "candlestick", "histogram", "baseline"}

        # Check if the type is recognized (case-insensitive)
        if v.lower() not in valid_types:
            # Allow unknown types for extensibility (e.g., custom series)
            # In production, you might want to log a warning here
            pass

        return v


class GetHistoryRequest(BaseModel):
    """Request model for getting historical data chunks.

    This model is used for infinite history loading where the frontend
    requests additional historical data as the user scrolls back in time.
    It implements a pagination-like pattern for large datasets.

    Attributes:
        pane_id: Pane index where the series is displayed. Must be non-negative.
            This identifies which pane of the chart the series belongs to.
        series_id: Unique identifier for the series within the pane.
            Used to retrieve the correct data series from storage.
        before_time: Unix timestamp boundary for historical data request.
            Returns data points with timestamps strictly before this value.
            This enables "scroll back" functionality - as users scroll left,
            they request data before the earliest visible timestamp.
        count: Number of data points to return in this chunk.
            Defaults to 500 points. Maximum allowed is 10000 to prevent
            memory issues and ensure responsive API performance.

    Example:
        >>> # Request 500 data points before timestamp 1609459200
        >>> request = GetHistoryRequest(
        ...     pane_id=0,
        ...     series_id="main_series",
        ...     before_time=1609459200,
        ...     count=500
        ... )
    """

    # Pane index - required, must be non-negative
    pane_id: int = Field(..., ge=0, description="Pane index")

    # Series identifier - required, must be non-empty string
    series_id: str = Field(..., min_length=1, description="Series identifier")

    # Timestamp boundary - required, must be non-negative (Unix timestamp)
    before_time: int = Field(..., ge=0, description="Timestamp boundary")

    # Number of points to fetch - optional with sensible defaults
    # Default 500 is a good balance between network overhead and responsiveness
    count: int = Field(default=500, ge=1, le=10000, description="Number of points")


class ChartOptionsRequest(BaseModel):
    """Request model for chart creation and configuration options.

    This model defines optional configuration for creating or updating charts.
    All fields are optional to allow partial configuration updates. The options
    follow TradingView Lightweight Charts API structure.

    Attributes:
        width: Chart width in pixels. Must be between 100 and 10000 pixels.
            If not specified, the chart will use default or container width.
        height: Chart height in pixels. Must be between 100 and 10000 pixels.
            If not specified, the chart will use default or container height.
        layout: Layout configuration dictionary for chart appearance.
            Can include: background color, text color, font family, etc.
            Example: {"background": {"color": "#ffffff"}, "textColor": "#333"}
        crosshair: Crosshair configuration dictionary for the cursor behavior.
            Can include: mode (normal/magnet), vertical/horizontal line styles.
            Example: {"mode": 1, "vertLine": {"visible": True}}
        grid: Grid configuration dictionary for chart gridlines.
            Can include: vertical/horizontal line colors, styles, visibility.
            Example: {"vertLines": {"color": "#e1e1e1"}, "horzLines": {"color": "#e1e1e1"}}
        time_scale: Time scale (x-axis) configuration dictionary.
            Can include: time visible, seconds visible, border settings.
            Example: {"timeVisible": True, "secondsVisible": False}
            Note: Uses snake_case internally but accepts camelCase from JSON.

    Example:
        >>> options = ChartOptionsRequest(
        ...     width=800,
        ...     height=600,
        ...     layout={"background": {"color": "#ffffff"}, "textColor": "#333"},
        ...     timeScale={"timeVisible": True, "secondsVisible": False}
        ... )
    """

    # Chart dimensions - optional with sensible constraints
    width: int | None = Field(default=None, ge=100, le=10000)
    height: int | None = Field(default=None, ge=100, le=10000)

    # Visual configuration - all optional for flexibility
    layout: dict[str, Any] | None = None
    crosshair: dict[str, Any] | None = None
    grid: dict[str, Any] | None = None

    # Time scale configuration - uses alias for camelCase JSON compatibility
    time_scale: dict[str, Any] | None = Field(default=None, alias="timeScale")
