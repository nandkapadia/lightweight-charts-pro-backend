"""WebSocket handlers for Lightweight Charts Backend.

This module provides real-time bidirectional communication between the
backend and frontend clients via WebSocket connections. Features include:

- Real-time data updates pushed to clients
- Historical data requests from clients
- Connection management and heartbeat
- Automatic reconnection handling
- Broadcasting to multiple connected clients

WebSocket connections enable live chart updates without polling,
reducing server load and improving user experience.
"""

# Local Imports
from lightweight_charts_pro_backend.websocket.handlers import router as websocket_router

# Public API for this module
__all__ = [
    "websocket_router",  # Router for WebSocket endpoint and connection handling
]
