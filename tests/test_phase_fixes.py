"""Tests for Phase 1-3 fixes from third Codex review."""

# Standard Imports

# Third Party Imports
import pytest

# Local Imports
from lightweight_charts_pro_backend.exceptions import (
    InvalidTimestampError,
)
from lightweight_charts_pro_backend.services.datafeed import DatafeedService


class TestPhase1CriticalFixes:
    """Test critical bug fixes from Phase 1."""

    @pytest.fixture
    def service(self):
        """Create a fresh DatafeedService for each test."""
        return DatafeedService()

    @pytest.mark.asyncio
    async def test_append_enforces_sorted_within_batch(self, service):
        """Verify append_series_data rejects out-of-order data within batch."""
        # Create initial series
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": 1, "value": 100}, {"time": 2, "value": 200}],
        )

        # Try to append unsorted batch - should fail with enforce_sorted=True
        with pytest.raises(InvalidTimestampError) as exc_info:
            await service.append_series_data(
                chart_id="test",
                pane_id=0,
                series_id="line1",
                data=[
                    {"time": 5, "value": 500},
                    {"time": 4, "value": 400},  # Out of order within batch
                    {"time": 6, "value": 600},
                ],
            )

        assert "not monotonic" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_append_prevents_backfilling_duplicates(self, service):
        """Verify append prevents backfilling (adding data before last timestamp).

        The monotonic check (first_new > last_existing) combined with enforce_sorted
        mathematically prevents duplicates:
        - Monotonic: all new timestamps > last existing
        - Enforce_sorted: all new timestamps are sorted
        - Therefore: no new timestamp can equal any existing timestamp

        This test verifies the monotonic check works correctly.
        """
        # Create initial series with gap
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[
                {"time": 1, "value": 100},
                {"time": 2, "value": 200},
                {"time": 5, "value": 500},  # Gap from 2 to 5
            ],
        )

        # Try to append data that would fill the gap (backfilling)
        # This fails the monotonic check: first_new_time (3) <= last_existing (5)
        with pytest.raises(InvalidTimestampError) as exc_info:
            await service.append_series_data(
                chart_id="test",
                pane_id=0,
                series_id="line1",
                data=[
                    {"time": 3, "value": 300},
                    {"time": 4, "value": 400},
                ],
            )

        assert "must be >" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_append_validates_monotonic_ordering(self, service):
        """Verify append fails when new data starts before last existing timestamp."""
        # Create initial series
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[
                {"time": 1, "value": 100},
                {"time": 5, "value": 500},  # Gap to 5
            ],
        )

        # Try to append data that fills the gap - should fail
        with pytest.raises(InvalidTimestampError) as exc_info:
            await service.append_series_data(
                chart_id="test",
                pane_id=0,
                series_id="line1",
                data=[
                    {"time": 3, "value": 300},  # Fills gap but <= last timestamp
                    {"time": 4, "value": 400},
                ],
            )

        assert "must be >" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_append_sorted_batch_succeeds(self, service):
        """Verify append_series_data accepts properly sorted batch."""
        # Create initial series
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": 1, "value": 100}, {"time": 2, "value": 200}],
        )

        # Append sorted batch - should succeed
        series = await service.append_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            data=[
                {"time": 3, "value": 300},
                {"time": 4, "value": 400},
                {"time": 5, "value": 500},
            ],
        )

        assert len(series.data) == 5
        assert series.data[-1]["time"] == 5


class TestPhase2HighPriorityFixes:
    """Test high-priority fixes from Phase 2."""

    @pytest.fixture
    def service(self):
        """Create a fresh DatafeedService for each test."""
        return DatafeedService()

    @pytest.mark.asyncio
    async def test_history_defaults_to_latest_when_none(self, service):
        """Verify get_history returns latest chunk when before_time=None."""
        # Create series with 1000 points
        data = [{"time": i, "value": i * 100} for i in range(1000)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        # Request history with before_time=None
        result = await service.get_history(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            before_time=None,
            count=100,
        )

        # Should return latest 100 points
        assert len(result["data"]) == 100
        assert result["data"][-1]["time"] == 999
        assert result["data"][0]["time"] == 900
        assert result["hasMoreBefore"] is True
        assert result["hasMoreAfter"] is False

    @pytest.mark.asyncio
    async def test_full_chart_payload_chunked(self, service):
        """Verify full-chart payload applies chunking to large datasets."""
        # Create large series (>= 500 points)
        data = [{"time": i, "value": i * 100} for i in range(1000)]
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        # Get full chart data (no pane_id or series_id specified)
        result = await service.get_initial_data("test")

        # Verify chunking is applied
        assert result["chartId"] == "test"
        # Panes is now a list format
        assert isinstance(result["panes"], list)
        assert len(result["panes"]) > 0
        assert result["panes"][0]["paneId"] == 0
        # Series is also a list now
        assert "series" in result["panes"][0]
        assert isinstance(result["panes"][0]["series"], list)
        assert len(result["panes"][0]["series"]) > 0

        series_data = result["panes"][0]["series"][0]
        assert series_data["seriesId"] == "line1"
        assert series_data["chunked"] is True
        assert len(series_data["data"]) == 500  # Should be chunked
        assert series_data["totalCount"] == 1000
        assert series_data["hasMoreBefore"] is True

    @pytest.mark.asyncio
    async def test_defensive_copy_prevents_mutation(self, service):
        """Verify defensive copying prevents external mutation."""
        # Create data array that we'll try to mutate later
        data = [{"time": 1, "value": 100}, {"time": 2, "value": 200}]
        list(data)  # Keep reference to original

        # Set series data
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=data,
        )

        # Mutate the original input array
        data.append({"time": 3, "value": 300})
        data[0]["value"] = 999

        # Verify internal state was not affected
        result = await service.get_initial_data("test", 0, "line1")
        stored_data = result["data"]

        assert len(stored_data) == 2  # Should still be 2 (not 3)
        assert stored_data[0]["value"] == 100  # Should still be 100 (not 999)


class TestPhase3MediumPriorityFixes:
    """Test medium-priority fixes from Phase 3."""

    @pytest.fixture
    def service(self):
        """Create a fresh DatafeedService for each test."""
        return DatafeedService()

    @pytest.mark.asyncio
    async def test_delete_chart_cleans_up_locks(self, service):
        """Verify delete_chart removes chart lock from registry."""
        # Create chart
        await service.create_chart("test")

        # Access lock to ensure it's created
        service._get_chart_lock("test")
        assert "test" in service._chart_locks

        # Delete chart
        deleted = await service.delete_chart("test")
        assert deleted is True

        # Verify lock was cleaned up
        assert "test" not in service._chart_locks
        assert "test" not in service._charts

    @pytest.mark.asyncio
    async def test_delete_nonexistent_chart_returns_false(self, service):
        """Verify delete_chart returns False for non-existent chart."""
        deleted = await service.delete_chart("missing")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_subscriber_snapshot_prevents_mutation(self, service):
        """Verify subscriber list is snapshotted before notification."""
        # Create chart
        await service.create_chart("test")

        callback_count = 0

        async def callback1(event_type, data):
            nonlocal callback_count
            callback_count += 1

        async def callback2(event_type, data):
            nonlocal callback_count
            callback_count += 1

        # Subscribe both callbacks
        unsubscribe1 = await service.subscribe("test", callback1)
        await service.subscribe("test", callback2)

        # Set data to trigger notification
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": 1, "value": 100}],
        )

        # Both callbacks should have been called
        assert callback_count == 2

        # Unsubscribe one and set more data
        await unsubscribe1()
        callback_count = 0

        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[{"time": 2, "value": 200}],
        )

        # Only one callback should be called now
        assert callback_count == 1


class TestEdgeCases:
    """Test edge cases and corner cases."""

    @pytest.fixture
    def service(self):
        """Create a fresh DatafeedService for each test."""
        return DatafeedService()

    @pytest.mark.asyncio
    async def test_append_to_empty_series(self, service):
        """Verify appending to empty series works correctly."""
        # Create empty series
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            series_type="line",
            data=[],
        )

        # Append data to empty series
        series = await service.append_series_data(
            chart_id="test",
            pane_id=0,
            series_id="line1",
            data=[{"time": 1, "value": 100}, {"time": 2, "value": 200}],
        )

        assert len(series.data) == 2

    @pytest.mark.asyncio
    async def test_full_chart_with_multiple_panes(self, service):
        """Verify full-chart chunking works with multiple panes."""
        # Create multiple series in different panes
        await service.set_series_data(
            chart_id="test",
            pane_id=0,
            series_id="main",
            series_type="candlestick",
            data=[
                {"time": i, "open": i, "high": i + 1, "low": i - 1, "close": i}
                for i in range(1, 600)
            ],
        )

        await service.set_series_data(
            chart_id="test",
            pane_id=1,
            series_id="volume",
            series_type="histogram",
            data=[{"time": i, "value": i * 1000} for i in range(1, 600)],
        )

        # Get full chart
        result = await service.get_initial_data("test")

        # Verify both panes have chunked data (panes is now a list)
        assert isinstance(result["panes"], list)
        assert len(result["panes"]) == 2

        # Find pane 0 and pane 1
        pane_0 = next(p for p in result["panes"] if p["paneId"] == 0)
        pane_1 = next(p for p in result["panes"] if p["paneId"] == 1)

        # Verify pane 0 has "main" series
        main_series = next(s for s in pane_0["series"] if s["seriesId"] == "main")
        assert main_series["chunked"] is True
        assert len(main_series["data"]) == 500

        # Verify pane 1 has "volume" series
        volume_series = next(s for s in pane_1["series"] if s["seriesId"] == "volume")
        assert volume_series["chunked"] is True
        assert len(volume_series["data"]) == 500
