"""Async database models and session management for chart persistence.

This module defines SQLAlchemy ORM models for charts and series data and
provides helpers to create async database sessions used throughout the
application.

IMPORTANT: These database models are currently NOT used by the DatafeedService.
All chart data is stored in-memory only. These models are provided as a foundation
for future persistence implementation. To enable persistence:
1. Wire DatabaseManager into DatafeedService
2. Implement save/load methods in DatafeedService
3. Add TTL-based cleanup logic
4. Consider using the two-tier storage architecture (hot cache + cold DB)

For production use with large datasets (multi-million bars), consider:
- TimescaleDB for time-series optimized storage
- Parquet files + DuckDB for columnar storage
- Arrow + memory-mapped files for zero-copy reads
"""

# Standard Imports
import json
from datetime import datetime
from typing import Any

# Third Party Imports
from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Local Imports
from lightweight_charts_pro_backend.config import Settings


class Base(DeclarativeBase):
    """Base class for all database models."""


class ChartModel(Base):
    """Database model for chart metadata and options."""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """Provide a readable string representation for debugging.

        Returns:
            str: Rendered model details including ID and chart identifier.
        """
        return f"<ChartModel(id={self.id}, chart_id='{self.chart_id}')>"


class SeriesModel(Base):
    """Database model for series data using JSON storage."""

    __tablename__ = "series"
    __table_args__ = (
        # Add uniqueness constraint to prevent duplicate series
        # This ensures data integrity in multi-tenant environments
        UniqueConstraint("chart_id", "pane_id", "series_id", name="uix_chart_pane_series"),
        # Add composite index for faster lookups by chart_id + pane_id
        Index("ix_chart_pane", "chart_id", "pane_id"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    pane_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    series_id: Mapped[str] = mapped_column(String(128), nullable=False)
    series_type: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string for large datasets
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """Provide a readable string representation for debugging.

        Returns:
            str: Rendered model details including identifiers for tracing.
        """
        return (
            f"<SeriesModel(id={self.id}, chart_id='{self.chart_id}', "
            f"pane_id={self.pane_id}, series_id='{self.series_id}')>"
        )

    @property
    def data_list(self) -> list[dict[str, Any]]:
        """Parse the stored JSON string into a Python list.

        Returns:
            list[dict[str, Any]]: Deserialized series payload.
        """
        # Convert persisted JSON text back into Python objects for use
        return json.loads(self.data) if self.data else []

    @data_list.setter
    def data_list(self, value: list[dict[str, Any]]) -> None:
        """Serialize a Python list into the JSON text column.

        Args:
            value (list[dict[str, Any]]): Series payload to persist.

        Returns:
            None: The serialized JSON string is stored on the model.
        """
        # Store JSON as text to support large payloads without ORM type issues
        self.data = json.dumps(value)


class DatabaseManager:
    """Manage database connections and provide an async session factory."""

    def __init__(self, settings: Settings):
        """Initialize database engine and session factory.

        Args:
            settings (Settings): Application settings containing database configuration.

        Returns:
            None: Engine and session factory are prepared for use.
        """
        # Persist settings for use across helper methods
        self.settings = settings
        # Create async SQLAlchemy engine with pooling and connection health checks
        # Pool size increased for multi-tenant concurrent backtest load
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=20,  # Base connection pool size (increased from 5 for multi-tenant)
            max_overflow=30,  # Allow up to 50 total connections (increased from 15)
            pool_timeout=30,  # Timeout for acquiring connection (prevent indefinite waits)
            pool_recycle=3600,  # Recycle connections after 1 hour to prevent stale connections
        )
        # Build session factory to create lightweight AsyncSession instances
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all ORM tables if they do not already exist.

        Returns:
            None: Tables are created within the configured database.
        """
        # Use a transaction-bound connection to run synchronous DDL in async context
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all ORM tables (destructive).

        Returns:
            None: Tables are removed from the configured database.
        """
        # Dangerous operation intended for tests or manual cleanup
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Dispose the engine and release connection pool resources.

        Returns:
            None: All pooled connections are closed.
        """
        # Ensure background connections are closed during application shutdown
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """Create a new async database session instance.

        Returns:
            AsyncSession: Session object for executing queries.
        """
        # Instantiate a fresh session; caller manages its lifecycle
        return self.session_factory()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager(settings: Settings | None = None) -> DatabaseManager:
    """Return a shared ``DatabaseManager`` instance.

    Args:
        settings (Settings | None): Settings used to initialize the manager on first call.

    Returns:
        DatabaseManager: Singleton-style database manager.

    Raises:
        ValueError: If ``settings`` is omitted before initial initialization.
    """
    global _db_manager

    if _db_manager is None:
        if settings is None:
            raise ValueError("Database manager not initialized. Pass settings on first call.")
        _db_manager = DatabaseManager(settings)

    return _db_manager


async def get_session() -> AsyncSession:
    """Provide a database session for FastAPI dependency injection.

    Yields:
        AsyncSession: Database session scoped to the request lifecycle.
    """
    # Lazily create or retrieve the shared database manager
    db_manager = get_db_manager()
    # Open a session for the caller and guarantee cleanup when done
    async with db_manager.get_session() as session:
        try:
            yield session
        finally:
            await session.close()
