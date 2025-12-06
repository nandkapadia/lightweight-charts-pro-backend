"""WebSocket router for real-time chart updates and history retrieval."""

# Standard Imports

# Third Party Imports

# Local Imports
from lightweight_charts_pro_backend.websocket.handlers import router as websocket_router

# Public API for this module
__all__ = [
    "websocket_router",  # Router for WebSocket endpoint and connection handling
]
