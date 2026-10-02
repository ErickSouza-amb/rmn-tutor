import asyncio
import json
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Identity, get_db, get_identity, load_session
from app.api.schemas import PostMessageIn
from app.config import Settings, get_settings
from app.errors import ApiError
from app.store import repo
from app.store.blob import get_blob_store
from app.store.db import get_sessionmaker
from app.store.models import SessionRow
from app.tutor.llm import get_llm
from app.tutor.turn import run_turn

router = APIRouter()
logger = logging.getLogger("rmn.messages")


def sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


async def enforce_rate_limit(db: AsyncSession, identity: Identity, settings: Settings) -> None:
    now = repo.utcnow()
    limits = (
        (f"uid:{identity.uid}", settings.rate_limit_per_hour, settings.rate_limit_per_day),
        (f"ip:{identity.ip}", settings.rate_limit_ip_per_hour, settings.rate_limit_ip_per_day),
    )
    for key, per_hour, per_day in limits:
        if await repo.count_rate_events(db, key, now - timedelta(hours=1)) >= per_hour:
            raise ApiError(429, "rate_limited", "Muitas mensagens em pouco tempo. Aguarde alguns minutos e tente de novo.")
        if await repo.count_rate_events(db, key, now - timedelta(days=1)) >= per_day:
            raise ApiError(429, "rate_limited", "Limite diário de mensagens atingido. Tente novamente amanhã.")
    for key, _, _ in limits:
        await repo.record_rate_event(db, key)


@router.post("/sessions/{session_id}/messages")
async def post_message(
    body: PostMessageIn,
    row: SessionRow = Depends(load_session),
    identity: Identity = Depends(get_identity),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    text = body.text.strip()
    if not text:
        raise ApiError(422, "empty_message", "Mensagem vazia.")
    if len(text) > settings.max_message_chars:
        raise ApiError(422, "message_too_long", f"Mensagem longa demais (máx. {settings.max_message_chars} caracteres).")
    if await repo.session_input_tokens(db, row.id) >= settings.session_input_token_cap:
        raise ApiError(429, "session_token_cap", "Esta sessão atingiu o limite de uso. Inicie uma nova sessão.")
    await enforce_rate_limit(db, identity, settings)
    if not await repo.acquire_turn_lock(db, row.id, settings.turn_lock_seconds):
        raise ApiError(409, "turn_in_progress", "O tutor ainda está respondendo à mensagem anterior.")

    session_id = row.id
    llm = get_llm(settings)
    blob = get_blob_store()
    sessionmaker = get_sessionmaker()

    async def release() -> None:
        async with sessionmaker() as lock_db:
            await repo.release_turn_lock(lock_db, session_id)

    async def gen():
        try:
            async for ev in run_turn(
                session_id=session_id, user_text=text, mode=body.mode, llm=llm,
                blob=blob, settings=settings, sessionmaker=sessionmaker,
            ):
                yield sse(ev.event, ev.data)
        except Exception:
            logger.exception("turn_crashed", extra={"fields": {"session_id": str(session_id)}})
            yield sse("error", {"code": "internal_error", "message": "Erro interno no tutor. Tente novamente."})
        finally:
            await asyncio.shield(release())

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
