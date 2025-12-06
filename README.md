# Lightweight Charts Pro - Backend API

Production-ready FastAPI backend for TradingView Lightweight Charts Pro with authentication, rate limiting, and database persistence.

## Overview

This package provides a REST API and WebSocket server for real-time chart data updates, data chunking, and lazy loading. It's designed to work with any frontend framework (Vue, React, etc.) and includes enterprise-grade features for production deployment.

## ✨ Features

### Core Functionality
- **REST API**: CRUD operations for chart data and configuration
- **WebSocket Server**: Real-time chart updates and data streaming
- **Data Chunking**: Efficient handling of large datasets (automatic for 500+ points)
- **Lazy Loading**: Load chart data on-demand as users interact
- **Validation**: Pydantic models for request/response validation
- **CORS Support**: Configurable cross-origin resource sharing

### Production Features (v0.1.0)
- **🔐 Authentication**: JWT-based auth with API key support
- **🛡️ Rate Limiting**: Prevent abuse with configurable per-IP limits
- **💾 Database Persistence**: SQLAlchemy async support (PostgreSQL, MySQL, SQLite)
- **📊 Monitoring**: Prometheus metrics for observability
- **📝 Structured Logging**: JSON logs with request correlation IDs
- **⚡ Error Handling**: Graceful error responses with proper HTTP codes
- **🔒 Security**: Input validation, path traversal prevention
- **🧹 Auto-Cleanup**: Automatic cleanup of stale WebSocket connections
- **⚙️ Environment Config**: Centralized configuration with environment variables

## Installation

```bash
pip install lightweight-charts-pro-backend
```

## Quick Start

### Development Mode

```python
from lightweight_charts_pro_backend import create_app
import uvicorn

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Production Mode

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Edit .env with your settings
# - Change SECRET_KEY (generate with: openssl rand -hex 32)
# - Set ENABLE_AUTH=true
# - Configure DATABASE_URL for PostgreSQL/MySQL
# - Set CORS_ORIGINS to your frontend domain

# 3. Start with production settings
uvicorn lightweight_charts_pro_backend.app_production:create_app --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```

**See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for complete production setup guide.**

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
uvicorn lightweight_charts_pro_backend.main:app --reload
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### Key Settings

```bash
# Security (REQUIRED for production)
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENABLE_AUTH=true

# Database (recommended for production)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
ENABLE_PERSISTENCE=true

# CORS (set to your frontend domain)
CORS_ORIGINS=https://yourdomain.com

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60

# Monitoring
ENABLE_METRICS=true
METRICS_PATH=/metrics
```

## Documentation

- **[Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)** - Complete production setup
- **[Quick Start Guide](QUICK_START.md)** - Get started quickly
- **[API Documentation](https://nandkapadia.github.io/lightweight-charts-pro-backend/)** - Full API reference
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

## Production Readiness

✅ **Version 0.1.0 is production-ready** with all critical features implemented:

- Authentication and authorization
- Rate limiting and abuse prevention
- Database persistence (PostgreSQL/MySQL recommended)
- Structured logging and monitoring
- Error handling and graceful degradation
- Security best practices (input validation, CORS, etc.)
- Comprehensive test suite (82% coverage)
- Production deployment guide

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for deployment checklist.

## License

MIT
