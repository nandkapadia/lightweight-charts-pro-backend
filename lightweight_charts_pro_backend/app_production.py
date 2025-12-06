"""Production-ready FastAPI application with authentication and monitoring."""

# Standard Imports
from contextlib import asynccontextmanager

# Third Party Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Local Imports
from lightweight_charts_pro_backend.api import chart_router
from lightweight_charts_pro_backend.config import Settings, get_settings
from lightweight_charts_pro_backend.database import get_db_manager
from lightweight_charts_pro_backend.logging_config import get_logger, setup_logging
from lightweight_charts_pro_backend.middleware import (
    ErrorHandlerMiddleware,
    RequestLoggingMiddleware,
)
from lightweight_charts_pro_backend.services import DatafeedService
from lightweight_charts_pro_backend.websocket import websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown routines for the FastAPI app.

    Args:
        app (FastAPI): FastAPI application instance being started.

    Yields:
        None: Control back to FastAPI while the app is running.

    Returns:
        None: This context manager is used for its side effects.
    """
    # Startup
    settings: Settings = app.state.settings
    logger.info(
        "Application starting",
        extra={
            "environment": settings.environment,
            "debug": settings.debug,
            "enable_auth": settings.enable_auth,
            "enable_persistence": settings.enable_persistence,
        },
    )

    # Initialize database if persistence is enabled
    if settings.enable_persistence:
        try:
            db_manager = get_db_manager(settings)
            await db_manager.create_tables()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    yield

    # Shutdown
    logger.info("Application shutting down")
    if settings.enable_persistence:
        try:
            db_manager = get_db_manager()
            await db_manager.close()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}", exc_info=True)


def create_app(
    settings: Settings | None = None,
    datafeed: DatafeedService | None = None,
) -> FastAPI:
    """Build a production-configured FastAPI application.

    Args:
        settings (Settings | None): Optional settings instance; falls back to environment.
        datafeed (DatafeedService | None): Prebuilt datafeed service for dependency injection.

    Returns:
        FastAPI: Application instance with middleware, routers, and monitoring configured.
    """
    # Load settings from environment if not provided
    if settings is None:
        settings = get_settings()

    # Setup structured logging
    setup_logging(settings)

    # Create FastAPI application with lifespan management
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Production-ready REST API and WebSocket backend for TradingView Lightweight Charts",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,  # Disable docs in prod
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # Store settings in app state
    app.state.settings = settings

    # Add custom middleware (order matters - first added is outermost)
    # 1. Request logging (outermost - logs everything)
    app.add_middleware(RequestLoggingMiddleware)

    # 2. Error handling (catches all exceptions)
    app.add_middleware(ErrorHandlerMiddleware)

    # 3. CORS (cross-origin requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup rate limiting if enabled
    if settings.enable_rate_limiting:
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting enabled", extra={"limit": settings.rate_limit_per_minute})

    # Initialize datafeed service
    if datafeed is None:
        datafeed = DatafeedService(chunk_size_threshold=settings.chunk_size_threshold)
    app.state.datafeed = datafeed

    # Register routers
    app.include_router(chart_router, prefix="/api/charts", tags=["charts"])
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

    # Setup Prometheus metrics if enabled
    if settings.enable_metrics:
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health", "/health/ready"],
        )
        instrumentator.instrument(app).expose(app, endpoint=settings.metrics_path)
        logger.info("Prometheus metrics enabled", extra={"path": settings.metrics_path})

    # Health check endpoints
    @app.get("/health", tags=["health"])
    async def health_check():
        """Liveness probe - confirms application is running.

        Returns:
            dict: Basic health status.
        """
        return {"status": "healthy", "version": "0.1.0", "environment": settings.environment}

    @app.get("/health/ready", tags=["health"])
    async def readiness_check():
        """Readiness probe - verifies all services are operational.

        Returns:
            dict: Detailed readiness status with individual checks.
        """
        checks = {
            "datafeed_initialized": False,
            "datafeed_operational": False,
            "database_connected": False if settings.enable_persistence else None,
        }
        errors = []

        # Check datafeed service
        try:
            datafeed_service = app.state.datafeed
            checks["datafeed_initialized"] = datafeed_service is not None

            if checks["datafeed_initialized"]:
                # Test operation
                test_chart_id = "__health_check_test__"
                await datafeed_service.create_chart(test_chart_id)
                chart = await datafeed_service.get_chart(test_chart_id)
                checks["datafeed_operational"] = chart is not None

                # Cleanup
                async with datafeed_service._lock:
                    datafeed_service._charts.pop(test_chart_id, None)
        except Exception as e:
            errors.append(f"Datafeed check failed: {e}")

        # Check database if persistence enabled
        if settings.enable_persistence:
            try:
                from sqlalchemy import text

                db_manager = get_db_manager()
                async with db_manager.get_session() as session:
                    await session.execute(text("SELECT 1"))
                    checks["database_connected"] = True
            except Exception as e:
                errors.append(f"Database check failed: {e}")

        # Determine overall status
        # Filter out None values (disabled features)
        active_checks = {k: v for k, v in checks.items() if v is not None}
        all_checks_passed = all(active_checks.values())
        status = "ready" if all_checks_passed else "degraded"

        response = {
            "status": status,
            "version": "0.1.0",
            "environment": settings.environment,
            "checks": checks,
        }

        if errors:
            response["errors"] = errors

        return response

    logger.info(
        "Application initialized successfully",
        extra={
            "environment": settings.environment,
            "auth_enabled": settings.enable_auth,
            "rate_limiting_enabled": settings.enable_rate_limiting,
            "persistence_enabled": settings.enable_persistence,
            "metrics_enabled": settings.enable_metrics,
        },
    )

    return app


# For backward compatibility with existing code
def create_app_legacy(
    datafeed: DatafeedService | None = None,
    cors_origins: list[str] | None = None,
    title: str = "Lightweight Charts API",
    version: str = "0.1.0",
) -> FastAPI:
    """Legacy create_app for backward compatibility.

    This maintains the old API signature but uses the new production setup.

    Args:
        datafeed: Optional DatafeedService instance.
        cors_origins: List of CORS origins (deprecated - use CORS_ORIGINS env var).
        title: API title (deprecated - use APP_NAME env var).
        version: API version.

    Returns:
        FastAPI: Configured application.
    """
    import warnings

    warnings.warn(
        "create_app_legacy is deprecated. Use create_app() with environment variables instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    settings = get_settings()

    # Override settings if legacy parameters provided
    if cors_origins:
        settings.cors_origins = cors_origins
    if title:
        settings.app_name = title

    return create_app(settings=settings, datafeed=datafeed)
