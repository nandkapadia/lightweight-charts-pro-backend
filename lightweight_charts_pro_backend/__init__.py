"""FastAPI backend package for delivering TradingView Lightweight Charts data.

This package bundles REST and WebSocket capabilities, datafeed management, and
production-ready configuration helpers to serve chart data to various frontends.
"""

# Standard Imports

# Third Party Imports

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
