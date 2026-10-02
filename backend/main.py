import asyncio
import json

import rdkit
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="RMN Tutor API (spike)")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0", "rdkit": rdkit.__version__}


@app.get("/api/spike/sse")
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
