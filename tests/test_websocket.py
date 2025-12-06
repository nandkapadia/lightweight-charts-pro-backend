"""Integration tests for WebSocket connection handling."""

# Standard Imports

# Third Party Imports
import pytest
from fastapi.testclient import TestClient

# Local Imports
from lightweight_charts_pro_backend.app import create_app
from lightweight_charts_pro_backend.websocket.handlers import ConnectionManager


class TestConnectionManager:
    """Validate connection tracking logic within ``ConnectionManager``."""

    def test_creation(self):
        """Ensure a new manager starts with empty connection tracking.

        Returns:
            None: Assertions verify initial state.
        """
        manager = ConnectionManager()
        assert manager._connections == {}

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Connect and disconnect a WebSocket while tracking state.

        Returns:
            None: Assertions validate connection bookkeeping.
        """
        manager = ConnectionManager()

        # Mock websocket
        class MockWebSocket:
            accepted = False

            async def accept(self):
                self.accepted = True

        ws = MockWebSocket()
        await manager.connect("chart1", ws)
        assert ws.accepted
        assert "chart1" in manager._connections
        assert ws in manager._connections["chart1"]

        await manager.disconnect("chart1", ws)
        assert "chart1" not in manager._connections

    @pytest.mark.asyncio
    async def test_multiple_connections_same_chart(self):
        """Track multiple simultaneous connections to the same chart.

        Returns:
            None: Assertions validate connection counts per chart.
        """
        manager = ConnectionManager()

        class MockWebSocket:
            async def accept(self):
                pass

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("chart1", ws1)
        await manager.connect("chart1", ws2)

        assert len(manager._connections["chart1"]) == 2

        await manager.disconnect("chart1", ws1)
        assert len(manager._connections["chart1"]) == 1

        await manager.disconnect("chart1", ws2)
        assert "chart1" not in manager._connections

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Broadcast a message to all connected sockets for a chart.

        Returns:
            None: Assertions ensure each client receives the payload.
        """
        manager = ConnectionManager()

        received_messages = []

        class MockWebSocket:
            async def accept(self):
                pass

            async def send_json(self, message):
                received_messages.append(message)

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("chart1", ws1)
        await manager.connect("chart1", ws2)

        await manager.broadcast("chart1", {"type": "test", "data": "hello"})

        assert len(received_messages) == 2
        assert all(msg["type"] == "test" for msg in received_messages)

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self):
        """Ensure broadcast removes connections that raise errors.

        Returns:
            None: Assertions validate connection cleanup.
        """
        manager = ConnectionManager()

        class GoodWebSocket:
            async def accept(self):
                pass

            async def send_json(self, message):
                pass

        class BadWebSocket:
            async def accept(self):
                pass

            async def send_json(self, message):
                raise Exception("Connection closed")

        good_ws = GoodWebSocket()
        bad_ws = BadWebSocket()

        await manager.connect("chart1", good_ws)
        await manager.connect("chart1", bad_ws)

        assert len(manager._connections["chart1"]) == 2

        await manager.broadcast("chart1", {"type": "test"})

        # Bad websocket should be removed
        assert len(manager._connections["chart1"]) == 1
        assert good_ws in manager._connections["chart1"]
        assert bad_ws not in manager._connections["chart1"]

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        """Broadcast gracefully when no connections are registered.

        Returns:
            None: Assertions confirm no exceptions are raised.
        """
        manager = ConnectionManager()
        # Should not raise
        await manager.broadcast("chart1", {"type": "test"})


class TestWebSocketEndpoint:
    """Exercise WebSocket endpoint behavior through TestClient."""

    @pytest.fixture
    def client(self):
        """Create a FastAPI test client with WebSocket support.

        Returns:
            TestClient: Client configured for websocket connections.
        """
        app = create_app()
        return TestClient(app)

    def test_websocket_connect(self, client):
        """Connect to the WebSocket and receive an acknowledgment.

        Args:
            client (TestClient): Configured FastAPI test client.

        Returns:
            None: Assertions validate acknowledgment payload.
        """
        with client.websocket_connect("/ws/charts/test-chart") as websocket:
            # Should receive connection acknowledgment
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["chartId"] == "test-chart"

    def test_websocket_ping_pong(self, client):
        """Exchange ping/pong messages to confirm connection health.

        Args:
            client (TestClient): Configured FastAPI test client.

        Returns:
            None: Assertions verify ping/pong handshake.
        """
        with client.websocket_connect("/ws/charts/test-chart") as websocket:
            # Skip connection message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_get_initial_data(self, client):
        """Request initial series data via WebSocket message.

        Args:
            client (TestClient): Configured FastAPI test client.

        Returns:
            None: Assertions validate returned payload structure.
        """
        # First, set up some data via REST API
        client.post("/api/charts/test-chart")
        client.post(
            "/api/charts/test-chart/data/line1",
            json={
                "pane_id": 0,
                "series_type": "line",
                "data": [{"time": i, "value": i * 100} for i in range(10)],
            },
        )

        # Connect via WebSocket
        with client.websocket_connect("/ws/charts/test-chart") as websocket:
            # Skip connection message
            websocket.receive_json()

            # Request initial data
            websocket.send_json(
                {
                    "type": "get_initial_data",
                    "paneId": 0,
                    "seriesId": "line1",
                }
            )

            # Should receive initial data response
            data = websocket.receive_json()
            assert data["type"] == "initial_data_response"
            assert data["chartId"] == "test-chart"

    def test_websocket_request_history(self, client):
        """Request historical data over WebSocket and verify response.

        Args:
            client (TestClient): Configured FastAPI test client.

        Returns:
            None: Assertions confirm correct response fields.
        """
        # Set up data
        client.post("/api/charts/test-chart")
        client.post(
            "/api/charts/test-chart/data/line1",
            json={
                "pane_id": 0,
                "series_type": "line",
                "data": [{"time": i, "value": i * 100} for i in range(100)],
            },
        )

        with client.websocket_connect("/ws/charts/test-chart") as websocket:
            # Skip connection message
            websocket.receive_json()

            # Request history
            websocket.send_json(
                {
                    "type": "request_history",
                    "paneId": 0,
                    "seriesId": "line1",
                    "beforeTime": 50,
                    "count": 20,
                }
            )

            # Should receive history response
            data = websocket.receive_json()
            assert data["type"] == "history_response"
            assert data["chartId"] == "test-chart"
            assert data["seriesId"] == "line1"

    def test_multiple_websocket_connections(self, client):
        """Open multiple WebSocket connections to the same chart ID.

        Args:
            client (TestClient): Configured FastAPI test client.

        Returns:
            None: Assertions validate both connections respond to ping.
        """
        with client.websocket_connect("/ws/charts/test-chart") as ws1:
            ws1.receive_json()  # connection ack

            with client.websocket_connect("/ws/charts/test-chart") as ws2:
                ws2.receive_json()  # connection ack

                # Both should be able to ping
                ws1.send_json({"type": "ping"})
                ws2.send_json({"type": "ping"})

                assert ws1.receive_json()["type"] == "pong"
                assert ws2.receive_json()["type"] == "pong"
