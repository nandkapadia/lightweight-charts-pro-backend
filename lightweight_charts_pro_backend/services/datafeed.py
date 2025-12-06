"""Datafeed service implementing smart chunking for chart data."""

# Standard Imports
import asyncio
import bisect
import copy
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict

# Local Imports
from lightweight_charts_pro_backend.exceptions import (
    ChartNotFoundError,
    InvalidTimestampError,
    SeriesNotFoundError,
)
from lightweight_charts_pro_backend.validation import validate_series_data

# Third Party Imports


logger = logging.getLogger(__name__)


class ChunkInfo(TypedDict):
    """Metadata describing a returned data chunk."""

    start_index: int
    end_index: int
    start_time: int
    end_time: int
    count: int


class DataChunk(TypedDict):
    """Container describing chart data and paging info."""

    data: list[dict[str, Any]]
    chunk_info: ChunkInfo
    has_more_before: bool
    has_more_after: bool
    total_available: int


@dataclass
class SeriesData:
    """Container for a single series payload and metadata."""

    series_id: str
    series_type: str
    data: list[dict[str, Any]] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    _sorted: bool = field(default=False, init=False)

    def get_data_range(self, start_time: int, end_time: int) -> list[dict[str, Any]]:
        """Return data points that fall within the provided time window.

        Uses binary search for O(log n) performance on large datasets.

        Args:
            start_time (int): Inclusive start timestamp.
            end_time (int): Inclusive end timestamp.

        Returns:
            list[dict[str, Any]]: Data points whose ``time`` field is in range.
        """
        if not self.data:
            return []

        # Ensure data is sorted
        self._ensure_sorted()

        # Use bisect for O(log n) range lookup instead of O(n) linear scan
        # bisect_left finds the insertion point (leftmost position for start_time)
        # bisect_right finds the insertion point (rightmost position for end_time)
        start_idx = bisect.bisect_left(self.data, start_time, key=lambda d: d["time"])
        end_idx = bisect.bisect_right(self.data, end_time, key=lambda d: d["time"])

        return self.data[start_idx:end_idx]

    def _ensure_sorted(self):
        """Ensure series data is sorted by ascending timestamp.

        Returns:
            None: Sorting occurs in place when needed.
        """
        # Only sort once to reduce cost when repeatedly serving slices
        if not self._sorted and self.data:
            # Use direct key access since data is validated to have 'time'
            self.data.sort(key=lambda d: d["time"])
            self._sorted = True

    def get_data_chunk(
        self,
        before_time: int | None = None,
        count: int = 500,
    ) -> DataChunk:
        """Return a chunk of series data for infinite-scroll history.

        Uses binary search for O(log n) performance instead of O(n) linear scan.

        Args:
            before_time (int | None): Timestamp boundary; when ``None`` the newest data
                is returned, otherwise slice data strictly before this time.
            count (int): Maximum number of records to include in the chunk.

        Returns:
            DataChunk: Dictionary containing data slice plus paging metadata.
        """
        # Short-circuit when no data exists to avoid unnecessary processing
        if not self.data:
            return DataChunk(
                data=[],
                chunk_info=ChunkInfo(
                    start_index=0,
                    end_index=0,
                    start_time=0,
                    end_time=0,
                    count=0,
                ),
                has_more_before=False,
                has_more_after=False,
                total_available=0,
            )

        # Ensure data is sorted (only sorts once)
        self._ensure_sorted()
        sorted_data = self.data

        if before_time is None:
            # Return latest data
            end_index = len(sorted_data)
            start_index = max(0, end_index - count)
        else:
            # Use bisect_left for O(log n) lookup instead of O(n) linear scan
            # Find the leftmost position where before_time could be inserted
            # This gives us the index of the first element >= before_time
            end_index = bisect.bisect_left(sorted_data, before_time, key=lambda d: d["time"])
            start_index = max(0, end_index - count)

        chunk_data = sorted_data[start_index:end_index]

        if chunk_data:
            start_time = chunk_data[0]["time"]
            end_time = chunk_data[-1]["time"]
        else:
            start_time = 0
            end_time = 0

        return DataChunk(
            data=chunk_data,
            chunk_info=ChunkInfo(
                start_index=start_index,
                end_index=end_index,
                start_time=start_time,
                end_time=end_time,
                count=len(chunk_data),
            ),
            has_more_before=start_index > 0,
            has_more_after=end_index < len(sorted_data),
            total_available=len(sorted_data),
        )


@dataclass
class ChartState:
    """State container holding panes and series for a single chart."""

    chart_id: str
    panes: dict[int, dict[str, SeriesData]] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    def get_series(self, pane_id: int, series_id: str) -> SeriesData | None:
        """Retrieve a specific series from the chart.

        Args:
            pane_id (int): Pane identifier within the chart layout.
            series_id (str): Unique series identifier.

        Returns:
            SeriesData | None: Matching series or ``None`` when missing.
        """
        if pane_id not in self.panes:
            return None
        return self.panes[pane_id].get(series_id)

    def set_series(self, pane_id: int, series_id: str, series: SeriesData) -> None:
        """Store a series inside the chart structure.

        Args:
            pane_id (int): Pane identifier to place the series in.
            series_id (str): Unique series identifier.
            series (SeriesData): Series payload to store.

        Returns:
            None: The chart state is updated in place.
        """
        # Ensure the pane container exists before assignment
        if pane_id not in self.panes:
            self.panes[pane_id] = {}
        # Save or overwrite the referenced series
        self.panes[pane_id][series_id] = series

    def get_all_series_data(self) -> dict[int, Any]:
        """Return all series data structured by pane for initial render.

        Returns:
            dict[int, Any]: Nested dictionary describing panes (keyed by int) and their series.
        """
        result: dict[int, Any] = {}

        for pane_id, series_dict in self.panes.items():
            pane_data: dict[str, Any] = {}
            for series_id, series in series_dict.items():
                pane_data[series_id] = {
                    "seriesType": series.series_type,
                    "data": series.data,
                    "options": series.options,
                }
            # Keep pane_id as integer for API consistency
            result[pane_id] = pane_data

        return result


class DatafeedService:
    """Service that manages chart data with chunked history retrieval."""

    def __init__(self, chunk_size_threshold: int = 500):
        """Initialize in-memory storage structures and locks.

        Args:
            chunk_size_threshold: Number of data points before chunking is applied.
                Below this threshold, all data is sent at once. Above it, data is
                chunked for pagination. Default is 500 points.

        Returns:
            None: Sets up internal state for the service instance.
        """
        # Configuration
        self.CHUNK_SIZE_THRESHOLD = chunk_size_threshold

        # Track chart state keyed by chart identifier
        self._charts: dict[str, ChartState] = {}
        # Track subscriber callbacks for each chart
        self._subscribers: dict[str, list[Callable]] = {}
        # Global lock guarding access to chart registry
        self._lock = asyncio.Lock()  # Only for charts dict access
        # Per-chart locks for fine-grained operations (currently unused)
        self._chart_locks: dict[str, asyncio.Lock] = {}  # Per-chart locks

    def _get_chart_lock(self, chart_id: str) -> asyncio.Lock:
        """Return a lock dedicated to a specific chart identifier.

        Args:
            chart_id (str): Unique chart identifier.

        Returns:
            asyncio.Lock: Async lock used to guard per-chart operations.
        """
        # Lazily create a lock so charts do not pay cost until first access
        if chart_id not in self._chart_locks:
            self._chart_locks[chart_id] = asyncio.Lock()
        return self._chart_locks[chart_id]

    async def get_chart(self, chart_id: str) -> ChartState | None:
        """Retrieve chart state by identifier.

        Returns a defensive copy to prevent external mutation of internal state.
        Uses per-chart locking to prevent race conditions during copy.

        Args:
            chart_id (str): Unique chart identifier.

        Returns:
            ChartState | None: Defensive copy of chart state if present, otherwise ``None``.
        """
        chart = self._charts.get(chart_id)
        if chart is None:
            return None

        # Use per-chart lock to prevent race conditions during deepcopy
        # A write operation could modify the chart while deepcopy is reading it
        chart_lock = self._get_chart_lock(chart_id)
        async with chart_lock:
            # Return a defensive copy to prevent callers from mutating internal state
            # This prevents bypassing validation by directly modifying chart.panes, etc.
            return copy.deepcopy(chart)

    async def create_chart(self, chart_id: str, options: dict | None = None) -> ChartState:
        """Create and register a new chart entry.

        Args:
            chart_id (str): Unique chart identifier.
            options (dict | None): Optional chart configuration options.

        Returns:
            ChartState: Created or existing chart state.
        """
        # Guard creation to avoid race conditions in concurrent requests
        async with self._lock:
            return self._create_chart_no_lock(chart_id, options)

    def _create_chart_no_lock(self, chart_id: str, options: dict | None = None) -> ChartState:
        """Create a chart without acquiring the global lock.

        This helper must only be invoked while the caller already holds ``_lock``.

        Args:
            chart_id (str): Unique chart identifier.
            options (dict | None): Optional chart configuration options.

        Returns:
            ChartState: Created or existing chart state.
        """
        # Return existing chart to keep operation idempotent
        if chart_id in self._charts:
            return self._charts[chart_id]

        # Build new ChartState and register it
        chart = ChartState(chart_id=chart_id, options=options or {})
        self._charts[chart_id] = chart
        return chart

    async def set_series_data(
        self,
        chart_id: str,
        pane_id: int,
        series_id: str,
        series_type: str,
        data: list[dict[str, Any]],
        options: dict | None = None,
    ) -> SeriesData:
        """Create or replace a series payload on a chart.

        Validates all timestamps and data points to prevent lookahead bias
        and data corruption in backtesting scenarios.

        Uses per-chart locking to allow concurrent operations on different charts.

        Args:
            chart_id (str): Chart identifier used as a namespace.
            pane_id (int): Pane index within the chart layout.
            series_id (str): Series identifier unique within the pane.
            series_type (str): Visual series type (for example, ``line`` or ``candlestick``).
            data (list[dict[str, Any]]): Collection of data points to store.
            options (dict | None): Optional series configuration options.

        Returns:
            SeriesData: Stored series data representation.

        Raises:
            InvalidTimestampError: When any timestamp is invalid or missing.
            InvalidDataError: When required fields are missing or contain NaN/invalid values.
            DuplicateTimestampError: When duplicate timestamps are detected.
        """
        # Validate data BEFORE acquiring lock to fail fast and avoid blocking
        # Use enforce_sorted=True to fail fast on unsorted data (prevents lookahead bias)
        validated_data = validate_series_data(
            data, series_type, check_duplicates=True, enforce_sorted=True
        )

        # Shallow defensive copy: reconstruct list and dicts to prevent mutation
        # More efficient than deepcopy while still protecting against external changes
        # We only need to copy the immediate container and dicts (not nested objects)
        validated_data_copy = [dict(point.items()) for point in validated_data]

        # Defensive copy for options to prevent external mutation
        options_copy = copy.deepcopy(options) if options else {}

        # Use per-chart lock to allow concurrent updates to different charts
        chart_lock = self._get_chart_lock(chart_id)
        async with chart_lock:
            chart = self._charts.get(chart_id)
            if not chart:
                # Create chart if it doesn't exist (requires global lock briefly)
                async with self._lock:
                    if chart_id not in self._charts:
                        chart = self._create_chart_no_lock(chart_id)
                    else:
                        chart = self._charts[chart_id]

            series = SeriesData(
                series_id=series_id,
                series_type=series_type,
                data=validated_data_copy,
                options=options_copy,
            )
            # Sort data once when setting
            series._ensure_sorted()
            chart.set_series(pane_id, series_id, series)

            # Prepare notification data while holding lock
            notification_data = {
                "paneId": pane_id,
                "seriesId": series_id,
                "count": len(validated_data),
            }

        # Notify subscribers OUTSIDE the lock to prevent blocking
        # This allows other operations to proceed while callbacks execute
        await self._notify_subscribers(chart_id, "data_update", notification_data)

        return series

    async def append_series_data(
        self,
        chart_id: str,
        pane_id: int,
        series_id: str,
        data: list[dict[str, Any]],
    ) -> SeriesData:
        """Append new data points to an existing series.

        This is optimized for incremental updates (e.g., adding new bars in live backtests)
        by validating only the new data and checking monotonic timestamp ordering.

        Uses per-chart locking to allow concurrent appends to different charts.

        Args:
            chart_id (str): Chart identifier.
            pane_id (int): Pane index.
            series_id (str): Series identifier.
            data (list[dict[str, Any]]): New data points to append.

        Returns:
            SeriesData: Updated series data representation.

        Raises:
            ChartNotFoundError: When the chart does not exist.
            SeriesNotFoundError: When the series does not exist.
            InvalidTimestampError: When timestamps are invalid or not monotonic.
            InvalidDataError: When required fields are missing or invalid.
        """
        chart = self._charts.get(chart_id)
        if not chart:
            raise ChartNotFoundError(chart_id)

        chart_lock = self._get_chart_lock(chart_id)
        async with chart_lock:
            series = chart.get_series(pane_id, series_id)
            if not series:
                raise SeriesNotFoundError(chart_id, pane_id, series_id)

            # Validate only the new data (not the entire series)
            # Use enforce_sorted=True to prevent lookahead bias from out-of-order batches
            validated_data = validate_series_data(
                data, series.series_type, check_duplicates=True, enforce_sorted=True
            )

            # Shallow defensive copy: reconstruct list and dicts
            # More efficient than deepcopy for OHLCV data (simple dicts with primitive values)
            validated_data_copy = [dict(point.items()) for point in validated_data]

            # Check monotonic ordering: first new timestamp must be > last existing timestamp
            # This, combined with enforce_sorted=True above, mathematically prevents duplicates:
            # - All new timestamps >= first_new_time (enforce_sorted)
            # - first_new_time > last_existing_time (monotonic check below)
            # - Therefore all new timestamps > last_existing_time
            # - Therefore no new timestamp can equal any existing timestamp (which are <= last_existing)
            if series.data and validated_data_copy:
                series._ensure_sorted()  # Ensure existing data is sorted

                last_existing_time = series.data[-1]["time"]
                first_new_time = validated_data_copy[0]["time"]

                if first_new_time <= last_existing_time:
                    raise InvalidTimestampError(
                        f"Cannot append data: first new timestamp {first_new_time} must be > "
                        f"last existing timestamp {last_existing_time}",
                        index=0,
                        value=first_new_time,
                    )

            # Append the new data (already sorted from validation)
            series.data.extend(validated_data_copy)

            # Prepare notification data
            notification_data = {
                "paneId": pane_id,
                "seriesId": series_id,
                "count": len(validated_data),
                "append": True,  # Flag to indicate this was an append operation
            }

        # Notify subscribers OUTSIDE the lock
        await self._notify_subscribers(chart_id, "data_update", notification_data)

        return series

    async def get_initial_data(
        self,
        chart_id: str,
        pane_id: int | None = None,
        series_id: str | None = None,
    ) -> dict[str, Any]:
        """Return initial chart payload using smart chunking.

        Implements smart chunking:
        - If total data < 500 points: Return all data
        - If total data >= 500 points: Return initial chunk

        Uses per-chart locking for read consistency.

        Args:
            chart_id (str): Chart identifier.
            pane_id (int | None): Optional pane identifier to scope the query.
            series_id (str | None): Optional series identifier to scope the query.

        Returns:
            dict[str, Any]: Payload containing series data and chunk metadata.

        Raises:
            ChartNotFoundError: When the requested chart does not exist.
            SeriesNotFoundError: When the requested series does not exist.
        """
        chart = self._charts.get(chart_id)
        if not chart:
            raise ChartNotFoundError(chart_id)

        # Use per-chart lock for read consistency
        chart_lock = self._get_chart_lock(chart_id)
        async with chart_lock:
            if pane_id is not None and series_id is not None:
                # Single series request
                series = chart.get_series(pane_id, series_id)
                if not series:
                    raise SeriesNotFoundError(chart_id, pane_id, series_id)

                total_count = len(series.data)

                if total_count < self.CHUNK_SIZE_THRESHOLD:
                    # Small dataset - send all
                    return {
                        "seriesId": series_id,
                        "seriesType": series.series_type,
                        "data": series.data,
                        "options": series.options,
                        "chunked": False,
                        "totalCount": total_count,
                    }
                # Large dataset - send initial chunk
                chunk = series.get_data_chunk(count=self.CHUNK_SIZE_THRESHOLD)
                # Build metadata to let callers know more history is available
                return {
                    "seriesId": series_id,
                    "seriesType": series.series_type,
                    "data": chunk["data"],
                    "options": series.options,
                    "chunked": True,
                    "chunkInfo": chunk["chunk_info"],
                    "hasMoreBefore": chunk["has_more_before"],
                    "hasMoreAfter": chunk["has_more_after"],
                    "totalCount": chunk["total_available"],
                }
            # Full chart data - apply chunking to prevent memory explosion
            # When no specific series is requested, include every pane and series
            # but chunk the data for each series to avoid sending 355M bars at once
            panes_list: list[dict[str, Any]] = []

            for pane_id, series_dict in chart.panes.items():
                series_list: list[dict[str, Any]] = []
                for series_id, series in series_dict.items():
                    total_count = len(series.data)

                    if total_count < self.CHUNK_SIZE_THRESHOLD:
                        # Small dataset - send all data
                        series_list.append(
                            {
                                "seriesId": series_id,
                                "seriesType": series.series_type,
                                "data": series.data,
                                "options": series.options,
                                "chunked": False,
                                "totalCount": total_count,
                            }
                        )
                    else:
                        # Large dataset - send chunked data
                        chunk = series.get_data_chunk(count=self.CHUNK_SIZE_THRESHOLD)
                        series_list.append(
                            {
                                "seriesId": series_id,
                                "seriesType": series.series_type,
                                "data": chunk["data"],
                                "options": series.options,
                                "chunked": True,
                                "chunkInfo": chunk["chunk_info"],
                                "hasMoreBefore": chunk["has_more_before"],
                                "hasMoreAfter": chunk["has_more_after"],
                                "totalCount": chunk["total_available"],
                            }
                        )

                panes_list.append(
                    {
                        "paneId": pane_id,
                        "series": series_list,
                    }
                )

            return {
                "chartId": chart_id,
                "panes": panes_list,
                "options": chart.options,
            }

    async def get_history(
        self,
        chart_id: str,
        pane_id: int,
        series_id: str,
        before_time: int | None = None,
        count: int = 500,
    ) -> dict[str, Any]:
        """Return a chunk of historical data for a specific series.

        Uses per-chart locking for read consistency.

        Args:
            chart_id (str): Chart identifier.
            pane_id (int): Pane index.
            series_id (str): Series identifier.
            before_time (int | None): Boundary timestamp to fetch data before.
                When None, returns the latest chunk of data (most recent).
            count (int): Maximum number of points to return.

        Returns:
            dict[str, Any]: Data slice plus pagination metadata.

        Raises:
            ChartNotFoundError: When the requested chart does not exist.
            SeriesNotFoundError: When the requested series does not exist.
        """
        chart = self._charts.get(chart_id)
        if not chart:
            raise ChartNotFoundError(chart_id)

        # Use per-chart lock for read consistency
        chart_lock = self._get_chart_lock(chart_id)
        async with chart_lock:
            series = chart.get_series(pane_id, series_id)
            if not series:
                raise SeriesNotFoundError(chart_id, pane_id, series_id)

            # Slice the dataset using the helper to honor before_time/count
            chunk = series.get_data_chunk(before_time=before_time, count=count)

            return {
                "seriesId": series_id,
                "data": chunk["data"],
                "chunkInfo": chunk["chunk_info"],
                "hasMoreBefore": chunk["has_more_before"],
                "hasMoreAfter": chunk["has_more_after"],
                "totalCount": chunk["total_available"],
            }

    async def delete_chart(self, chart_id: str) -> bool:
        """Delete a chart and clean up all associated resources.

        Args:
            chart_id (str): Chart identifier to delete.

        Returns:
            bool: True if chart was deleted, False if it didn't exist.
        """
        async with self._lock:
            # Remove chart from registry
            chart_existed = chart_id in self._charts
            if chart_existed:
                self._charts.pop(chart_id, None)

            # Clean up subscribers
            self._subscribers.pop(chart_id, None)

            # Clean up per-chart lock to prevent memory leak
            self._chart_locks.pop(chart_id, None)

            return chart_existed

    async def subscribe(self, chart_id: str, callback: Callable) -> Callable[[], None]:
        """Register a callback to be notified of chart updates.

        Args:
            chart_id (str): Chart identifier to subscribe to.
            callback (Callable): Async callback invoked with ``event_type`` and ``data``.

        Returns:
            Callable[[], None]: Async function that removes the subscription.
        """
        async with self._lock:
            if chart_id not in self._subscribers:
                self._subscribers[chart_id] = []
            self._subscribers[chart_id].append(callback)

        async def unsubscribe():
            async with self._lock:
                if chart_id in self._subscribers:
                    try:
                        self._subscribers[chart_id].remove(callback)
                    except ValueError:
                        pass  # Already removed

        return unsubscribe

    async def _notify_subscribers(
        self,
        chart_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Invoke all subscriber callbacks for a chart event.

        Runs callbacks in parallel using asyncio.gather to avoid blocking.
        Failed callbacks are isolated and logged without affecting others.

        Returns:
            None: Notifications are sent asynchronously to each subscriber.
        """
        # Create a snapshot of subscribers to prevent mutation during iteration
        # This prevents race conditions if unsubscribe is called during notification
        async with self._lock:
            subscribers_snapshot = list(self._subscribers.get(chart_id, []))

        if not subscribers_snapshot:
            return

        # Create tasks for all callbacks to run in parallel
        async def safe_callback(callback: Callable) -> None:
            """Wrapper to isolate callback errors."""
            try:
                await callback(event_type, data)
            except Exception:
                logger.exception("Callback error for %s", chart_id)

        # Run all callbacks concurrently with error isolation
        await asyncio.gather(
            *[safe_callback(cb) for cb in subscribers_snapshot], return_exceptions=True
        )
