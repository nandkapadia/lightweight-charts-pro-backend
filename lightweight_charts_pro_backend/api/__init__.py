"""API routers for Lightweight Charts Backend.

This module exports all FastAPI routers that define the REST API endpoints.
Each router groups related endpoints together for organization and modularity.

The routers are registered in the main application via app.include_router()
with appropriate prefixes and tags for clear API organization.
"""

# Local Imports
from lightweight_charts_pro_backend.api.charts import router as chart_router

# Public API for this module
__all__ = [
    "chart_router",  # Router for chart CRUD and data management endpoints
]
