"""Services for Lightweight Charts Backend.

This module contains the business logic layer that sits between the API
endpoints and the data models. Services handle:

- Data management and persistence
- Business rules and validation
- Complex operations and workflows
- Coordination between different components

The service layer ensures separation of concerns and makes the codebase
easier to test, maintain, and extend.
"""

# Local Imports
from lightweight_charts_pro_backend.services.datafeed import DatafeedService

# Public API for this module
__all__ = [
    "DatafeedService",  # Core service for managing chart data with chunking support
]
