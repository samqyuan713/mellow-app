"""
Mellow — Database Configuration
Fixed: auto-corrects DATABASE_URL format for Railway compatibility.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging

from app.config import settings

logger = logging.getLogger("mellow.database")


# ── Auto-correct DATABASE_URL format ───────────────────────────
def _fix_db_url(url: str) -> str:
    """
    Railway injects postgresql:// or postgres:// but asyncpg needs
    postgresql+asyncpg:// — fix automatically regardless of source.
    """
    url = url.replace("postgres://", "postgresql://")
    if "postgresql+asyncpg://" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


_DATABASE_URL = _fix_db_url(settings.DATABASE_URL)

# ── Engine ─────────────────────────────────────────────────────
engine = create_async_engine(
    _DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ── Session Factory ────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base Model ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Create All Tables ──────────────────────────────────────────
async def create_tables():
    """Create all tables on startup if they don't exist."""
    from app.models import user, profile, match, message, subscription  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables synced")


# ── Dependency: get DB session ─────────────────────────────────
async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Health check ───────────────────────────────────────────────
async def check_db_connection() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
