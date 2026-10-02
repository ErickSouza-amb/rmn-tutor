from app.store.blob import MemoryBlobStore, VercelBlobStore, get_blob_store, reset_blob_store


async def test_memory_blob_roundtrip():
    store = MemoryBlobStore()
    path = await store.put("sessions/abc/image.png", b"data", "image/png")
    assert await store.get(path) == b"data"
    await store.delete(path)
    assert path not in store.objects


def test_get_blob_store_selects_backend(monkeypatch):
    from app.config import get_settings

    reset_blob_store()
    assert isinstance(get_blob_store(), MemoryBlobStore)
    monkeypatch.setenv("BLOB_BACKEND", "vercel")
    get_settings.cache_clear()
    reset_blob_store()
    assert isinstance(get_blob_store(), VercelBlobStore)
    reset_blob_store()
