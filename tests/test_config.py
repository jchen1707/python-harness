"""Offline unit tests for app.config (architecture §5, §8)."""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings


def test_get_settings_returns_cached_singleton() -> None:
    """get_settings() is lru_cached: the same instance is returned on every call (§5)."""
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


def test_settings_default_app_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """With APP_NAME unset and no .env, the default app_name is 'python-harness'."""
    get_settings.cache_clear()
    monkeypatch.delenv("APP_NAME", raising=False)
    try:
        assert Settings().app_name == "python-harness"
    finally:
        get_settings.cache_clear()
