"""Unit tests for the in-memory ``DatafeedService`` implementation."""

# Standard Imports

# Third Party Imports
import pytest

# Local Imports
from lightweight_charts_pro_backend.services.datafeed import (
    ChartState,
    DatafeedService,
    SeriesData,
)


class TestSeriesData:
    """Validate behaviors of the ``SeriesData`` container."""

    def test_creation(self):
        """Create a default series and confirm initial attributes.

        Returns:
            None: Assertions verify default values.
        """
        series = SeriesData(series_id="test", series_type="line")
        assert series.series_id == "test"
        assert series.series_type == "line"
        assert series.data == []
        assert series.options == {}

    def test_creation_with_data(self):
        """Create a series with seeded data and ensure it is stored.

        Returns:
            None: Assertions verify data length.
        """
        data = [{"time": 1, "value": 100}, {"time": 2, "value": 200}]
        series = SeriesData(series_id="test", series_type="line", data=data)
        assert len(series.data) == 2

    def test_get_data_range(self):
        """Fetch a subset of data bounded by timestamps.

        Returns:
            None: Assertions check returned values.
        """
        data = [
            {"time": 1, "value": 100},
            {"time": 2, "value": 200},
            {"time": 3, "value": 300},
            {"time": 4, "value": 400},
        ]
        series = SeriesData(series_id="test", series_type="line", data=data)
        result = series.get_data_range(2, 3)
        assert len(result) == 2
        assert result[0]["value"] == 200
        assert result[1]["value"] == 300

    def test_get_data_chunk_empty(self):
        """Return an empty chunk when the series has no data.

        Returns:
            None: Assertions ensure flags and counts are zeroed.
        """
        series = SeriesData(series_id="test", series_type="line")
        chunk = series.get_data_chunk()
        assert chunk["data"] == []
        assert chunk["has_more_before"] is False
        assert chunk["has_more_after"] is False
        assert chunk["total_available"] == 0

    def test_get_data_chunk_small_dataset(self):
        """Ensure small datasets are returned fully in a single chunk.

        Returns:
            None: Assertions check counts and flags.
        """
        data = [{"time": i, "value": i * 100} for i in range(10)]
        series = SeriesData(series_id="test", series_type="line", data=data)
        chunk = series.get_data_chunk(count=500)
        assert len(chunk["data"]) == 10
        assert chunk["has_more_before"] is False
        assert chunk["has_more_after"] is False
        assert chunk["total_available"] == 10

    def test_get_data_chunk_large_dataset(self):
        """Return a limited chunk from a large dataset.

        Returns:
            None: Assertions verify bounds and paging flags.
        """
        data = [{"time": i, "value": i * 100} for i in range(1000)]
        series = SeriesData(series_id="test", series_type="line", data=data)
        chunk = series.get_data_chunk(count=500)
        assert len(chunk["data"]) == 500
        assert chunk["has_more_before"] is True
        assert chunk["has_more_after"] is False
        assert chunk["total_available"] == 1000
        # Should return latest 500 points
        assert chunk["data"][0]["time"] == 500
        assert chunk["data"][-1]["time"] == 999

    def test_get_data_chunk_before_time(self):
        """Fetch a data chunk preceding a specified timestamp.

        Returns:
            None: Assertions confirm boundaries and flags.
        """
        data = [{"time": i, "value": i * 100} for i in range(1000)]
        series = SeriesData(series_id="test", series_type="line", data=data)
        chunk = series.get_data_chunk(before_time=500, count=100)
        assert len(chunk["data"]) == 100
        assert chunk["has_more_before"] is True
        assert chunk["has_more_after"] is True
        # Should return 100 points before time 500
        assert chunk["data"][-1]["time"] == 499

    def test_get_data_chunk_pagination(self):
        """Paginate sequentially through multiple data chunks.

        Returns:
            None: Assertions validate continuity between chunks.
        """
        data = [{"time": i, "value": i * 100} for i in range(100)]
        series = SeriesData(series_id="test", series_type="line", data=data)

        # Get first chunk (latest)
        chunk1 = series.get_data_chunk(count=30)
        assert len(chunk1["data"]) == 30
        assert chunk1["data"][-1]["time"] == 99

        # Get next chunk before first chunk
        first_time = chunk1["data"][0]["time"]
        chunk2 = series.get_data_chunk(before_time=first_time, count=30)
        assert len(chunk2["data"]) == 30
        assert chunk2["data"][-1]["time"] == first_time - 1


class TestChartState:
    """Validate pane and series management within ``ChartState``."""

    def test_creation(self):
        """Create a chart state and confirm default values.

        Returns:
            None: Assertions verify empty panes and options.
        """
        chart = ChartState(chart_id="test-chart")
        assert chart.chart_id == "test-chart"
        assert chart.panes == {}
        assert chart.options == {}

    def test_get_series_not_found(self):
        """Attempt to get a missing series and expect ``None``.

        Returns:
            None: Assertions verify missing series handling.
        """
        chart = ChartState(chart_id="test")
        assert chart.get_series(0, "missing") is None

    def test_set_and_get_series(self):
        """Store and retrieve a series within a chart state.

        Returns:
            None: Assertions validate retrieved data.
        """
        chart = ChartState(chart_id="test")
        series = SeriesData(series_id="line1", series_type="line")
        chart.set_series(0, "line1", series)

        retrieved = chart.get_series(0, "line1")
        assert retrieved is not None
        assert retrieved.series_id == "line1"

    def test_multiple_panes(self):
        """Store series across multiple panes and confirm isolation.

        Returns:
            None: Assertions ensure pane separation.
        """
        chart = ChartState(chart_id="test")
        series1 = SeriesData(series_id="main", series_type="candlestick")
        series2 = SeriesData(series_id="volume", series_type="histogram")

        chart.set_series(0, "main", series1)
        chart.set_series(1, "volume", series2)

        assert chart.get_series(0, "main") is not None
        assert chart.get_series(1, "volume") is not None
        assert chart.get_series(0, "volume") is None

    def test_get_all_series_data(self):
        """Aggregate all series data for initial render payloads.

        Returns:
            None: Assertions verify structure and content.
        """
        chart = ChartState(chart_id="test")
        data = [{"time": 1, "value": 100}]
        series = SeriesData(
            series_id="line1",
            series_type="line",
            data=data,
            options={"color": "red"},
        )
        chart.set_series(0, "line1", series)

        result = chart.get_all_series_data()
        assert 0 in result  # Pane IDs are now integers
        assert "line1" in result[0]
        assert result[0]["line1"]["seriesType"] == "line"
        assert result[0]["line1"]["data"] == data


class TestDatafeedService:
    """Validate public behaviors of ``DatafeedService``."""

    @pytest.fixture
    def service(self):
        """Create a fresh ``DatafeedService`` for each test case.

        Returns:
            DatafeedService: New service instance with empty state.
        """
        return DatafeedService()

    @pytest.mark.asyncio
    async def test_create_chart(self, service):
        """Create a chart and confirm options are stored.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions validate chart creation.
        """
        chart = await service.create_chart("test-chart", {"width": 800})
        assert chart.chart_id == "test-chart"
        assert chart.options == {"width": 800}

    @pytest.mark.asyncio
    async def test_create_chart_idempotent(self, service):
        """Create the same chart twice and ensure idempotency.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions confirm both references point to same chart.
        """
        chart1 = await service.create_chart("test-chart")
        chart2 = await service.create_chart("test-chart")
        assert chart1.chart_id == chart2.chart_id

    @pytest.mark.asyncio
    async def test_get_chart(self, service):
        """Retrieve an existing chart from the registry.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions confirm chart retrieval.
        """
        await service.create_chart("test-chart")
        chart = await service.get_chart("test-chart")
        assert chart is not None
        assert chart.chart_id == "test-chart"

    @pytest.mark.asyncio
    async def test_get_chart_not_found(self, service):
        """Attempt to retrieve a missing chart and expect ``None``.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions validate missing chart handling.
        """
        chart = await service.get_chart("missing")
        assert chart is None

    @pytest.mark.asyncio
    async def test_set_series_data(self, service):
        """Set series data on a chart and ensure metadata reflects it.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions confirm stored metadata.
        """
        data = [{"time": i, "value": i * 100} for i in range(10)]
        series = await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
            options={"color": "blue"},
        )
        assert series.series_id == "line1"
        assert len(series.data) == 10

    @pytest.mark.asyncio
    async def test_get_initial_data_small_dataset(self, service):
        """Return full dataset when under the chunk threshold.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions verify chunking flags.
        """
        # Small dataset (< 500 points)
        data = [{"time": i, "value": i * 100} for i in range(100)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        result = await service.get_initial_data("test", 0, "line1")
        assert result["chunked"] is False
        assert result["totalCount"] == 100
        assert len(result["data"]) == 100

    @pytest.mark.asyncio
    async def test_get_initial_data_large_dataset(self, service):
        """Chunk data when dataset exceeds threshold.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions check returned chunk.
        """
        # Large dataset (>= 500 points)
        data = [{"time": i, "value": i * 100} for i in range(1000)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        result = await service.get_initial_data("test", 0, "line1")
        assert result["chunked"] is True
        assert result["totalCount"] == 1000
        assert len(result["data"]) == 500
        assert result["hasMoreBefore"] is True
        assert result["hasMoreAfter"] is False

    @pytest.mark.asyncio
    async def test_get_initial_data_full_chart(self, service):
        """Return the full chart structure when requesting without series filters.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions validate aggregate payload.
        """
        data = [{"time": i, "value": i * 100} for i in range(10)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        result = await service.get_initial_data("test")
        assert result["chartId"] == "test"
        assert "panes" in result
        # Panes is now a list of pane objects with paneId field
        assert isinstance(result["panes"], list)
        assert len(result["panes"]) > 0
        assert result["panes"][0]["paneId"] == 0

    @pytest.mark.asyncio
    async def test_get_initial_data_chart_not_found(self, service):
        """Request initial data for a missing chart and expect an exception.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions confirm exception is raised.
        """
        from lightweight_charts_pro_backend.exceptions import ChartNotFoundError

        with pytest.raises(ChartNotFoundError) as exc_info:
            await service.get_initial_data("missing")

        assert exc_info.value.chart_id == "missing"

    @pytest.mark.asyncio
    async def test_get_history(self, service):
        """Retrieve a historical data chunk for a series.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions verify chunk metadata.
        """
        data = [{"time": i, "value": i * 100} for i in range(1000)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        result = await service.get_history(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            before_time=500,
            count=100,
        )

        assert len(result["data"]) == 100
        assert result["hasMoreBefore"] is True
        assert result["hasMoreAfter"] is True

    @pytest.mark.asyncio
    async def test_get_history_chart_not_found(self, service):
        """Request history for a missing chart and expect an exception.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions validate exception is raised.
        """
        from lightweight_charts_pro_backend.exceptions import ChartNotFoundError

        with pytest.raises(ChartNotFoundError) as exc_info:
            await service.get_history(
                chart_id="missing",
                pane_id=0,
                series_id="line1",
                before_time=500,
            )

        assert exc_info.value.chart_id == "missing"

    @pytest.mark.asyncio
    async def test_subscribe_and_notify(self, service):
        """Subscribe to chart updates and verify notifications trigger.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions confirm callback execution.
        """
        received_events = []

        async def callback(event_type, data):
            received_events.append((event_type, data))

        await service.create_chart("test")
        unsubscribe = await service.subscribe("test", callback)

        # Trigger update by setting data
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": 1, "value": 100}],
        )

        assert len(received_events) == 1
        assert received_events[0][0] == "data_update"

        # Unsubscribe
        await unsubscribe()

    @pytest.mark.asyncio
    async def test_chunk_size_threshold(self, service):
        """Validate chunking threshold boundaries.

        Args:
            service (DatafeedService): Fresh service fixture.

        Returns:
            None: Assertions validate behavior around threshold edges.
        """
        assert service.CHUNK_SIZE_THRESHOLD == 500

        # Test boundary conditions
        data_499 = [{"time": i, "value": i} for i in range(499)]
        await service.set_series_data(
            chart_id="test1",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data_499,
        )
        result = await service.get_initial_data("test1", 0, "line1")
        assert result["chunked"] is False

        data_500 = [{"time": i, "value": i} for i in range(500)]
        await service.set_series_data(
            chart_id="test2",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data_500,
        )
        result = await service.get_initial_data("test2", 0, "line1")
        assert result["chunked"] is True
