import json
import logging

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import get_settings
from app.errors import ApiError
from app.logging import JsonFormatter
from app.main import create_app


def _app_with_test_routes():
    app = create_app()
    router = APIRouter()

    class Body(BaseModel):
        n: int

    @router.get("/api/_t/api-error")
    def raise_api_error():
        raise ApiError(409, "conflict_x", "Conflito de teste")

    @router.get("/api/_t/boom")
    def boom():
        raise RuntimeError("segredo interno")

    @router.post("/api/_t/validate")
    def validate(body: Body):
        return {"n": body.n}

    app.include_router(router)
    return app


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("TUTOR_MODEL", "claude-opus-5-5")
    get_settings.cache_clear()
    s = get_settings()
    assert s.tutor_model == "claude-opus-5-5"
    assert s.rate_limit_per_hour == 30
    assert s.max_upload_bytes == 4 * 1024 * 1024


def test_api_error_envelope():
    client = TestClient(_app_with_test_routes())
    res = client.get("/api/_t/api-error")
    assert res.status_code == 409
    assert res.json() == {"error": {"code": "conflict_x", "message": "Conflito de teste"}}


def test_unhandled_error_hides_details():
    client = TestClient(_app_with_test_routes(), raise_server_exceptions=False)
    res = client.get("/api/_t/boom")
    assert res.status_code == 500
    body = res.json()
    assert body["error"]["code"] == "internal_error"
    assert "segredo" not in json.dumps(body)


def test_validation_error_envelope():
    client = TestClient(_app_with_test_routes())
    res = client.post("/api/_t/validate", json={"n": "abc"})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["details"], list)


def test_request_id_header():
    client = TestClient(create_app())
    res = client.get("/api/health")
    assert res.status_code == 200
    assert len(res.headers["x-request-id"]) == 16


def test_json_formatter_includes_fields():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "evento", None, None)
    record.fields = {"session_id": "abc", "tokens": 3}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["msg"] == "evento"
    assert payload["session_id"] == "abc"
    assert payload["level"] == "INFO"
