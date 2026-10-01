"""Shared pytest fixtures. Tests never touch the real .env or database."""

import pytest

from app.database import Database

_ENV_NAMES = (
    "WEATHER_API_KEY",
    "SMTP_EMAIL",
    "SMTP_APP_PASSWORD",
    "SMTP_SERVER",
    "SMTP_PORT",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Remove secrets from the environment for every test."""
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def db(tmp_path):
    """Create a fresh temporary database for a test."""
    database = Database(tmp_path / "test_assistant.db")
    database.initialize()
    return database
