"""Configuration behaviour at the public Settings seam."""

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def isolate_settings_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep unit tests independent from the developer's local configuration."""
    monkeypatch.chdir(tmp_path)
    for name in ("DATABASE_URL", "VOYAGE_API_KEY", "SIMILARITY_THRESHOLD", "LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)


def test_settings_has_the_approved_fields() -> None:
    assert set(Settings.model_fields) == {
        "database_url",
        "voyage_api_key",
        "similarity_threshold",
        "log_level",
    }


def test_similarity_threshold_defaults_to_disabled() -> None:
    settings = Settings(
        database_url="postgresql://localhost/support",
        voyage_api_key=SecretStr("test-voyage-key"),
        log_level="INFO",
    )

    assert settings.similarity_threshold == 0.0


def test_settings_keeps_the_voyage_key_secret() -> None:
    raw_key = "test-voyage-key"

    settings = Settings(
        database_url="postgresql://localhost/support",
        voyage_api_key=SecretStr(raw_key),
        log_level="INFO",
    )

    assert isinstance(settings.voyage_api_key, SecretStr)
    assert raw_key not in repr(settings)


def test_settings_rejects_startup_without_the_voyage_key() -> None:
    with pytest.raises(ValidationError) as error:
        Settings.model_validate(
            {"database_url": "postgresql://localhost/support", "log_level": "INFO"}
        )

    assert {item["loc"] for item in error.value.errors()} == {("voyage_api_key",)}


def test_settings_reads_the_declared_dotenv_values(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://localhost/from-dotenv\n"
        "VOYAGE_API_KEY=dotenv-voyage-key\n"
        "SIMILARITY_THRESHOLD=0.25\n"
        "LOG_LEVEL=DEBUG\n",
        encoding="utf-8",
    )
    settings = Settings()  # type: ignore[call-arg]  # BaseSettings reads the dotenv fields.

    assert settings.model_dump() == {
        "database_url": "postgresql://localhost/from-dotenv",
        "voyage_api_key": SecretStr("dotenv-voyage-key"),
        "similarity_threshold": 0.25,
        "log_level": "DEBUG",
    }
