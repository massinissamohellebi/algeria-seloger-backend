from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "algeria-seloger-backend"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/algeria_seloger"
    )

    # JWT / Auth
    secret_key: str = Field(default="change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Object storage (S3). When s3_bucket is empty, an in-memory backend is used
    # (dev/tests). Photo upload limits below are enforced server-side.
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None

    # Public base URL used to serve in-memory (dev) photo bytes over HTTP.
    media_base_url: str = "http://api.localhost/api"

    max_photo_size_bytes: int = 5 * 1024 * 1024
    max_photos_per_listing: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
