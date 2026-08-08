"""Unit tests for `app.core.config.Settings`.

Offline: construct `Settings` with explicit values or via a tmp `.env`. Never read the
real repository `.env` — pass `_env_file=None` and clear the app env vars. Plan: BAC-4
test-plan.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def _clear_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the four app env vars so a test is independent of the host environment."""
    for key in ("DATABASE_URL", "VOYAGE_API_KEY", "SIMILARITY_THRESHOLD", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)


def test_settings_reads_four_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_app_env(monkeypatch)
    # pydantic coerces a str into the SecretStr field at runtime.
    settings = Settings(database_url="postgresql://x", voyage_api_key="secret", _env_file=None)  # type: ignore[arg-type, call-arg]

    assert settings.database_url == "postgresql://x"
    assert settings.similarity_threshold == 0.0
    assert settings.log_level == "INFO"


def test_voyage_key_is_secret_str() -> None:
    settings = Settings(database_url="postgresql://x", voyage_api_key="hunter2", _env_file=None)  # type: ignore[arg-type, call-arg]

    assert isinstance(settings.voyage_api_key, SecretStr)
    assert "hunter2" not in repr(settings)
    assert settings.voyage_api_key.get_secret_value() == "hunter2"


def test_missing_required_secret_fails_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_app_env(monkeypatch)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_missing_database_url_fails_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_app_env(monkeypatch)
    monkeypatch.setenv("VOYAGE_API_KEY", "k")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_empty_required_secret_fails_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_app_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("VOYAGE_API_KEY", "")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_invalid_log_level_fails_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_app_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("VOYAGE_API_KEY", "k")
    monkeypatch.setenv("LOG_LEVEL", "BOGUS")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_similarity_threshold_defaults_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_app_env(monkeypatch)
    settings = Settings(database_url="postgresql://x", voyage_api_key="secret", _env_file=None)  # type: ignore[arg-type, call-arg]

    assert settings.similarity_threshold == 0.0


def test_settings_reads_env_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_app_env(monkeypatch)
    env = tmp_path / ".env"
    env.write_text(
        "DATABASE_URL=postgresql://from-file\n"
        "VOYAGE_API_KEY=file-secret\n"
        "SIMILARITY_THRESHOLD=0.7\n"
        "LOG_LEVEL=DEBUG\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env)  # type: ignore[call-arg]

    assert settings.database_url == "postgresql://from-file"
    assert settings.voyage_api_key.get_secret_value() == "file-secret"
    assert settings.similarity_threshold == 0.7
    assert settings.log_level == "DEBUG"
