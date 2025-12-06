"""Chart API endpoints for data management.

This module provides REST API endpoints for managing chart data with the
TradingView Lightweight Charts backend. It includes endpoints for creating
charts, setting series data, and retrieving historical data with support
for infinite history loading through smart chunking.

All endpoints include comprehensive validation to prevent common security
issues like path traversal, injection attacks, and resource exhaustion.
"""

# Standard Imports

# Third Party Imports
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request

# Local Imports
from lightweight_charts_pro_backend.exceptions import DatafeedException, ValidationError
from lightweight_charts_pro_backend.models import (
    AppendSeriesDataRequest,
    ChartOptionsRequest,
    GetHistoryRequest,
    SetSeriesDataRequest,
)
from lightweight_charts_pro_backend.services import DatafeedService
from lightweight_charts_pro_backend.validation import (
    MAX_ID_LENGTH,
    validate_before_time,
    validate_count,
    validate_identifier,
)

# Create the FastAPI router that will be registered in the main app
router = APIRouter()


def get_datafeed(request: Request) -> DatafeedService:
    """Retrieve the configured datafeed service from application state.

    Args:
        request (Request): Incoming FastAPI request carrying the app state.

    Returns:
        DatafeedService: Datafeed service instance used by route handlers.
    """
    return request.app.state.datafeed


@router.get("/{chart_id}")
async def get_chart(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Retrieve full chart data including all panes and series.

    Args:
        chart_id (str): Chart identifier from the path parameter.
        datafeed (DatafeedService): Datafeed service injected via dependency.

    Returns:
        dict: Chart data including chart ID, panes with series data, and options.

    Raises:
        HTTPException: Raised with appropriate status code when errors occur.
    """
    try:
        # Validate the chart_id to prevent security issues
        chart_id = validate_identifier(chart_id, "chart_id")

        # Check if chart exists before attempting to retrieve data
        chart = await datafeed.get_chart(chart_id)
        if not chart:
            # Return 404 if chart doesn't exist - standard REST convention
            raise HTTPException(status_code=404, detail="Chart not found")

        # Retrieve all chart data including all panes and series
        return await datafeed.get_initial_data(chart_id)
    except DatafeedException as e:
        # Convert typed exceptions to HTTP responses
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/{chart_id}")
async def create_chart(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    options: ChartOptionsRequest | None = Body(None),
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Create a new chart entry.

    Args:
        chart_id (str): Unique chart identifier.
        options (ChartOptionsRequest | None): Optional validated chart options from request body.
        datafeed (DatafeedService): Injected datafeed service managing chart storage.

    Returns:
        dict: Created chart ID and stored options.

    Raises:
        HTTPException: Raised with appropriate status code when validation fails.
    """
    try:
        chart_id = validate_identifier(chart_id, "chart_id")
        # Convert Pydantic model to dict, excluding None values
        options_dict = options.model_dump(exclude_none=True) if options else {}
        chart = await datafeed.create_chart(chart_id, options_dict)
        return {
            "chartId": chart.chart_id,
            "options": chart.options,
        }
    except (DatafeedException, ValidationError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{chart_id}/data/{pane_id}/{series_id}")
async def get_series_data(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    pane_id: int = Path(..., ge=0, le=100),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Get series data with smart chunking support.

    Args:
        chart_id (str): Chart identifier from path.
        pane_id (int): Pane index to query.
        series_id (str): Series identifier to fetch.
        datafeed (DatafeedService): Injected datafeed service instance.

    Returns:
        dict: Series data payload with chunk metadata when applicable.

    Raises:
        HTTPException: Raised with appropriate status code when errors occur.
    """
    try:
        chart_id = validate_identifier(chart_id, "chart_id")
        series_id = validate_identifier(series_id, "series_id")
        return await datafeed.get_initial_data(chart_id, pane_id, series_id)
    except (DatafeedException, ValidationError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/{chart_id}/data/{series_id}")
async def set_series_data(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    request: SetSeriesDataRequest = ...,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Create or update series data on a chart.

    Validates timestamps and data to prevent lookahead bias in backtesting.

    Args:
        chart_id (str): Chart identifier.
        series_id (str): Series identifier within the chart.
        request (SetSeriesDataRequest): Validated payload containing series details.
        datafeed (DatafeedService): Injected datafeed service instance.

    Returns:
        dict: Series metadata including identifier, type, and total count.

    Raises:
        HTTPException: Raised with appropriate status code when validation or data errors occur.
    """
    try:
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
    except (DatafeedException, ValidationError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{chart_id}/data/{series_id}")
async def append_series_data(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    request: AppendSeriesDataRequest = ...,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Append new data points to an existing series (incremental update).

    This endpoint is optimized for live/streaming scenarios where you want to
    add new bars without resending the entire dataset. It validates monotonic
    timestamp ordering to prevent lookahead bias.

    Args:
        chart_id (str): Chart identifier.
        series_id (str): Series identifier within the chart.
        request (SetSeriesDataRequest): Payload containing new data points to append.
        datafeed (DatafeedService): Injected datafeed service instance.

    Returns:
        dict: Series metadata including identifier, type, and total count.

    Raises:
        HTTPException: Raised with appropriate status code when validation or ordering errors occur.
    """
    try:
        chart_id = validate_identifier(chart_id, "chart_id")
        series_id = validate_identifier(series_id, "series_id")

        series = await datafeed.append_series_data(
            chart_id=chart_id,
            pane_id=request.pane_id,
            series_id=series_id,
            data=request.data,
        )

        return {
            "seriesId": series.series_id,
            "seriesType": series.series_type,
            "count": len(series.data),
        }
    except (DatafeedException, ValidationError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{chart_id}/history/{pane_id}/{series_id}")
async def get_history(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    pane_id: int = Path(..., ge=0, le=100),
    series_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    before_time: int | None = None,
    count: int = 500,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Return a chunk of historical data for a series.

    When before_time is omitted, returns the latest chunk (most recent data).
    When before_time is provided, returns data before that timestamp.

    Args:
        chart_id (str): Chart identifier.
        pane_id (int): Pane index.
        series_id (str): Series identifier.
        before_time (int): Timestamp boundary to fetch data before.
        count (int): Maximum number of items to fetch.
        datafeed (DatafeedService): Injected datafeed service instance.

    Returns:
        dict: Data chunk with pagination metadata.

    Raises:
        HTTPException: Raised with appropriate status code when errors occur.
    """
    try:
        chart_id = validate_identifier(chart_id, "chart_id")
        series_id = validate_identifier(series_id, "series_id")
        validated_before_time = validate_before_time(before_time)
        validated_count = validate_count(count)

        return await datafeed.get_history(
            chart_id=chart_id,
            pane_id=pane_id,
            series_id=series_id,
            before_time=validated_before_time,  # Pass None through to get latest chunk
            count=validated_count,
        )
    except (DatafeedException, ValidationError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/{chart_id}/history")
async def get_history_batch(
    chart_id: str = Path(..., min_length=1, max_length=MAX_ID_LENGTH),
    request: GetHistoryRequest = ...,
    datafeed: DatafeedService = Depends(get_datafeed),
):
    """Get historical data for a series using POST body parameters.

    Args:
        chart_id (str): Chart identifier from the path parameter.
        request (GetHistoryRequest): Validated history request payload.
        datafeed (DatafeedService): Injected datafeed service instance.

    Returns:
        dict: Data chunk including pagination metadata.

    Raises:
        HTTPException: Raised with appropriate status code when errors occur.
    """
    try:
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
    except (DatafeedException, ValidationError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
