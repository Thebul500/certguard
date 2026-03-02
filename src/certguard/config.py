"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment.

    Required environment variables:
        CERTGUARD_DATABASE_URL: Database connection string.
        CERTGUARD_SECRET_KEY: Secret key for JWT signing.
    """

    database_url: str = "sqlite+aiosqlite://"
    secret_key: str  # Required — set CERTGUARD_SECRET_KEY env var
    access_token_expire_minutes: int = 30
    debug: bool = False

    model_config = {"env_prefix": "CERTGUARD_"}


settings = Settings()
