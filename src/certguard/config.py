"""Application configuration from environment variables."""

import secrets

from pydantic_settings import BaseSettings


def _default_secret_key() -> str:
    """Generate a random secret key when none is configured."""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """Application settings loaded from environment.

    Environment variables (prefixed with CERTGUARD_):
        CERTGUARD_DATABASE_URL: Database connection string.
        CERTGUARD_SECRET_KEY: Secret key for JWT signing (auto-generated if unset).
    """

    database_url: str = "sqlite+aiosqlite://"
    secret_key: str = _default_secret_key()
    access_token_expire_minutes: int = 30
    debug: bool = False

    model_config = {"env_prefix": "CERTGUARD_"}


settings = Settings()
