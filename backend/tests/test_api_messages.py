import json

from app.config import get_settings
from app.store import repo
from app.store.db import get_sessionmaker


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.strip().split("\n\n"):
        name, data = None, None
        for line in frame.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name:
            events.append((name, data))
    return events


async def _session(client) -> str:
    return (await client.post("/api/sessions", json={"exercise_id": "ex02"})).json()["id"]


async def test_message_streams_and_persists(client):
    sid = await _session(client)
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Vejo três sinais."})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(res.text)
    names = [n for n, _ in events]
    assert "text_delta" in names and "tool_call" in names and names[-1] == "done"
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert [(m["role"], m["text"]) for m in s["messages"]][0] == ("user", "Vejo três sinais.")
    assert s["messages"][1]["role"] == "assistant" and "P1" in s["messages"][1]["text"]
    res2 = await client.post(f"/api/sessions/{sid}/messages", json={"text": "E agora?", "mode": "hint"})
    assert res2.status_code == 200
    s2 = (await client.get(f"/api/sessions/{sid}")).json()
    assert s2["assist_mode"] == "hint" and len(s2["messages"]) == 4


async def test_concurrent_turn_is_rejected(client):
    sid = await _session(client)
    import uuid

    async with get_sessionmaker()() as db:
        assert await repo.acquire_turn_lock(db, uuid.UUID(sid), 60)
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    assert res.status_code == 409 and res.json()["error"]["code"] == "turn_in_progress"
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert s["messages"] == []


async def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    get_settings.cache_clear()
    sid = await _session(client)
    for _ in range(2):
        assert (await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})).status_code == 200
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    assert res.status_code == 429 and res.json()["error"]["code"] == "rate_limited"


async def test_session_token_cap(client, monkeypatch):
    monkeypatch.setenv("SESSION_INPUT_TOKEN_CAP", "1")
    get_settings.cache_clear()
    sid = await _session(client)
    assert (await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})).status_code == 200
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    assert res.status_code == 429 and res.json()["error"]["code"] == "session_token_cap"


async def test_message_validation(client, monkeypatch):
    monkeypatch.setenv("MAX_MESSAGE_CHARS", "10")
    get_settings.cache_clear()
    sid = await _session(client)
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "x" * 11})
    assert res.status_code == 422 and res.json()["error"]["code"] == "message_too_long"
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "   "})
    assert res.status_code == 422 and res.json()["error"]["code"] == "empty_message"
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "oi", "mode": "cheat"})
    assert res.status_code == 422


async def test_ip_limit_is_separate_from_uid_limit(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "1")
    monkeypatch.setenv("RATE_LIMIT_IP_PER_HOUR", "5")
    get_settings.cache_clear()
    import httpx

    from app.main import create_app

    for _ in range(3):  # three students (cookies) behind the same IP
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test") as other:
            sid = (await other.post("/api/sessions", json={"exercise_id": "ex02"})).json()["id"]
            assert (await other.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})).status_code == 200
            assert (await other.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})).status_code == 429
