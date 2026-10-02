import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("rmn.errors")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_body(code: str, message: str, details=None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = jsonable_encoder(
            [
                {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
                for e in exc.errors()
            ]
        )
        return JSONResponse(
            error_body("validation_error", "Dados inválidos na requisição.", details),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("unhandled_error", exc_info=exc)
        return JSONResponse(
            error_body("internal_error", "Erro interno. Tente novamente em instantes."),
            status_code=500,
        )
