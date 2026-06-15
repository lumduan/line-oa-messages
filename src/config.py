"""Application configuration loaded from environment / ``.env``."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values are read from environment variables or ``.env``.

    Field names map case-insensitively to env vars, e.g. ``line_channel_secret``
    is populated from ``LINE_CHANNEL_SECRET``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    log_level: str = "info"

    # Ports / host
    webhook_port: int = 9990
    dashboard_port: int = 9991
    app_host: str = "0.0.0.0"  # noqa: S104 — POC binds all interfaces inside the container

    # LINE credentials (empty by default so the app/tests import without a real channel)
    line_channel_secret: str = ""
    line_channel_access_token: str = ""

    # Behaviour
    auto_reply: bool = True

    # Storage
    database_url: str = "sqlite:///./data/line.db"
    storage_secret: str = "change-me"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance (override the cache in tests)."""
    return Settings()


settings = get_settings()
