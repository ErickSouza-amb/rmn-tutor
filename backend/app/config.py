from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    session_secret: str = "dev-insecure-secret-change-me"
    cookie_secure: bool = True

    anthropic_api_key: str | None = None
    tutor_model: str = "claude-sonnet-5-5"
    tutor_effort: str = "medium"
    tutor_max_tokens: int = 16000
    tutor_max_tool_iterations: int = 6
    fake_llm: bool = False

    blob_backend: Literal["memory", "vercel"] = "memory"
    blob_read_write_token: str | None = None

    rate_limit_per_hour: int = 30
    rate_limit_per_day: int = 200
    # one campus NAT IP is shared by a whole class, so the IP limit is much higher than the per-student one
    rate_limit_ip_per_hour: int = 300
    rate_limit_ip_per_day: int = 2000
    session_input_token_cap: int = 400_000
    max_upload_bytes: int = 4 * 1024 * 1024  # Vercel Functions cap request bodies at 4.5 MB
    max_message_chars: int = 4000
    turn_lock_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
