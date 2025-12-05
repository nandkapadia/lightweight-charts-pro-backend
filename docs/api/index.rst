API Reference
=============

This section provides detailed API reference for all public interfaces.

REST API Endpoints
------------------

Charts API
~~~~~~~~~~

All endpoints are prefixed with ``/api/charts``.

GET /{chart_id}
^^^^^^^^^^^^^^^

Get full chart data including all series.

- **Parameters**: ``chart_id`` (string) - Unique chart identifier
- **Returns**: Chart data with all series and configuration
- **Status Codes**: 200 (Success), 404 (Chart not found)

POST /{chart_id}
^^^^^^^^^^^^^^^^

Create a new chart.

- **Parameters**: ``chart_id`` (string) - Unique chart identifier
- **Body**: ``options`` (object, optional) - Chart configuration options
- **Returns**: Created chart state
- **Status Codes**: 200 (Success), 400 (Invalid request)

GET /{chart_id}/data/{pane_id}/{series_id}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get data for a specific series with smart chunking.

- **Parameters**:
  - ``chart_id`` (string) - Chart identifier
  - ``pane_id`` (integer) - Pane index
  - ``series_id`` (string) - Series identifier
- **Returns**: Series data with chunking metadata
- **Status Codes**: 200 (Success), 404 (Chart or series not found)

POST /{chart_id}/data/{series_id}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set data for a series.

- **Parameters**:
  - ``chart_id`` (string) - Chart identifier
  - ``series_id`` (string) - Series identifier
- **Body**:
  - ``pane_id`` (integer) - Pane index (default: 0)
  - ``series_type`` (string) - Type of series (line, candlestick, etc.)
  - ``data`` (array) - Array of data points
  - ``options`` (object, optional) - Series configuration options
- **Returns**: Updated series metadata
- **Status Codes**: 200 (Success), 400 (Invalid request), 404 (Chart not found)

GET /{chart_id}/history/{pane_id}/{series_id}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get historical data chunk for infinite history loading.

- **Parameters**:
  - ``chart_id`` (string) - Chart identifier
  - ``pane_id`` (integer) - Pane index
  - ``series_id`` (string) - Series identifier
- **Query Parameters**:
  - ``before_time`` (integer) - Get data before this timestamp
  - ``count`` (integer) - Number of data points to return (default: 500)
- **Returns**: Data chunk with pagination metadata
- **Status Codes**: 200 (Success), 400 (Invalid parameters), 404 (Chart or series not found)

Health Endpoints
~~~~~~~~~~~~~~~~

GET /health
^^^^^^^^^^^

Basic health check endpoint for liveness probes.

- **Returns**: ``{"status": "healthy", "version": "0.1.0"}``
- **Status Codes**: 200 (Success)

GET /health/ready
^^^^^^^^^^^^^^^^^

Readiness check that verifies DatafeedService is functional.

- **Returns**: Detailed health status with service checks
- **Status Codes**: 200 (Ready), 503 (Degraded)

WebSocket API
-------------

WS /ws/charts/{chart_id}
~~~~~~~~~~~~~~~~~~~~~~~~

WebSocket endpoint for real-time chart updates.

- **Parameters**: ``chart_id`` (string) - Chart identifier

**Supported Message Types:**

- ``request_history`` - Request historical data chunk
- ``get_initial_data`` - Request initial data for a series
- ``ping`` - Connection health check

**Example Messages:**

Request history::

    {
      "type": "request_history",
      "paneId": 0,
      "seriesId": "main",
      "beforeTime": 1609459200,
      "count": 500
    }

Get initial data::

    {
      "type": "get_initial_data",
      "paneId": 0,
      "seriesId": "main"
    }

Ping::

    {
      "type": "ping"
    }

Response Types
~~~~~~~~~~~~~~

The WebSocket server sends the following message types:

- ``connected`` - Connection acknowledgment
- ``initial_data_response`` - Response with initial series data
- ``history_response`` - Response with historical data chunk
- ``data_update`` - Real-time data update notification
- ``error`` - Error message
- ``pong`` - Response to ping
