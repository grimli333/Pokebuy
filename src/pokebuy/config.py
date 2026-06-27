from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="POKEBUY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "sqlite:///.pokebuy/pokebuy.sqlite3"
    secret_key: SecretStr = Field(default=SecretStr("change-me-for-local-development"))
    data_dir: Path = Path(".pokebuy")
    browser_state_dir: Path = Path(".pokebuy/browser-state")

    poll_min_seconds: float = 30.0
    http_timeout_seconds: float = 20.0

    discord_webhook_url: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    email_from: str | None = None
    email_to: str | None = None

    auto_cart_enabled: bool = False
    auto_checkout_enabled: bool = False

    @field_validator("poll_min_seconds", "http_timeout_seconds")
    @classmethod
    def positive_duration(cls, value: float) -> float:
        if value <= 0:
            msg = "duration must be greater than zero"
            raise ValueError(msg)
        return value

    @field_validator("auto_checkout_enabled")
    @classmethod
    def checkout_requires_cart(cls, value: bool, info: object) -> bool:
        data = getattr(info, "data", {})
        if value and not data.get("auto_cart_enabled", False):
            msg = "auto checkout requires auto cart to be enabled"
            raise ValueError(msg)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
