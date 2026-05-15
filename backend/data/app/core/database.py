# app/core/database.py
# Async SQLAlchemy database configuration for PostgreSQL and SQLite.

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Engine Setup ──────────────────────────────────────────────────────────────
# Create an async engine for PostgreSQL or SQLite.
# For local dev with SQLite: DATABASE_URL=sqlite+aiosqlite:///./student_feedback.db
# For production with PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# ── Session Management ────────────────────────────────────────────────────────
# Create a session factory for generating async database sessions.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# ── Base Model ────────────────────────────────────────────────────────────────
# Shared base class for all SQLAlchemy models.
class Base(DeclarativeBase):
    pass

# ── Dependency ────────────────────────────────────────────────────────────────
# FastAPI dependency to get a database session per request.
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def _ensure_prediction_extra_columns(conn) -> None:
    """Add Phase-2 columns to predictions if DB was created before they existed."""
    url = settings.DATABASE_URL.lower()
    want = [
        ("sentiment_score", "FLOAT"),
        ("umap_x", "FLOAT"),
        ("umap_y", "FLOAT"),
    ]
    if "sqlite" in url:
        res = await conn.execute(text("PRAGMA table_info(predictions)"))
        existing = {row[1] for row in res.fetchall()}
        for col, sql_type in want:
            if col not in existing:
                await conn.execute(
                    text(f"ALTER TABLE predictions ADD COLUMN {col} {sql_type}")
                )
                logger.info(f"Added column predictions.{col}")
        return

    if "postgresql" in url:
        res = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'predictions'"
            )
        )
        existing = {row[0] for row in res.fetchall()}
        for col, sql_type in want:
            if col not in existing:
                await conn.execute(
                    text(f"ALTER TABLE predictions ADD COLUMN {col} DOUBLE PRECISION")
                )
                logger.info(f"Added column predictions.{col}")


# ── Automatic Table Creation ──────────────────────────────────────────────────
async def init_db():
    """
    Create all database tables defined in models.
    Imports all models to ensure their metadata is registered.
    Supports both SQLite and PostgreSQL.
    """
    try:
        logger.info(f"Initializing database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'SQLite'}")

        # Import all models to register their metadata with Base
        import app.models

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_prediction_extra_columns(conn)

        logger.info("✓ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {str(e)}")
        raise
