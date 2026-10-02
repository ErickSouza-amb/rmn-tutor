import logging
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger("rmn.blob")


class BlobStore(Protocol):
    async def put(self, path: str, data: bytes, content_type: str) -> str: ...
    async def get(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...


class MemoryBlobStore:
    """Development/test store. Data is lost on restart."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, path: str, data: bytes, content_type: str) -> str:
        self.objects[path] = (data, content_type)
        return path

    async def get(self, path: str) -> bytes:
        return self.objects[path][0]

    async def delete(self, path: str) -> None:
        self.objects.pop(path, None)


class VercelBlobStore:
    """Private Vercel Blob store (token from BLOB_READ_WRITE_TOKEN or OIDC via the SDK)."""

    def __init__(self, token: str | None) -> None:
        self.token = token

    async def put(self, path: str, data: bytes, content_type: str) -> str:
        from vercel.blob import put_async

        res = await put_async(
            path, data, access="private", content_type=content_type, add_random_suffix=True, token=self.token
        )
        return res.pathname

    async def get(self, path: str) -> bytes:
        from vercel.blob import get_async

        res = await get_async(path, access="private", token=self.token)
        return res.content

    async def delete(self, path: str) -> None:
        from vercel.blob import delete_async

        await delete_async(path, token=self.token)


_store: BlobStore | None = None


def get_blob_store() -> BlobStore:
    global _store
    if _store is None:
        settings = get_settings()
        if settings.blob_backend == "vercel":
            _store = VercelBlobStore(settings.blob_read_write_token)
        else:
            logger.warning("Using in-memory blob store (BLOB_BACKEND=memory)")
            _store = MemoryBlobStore()
    return _store


def reset_blob_store() -> None:
    global _store
    _store = None
