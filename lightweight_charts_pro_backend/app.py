"""FastAPI application factory for Lightweight Charts Backend.

This module provides the create_app factory function that initializes and
configures a FastAPI application with chart endpoints, WebSocket support,
and CORS middleware for real-time TradingView Lightweight Charts data.
"""

# Standard Imports

# Third Party Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local Imports
from lightweight_charts_pro_backend.api import chart_router
from lightweight_charts_pro_backend.services import DatafeedService
from lightweight_charts_pro_backend.websocket import websocket_router


def create_app(
    datafeed: DatafeedService | None = None,
    cors_origins: list[str] | None = None,
    title: str = "Lightweight Charts API",
    version: str = "0.1.0",
) -> FastAPI:
    """Create and configure FastAPI application with chart endpoints and WebSocket support.

    This factory function initializes a FastAPI application configured for
    serving TradingView Lightweight Charts data. It sets up CORS middleware,
    initializes the datafeed service, and registers API and WebSocket routers.

    Args:
        datafeed: Optional DatafeedService instance for managing chart data.
            If None, creates a new default instance. This allows for custom
            datafeed implementations or dependency injection in tests.
        cors_origins: List of allowed CORS origins as strings. If None,
            defaults to ["http://localhost:3000", "http://localhost:8501"]
            to support common development servers (React, Streamlit).
        title: API title shown in OpenAPI documentation. Defaults to
            "Lightweight Charts API".
        version: API version string for documentation and versioning.
            Defaults to "0.1.0".

    Returns:
        FastAPI: Fully configured FastAPI application instance ready to run
            with uvicorn or other ASGI servers.

    Example:
        >>> app = create_app()
        >>> import uvicorn
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    # Create the FastAPI application instance with metadata for documentation
    app = FastAPI(
        title=title,
        version=version,
        description="REST API and WebSocket backend for TradingView Lightweight Charts",
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
        datafeed = DatafeedService()

    # Store datafeed in app state for access in route handlers via dependency injection
    app.state.datafeed = datafeed

    # Register API routers with appropriate prefixes and tags for documentation
    # Chart router handles REST endpoints for CRUD operations on chart data
    app.include_router(chart_router, prefix="/api/charts", tags=["charts"])
    # WebSocket router handles real-time bidirectional communication
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

    @app.get("/health")
    async def health_check():
        """Basic health check endpoint for liveness probes.

        This is a simple liveness check that confirms the application is running.
        It doesn't verify that all services are functional, just that the app
        process is alive and can respond to requests.

        Returns:
            dict: Status dictionary with "status" and "version" keys.

        Example:
            >>> # GET /health
            >>> {"status": "healthy", "version": "0.1.0"}
        """
        return {"status": "healthy", "version": version}

    @app.get("/health/ready")
    async def readiness_check():
        """Readiness check that verifies DatafeedService is functional.

        This endpoint performs actual operations on DatafeedService to verify
        it's working correctly, not just that the app started. This is useful
        for Kubernetes readiness probes or load balancer health checks that
        need to confirm the service can handle traffic.

        The check creates a temporary test chart, verifies it can be retrieved,
        then cleans it up. This ensures the core datafeed operations work.

        Returns:
            dict: Detailed health status with the following keys:
                - status (str): "ready" if all checks pass, "degraded" otherwise
                - version (str): API version
                - checks (dict): Individual check results
                - errors (list, optional): List of error messages if any checks failed

        Example:
            >>> # GET /health/ready
            >>> {
            ...     "status": "ready",
            ...     "version": "0.1.0",
            ...     "checks": {
            ...         "datafeed_initialized": True,
            ...         "datafeed_operational": True
            ...     }
            ... }
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

                # Clean up - remove test chart from internal state to avoid pollution
                # We access internal state directly here since this is a health check
                async with datafeed_service._lock:
                    datafeed_service._charts.pop(test_chart_id, None)
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
