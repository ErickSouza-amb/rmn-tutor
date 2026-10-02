import secrets
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import ApiError
from app.store import repo
from app.store.db import get_sessionmaker
from app.store.models import SessionRow

COOKIE_NAME = "rmn_uid"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt="rmn-uid")


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@dataclass
class Identity:
    uid: str
    ip: str


def get_identity(request: Request, response: Response) -> Identity:
    uid = None
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        try:
            value = _serializer().loads(raw)
            uid = value if isinstance(value, str) and 8 <= len(value) <= 64 else None
        except BadSignature:
            uid = None
    if uid is None:
        uid = secrets.token_urlsafe(16)
        response.set_cookie(
            COOKIE_NAME,
            _serializer().dumps(uid),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            secure=get_settings().cookie_secure,
            samesite="lax",
            path="/",
        )
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    return Identity(uid=uid, ip=ip)


async def load_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionRow:
    row = await repo.get_session(db, session_id)
    if row is None:
        raise ApiError(404, "session_not_found", "Sessão não encontrada.")
    return row
