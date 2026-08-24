"""Read application configuration from the environment and `.env`."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Hold the complete application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    voyage_api_key: SecretStr
    similarity_threshold: float = 0.0
    log_level: str
