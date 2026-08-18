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
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    email_verification_ttl_hours: int = 24
    password_reset_ttl_hours: int = 1

    # Rate limiting (login + forgot-password): max attempts per sliding window.
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_minutes: int = 15

    # Mailer. `console` logs emails (dev/tests); `smtp` sends via an SMTP server
    # (MailDev locally, a transactional provider in prod).
    mailer_backend: str = "console"
    mail_from: str = "no-reply@algeria-seloger.dz"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    # Base URL of the frontend, used to build verification / reset links.
    frontend_base_url: str = "http://algeria-seloger.localhost:5173"

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
