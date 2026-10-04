from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Meridian"
    environment: Literal["local", "test", "production"] = "local"
    data_mode: Literal["mock", "live"] = "mock"
    ai_provider: Literal["local", "openai", "anthropic", "bedrock"] = "local"

    database_url: str = "postgresql+psycopg://meridian:meridian@localhost:5433/meridian"
    redis_url: str = "redis://localhost:6379/0"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_origin: str = "http://localhost:3000,http://localhost:3010"

    @property
    def web_origins(self) -> list[str]:
        return [origin.strip() for origin in self.web_origin.split(",") if origin.strip()]

    local_ai_base_url: str = "http://127.0.0.1:11434"
    local_ai_model: str = ""

    secret_key: str = "local-dev-only-change-me"
    log_level: str = "INFO"
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    bedrock_region: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True
    alert_watch: bool = True
    alert_check_seconds: int = Field(default=300, ge=30, le=3600)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
