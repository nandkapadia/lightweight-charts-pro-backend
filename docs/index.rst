Lightweight Charts Pro Backend Documentation
===========================================

Welcome to the Lightweight Charts Pro Backend documentation. This package provides
a FastAPI backend for TradingView Lightweight Charts with real-time updates and
infinite history loading.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
   api/index
   examples

Features
--------

* **REST API**: CRUD operations for chart data and configuration
* **WebSocket Server**: Real-time chart updates and data streaming
* **Data Chunking**: Efficient handling of large datasets
* **Lazy Loading**: Load chart data on-demand as users interact
* **Validation**: Pydantic models for request/response validation
* **CORS Support**: Configurable cross-origin resource sharing

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install lightweight-charts-pro-backend

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from lightweight_charts_pro_backend import create_app
   import uvicorn

   # Create the FastAPI application
   app = create_app()

   # Run the server
   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8000)

API Reference
-------------

.. autosummary::
   :toctree: _autosummary
   :template: custom-module-template.rst
   :recursive:

   lightweight_charts_pro_backend

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
