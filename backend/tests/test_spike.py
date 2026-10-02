from fastapi.testclient import TestClient

from main import app


def test_health_reports_rdkit():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["rdkit"]


def test_spike_sse_streams_ticks():
    client = TestClient(app)
    with client.stream("GET", "/api/spike/sse?n=3&delay=0") as res:
        assert res.headers["content-type"].startswith("text/event-stream")
        text = "".join(res.iter_text())
    assert text.count("event: tick") == 3
