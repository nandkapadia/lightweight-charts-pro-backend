API Reference
=============

This section provides detailed API reference for all public interfaces.

Endpoints
---------

REST API Endpoints
~~~~~~~~~~~~~~~~~~

Charts API
^^^^^^^^^^

.. http:get:: /api/charts/{chart_id}

   Get full chart data including all series.

   :param chart_id: Unique chart identifier
   :type chart_id: string
   :statuscode 200: Success
   :statuscode 404: Chart not found

.. http:post:: /api/charts/{chart_id}

   Create a new chart.

   :param chart_id: Unique chart identifier
   :type chart_id: string
   :reqjson object options: Chart configuration options
   :statuscode 200: Chart created successfully
   :statuscode 400: Invalid request

.. http:get:: /api/charts/{chart_id}/data/{pane_id}/{series_id}

   Get data for a specific series with smart chunking.

   :param chart_id: Chart identifier
   :param pane_id: Pane index
   :param series_id: Series identifier
   :statuscode 200: Success
   :statuscode 404: Chart or series not found

.. http:post:: /api/charts/{chart_id}/data/{series_id}

   Set data for a series.

   :param chart_id: Chart identifier
   :param series_id: Series identifier
   :reqjson int pane_id: Pane index (default: 0)
   :reqjson string series_type: Type of series (line, candlestick, etc.)
   :reqjson array data: Array of data points
   :reqjson object options: Series configuration options
   :statuscode 200: Data set successfully
   :statuscode 400: Invalid request
   :statuscode 404: Chart not found

.. http:get:: /api/charts/{chart_id}/history/{pane_id}/{series_id}

   Get historical data chunk for infinite history loading.

   :param chart_id: Chart identifier
   :param pane_id: Pane index
   :param series_id: Series identifier
   :query int before_time: Get data before this timestamp
   :query int count: Number of data points to return (default: 500)
   :statuscode 200: Success
   :statuscode 400: Invalid parameters
   :statuscode 404: Chart or series not found

Health Endpoints
^^^^^^^^^^^^^^^^

.. http:get:: /health

   Basic health check endpoint for liveness probes.

   :statuscode 200: Service is alive

.. http:get:: /health/ready

   Readiness check that verifies DatafeedService is functional.

   :statuscode 200: Service is ready
   :statuscode 503: Service is degraded

WebSocket API
~~~~~~~~~~~~~

.. websocket:: /ws/charts/{chart_id}

   WebSocket endpoint for real-time chart updates.

   :param chart_id: Chart identifier

   **Supported Message Types:**

   * ``request_history``: Request historical data chunk
   * ``get_initial_data``: Request initial data for a series
   * ``ping``: Connection health check

   **Example Messages:**

   Request history:

   .. code-block:: json

      {
        "type": "request_history",
        "paneId": 0,
        "seriesId": "main",
        "beforeTime": 1609459200,
        "count": 500
      }

   Get initial data:

   .. code-block:: json

      {
        "type": "get_initial_data",
        "paneId": 0,
        "seriesId": "main"
      }

   Ping:

   .. code-block:: json

      {
        "type": "ping"
      }
