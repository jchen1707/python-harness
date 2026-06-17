"""Application configuration — the ONLY place env/secrets are read (architecture §5).

Uses pydantic-settings to load from the process environment and `.env`. Dependents
receive a `Settings` instance (or its fields) via injection — never call `os.environ`
or read `.env` elsewhere. `.env` is gitignored; `.env.example` lists the supported vars.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment and `.env`.

    Add secrets/DSNs (Anthropic, Voyage, Postgres, …) here as the app grows; this is the
    single read site. Fields map env vars case-insensitively (e.g. ``APP_NAME`` →
    ``app_name``).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "python-harness"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings.

    Cached so env is parsed once per process. Inject the result (or its fields) into
    dependents rather than re-reading env elsewhere (§5).
    """
    return Settings()
