from pathlib import Path

import pytest
from pydantic import ValidationError

from pokebuy.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.env == "dev"
    assert settings.data_dir == Path(".pokebuy")
    assert settings.browser_profile_dir == Path(".pokebuy/browser-profile")
    assert settings.poll_min_seconds == 30.0
    assert settings.browser_timeout_seconds == 45.0
    assert settings.browser_manual_wait_seconds == 0.0
    assert settings.browser_headless is False
    assert settings.auto_cart_enabled is False
    assert settings.auto_checkout_enabled is False


def test_poll_interval_can_represent_ten_hertz() -> None:
    settings = Settings(poll_min_seconds=0.1)

    assert settings.poll_min_seconds == 0.1


def test_checkout_requires_cart_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(auto_checkout_enabled=True)
