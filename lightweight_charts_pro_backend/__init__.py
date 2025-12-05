"""Lightweight Charts Pro Backend - FastAPI backend for TradingView Lightweight Charts.

This package provides a production-ready REST API and WebSocket server for managing
TradingView Lightweight Charts data. It includes support for:

- Real-time data updates via WebSocket
- Infinite history loading with smart chunking
- Multiple chart panes and series types
- Efficient data management for large datasets
- Comprehensive request validation and security

The package is framework-agnostic and can be used with any frontend framework
(React, Vue, Svelte, etc.) or with Streamlit for rapid prototyping.

Example:
    >>> from lightweight_charts_pro_backend import create_app
    >>> import uvicorn
    >>> app = create_app()
    >>> uvicorn.run(app, host="0.0.0.0", port=8000)
"""

# Local Imports
from lightweight_charts_pro_backend.app import create_app
from lightweight_charts_pro_backend.services import DatafeedService

# Package version following semantic versioning
__version__ = "0.1.0"

# Public API - explicitly define what can be imported with "from package import *"
__all__ = [
    "create_app",  # Factory function to create FastAPI application
    "DatafeedService",  # Core service for managing chart data
    "__version__",  # Package version string
]
