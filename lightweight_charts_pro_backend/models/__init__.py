"""Pydantic models for Lightweight Charts Backend.

This module exports all Pydantic models used for request and response
validation in the API endpoints. These models provide:

- Automatic validation of incoming requests
- Type safety throughout the application
- Clear API documentation via FastAPI's OpenAPI integration
- Serialization/deserialization of JSON data

All models follow strict validation rules to ensure data integrity
and prevent common security issues.
"""

# Local Imports
from lightweight_charts_pro_backend.models.charts import (
    ChartOptionsRequest,
    GetHistoryRequest,
    SetSeriesDataRequest,
)

# Public API for this module
__all__ = [
    "SetSeriesDataRequest",  # Model for setting series data
    "GetHistoryRequest",  # Model for requesting historical data chunks
    "ChartOptionsRequest",  # Model for chart configuration options
]
