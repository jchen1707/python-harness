"""Application configuration — the single source of env/secrets (architecture §5).

Env and secrets are read ONLY here. Inject ``Settings`` (or its fields) into
dependents; never read ``os.environ`` or ``.env`` elsewhere.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, loaded from environment / ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "python-harness"
    log_level: str = "INFO"
    # Default model for agent code (see docs/architecture.md §9).
    anthropic_model: str = "claude-opus-4-8"
    # Document-search bounds (used by the DocumentService).
    search_default_limit: int = 5
    search_max_limit: int = 50


@lru_cache
def get_settings() -> Settings:
    """Return the cached ``Settings`` instance (read env once)."""
    return Settings()
