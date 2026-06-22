"""
Mellow — Application Configuration
Loads all settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import secrets


class Settings(BaseSettings):

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "Mellow"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = secrets.token_hex(32)

    # ── Database ───────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://mellow:mellow@localhost:5432/mellow"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT Auth ───────────────────────────────────────────────
    JWT_SECRET: str = secrets.token_hex(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Google OAuth ───────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # ── Cloudinary ─────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── Stripe ─────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_KINDRED_PRICE_ID: str = ""
    STRIPE_KINDRED_PLUS_PRICE_ID: str = ""

    # ── SendGrid ───────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "hello@mellow.app"
    FROM_NAME: str = "Mellow"

    # ── Twilio (optional SMS) ──────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # ── CORS ───────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5500"
    ALLOWED_ORIGINS: str = "http://localhost:5500,http://localhost:8000,https://mellow.app"

    # ── Rate Limiting ──────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10

    # ── Subscription Limits ────────────────────────────────────
    FREE_DAILY_SWIPES: int = 10
    FREE_MESSAGES_PER_MATCH: int = 3
    FREE_MAX_PHOTOS: int = 2
    KINDRED_MAX_PHOTOS: int = 6
    KINDRED_PLUS_MAX_PHOTOS: int = 6

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Single settings instance used across the app
settings = Settings()
