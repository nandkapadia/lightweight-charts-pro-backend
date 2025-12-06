"""Configuration management using pydantic-settings.

This module provides centralized configuration for the application,
loading settings from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    For production deployments, create a .env file or set environment
    variables directly in your deployment environment.

    Example .env file:
        DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
        SECRET_KEY=your-secret-key-here
        CORS_ORIGINS=https://example.com,https://app.example.com
        ENVIRONMENT=production
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
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8501",
        description="Comma-separated list of allowed CORS origins",
    )

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if not v:
            return []
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
    database_echo: bool = Field(
        default=False, description="Echo SQL statements (for debugging)"
    )

    # Data Management
    enable_persistence: bool = Field(
        default=False,
        description="Enable database persistence (False = in-memory only)",
    )
    chart_ttl_hours: int = Field(
        default=24, ge=1, description="Chart time-to-live in hours before cleanup"
    )
    cleanup_interval_minutes: int = Field(
        default=60, ge=1, description="Interval for running cleanup tasks"
    )

    # WebSocket Settings
    websocket_timeout_seconds: int = Field(
        default=300, ge=30, description="WebSocket connection timeout in seconds"
    )
    websocket_ping_interval_seconds: int = Field(
        default=30, ge=5, description="WebSocket ping interval in seconds"
    )

    # Monitoring
    enable_metrics: bool = Field(
        default=True, description="Enable Prometheus metrics endpoint"
    )
    metrics_path: str = Field(default="/metrics", description="Prometheus metrics endpoint path")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function is cached to ensure we only load settings once.
    Use this function instead of instantiating Settings directly.

    Returns:
        Settings: Cached settings instance.
    """
    return Settings()
