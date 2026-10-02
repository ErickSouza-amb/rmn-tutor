import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.store import models  # noqa: F401
from app.store.db import Base, normalize_db_url

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    return config.attributes.get("database_url") or normalize_db_url(get_settings().database_url)


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = _url()
    kwargs = {"connect_args": {"prepare_threshold": None}} if url.startswith("postgresql") else {}
    engine = create_async_engine(url, poolclass=NullPool, **kwargs)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
