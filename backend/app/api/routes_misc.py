import asyncio
import json

import rdkit
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": get_settings().app_version, "rdkit": rdkit.__version__}


@router.get("/spike/sse")
async def spike_sse(n: int = 5, delay: float = 1.0) -> StreamingResponse:
    async def gen():
        for i in range(max(1, min(n, 20))):
            yield f"event: tick\ndata: {json.dumps({'i': i})}\n\n".encode()
            await asyncio.sleep(max(0.0, min(delay, 2.0)))

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
