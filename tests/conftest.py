"""Pytest configuration and reusable fixtures for backend tests."""

# Standard Imports

# Third Party Imports
import pytest

# Local Imports


@pytest.fixture
def sample_line_data():
    """Provide sample line series data.

    Returns:
        list[dict[str, int]]: Generated line data points.
    """
    return [{"time": i, "value": i * 100} for i in range(100)]


@pytest.fixture
def sample_candlestick_data():
    """Provide sample candlestick series data.

    Returns:
        list[dict[str, int]]: Generated candlestick OHLC data.
    """
    return [
        {
            "time": i,
            "open": 100 + i,
            "high": 105 + i,
            "low": 95 + i,
            "close": 102 + i,
        }
        for i in range(100)
    ]


@pytest.fixture
def large_dataset():
    """Provide a large dataset for chunking tests.

    Returns:
        list[dict[str, int]]: Large collection of line data points.
    """
    return [{"time": i, "value": i * 100} for i in range(1000)]


@pytest.fixture
def small_dataset():
    """Provide a small dataset that should not be chunked.

    Returns:
        list[dict[str, int]]: Compact line dataset below chunk threshold.
    """
    return [{"time": i, "value": i * 100} for i in range(100)]
