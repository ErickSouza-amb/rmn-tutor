from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_engine_url: str | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker, _engine_url
    url = normalize_db_url(get_settings().database_url)
    if _engine is None or url != _engine_url:
        if url.startswith("postgresql"):
            # NullPool + no server-side prepared statements: safe behind Neon's pgbouncer on serverless.
            _engine = create_async_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
        else:
            _engine = create_async_engine(url)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
        _engine_url = url
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def create_all() -> None:
    from app.store import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
