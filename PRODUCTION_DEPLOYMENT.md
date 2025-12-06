# Production Deployment Guide

## Overview

This guide covers deploying Lightweight Charts Pro Backend v0.1.0 to production with all security and performance features enabled.

## What's New in v0.1.0

### Production-Ready Features

✅ **Environment Configuration** - Centralized config with `pydantic-settings`
✅ **Database Persistence** - SQLAlchemy async support (PostgreSQL, MySQL, SQLite)
✅ **Authentication** - JWT-based auth with optional API key support
✅ **Rate Limiting** - Per-IP rate limits to prevent abuse
✅ **Structured Logging** - JSON logs with request correlation IDs
✅ **Error Handling** - Graceful error responses with proper HTTP status codes
✅ **Monitoring** - Prometheus metrics for observability
✅ **WebSocket Cleanup** - Automatic cleanup of stale connections
✅ **Per-Chart Locking** - Improved concurrency with fine-grained locks

### Architecture Changes

- **New Module**: `config.py` - Environment-based settings management
- **New Module**: `database.py` - Async database models and session management
- **New Module**: `auth.py` - JWT authentication and authorization
- **New Module**: `logging_config.py` - Structured JSON logging
- **New Module**: `middleware.py` - Error handling and request logging
- **New Module**: `app_production.py` - Production app factory with all features

---

## Quick Start

### 1. Install Dependencies

```bash
# Install with all production dependencies
pip install -e ".[dev]"

# Or install from PyPI (once published)
pip install lightweight-charts-pro-backend
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your production settings
nano .env
```

**Critical Settings to Change**:
```bash
# Security - MUST change in production!
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENABLE_AUTH=true

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# CORS - Set to your frontend domain
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Database - Use PostgreSQL for production
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/charts_db
ENABLE_PERSISTENCE=true

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60
```

### 3. Run Database Migrations

```bash
# Create database tables
# (Automatic on startup if ENABLE_PERSISTENCE=true)

# Or manually with alembic (recommended for production)
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4. Start the Server

**Development Mode** (uses original app.py):
```bash
uvicorn lightweight_charts_pro_backend.app:create_app --factory --reload
```

**Production Mode** (uses app_production.py with all features):
```bash
# With gunicorn for production
gunicorn lightweight_charts_pro_backend.app_production:create_app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile -

# Or with uvicorn directly
uvicorn lightweight_charts_pro_backend.app_production:create_app --factory \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```

---

## Environment Variables Reference

### Application Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Lightweight Charts Pro Backend | Application name |
| `ENVIRONMENT` | development | Environment: development/staging/production |
| `DEBUG` | false | Enable debug mode |
| `LOG_LEVEL` | INFO | Logging level: DEBUG/INFO/WARNING/ERROR/CRITICAL |

### Server Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Server bind host |
| `PORT` | 8000 | Server port |

### Security
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev-secret-key-change-in-production | **MUST CHANGE** - JWT signing key |
| `ALGORITHM` | HS256 | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT token expiration |
| `ENABLE_AUTH` | false | **Enable for production!** |
| `API_KEY_HEADER` | X-API-Key | API key header name |

### CORS
| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | http://localhost:3000,http://localhost:8501 | Comma-separated allowed origins |

### Rate Limiting
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_RATE_LIMITING` | true | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | 60 | Requests per minute per IP |
| `RATE_LIMIT_HISTORY_PER_MINUTE` | 30 | History requests per minute |

### Database
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | sqlite+aiosqlite:///./charts.db | SQLAlchemy connection URL |
| `DATABASE_ECHO` | false | Log SQL queries (debug only) |
| `ENABLE_PERSISTENCE` | false | **Enable for production!** |
| `CHART_TTL_HOURS` | 24 | Chart time-to-live before cleanup |
| `CLEANUP_INTERVAL_MINUTES` | 60 | Cleanup task interval |

### WebSocket
| Variable | Default | Description |
|----------|---------|-------------|
| `WEBSOCKET_TIMEOUT_SECONDS` | 300 | Connection timeout (5 min) |
| `WEBSOCKET_PING_INTERVAL_SECONDS` | 30 | Ping interval |

### Monitoring
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_METRICS` | true | Enable Prometheus metrics |
| `METRICS_PATH` | /metrics | Metrics endpoint path |

---

## Database Setup

### PostgreSQL (Recommended for Production)

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
postgres=# CREATE DATABASE charts_db;
postgres=# CREATE USER charts_user WITH ENCRYPTED PASSWORD 'your_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE charts_db TO charts_user;
postgres=# \q

# Set connection URL in .env
DATABASE_URL=postgresql+asyncpg://charts_user:your_password@localhost:5432/charts_db
ENABLE_PERSISTENCE=true
```

### MySQL/MariaDB

```bash
# Install MySQL
sudo apt-get install mysql-server

# Create database
mysql -u root -p
mysql> CREATE DATABASE charts_db;
mysql> CREATE USER 'charts_user'@'localhost' IDENTIFIED BY 'your_password';
mysql> GRANT ALL PRIVILEGES ON charts_db.* TO 'charts_user'@'localhost';
mysql> FLUSH PRIVILEGES;
mysql> EXIT;

# Set connection URL in .env
DATABASE_URL=mysql+aiomysql://charts_user:your_password@localhost:3306/charts_db
ENABLE_PERSISTENCE=true
```

### SQLite (Development Only)

```bash
# SQLite is default - no setup needed
DATABASE_URL=sqlite+aiosqlite:///./charts.db
ENABLE_PERSISTENCE=true
```

---

## Authentication Setup

### Generating Secret Key

```bash
# Generate a secure secret key
openssl rand -hex 32

# Add to .env
SECRET_KEY=<generated-key-here>
ENABLE_AUTH=true
```

### Creating JWT Tokens

```python
from lightweight_charts_pro_backend.auth import create_access_token
from lightweight_charts_pro_backend.config import get_settings

settings = get_settings()

# Create token for a user
token = create_access_token(
    {"sub": "user123", "chart_ids": ["chart1", "chart2"]},
    settings
)

print(f"Token: {token}")
```

### Using Authentication

**With JWT Bearer Token**:
```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:8000/api/charts/chart1
```

**With API Key**:
```bash
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/charts/chart1
```

---

## Monitoring and Observability

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint:

```bash
# View metrics
curl http://localhost:8000/metrics
```

**Key Metrics**:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_in_progress` - Current in-flight requests

### Health Checks

**Liveness Probe** (basic health):
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "version": "0.1.0"}
```

**Readiness Probe** (checks all services):
```bash
curl http://localhost:8000/health/ready
# Response includes datafeed and database status
```

### Structured Logging

Logs are JSON-formatted in production:

```json
{
  "timestamp": "2025-01-15T10:30:00",
  "level": "INFO",
  "logger": "lightweight_charts_pro_backend.api.charts",
  "message": "Chart created",
  "request_id": "a1b2c3d4",
  "chart_id": "chart1",
  "user": "user123"
}
```

**Viewing Logs**:
```bash
# Follow logs
tail -f app.log | jq .

# Filter by request ID
cat app.log | jq 'select(.request_id == "a1b2c3d4")'

# Filter by level
cat app.log | jq 'select(.level == "ERROR")'
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml setup.py ./
RUN pip install --no-cache-dir -e .

# Copy application code
COPY lightweight_charts_pro_backend ./lightweight_charts_pro_backend

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "lightweight_charts_pro_backend.app_production:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://charts_user:password@db:5432/charts_db
      - ENABLE_PERSISTENCE=true
      - ENABLE_AUTH=true
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=charts_db
      - POSTGRES_USER=charts_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

volumes:
  postgres_data:
  prometheus_data:
```

### Build and Run

```bash
# Build image
docker build -t charts-backend:0.1.0 .

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f api

# Scale workers
docker-compose up -d --scale api=4
```

---

## Kubernetes Deployment

### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: charts-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: charts-backend
  template:
    metadata:
      labels:
        app: charts-backend
    spec:
      containers:
      - name: api
        image: charts-backend:0.1.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: charts-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: charts-secrets
              key: secret-key
        - name: ENVIRONMENT
          value: "production"
        - name: ENABLE_AUTH
          value: "true"
        - name: ENABLE_PERSISTENCE
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: charts-backend-service
spec:
  selector:
    app: charts-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Security Checklist

- [ ] Change `SECRET_KEY` from default
- [ ] Set `ENABLE_AUTH=true`
- [ ] Configure `CORS_ORIGINS` to your domain only
- [ ] Enable `ENABLE_RATE_LIMITING=true`
- [ ] Use PostgreSQL or MySQL (not SQLite) for production
- [ ] Enable `ENABLE_PERSISTENCE=true`
- [ ] Set `ENVIRONMENT=production`
- [ ] Disable debug mode: `DEBUG=false`
- [ ] Use HTTPS/TLS for all connections
- [ ] Implement API key rotation policy
- [ ] Set up firewall rules to restrict database access
- [ ] Enable database backups
- [ ] Configure log aggregation and monitoring
- [ ] Set up alerting for errors and performance issues

---

## Performance Tuning

### Worker Configuration

```bash
# Calculate workers: (2 x CPU cores) + 1
gunicorn app_production:create_app --factory \
    --workers 9 \  # For 4-core server
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30
```

### Database Connection Pool

```python
# In database.py configuration
self.engine = create_async_engine(
    settings.database_url,
    pool_size=20,        # Adjust based on load
    max_overflow=40,     # Total = 60 connections
    pool_pre_ping=True,
    pool_recycle=3600,   # Recycle connections every hour
)
```

### Rate Limit Tuning

Adjust based on expected traffic:
```bash
# High-traffic API
RATE_LIMIT_PER_MINUTE=300
RATE_LIMIT_HISTORY_PER_MINUTE=100

# Standard API
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_HISTORY_PER_MINUTE=30
```

---

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Check database is running
pg_isready -h localhost -p 5432

# Test connection
psql -h localhost -U charts_user -d charts_db

# Check DATABASE_URL format
echo $DATABASE_URL
```

**2. Authentication Errors**
```bash
# Verify SECRET_KEY is set
echo $SECRET_KEY

# Check token expiration
# Tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES
```

**3. Rate Limiting Issues**
```bash
# Temporarily disable for testing
ENABLE_RATE_LIMITING=false

# Check client IP
curl http://localhost:8000/api/charts/test -v
# Look for X-Forwarded-For header
```

**4. WebSocket Disconnections**
```bash
# Increase timeout
WEBSOCKET_TIMEOUT_SECONDS=600

# Check nginx/proxy timeout settings
# Must be >= WEBSOCKET_TIMEOUT_SECONDS
```

---

## Migration from v0.0.x

### Breaking Changes

None - v0.1.0 maintains backward compatibility with the original `app.py`.

### Recommended Upgrade Path

1. **Install new dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Test with development mode** (uses original app.py):
   ```bash
   uvicorn lightweight_charts_pro_backend.app:create_app --factory --reload
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env
   ```

4. **Test with production mode**:
   ```bash
   uvicorn lightweight_charts_pro_backend.app_production:create_app --factory
   ```

5. **Deploy to production** when ready.

---

## Support

- **Documentation**: https://nandkapadia.github.io/lightweight-charts-pro-backend/
- **Issues**: https://github.com/nandkapadia/lightweight-charts-pro-backend/issues
- **Discussions**: https://github.com/nandkapadia/lightweight-charts-pro-backend/discussions

---

## License

MIT License - see LICENSE file for details.
