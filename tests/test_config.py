"""Tests for application configuration."""

import os

from certguard.config import Settings, settings


def test_settings_defaults():
    """Default settings are populated correctly."""
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/certguard"
    assert s.secret_key == "change-me-in-production"
    assert s.access_token_expire_minutes == 30
    assert s.debug is False


def test_settings_env_prefix(monkeypatch):
    """Settings respect the CERTGUARD_ env prefix."""
    monkeypatch.setenv("CERTGUARD_DEBUG", "true")
    monkeypatch.setenv("CERTGUARD_SECRET_KEY", "test-secret")
    s = Settings()
    assert s.debug is True
    assert s.secret_key == "test-secret"


def test_module_level_settings_instance():
    """Module-level settings singleton is a Settings instance."""
    assert isinstance(settings, Settings)
