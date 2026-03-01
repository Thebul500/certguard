"""Tests for application configuration."""

from certguard.config import Settings, settings


def test_settings_defaults(monkeypatch):
    """Default settings are populated correctly."""
    monkeypatch.delenv("CERTGUARD_DATABASE_URL", raising=False)
    monkeypatch.setenv("CERTGUARD_SECRET_KEY", "test-key")
    s = Settings()
    assert s.database_url == "sqlite+aiosqlite://"
    assert s.access_token_expire_minutes == 30
    assert s.debug is False


def test_settings_env_prefix(monkeypatch):
    """Settings respect the CERTGUARD_ env prefix."""
    monkeypatch.setenv("CERTGUARD_SECRET_KEY", "from-env")
    monkeypatch.setenv("CERTGUARD_DEBUG", "true")
    s = Settings()
    assert s.debug is True
    assert s.secret_key == "from-env"


def test_settings_database_url_from_env(monkeypatch):
    """Database URL can be set via environment."""
    monkeypatch.setenv("CERTGUARD_SECRET_KEY", "test-key")
    monkeypatch.setenv("CERTGUARD_DATABASE_URL", "postgresql+asyncpg://u:p@host/db")
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@host/db"


def test_module_level_settings_instance():
    """Module-level settings singleton is a Settings instance."""
    assert isinstance(settings, Settings)
