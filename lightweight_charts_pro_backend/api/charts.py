"""Chart API endpoints for data management.

This module provides REST API endpoints for managing chart data with the
TradingView Lightweight Charts backend. It includes endpoints for creating
charts, setting series data, and retrieving historical data with support
for infinite history loading through smart chunking.

All endpoints include comprehensive validation to prevent common security
issues like path traversal, injection attacks, and resource exhaustion.
"""

# Standard Imports
import re
from typing import Any

# Third Party Imports
from fastapi import APIRouter, Depends, HTTPException, Path, Request

# Local Imports
from lightweight_charts_pro_backend.models import GetHistoryRequest, SetSeriesDataRequest
from lightweight_charts_pro_backend.services import DatafeedService

# Create the FastAPI router that will be registered in the main app
router = APIRouter()

# Validation constants to prevent security issues and resource exhaustion
MAX_ID_LENGTH = 128  # Prevent excessively long identifiers that could cause memory issues
ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")  # Only allow safe characters in identifiers


def validate_identifier(value: str, field_name: str) -> str:
    r"""Validate an identifier (chart_id, series_id) for security and correctness.

    This function performs comprehensive validation to prevent security
    vulnerabilities like path traversal attacks and resource exhaustion
    from maliciously crafted identifiers.

    Args:
        value: The identifier string to validate.
        field_name: Name of the field being validated, used in error messages
            to provide clear feedback to API users.

    Returns:
        str: The validated identifier, unchanged if validation passes.

    Raises:
        HTTPException: With 400 status code if validation fails, including:
            - Empty identifier
            - Identifier too long (>128 chars)
            - Invalid characters (only alphanumeric, _, -, . allowed)
            - Path traversal attempts (.. or starting with / or \)

    Example:
        >>> validate_identifier("my_chart_123", "chart_id")
        "my_chart_123"
        >>> validate_identifier("../etc/passwd", "chart_id")
        # Raises HTTPException(status_code=400)

    Security Notes:
        - Prevents directory traversal attacks
        - Limits identifier length to prevent memory exhaustion
        - Uses whitelist approach (only safe characters allowed)
    """
    # Check for empty identifier - must have a value
    if not value:
        raise HTTPException(status_code=400, detail=f"{field_name} cannot be empty")

    # Prevent resource exhaustion from extremely long identifiers
    # Long strings could consume excessive memory or cause performance issues
    if len(value) > MAX_ID_LENGTH:
        raise HTTPException(
            status_code=400, detail=f"{field_name} cannot exceed {MAX_ID_LENGTH} characters"
        )

    # Use whitelist approach: only allow known-safe characters
    # This prevents injection attacks and ensures identifiers are URL-safe
    if not ID_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_name} contains invalid characters. "
                "Only alphanumeric, underscore, hyphen, and dot allowed."
            ),
        )

    # Prevent path traversal attacks that could access filesystem outside intended directory
    # ".." moves up directory tree, leading "/" or "\" indicates absolute path
    if ".." in value or value.startswith(("/", "\\")):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format")

    # All validation checks passed - return the identifier
    return value


def get_datafeed(request: Request) -> DatafeedService:
    """Get datafeed service from FastAPI application state.

    This is a FastAPI dependency function that retrieves the DatafeedService
    instance from the application state. It's used with FastAPI's dependency
    injection system to provide the service to endpoint handlers.

    Args:
        request: The FastAPI Request object containing app state.

    Returns:
        DatafeedService: The datafeed service instance for managing chart data.

    Note:
        This function is used as a dependency via FastAPI's Depends() mechanism.
        The datafeed service is initialized in app.py during application startup.

    Example:
        >>> @router.get("/endpoint")
        >>> async def endpoint(datafeed: DatafeedService = Depends(get_datafeed)):
        ...     # Use datafeed service
        ...     pass
    """
    return request.app.state.datafeed


@router.get("/{chart_id}")
async def get_chart(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Get full chart data including all series across all panes.

    This endpoint retrieves complete chart configuration and all series data.
    It's typically used for initial chart loading on the frontend.

    Args:
        chart_id: Unique chart identifier from the URL path.
            Must be 1-128 characters, alphanumeric with _, -, . allowed.
        datafeed: DatafeedService instance injected via FastAPI dependency.

    Returns:
        dict: Chart data structure containing:
            - chartId (str): The chart identifier
            - panes (dict): All panes with their series data
            - options (dict): Chart configuration options

    Raises:
        HTTPException: 404 if chart does not exist
        HTTPException: 400 if chart_id validation fails

    Example Response:
        {
            "chartId": "my_chart",
            "panes": {
                "0": {
                    "main": {
                        "seriesType": "candlestick",
                        "data": [...],
                        "options": {...}
                    }
                }
            },
            "options": {"width": 800, "height": 600}
        }
    """
    # Validate the chart_id to prevent security issues
    chart_id = validate_identifier(chart_id, "chart_id")

    # Check if chart exists before attempting to retrieve data
    chart = await datafeed.get_chart(chart_id)
    if not chart:
        # Return 404 if chart doesn't exist - standard REST convention
        raise HTTPException(status_code=404, detail="Chart not found")

    # Retrieve all chart data including all panes and series
    return await datafeed.get_initial_data(chart_id)


@router.post("/{chart_id}")
async def create_chart(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    options: dict[str, Any] | None = None,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Create a new chart.

    Args:
        chart_id: Unique chart identifier.
        options: Chart options.

    Returns:
        Created chart state.
    """
    chart_id = validate_identifier(chart_id, "chart_id")
    chart = await datafeed.create_chart(chart_id, options)
    return {
        "chartId": chart.chart_id,
        "options": chart.options,
    }


@router.get("/{chart_id}/data/{pane_id}/{series_id}")
async def get_series_data(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    pane_id: int = Path(..., ge=0, le=100),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Get data for a specific series.

    Uses smart chunking - small datasets return all data, large datasets
    return an initial chunk with metadata for pagination.

    Args:
        chart_id: Chart identifier.
        pane_id: Pane index.
        series_id: Series identifier.

    Returns:
        Series data with chunking metadata.
    """
    chart_id = validate_identifier(chart_id, "chart_id")
    series_id = validate_identifier(series_id, "series_id")

    result = await datafeed.get_initial_data(chart_id, pane_id, series_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/{chart_id}/data/{series_id}")
async def set_series_data(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    request: SetSeriesDataRequest = ...,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Set data for a series.

    Args:
        chart_id: Chart identifier.
        series_id: Series identifier.
        request: Series data and options.

    Returns:
        Updated series metadata.
    """
    chart_id = validate_identifier(chart_id, "chart_id")
    series_id = validate_identifier(series_id, "series_id")

    series = await datafeed.set_series_data(
        chart_id=chart_id,
        pane_id=request.pane_id,
        series_id=series_id,
        series_type=request.series_type,
        data=request.data,
        options=request.options,
    )

    return {
        "seriesId": series.series_id,
        "seriesType": series.series_type,
        "count": len(series.data),
    }


@router.get("/{chart_id}/history/{pane_id}/{series_id}")
async def get_history(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    pane_id: int = Path(..., ge=0, le=100),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    before_time: int = 0,
    count: int = 500,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Get historical data chunk for infinite history loading.

    This endpoint is called by the frontend when the user scrolls near the
    edge of the visible data range.

    Args:
        chart_id: Chart identifier.
        pane_id: Pane index.
        series_id: Series identifier.
        before_time: Get data before this timestamp.
        count: Number of data points to return.

    Returns:
        Data chunk with pagination metadata.
    """
    chart_id = validate_identifier(chart_id, "chart_id")
    series_id = validate_identifier(series_id, "series_id")

    # Validate input parameters
    if before_time < 0:
        raise HTTPException(status_code=400, detail="before_time must be >= 0")

    if count <= 0 or count > 10000:
        raise HTTPException(status_code=400, detail="count must be between 1 and 10000")

    result = await datafeed.get_history(
        chart_id=chart_id,
        pane_id=pane_id,
        series_id=series_id,
        before_time=before_time,
        count=count,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/{chart_id}/history")
async def get_history_batch(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    request: GetHistoryRequest = ...,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Get historical data for multiple series at once.

    Useful when loading history for all series in a pane together.

    Args:
        chart_id: Chart identifier.
        request: History request parameters.

    Returns:
        Data chunk with pagination metadata.
    """
    chart_id = validate_identifier(chart_id, "chart_id")

    # Pydantic model already validates before_time and count
    # Additional validation for series_id from request body
    validate_identifier(request.series_id, "series_id")

    return await datafeed.get_history(
        chart_id=chart_id,
        pane_id=request.pane_id,
        series_id=request.series_id,
        before_time=request.before_time,
        count=request.count,
    )
