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
    browser_profile_dir: Path = Path(".pokebuy/browser-profile")

    poll_min_seconds: float = 30.0
    http_timeout_seconds: float = 20.0
    http_max_attempts: int = 2
    http_retry_backoff_seconds: float = 1.0
    http_retry_after_max_seconds: float = 60.0
    browser_timeout_seconds: float = 45.0
    browser_manual_wait_seconds: float = 0.0
    browser_headless: bool = False

    web_host: str = "127.0.0.1"
    web_port: int = 8000

    log_file_enabled: bool = True
    log_file_path: Path = Path("pokebuy.log")

    debug_enabled: bool = True
    debug_print_html: bool = True
    debug_redact_html: bool = False
    debug_dir: Path = Path("debug")

    discord_webhook_url: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    email_from: str | None = None
    email_to: str | None = None

    auto_cart_enabled: bool = False
    auto_checkout_enabled: bool = False

    @field_validator(
        "poll_min_seconds",
        "http_timeout_seconds",
        "http_retry_backoff_seconds",
        "http_retry_after_max_seconds",
        "browser_timeout_seconds",
    )
    @classmethod
    def positive_duration(cls, value: float) -> float:
        if value <= 0:
            msg = "duration must be greater than zero"
            raise ValueError(msg)
        return value

    @field_validator("http_max_attempts")
    @classmethod
    def positive_attempts(cls, value: int) -> int:
        if value <= 0:
            msg = "attempt count must be greater than zero"
            raise ValueError(msg)
        return value

    @field_validator("web_port")
    @classmethod
    def valid_port(cls, value: int) -> int:
        if value <= 0 or value > 65535:
            msg = "web port must be between 1 and 65535"
            raise ValueError(msg)
        return value

    @field_validator("browser_manual_wait_seconds")
    @classmethod
    def non_negative_duration(cls, value: float) -> float:
        if value < 0:
            msg = "duration must not be negative"
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
