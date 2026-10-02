from fastapi import FastAPI

from app.api.routes_misc import router as misc_router
from app.config import get_settings
from app.errors import install_error_handlers
from app.logging import RequestContextMiddleware, configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="RMN Tutor API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(misc_router, prefix="/api")
    return app


app = create_app()
