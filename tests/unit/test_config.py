"""Unit tests for configuration."""
import os

from todo.config import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(secret_key="test-secret-key-minimum-32-characters-long")

    assert settings.environment == "development"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.reload is False
    assert settings.password_min_length == 12


def test_settings_database_url():
    """Test database URL setting."""
    db_url = "postgresql://user:pass@localhost/testdb"
    settings = Settings(
        secret_key="test-secret-key-minimum-32-characters-long", database_url=db_url
    )
    assert settings.database_url == db_url


def test_settings_llm_config():
    """Test LLM configuration."""
    settings = Settings(
        secret_key="test-secret-key-minimum-32-characters-long",
        llm_provider="openrouter",
        llm_api_key="test-api-key",
        llm_model="anthropic/claude-3.5-sonnet",
        llm_temperature=0.5,
    )

    assert settings.llm_provider == "openrouter"
    assert settings.llm_api_key == "test-api-key"
    assert settings.llm_model == "anthropic/claude-3.5-sonnet"
    assert settings.llm_temperature == 0.5


def test_settings_cors_origins():
    """Test CORS origins configuration."""
    settings = Settings(
        secret_key="test-secret-key-minimum-32-characters-long",
        cors_origins=["http://localhost:3000", "https://example.com"],
    )
    assert len(settings.cors_origins) == 2
    assert "http://localhost:3000" in settings.cors_origins
