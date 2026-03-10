from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Shared synchronous engine for Celery tasks -- avoids creating a new engine
# per task invocation, which would leak connection pools.
# Lazy-initialised because psycopg2 may not be available in the FastAPI
# (async-only) process.
_sync_engine = None
_SyncSessionLocal = None


def _get_sync_engine():
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.database_url_sync,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
        )
        _SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_engine, _SyncSessionLocal


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_sync_session() -> Session:
    """Provide a transactional sync session for use in Celery tasks.

    Usage::

        with get_sync_session() as db:
            ...
    """
    _, sync_session_factory = _get_sync_engine()
    session = sync_session_factory()
    try:
        yield session
    finally:
        session.close()
