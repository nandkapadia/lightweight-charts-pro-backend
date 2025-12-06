"""FastAPI application factory for the Lightweight Charts backend.

This module exposes helpers to build a FastAPI application that serves chart
data over both REST and WebSocket interfaces while applying sensible defaults
such as CORS configuration and health probes.
"""

# Standard Imports
from contextlib import asynccontextmanager

# Third Party Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local Imports
from lightweight_charts_pro_backend.api import chart_router
from lightweight_charts_pro_backend.config import get_settings
from lightweight_charts_pro_backend.services import DatafeedService
from lightweight_charts_pro_backend.websocket import websocket_router
from lightweight_charts_pro_backend.websocket.handlers import manager as websocket_manager


def create_app(
    datafeed: DatafeedService | None = None,
    cors_origins: list[str] | None = None,
    title: str = "Lightweight Charts API",
    version: str = "0.1.0",
) -> FastAPI:
    """Build a FastAPI application configured for chart REST and WebSocket APIs.

    Args:
        datafeed (DatafeedService | None): Preconfigured datafeed service for dependency
            injection. When ``None``, a default ``DatafeedService`` is created.
        cors_origins (list[str] | None): Allowed origins for cross-origin requests.
            Defaults to common development origins when omitted.
        title (str): Title shown in generated OpenAPI documentation pages.
        version (str): API semantic version string shown in metadata and health checks.

    Returns:
        FastAPI: Configured FastAPI application instance ready to serve requests.

    Examples:
        >>> app = create_app()
        >>> import uvicorn
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifespan events (startup/shutdown).

        Args:
            app: FastAPI application instance.

        Yields:
            None: Application runs between startup and shutdown.
        """
        # Startup: nothing special needed yet
        yield
        # Shutdown: gracefully close WebSocket connections
        await websocket_manager.shutdown()

    # Create the FastAPI application instance with metadata and lifespan handler
    app = FastAPI(
        title=title,
        version=version,
        description="REST API and WebSocket backend for TradingView Lightweight Charts",
        lifespan=lifespan,
    )

    # Configure CORS middleware to allow cross-origin requests from frontend apps
    # This is essential for web applications hosted on different domains/ports
    if cors_origins is None:
        # Default origins for common development environments
        # localhost:3000 = React/Next.js, localhost:8501 = Streamlit
        cors_origins = ["http://localhost:3000", "http://localhost:8501"]

    # Add CORS middleware to the application stack
    # This middleware intercepts requests and adds appropriate CORS headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # Which origins can access the API
        allow_credentials=True,  # Allow cookies and auth headers
        allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],  # Allow all headers
    )

    # Initialize or use provided datafeed service for chart data management
    # The datafeed service handles data storage, chunking, and pagination
    if datafeed is None:
        settings = get_settings()
        datafeed = DatafeedService(chunk_size_threshold=settings.chunk_size_threshold)

    # Store datafeed in app state for access in route handlers via dependency injection
    app.state.datafeed = datafeed

    # Register API routers with appropriate prefixes and tags for documentation
    # Chart router handles REST endpoints for CRUD operations on chart data
    app.include_router(chart_router, prefix="/api/charts", tags=["charts"])
    # WebSocket router handles real-time bidirectional communication
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

    @app.get("/health")
    async def health_check():
        """Report liveness of the application instance.

        Returns:
            dict: Dictionary containing ``status`` and ``version`` keys to indicate
            that the process is running.
        """
        # Simple heartbeat response without deep dependency checks
        return {"status": "healthy", "version": version}

    @app.get("/health/ready")
    async def readiness_check():
        """Verify readiness by exercising the ``DatafeedService`` dependencies.

        Returns:
            dict: Health payload containing overall ``status``, ``version``, detailed
            check booleans, and optional error messages when a check fails.
        """
        # Initialize check results dictionary to track individual service health
        checks = {
            "datafeed_initialized": False,
            "datafeed_operational": False,
        }
        errors = []

        # Check if DatafeedService is initialized in app state
        # This verifies the application bootstrapped correctly
        try:
            datafeed_service = app.state.datafeed
            checks["datafeed_initialized"] = datafeed_service is not None
        except AttributeError:
            # app.state.datafeed doesn't exist - configuration error
            errors.append("DatafeedService not found in app.state")

        # Test DatafeedService operations to ensure it's not just initialized
        # but actually functional and can perform CRUD operations
        if checks["datafeed_initialized"]:
            try:
                # Create a test chart with a special ID to verify create operation
                test_chart_id = "__health_check_test__"
                await datafeed_service.create_chart(test_chart_id)

                # Verify we can retrieve the chart we just created (read operation)
                chart = await datafeed_service.get_chart(test_chart_id)
                if chart is not None:
                    checks["datafeed_operational"] = True

                # Clean up - remove test chart and associated resources
                await datafeed_service.delete_chart(test_chart_id)
            except Exception as e:
                # Any exception during operations means the service is not ready
                errors.append(f"DatafeedService operation failed: {e!s}")

        # Determine overall status based on all checks
        # Service is only "ready" if ALL checks pass
        all_checks_passed = all(checks.values())
        status = "ready" if all_checks_passed else "degraded"

        # Build response with detailed check information
        response = {
            "status": status,
            "version": version,
            "checks": checks,
        }

        # Only include errors key if there are actual errors
        if errors:
            response["errors"] = errors

        return response

    return app
