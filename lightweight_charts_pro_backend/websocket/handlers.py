"""WebSocket handlers for real-time chart updates."""

# Standard Imports
import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING

# Third Party Imports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Local Imports
from lightweight_charts_pro_backend.exceptions import DatafeedException, ValidationError
from lightweight_charts_pro_backend.validation import (
    validate_before_time,
    validate_count,
    validate_identifier,
    validate_pane_id,
)

if TYPE_CHECKING:
    from lightweight_charts_pro_backend.services import DatafeedService

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for chart updates."""

    def __init__(self, timeout_seconds: int = 300):
        """Initialize connection tracking structures and timeout settings.

        Args:
            timeout_seconds (int): Idle timeout before connections are cleaned up.

        Returns:
            None: The manager initializes internal tracking structures.
        """
        self._connections: dict[str, set[WebSocket]] = {}
        self._connection_times: dict[tuple[str, int], float] = {}  # (chart_id, ws_id) -> timestamp
        self._lock = asyncio.Lock()
        self._timeout_seconds = timeout_seconds
        self._cleanup_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._ping_interval_seconds = 30  # Send pings every 30 seconds

    async def connect(self, chart_id: str, websocket: WebSocket) -> None:
        """Accept and track a new WebSocket connection.

        Args:
            chart_id (str): Chart identifier for the connection.
            websocket (WebSocket): Incoming WebSocket connection object.

        Returns:
            None: Connection is accepted and tracked internally.
        """
        await websocket.accept()
        async with self._lock:
            if chart_id not in self._connections:
                self._connections[chart_id] = set()
            self._connections[chart_id].add(websocket)
            # Track last activity time for timeout cleanup
            self._connection_times[(chart_id, id(websocket))] = time.time()

        # Start cleanup task if not already running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())

        # Start ping task if not already running (keeps passive listeners alive)
        if self._ping_task is None or self._ping_task.done():
            self._ping_task = asyncio.create_task(self._send_periodic_pings())

    async def update_activity(self, chart_id: str, websocket: WebSocket) -> None:
        """Update last activity timestamp for a connection.

        Args:
            chart_id (str): Chart identifier for the connection.
            websocket (WebSocket): WebSocket connection to update.

        Returns:
            None: Activity timestamp is updated.
        """
        async with self._lock:
            self._connection_times[(chart_id, id(websocket))] = time.time()

    async def shutdown(self) -> None:
        """Gracefully shutdown the connection manager.

        Cancels the cleanup and ping tasks and closes all active connections.

        Returns:
            None: All resources are cleaned up.
        """
        # Cancel the cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled successfully")

        # Cancel the ping task
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                logger.info("Ping task cancelled successfully")

        # Close all active connections
        async with self._lock:
            all_connections = []
            for connections in self._connections.values():
                all_connections.extend(connections)

        for websocket in all_connections:
            try:
                await websocket.close(code=1001, reason="Server shutting down")
            except Exception as e:
                logger.warning(f"Error closing connection during shutdown: {e}")

        logger.info(f"Closed {len(all_connections)} WebSocket connections during shutdown")

    async def disconnect(self, chart_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from tracking.

        Args:
            chart_id (str): Chart identifier for the connection.
            websocket (WebSocket): WebSocket instance to remove.

        Returns:
            None: The connection is removed from internal registries.
        """
        async with self._lock:
            if chart_id in self._connections:
                self._connections[chart_id].discard(websocket)
                if not self._connections[chart_id]:
                    del self._connections[chart_id]
            # Clean up connection time tracking
            self._connection_times.pop((chart_id, id(websocket)), None)

    async def broadcast(self, chart_id: str, message: dict) -> None:
        """Broadcast a message to all connections for a chart.

        Args:
            chart_id (str): Chart identifier determining recipients.
            message (dict): JSON-serializable payload to send.

        Returns:
            None: Messages are sent to each tracked connection.
        """
        async with self._lock:
            if chart_id not in self._connections:
                return
            # Copy set to avoid modification during iteration
            connections = self._connections[chart_id].copy()

        disconnected = set()
        for websocket in connections:
            try:
                await websocket.send_json(message)
                # Update activity timestamp on successful send to prevent passive listeners from timing out
                async with self._lock:
                    self._connection_times[(chart_id, id(websocket))] = time.time()
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                # Expected disconnection errors
                logger.debug("Client disconnected during broadcast: %s", e)
                disconnected.add(websocket)
            except Exception as e:
                # Unexpected errors - log but continue
                logger.warning("Unexpected error broadcasting to client: %s", e)
                disconnected.add(websocket)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for websocket in disconnected:
                    if chart_id in self._connections:
                        self._connections[chart_id].discard(websocket)
                    # Clean up connection time tracking
                    self._connection_times.pop((chart_id, id(websocket)), None)

    async def _cleanup_stale_connections(self) -> None:
        """Close stale WebSocket connections exceeding idle timeout.

        Returns:
            None: Stale connections are closed on a periodic schedule.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                current_time = time.time()
                stale_connections = []

                async with self._lock:
                    # Find stale connections
                    for (chart_id, ws_id), connect_time in list(self._connection_times.items()):
                        if current_time - connect_time > self._timeout_seconds:
                            # Find the websocket object
                            if chart_id in self._connections:
                                for ws in self._connections[chart_id]:
                                    if id(ws) == ws_id:
                                        stale_connections.append((chart_id, ws))
                                        break

                # Close stale connections outside the lock
                for chart_id, websocket in stale_connections:
                    try:
                        await websocket.close(code=1000, reason="Connection timeout")
                        logger.info(f"Closed stale WebSocket connection for chart {chart_id}")
                    except Exception as e:
                        logger.warning(f"Error closing stale connection: {e}")
                    finally:
                        await self.disconnect(chart_id, websocket)

            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", exc_info=True)

    async def _send_periodic_pings(self) -> None:
        """Send periodic ping messages to keep connections alive.

        This prevents passive listeners (read-only clients) from being
        incorrectly closed as "stale" when they only receive broadcasts.

        Returns:
            None: Pings are sent on a periodic schedule.
        """
        while True:
            try:
                await asyncio.sleep(self._ping_interval_seconds)

                # Get all active connections
                async with self._lock:
                    all_connections = []
                    for chart_id, connections in self._connections.items():
                        for ws in connections:
                            all_connections.append((chart_id, ws))

                # Send pings outside the lock to avoid blocking
                for chart_id, websocket in all_connections:
                    try:
                        await websocket.send_json({"type": "ping", "timestamp": time.time()})
                        # Update activity time so ping doesn't count as idle
                        async with self._lock:
                            self._connection_times[(chart_id, id(websocket))] = time.time()
                    except Exception as e:
                        # Connection probably dead, will be cleaned up by cleanup task
                        logger.debug(f"Failed to send ping to {chart_id}: {e}")

            except asyncio.CancelledError:
                logger.info("Ping task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in ping task: {e}", exc_info=True)


manager = ConnectionManager()


@router.websocket("/charts/{chart_id}")
async def chart_websocket(websocket: WebSocket, chart_id: str):
    """Handle WebSocket connections for streaming chart updates.

    Args:
        websocket (WebSocket): Active WebSocket connection from client.
        chart_id (str): Chart identifier extracted from the URL path.

    Returns:
        None: The coroutine manages the connection lifecycle.
    """
    # Validate chart_id before accepting connection
    try:
        chart_id = validate_identifier(chart_id, "chart_id")
    except (ValidationError, ValueError, TypeError) as e:
        await websocket.accept()
        error_msg = e.message if isinstance(e, ValidationError) else str(e)
        await websocket.close(code=1008, reason=error_msg)
        return

    await manager.connect(chart_id, websocket)

    # Safely access datafeed service from app state
    try:
        datafeed: DatafeedService = websocket.app.state.datafeed
    except AttributeError:
        logger.exception("DatafeedService not initialized in app.state")
        await websocket.close(code=1011, reason="Server configuration error")
        await manager.disconnect(chart_id, websocket)
        return

    # Subscribe to datafeed updates
    async def on_update(event_type: str, data: dict):
        await manager.broadcast(
            chart_id,
            {
                "type": event_type,
                "chartId": chart_id,
                **data,
            },
        )

    unsubscribe = await datafeed.subscribe(chart_id, on_update)

    try:
        # Send initial connection acknowledgment
        await websocket.send_json(
            {
                "type": "connected",
                "chartId": chart_id,
            }
        )

        while True:
            # Receive and process messages
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                # Update activity timestamp on every message to prevent timeout
                await manager.update_activity(chart_id, websocket)
            except json.JSONDecodeError as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": f"Invalid JSON: {e!s}",
                    }
                )
                continue

            msg_type = message.get("type")

            if msg_type == "request_history":
                # Handle history request with validation
                try:
                    pane_id = validate_pane_id(message.get("paneId"))
                    series_id = validate_identifier(message.get("seriesId"), "seriesId")
                    # beforeTime can be None (fetch latest) or 0 (fetch from beginning)
                    # Only validate if provided, otherwise use None to fetch latest
                    raw_before_time = message.get("beforeTime")
                    before_time = (
                        validate_before_time(raw_before_time)
                        if raw_before_time is not None
                        else None
                    )
                    count = validate_count(message.get("count"))

                    if series_id is not None:
                        result = await datafeed.get_history(
                            chart_id=chart_id,
                            pane_id=pane_id,
                            series_id=series_id,
                            before_time=before_time,  # Pass None through to get latest chunk
                            count=count,
                        )

                        await websocket.send_json(
                            {
                                "type": "history_response",
                                "chartId": chart_id,
                                "paneId": pane_id,
                                "seriesId": series_id,
                                **result,
                            }
                        )
                    else:
                        await websocket.send_json(
                            {"type": "error", "error": "seriesId is required"}
                        )
                except (ValidationError, DatafeedException) as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": e.message,
                            "errorCode": e.error_code,
                        }
                    )
                except (ValueError, TypeError) as e:
                    await websocket.send_json({"type": "error", "error": str(e)})

            elif msg_type == "get_initial_data":
                # Handle initial data request with validation
                # seriesId is optional - if omitted, returns whole chart or whole pane
                try:
                    # Validate paneId (defaults to 0 if None)
                    raw_pane_id = message.get("paneId")
                    pane_id = validate_pane_id(raw_pane_id) if raw_pane_id is not None else None

                    # Validate seriesId only if provided (optional)
                    raw_series_id = message.get("seriesId")
                    series_id = (
                        validate_identifier(raw_series_id, "seriesId") if raw_series_id else None
                    )

                    result = await datafeed.get_initial_data(
                        chart_id=chart_id,
                        pane_id=pane_id,
                        series_id=series_id,
                    )

                    await websocket.send_json(
                        {
                            "type": "initial_data_response",
                            "chartId": chart_id,
                            **result,
                        }
                    )
                except (ValidationError, DatafeedException) as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": e.message,
                            "errorCode": e.error_code,
                        }
                    )
                except (ValueError, TypeError) as e:
                    await websocket.send_json({"type": "error", "error": str(e)})

            elif msg_type == "ping":
                # Handle ping for connection health
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for chart %s", chart_id)
    finally:
        await manager.disconnect(chart_id, websocket)
        await unsubscribe()
