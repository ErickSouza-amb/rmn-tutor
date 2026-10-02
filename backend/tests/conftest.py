import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _test_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("FAKE_LLM", "true")
    monkeypatch.setenv("BLOB_BACKEND", "memory")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db():
    from app.store.db import create_all, get_sessionmaker

    await create_all()
    async with get_sessionmaker()() as session:
        yield session
