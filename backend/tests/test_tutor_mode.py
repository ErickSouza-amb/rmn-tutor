from app.config import get_settings


async def test_health_reports_simulated_tutor(client):
    body = (await client.get("/api/health")).json()
    assert body["tutor"] == "simulated"


async def test_health_reports_claude_when_key_and_not_fake(client, monkeypatch):
    monkeypatch.setenv("FAKE_LLM", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    get_settings.cache_clear()
    body = (await client.get("/api/health")).json()
    assert body["tutor"] == "claude"
    assert "sk-test" not in str(body)
