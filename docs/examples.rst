Examples
========

This section provides practical examples of using the Lightweight Charts Pro Backend.

Basic Server Setup
------------------

Create a basic server with default configuration:

.. code-block:: python

   from lightweight_charts_pro_backend import create_app
   import uvicorn

   # Create the application
   app = create_app()

   # Run the server
   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8000)

Custom Configuration
--------------------

Create a server with custom CORS origins and custom datafeed:

.. code-block:: python

   from lightweight_charts_pro_backend import create_app, DatafeedService
   import uvicorn

   # Create a custom datafeed instance
   datafeed = DatafeedService()

   # Create app with custom configuration
   app = create_app(
       datafeed=datafeed,
       cors_origins=[
           "http://localhost:3000",
           "http://localhost:5173",
           "https://myapp.com"
       ],
       title="My Trading Charts API",
       version="1.0.0"
   )

   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8000)

Setting Chart Data
------------------

Using the DatafeedService directly:

.. code-block:: python

   from lightweight_charts_pro_backend import DatafeedService
   import asyncio

   async def main():
       # Create datafeed service
       datafeed = DatafeedService()

       # Create a chart
       chart = await datafeed.create_chart("my_chart")

       # Prepare candlestick data
       candlestick_data = [
           {"time": 1609459200, "open": 100, "high": 105, "low": 99, "close": 103},
           {"time": 1609545600, "open": 103, "high": 108, "low": 102, "close": 107},
           {"time": 1609632000, "open": 107, "high": 110, "low": 105, "close": 109},
       ]

       # Set series data
       await datafeed.set_series_data(
           chart_id="my_chart",
           pane_id=0,
           series_id="main",
           series_type="candlestick",
           data=candlestick_data,
           options={
               "upColor": "#26a69a",
               "downColor": "#ef5350",
               "borderVisible": False,
           }
       )

       # Get initial data
       initial_data = await datafeed.get_initial_data("my_chart")
       print(initial_data)

   if __name__ == "__main__":
       asyncio.run(main())

Working with Large Datasets
----------------------------

The backend automatically handles chunking for large datasets:

.. code-block:: python

   from lightweight_charts_pro_backend import DatafeedService
   import asyncio

   async def main():
       datafeed = DatafeedService()

       # Create chart and add large dataset (10000 points)
       large_dataset = [
           {"time": i * 60, "value": 100 + (i % 100) / 10}
           for i in range(10000)
       ]

       await datafeed.set_series_data(
           chart_id="large_chart",
           pane_id=0,
           series_id="main",
           series_type="line",
           data=large_dataset
       )

       # Get initial data - automatically returns chunked data
       initial_data = await datafeed.get_initial_data(
           "large_chart",
           pane_id=0,
           series_id="main"
       )

       # Check if data is chunked
       if initial_data.get("chunked"):
           print(f"Data is chunked. Total points: {initial_data['totalCount']}")
           print(f"Initial chunk size: {len(initial_data['data'])}")
           print(f"Has more data before: {initial_data['hasMoreBefore']}")

       # Get historical chunk
       if initial_data.get("hasMoreBefore"):
           chunk_info = initial_data["chunkInfo"]
           history = await datafeed.get_history(
               chart_id="large_chart",
               pane_id=0,
               series_id="main",
               before_time=chunk_info["start_time"],
               count=500
           )
           print(f"Historical chunk size: {len(history['data'])}")

   if __name__ == "__main__":
       asyncio.run(main())

WebSocket Client Example
-------------------------

JavaScript client connecting to the WebSocket endpoint:

.. code-block:: javascript

   const ws = new WebSocket('ws://localhost:8000/ws/charts/my_chart');

   ws.onopen = () => {
       console.log('Connected to chart websocket');

       // Request initial data
       ws.send(JSON.stringify({
           type: 'get_initial_data',
           paneId: 0,
           seriesId: 'main'
       }));
   };

   ws.onmessage = (event) => {
       const message = JSON.parse(event.data);

       switch (message.type) {
           case 'connected':
               console.log('Connection acknowledged');
               break;

           case 'initial_data_response':
               console.log('Received initial data:', message.data);
               break;

           case 'history_response':
               console.log('Received historical data:', message.data);
               break;

           case 'data_update':
               console.log('Data updated:', message);
               break;

           case 'error':
               console.error('Error:', message.error);
               break;
       }
   };

   // Request historical data when user scrolls
   function requestHistory(beforeTime) {
       ws.send(JSON.stringify({
           type: 'request_history',
           paneId: 0,
           seriesId: 'main',
           beforeTime: beforeTime,
           count: 500
       }));
   }

   // Send ping to keep connection alive
   setInterval(() => {
       ws.send(JSON.stringify({ type: 'ping' }));
   }, 30000);  // Every 30 seconds

Integration with FastAPI Dependencies
--------------------------------------

Using the datafeed service in your own FastAPI endpoints:

.. code-block:: python

   from fastapi import FastAPI, Depends, Request
   from lightweight_charts_pro_backend import create_app, DatafeedService

   # Create the base app
   app = create_app()

   # Dependency to get datafeed service
   def get_datafeed(request: Request) -> DatafeedService:
       return request.app.state.datafeed

   # Add your own custom endpoint
   @app.post("/api/custom/bulk-load")
   async def bulk_load_charts(
       chart_data: dict,
       datafeed: DatafeedService = Depends(get_datafeed)
   ):
       \"\"\"Custom endpoint for bulk loading multiple charts.\"\"\"
       results = []

       for chart_id, series_list in chart_data.items():
           await datafeed.create_chart(chart_id)

           for series in series_list:
               await datafeed.set_series_data(
                   chart_id=chart_id,
                   pane_id=series["pane_id"],
                   series_id=series["series_id"],
                   series_type=series["series_type"],
                   data=series["data"],
                   options=series.get("options")
               )

           results.append({"chart_id": chart_id, "status": "loaded"})

       return {"results": results}

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)
