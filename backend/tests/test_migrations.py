import sqlite3

from alembic import command
from alembic.config import Config


def test_alembic_upgrade_creates_tables(tmp_path):
    path = tmp_path / "mig.db"
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = f"sqlite+aiosqlite:///{path.as_posix()}"
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    con = sqlite3.connect(path)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    con.close()
    assert {"sessions", "messages", "structure_checks", "rate_events", "alembic_version"} <= tables


def test_migration_matches_models(tmp_path):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.store import models  # noqa: F401
    from app.store.db import Base

    path = tmp_path / "mig2.db"
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = f"sqlite+aiosqlite:///{path.as_posix()}"
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []
