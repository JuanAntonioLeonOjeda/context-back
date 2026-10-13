"""Application settings, read once at startup.

No other module reads environment variables: they receive a `Settings` instance.
"""

from enum import StrEnum

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Settings from environment variables (and `.env` in local development)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    database_url: PostgresDsn
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = True


def load_settings() -> Settings:
    """Read and validate settings; fails fast at startup if something is missing."""
    # mypy cannot see that pydantic-settings fills required fields from the environment.
    return Settings()  # type: ignore[call-arg]
