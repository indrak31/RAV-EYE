"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///./data/tv.db"
    APP_NAME: str = "tv-backend"
    APP_VERSION: str = "v1"
    ENV: str = "dev"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    CORS_ORIGINS: str = "*"
    MEDIA_DIR: str = "./media"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def ensure_sqlite_dir(self) -> None:
        """Create the parent directory for the SQLite file path if needed."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            db_path = self.DATABASE_URL.replace("sqlite:///", "", 1)
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

    def ensure_media_dir(self) -> None:
        """Create the media directory if needed."""
        Path(self.MEDIA_DIR).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_sqlite_dir()
    settings.ensure_media_dir()
    return settings
