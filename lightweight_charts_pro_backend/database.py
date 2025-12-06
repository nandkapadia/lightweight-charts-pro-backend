"""Database models and session management using SQLAlchemy.

This module provides async database support with SQLAlchemy for persisting
chart data, series data, and managing chart lifecycle.
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from lightweight_charts_pro_backend.config import Settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class ChartModel(Base):
    """Database model for chart metadata and options.

    Stores chart-level configuration and tracks chart lifecycle.
    """

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
        """String representation of chart model."""
        return f"<ChartModel(id={self.id}, chart_id='{self.chart_id}')>"


class SeriesModel(Base):
    """Database model for series data.

    Stores individual series data points with efficient JSON storage.
    """

    __tablename__ = "series"

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
        """String representation of series model."""
        return (
            f"<SeriesModel(id={self.id}, chart_id='{self.chart_id}', "
            f"pane_id={self.pane_id}, series_id='{self.series_id}')>"
        )

    @property
    def data_list(self) -> list[dict[str, Any]]:
        """Parse JSON data string into list."""
        return json.loads(self.data) if self.data else []

    @data_list.setter
    def data_list(self, value: list[dict[str, Any]]) -> None:
        """Serialize list to JSON string."""
        self.data = json.dumps(value)


class DatabaseManager:
    """Manages database connections and provides async session factory.

    This class handles database initialization, connection pooling,
    and provides async context managers for database sessions.
    """

    def __init__(self, settings: Settings):
        """Initialize database manager with settings.

        Args:
            settings: Application settings containing database configuration.
        """
        self.settings = settings
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,  # Connection pool size
            max_overflow=10,  # Allow up to 15 total connections
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all database tables.

        This should be called during application startup to ensure
        all tables exist. Safe to call multiple times (idempotent).
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables.

        WARNING: This will delete all data. Only use for testing or cleanup.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connections and cleanup resources.

        Should be called during application shutdown.
        """
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """Get a new async database session.

        Returns:
            AsyncSession: New database session for queries.

        Example:
            >>> async with db_manager.get_session() as session:
            ...     result = await session.execute(select(ChartModel))
            ...     charts = result.scalars().all()
        """
        return self.session_factory()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager(settings: Settings | None = None) -> DatabaseManager:
    """Get or create the global database manager instance.

    Args:
        settings: Optional settings to initialize database manager.
            Required on first call, ignored on subsequent calls.

    Returns:
        DatabaseManager: Global database manager instance.

    Raises:
        ValueError: If called without settings before initialization.
    """
    global _db_manager

    if _db_manager is None:
        if settings is None:
            raise ValueError("Database manager not initialized. Pass settings on first call.")
        _db_manager = DatabaseManager(settings)

    return _db_manager


async def get_session() -> AsyncSession:
    """Dependency injection helper for FastAPI routes.

    Yields:
        AsyncSession: Database session for the request.

    Example:
        >>> @app.get("/charts")
        ... async def get_charts(session: AsyncSession = Depends(get_session)):
        ...     result = await session.execute(select(ChartModel))
        ...     return result.scalars().all()
    """
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        try:
            yield session
        finally:
            await session.close()
