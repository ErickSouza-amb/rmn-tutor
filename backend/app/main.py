from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_misc import router as misc_router
from app.api.routes_sessions import router as sessions_router
from app.config import get_settings
from app.errors import install_error_handlers
from app.logging import RequestContextMiddleware, configure_logging
from app.store.db import create_all


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().database_url.startswith("sqlite"):
        await create_all()  # local dev / e2e convenience; Postgres uses Alembic
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="RMN Tutor API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(misc_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    return app


app = create_app()
