# Lightweight Charts Pro - Backend API

Framework-agnostic FastAPI backend for TradingView Lightweight Charts Pro.

## Overview

This package provides a REST API and WebSocket server for real-time chart data updates, data chunking, and lazy loading. It's designed to work with any frontend framework (Vue, React, etc.) and uses `lightweight-charts-core` for data management.

## Features

- **REST API**: CRUD operations for chart data and configuration
- **WebSocket Server**: Real-time chart updates and data streaming
- **Data Chunking**: Efficient handling of large datasets
- **Lazy Loading**: Load chart data on-demand as users interact
- **Validation**: Pydantic models for request/response validation
- **CORS Support**: Configurable cross-origin resource sharing

## Installation

```bash
pip install lightweight-charts-backend
```

## Usage

### Starting the Server

```python
from lightweight_charts_backend import create_app
import uvicorn

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### API Endpoints

- `GET /api/charts` - List all charts
- `POST /api/charts` - Create a new chart
- `GET /api/charts/{chart_id}` - Get chart data
- `PUT /api/charts/{chart_id}` - Update chart data
- `DELETE /api/charts/{chart_id}` - Delete chart
- `WS /ws/charts/{chart_id}` - WebSocket for real-time updates

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Start development server
uvicorn lightweight_charts_backend.main:app --reload
```

## Configuration

Set environment variables:

```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## License

MIT
