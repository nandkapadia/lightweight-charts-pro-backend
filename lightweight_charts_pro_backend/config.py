"""Configuration management utilities backed by pydantic-settings.

This module defines the ``Settings`` class for loading environment-driven
configuration and exposes a cached helper for retrieving those settings across
the application.
"""

# Standard Imports
from functools import lru_cache
from typing import Literal

# Third Party Imports
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Local Imports


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name (str): Human-readable application name.
        environment (Literal): Deployment environment selection.
        debug (bool): Flag to toggle debug-friendly behavior.
        log_level (Literal): Log level string compatible with ``logging``.
        host (str): Host address for the ASGI server to bind.
        port (int): Port number for the ASGI server.
        cors_origins (str): Comma-separated string of allowed origins.
        secret_key (str): Secret key for JWT signing.
        algorithm (str): JWT algorithm identifier.
        access_token_expire_minutes (int): Minutes until JWT access tokens expire.
        enable_auth (bool): Toggle authentication requirements.
        api_key_header (str): Header name expected for API key auth.
        enable_rate_limiting (bool): Toggle rate limiting middleware.
        rate_limit_per_minute (int): Allowed requests per minute.
        rate_limit_history_per_minute (int): Allowed history requests per minute.
        database_url (str): SQLAlchemy connection string.
        database_echo (bool): Flag to echo SQL statements for debugging.
        enable_persistence (bool): Flag to enable database persistence.
        chart_ttl_hours (int): Hours before chart cleanup when persistence is on.
        cleanup_interval_minutes (int): Interval to run cleanup jobs.
        websocket_timeout_seconds (int): Idle timeout for WebSocket connections.
        websocket_ping_interval_seconds (int): Ping cadence for WebSocket keepalive.
        enable_metrics (bool): Toggle Prometheus metrics endpoint.
        metrics_path (str): URL path where metrics are exposed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = Field(default="Lightweight Charts Pro Backend", description="Application name")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # CORS Settings
    # Note: Field type is str for environment variable input, but validator returns list[str]
    # This is a Pydantic pattern for parsing delimited strings
    cors_origins: str | list[str] = Field(
        default="http://localhost:3000,http://localhost:8501",
        description="Comma-separated list of allowed CORS origins (or list)",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated CORS origins into a list format.

        Args:
            v: Raw comma-separated origins string or pre-parsed list.

        Returns:
            list[str]: Cleaned list of individual origin strings.
        """
        # If already a list, return as-is
        if isinstance(v, list):
            return v

        # Skip parsing when string is empty or missing
        if not v:
            return []
        # Split string by comma and trim whitespace to produce usable list
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # Security Settings
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT encoding (MUST be changed in production)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=1, description="JWT access token expiration in minutes"
    )

    # Authentication
    enable_auth: bool = Field(
        default=False,
        description="Enable authentication (set to True for production)",
    )
    api_key_header: str = Field(
        default="X-API-Key", description="Header name for API key authentication"
    )

    # Rate Limiting
    enable_rate_limiting: bool = Field(
        default=True, description="Enable rate limiting to prevent abuse"
    )
    rate_limit_per_minute: int = Field(
        default=60, ge=1, description="Maximum requests per minute per IP"
    )
    rate_limit_history_per_minute: int = Field(
        default=30, ge=1, description="Maximum history requests per minute per IP"
    )

    # Database Settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./charts.db",
        description="Database connection URL (SQLAlchemy format)",
    )
    database_echo: bool = Field(default=False, description="Echo SQL statements (for debugging)")

    # Data Management (NOT IMPLEMENTED - All data is currently in-memory only)
    enable_persistence: bool = Field(
        default=False,
        description="[NOT IMPLEMENTED] Enable database persistence (currently all data is in-memory only)",
    )
    chart_ttl_hours: int = Field(
        default=24, ge=1, description="[NOT IMPLEMENTED] Chart time-to-live in hours before cleanup"
    )
    cleanup_interval_minutes: int = Field(
        default=60, ge=1, description="[NOT IMPLEMENTED] Interval for running cleanup tasks"
    )

    # WebSocket Settings
    websocket_timeout_seconds: int = Field(
        default=300, ge=30, description="WebSocket connection timeout in seconds"
    )
    websocket_ping_interval_seconds: int = Field(
        default=30, ge=5, description="WebSocket ping interval in seconds"
    )

    # Data Chunking Settings
    chunk_size_threshold: int = Field(
        default=500,
        ge=100,
        le=10000,
        description="Number of data points before chunking is applied (default 500)",
    )

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics endpoint")
    metrics_path: str = Field(default="/metrics", description="Prometheus metrics endpoint path")

    @property
    def is_production(self) -> bool:
        """Determine whether the app is running in production mode.

        Returns:
            bool: ``True`` when the ``environment`` is set to ``production``.
        """
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Determine whether the app is running in development mode.

        Returns:
            bool: ``True`` when the ``environment`` equals ``development``.
        """
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance for reuse across the codebase.

    Returns:
        Settings: Singleton-style settings object created on first call.
    """
    # lru_cache ensures the environment is parsed only once for performance
    return Settings()
