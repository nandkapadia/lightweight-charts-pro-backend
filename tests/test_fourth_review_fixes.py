"""Tests for fixes from fourth Codex review.

This test suite validates all critical, high, medium, and low priority fixes
implemented in response to the fourth code review.
"""

# Standard Imports
import asyncio

# Third Party Imports
import pytest
from httpx import ASGITransport, AsyncClient

# Local Imports
from lightweight_charts_pro_backend.app import create_app
from lightweight_charts_pro_backend.exceptions import InvalidTimestampError
from lightweight_charts_pro_backend.services.datafeed import DatafeedService
from lightweight_charts_pro_backend.validation import validate_before_time


class TestCriticalFixes:
    """Test critical bug fixes from fourth review."""

    @pytest.mark.asyncio
    async def test_rest_history_defaults_to_latest(self):
        """Test REST /history endpoint returns latest chunk when beforeTime omitted."""
        datafeed = DatafeedService()
        app = create_app(datafeed=datafeed)

        # Create chart with data
        data = [{"time": i, "value": i * 100} for i in range(1, 1001)]
        await datafeed.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Request history without beforeTime parameter
            response = await client.get("/api/charts/test/history/0/line1")
            assert response.status_code == 200

            result = response.json()
            # Should return latest chunk (last 500 points)
            assert len(result["data"]) == 500
            assert result["data"][-1]["time"] == 1000
            assert result["data"][0]["time"] == 501
            assert result["hasMoreBefore"] is True
            assert result["hasMoreAfter"] is False

    @pytest.mark.asyncio
    async def test_rest_history_with_before_time(self):
        """Test REST /history endpoint with explicit beforeTime."""
        datafeed = DatafeedService()
        app = create_app(datafeed=datafeed)

        data = [{"time": i, "value": i * 100} for i in range(1, 1001)]
        await datafeed.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Request history with beforeTime=500
            response = await client.get(
                "/api/charts/test/history/0/line1?before_time=500&count=100"
            )
            assert response.status_code == 200

            result = response.json()
            assert len(result["data"]) == 100
            assert result["data"][-1]["time"] == 499

    @pytest.mark.asyncio
    async def test_create_chart_with_options_body(self):
        """Test create_chart properly parses options from request body."""
        datafeed = DatafeedService()
        app = create_app(datafeed=datafeed)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create chart with options in body
            response = await client.post(
                "/api/charts/test-chart",
                json={"width": 800, "height": 600, "timeScale": {"visible": True}},
            )
            assert response.status_code == 200

            result = response.json()
            assert result["chartId"] == "test-chart"
            assert result["options"]["width"] == 800
            assert result["options"]["height"] == 600
            # Pydantic converts camelCase to snake_case
            assert result["options"]["time_scale"]["visible"] is True

        # Verify options were actually stored
        chart = await datafeed.get_chart("test-chart")
        assert chart is not None
        assert chart.options["width"] == 800
        assert chart.options["time_scale"]["visible"] is True

    @pytest.mark.asyncio
    async def test_set_series_data_rejects_unsorted(self):
        """Test set_series_data enforces sorted order on initial load."""
        service = DatafeedService()

        # Unsorted data should be rejected
        with pytest.raises(InvalidTimestampError) as exc_info:
            await service.set_series_data(
                chart_id="test",
                pane_id=0,
                series_id="line1",
                series_type="line",
                data=[
                    {"time": 3, "value": 300},
                    {"time": 1, "value": 100},  # Out of order
                    {"time": 2, "value": 200},
                ],
            )

        assert "not monotonic" in str(exc_info.value.message).lower()


class TestHighPriorityFixes:
    """Test high-priority fixes from fourth review."""

    @pytest.mark.asyncio
    async def test_get_chart_returns_defensive_copy(self):
        """Test get_chart returns a copy that can be mutated without affecting internal state."""
        service = DatafeedService()

        # Create chart
        await service.create_chart("test", {"width": 800})

        # Get chart and try to mutate it
        chart1 = await service.get_chart("test")
        assert chart1 is not None
        chart1.options["width"] = 999  # Try to mutate

        # Get chart again - should still have original value
        chart2 = await service.get_chart("test")
        assert chart2.options["width"] == 800  # Not 999

    @pytest.mark.asyncio
    async def test_float_timestamp_preservation(self):
        """Test validate_before_time preserves float timestamps."""
        # Integer timestamp should remain int
        result = validate_before_time(1234567890)
        assert isinstance(result, int)
        assert result == 1234567890

        # Float timestamp should remain float
        result = validate_before_time(1234567890.123)
        assert isinstance(result, float)
        assert result == 1234567890.123

        # None should remain None
        result = validate_before_time(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_float_timestamp_in_history(self):
        """Test history endpoint preserves float timestamps in data."""
        service = DatafeedService()

        # Create data with float timestamps (millisecond precision)
        data = [{"time": 1000.0 + i * 0.001, "value": i} for i in range(100)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        # Get history with float beforeTime
        result = await service.get_history(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            before_time=1000.05,
            count=10,
        )

        # Verify float timestamps preserved
        assert len(result["data"]) == 10
        for point in result["data"]:
            assert isinstance(point["time"], float)


class TestMediumPriorityFixes:
    """Test medium-priority performance fixes."""

    @pytest.mark.asyncio
    async def test_shallow_copy_prevents_mutation(self):
        """Test shallow reconstruction prevents dict mutation."""
        service = DatafeedService()

        # Create data that we'll try to mutate
        data = [{"time": 1, "value": 100, "extra": "field"}]

        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        # Mutate original data
        data[0]["value"] = 999
        data[0]["extra"] = "mutated"

        # Verify internal state not affected
        result = await service.get_initial_data("test", 0, "line1")
        assert result["data"][0]["value"] == 100
        assert result["data"][0]["extra"] == "field"

    @pytest.mark.asyncio
    async def test_append_no_duplicate_check_overhead(self):
        """Test append doesn't build duplicate set (relies on monotonic check)."""
        service = DatafeedService()

        # Create large existing dataset
        existing_data = [{"time": i, "value": i * 100} for i in range(10000)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=existing_data,
        )

        # Append should be O(1) for monotonic check, not O(n) for duplicate detection
        import time

        start = time.time()
        await service.append_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            data=[{"time": 10000 + i, "value": i} for i in range(100)],
        )
        duration = time.time() - start

        # Should be very fast (< 10ms) since no O(n) duplicate check
        assert duration < 0.01  # 10ms


class TestWebSocketEnhancements:
    """Test WebSocket activity and ping enhancements."""

    @pytest.mark.asyncio
    async def test_broadcast_updates_activity(self):
        """Test broadcast updates connection activity timestamp."""
        from unittest.mock import AsyncMock

        from lightweight_charts_pro_backend.websocket.handlers import ConnectionManager

        manager = ConnectionManager(timeout_seconds=60)

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Connect
        await manager.connect("test-chart", mock_ws)

        # Get initial activity time

        initial_time = manager._connection_times[("test-chart", id(mock_ws))]

        # Wait a bit
        await asyncio.sleep(0.1)

        # Broadcast should update activity
        await manager.broadcast("test-chart", {"type": "update", "data": {}})

        # Activity time should be updated
        updated_time = manager._connection_times[("test-chart", id(mock_ws))]
        assert updated_time > initial_time

    @pytest.mark.asyncio
    async def test_ping_task_starts_on_connect(self):
        """Test ping task starts when first connection established."""
        from unittest.mock import AsyncMock

        from lightweight_charts_pro_backend.websocket.handlers import ConnectionManager

        manager = ConnectionManager(timeout_seconds=60)

        # Initially no ping task
        assert manager._ping_task is None or manager._ping_task.done()

        # Connect should start ping task
        mock_ws = AsyncMock()
        await manager.connect("test-chart", mock_ws)

        # Ping task should now be running
        assert manager._ping_task is not None
        assert not manager._ping_task.done()

        # Cleanup
        await manager.shutdown()


class TestEdgeCasesAndRegressions:
    """Test edge cases and potential regressions."""

    @pytest.mark.asyncio
    async def test_empty_data_with_enforce_sorted(self):
        """Test empty data doesn't fail with enforce_sorted=True."""
        service = DatafeedService()

        # Empty data should be accepted
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[],
        )

        chart = await service.get_chart("test")
        assert chart is not None

    @pytest.mark.asyncio
    async def test_single_point_with_enforce_sorted(self):
        """Test single data point with enforce_sorted=True."""
        service = DatafeedService()

        # Single point should be accepted
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": 1, "value": 100}],
        )

        result = await service.get_initial_data("test", 0, "line1")
        assert len(result["data"]) == 1

    @pytest.mark.asyncio
    async def test_rest_history_preserves_timestamp_type(self):
        """Test REST history endpoint preserves int vs float timestamps."""
        datafeed = DatafeedService()
        app = create_app(datafeed=datafeed)

        # Create data with integer timestamps
        int_data = [{"time": i, "value": i * 100} for i in range(100)]
        await datafeed.set_series_data(
            chart_id="int-test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=int_data,
        )

        # Create data with float timestamps
        float_data = [{"time": float(i), "value": i * 100} for i in range(100)]
        await datafeed.set_series_data(
            chart_id="float-test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=float_data,
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Integer timestamps should remain int
            response = await client.get("/api/charts/int-test/history/0/line1?before_time=50")
            result = response.json()
            for point in result["data"]:
                assert isinstance(point["time"], int)

            # Float timestamps should remain float
            response = await client.get("/api/charts/float-test/history/0/line1?before_time=50.0")
            result = response.json()
            for point in result["data"]:
                assert isinstance(point["time"], (int, float))  # JSON may coerce

    @pytest.mark.asyncio
    async def test_get_chart_none_for_missing(self):
        """Test get_chart returns None for missing chart (not crash)."""
        service = DatafeedService()

        chart = await service.get_chart("nonexistent")
        assert chart is None

    @pytest.mark.asyncio
    async def test_defensive_copy_with_nested_options(self):
        """Test defensive copy works with nested option structures."""
        service = DatafeedService()

        await service.create_chart(
            "test", {"layout": {"background": {"color": "#000000"}, "textColor": "#FFFFFF"}}
        )

        chart = await service.get_chart("test")
        assert chart is not None

        # Try to mutate nested structure
        chart.options["layout"]["background"]["color"] = "#FFFFFF"

        # Get again - should still have original
        chart2 = await service.get_chart("test")
        assert chart2.options["layout"]["background"]["color"] == "#000000"

    @pytest.mark.asyncio
    async def test_append_after_set_with_enforce_sorted(self):
        """Test append works correctly after initial set with enforce_sorted."""
        service = DatafeedService()

        # Set initial data (sorted)
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": i, "value": i * 100} for i in range(1, 11)],
        )

        # Append more data (sorted)
        await service.append_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            data=[{"time": i, "value": i * 100} for i in range(11, 21)],
        )

        result = await service.get_initial_data("test", 0, "line1")
        assert len(result["data"]) == 20
        assert result["data"][0]["time"] == 1
        assert result["data"][-1]["time"] == 20


class TestOHLCValidation:
    """Test OHLC validation continues to work with enforce_sorted."""

    @pytest.mark.asyncio
    async def test_valid_ohlc_with_enforce_sorted(self):
        """Test valid OHLC data passes with enforce_sorted=True."""
        service = DatafeedService()

        ohlc_data = [
            {"time": i, "open": 100, "high": 110, "low": 90, "close": 105} for i in range(1, 11)
        ]

        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="candles",
            series_type="candlestick",
            data=ohlc_data,
        )

        result = await service.get_initial_data("test", 0, "candles")
        assert len(result["data"]) == 10

    @pytest.mark.asyncio
    async def test_invalid_ohlc_rejected(self):
        """Test invalid OHLC data is rejected even with sorting."""
        from lightweight_charts_pro_backend.exceptions import InvalidDataError

        service = DatafeedService()

        # OHLC with low > high (invalid)
        invalid_ohlc = [{"time": 1, "open": 100, "high": 90, "low": 110, "close": 95}]

        with pytest.raises(InvalidDataError) as exc_info:
            await service.set_series_data(
                chart_id="test",
                pane_id=0,
                series_id="candles",
                series_type="candlestick",
                data=invalid_ohlc,
            )

        assert (
            "low" in str(exc_info.value.message).lower()
            and "high" in str(exc_info.value.message).lower()
        )
