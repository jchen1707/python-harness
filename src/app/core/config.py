"""Application settings — the single reader of the environment.

`Settings` is the only place that reads environment variables or `.env`. No other module
calls `os.getenv`. Required fields (`database_url`, `voyage_api_key`) have no default, so
pydantic-settings raises `ValidationError` at construction when they are absent or empty —
the application fails at startup, not at first use. The Voyage key is a `SecretStr` so it
stays out of logs and tracebacks.

Conventions: core/CLAUDE.md (Configuration).
"""

from __future__ import annotations

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"}


class Settings(BaseSettings):
    """Application configuration, loaded from the environment and `.env`.

    Four fields only. Required fields have no default and raise `ValidationError` at
    construction when absent or empty.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    voyage_api_key: SecretStr
    similarity_threshold: float = 0.0
    log_level: str = "INFO"

    @field_validator("database_url", "voyage_api_key", mode="after")
    @classmethod
    def _require_non_empty(cls, value: str | SecretStr) -> str | SecretStr:
        """Reject empty required values so the app fails at startup, not at first use."""
        secret = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not secret.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("log_level", mode="after")
    @classmethod
    def _valid_log_level(cls, value: str) -> str:
        """Reject unknown log level names so a bad LOG_LEVEL fails at startup."""
        if value.upper() not in _VALID_LOG_LEVELS:
            raise ValueError(f"invalid log level: {value!r}")
        return value
