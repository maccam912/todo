"""Unit tests for security utilities."""
from datetime import UTC, datetime, timedelta

import pytest

from todo.config import Settings
from todo.core.security import (
    generate_access_token,
    generate_random_token,
    generate_session_token,
    hash_access_token,
    hash_password,
    is_session_token_expired,
    should_rotate_session_token,
    verify_password,
)


def test_hash_password():
    """Test password hashing."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2b$")


def test_verify_password():
    """Test password verification."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_generate_random_token():
    """Test random token generation."""
    token1 = generate_random_token(32)
    token2 = generate_random_token(32)
    assert len(token1) == 32
    assert len(token2) == 32
    assert token1 != token2


def test_generate_access_token():
    """Test access token generation."""
    plaintext, token_hash, prefix = generate_access_token()

    # Check plaintext token format
    assert isinstance(plaintext, str)
    assert len(plaintext) > 40  # Base64URL encoded 32 bytes

    # Check hash
    assert isinstance(token_hash, bytes)
    assert len(token_hash) == 32  # SHA256 hash

    # Check prefix
    assert prefix == plaintext[:8]

    # Verify hash matches
    assert hash_access_token(plaintext) == token_hash


def test_hash_access_token():
    """Test access token hashing."""
    token = "test-token-string"
    hash1 = hash_access_token(token)
    hash2 = hash_access_token(token)

    assert hash1 == hash2
    assert len(hash1) == 32  # SHA256 hash


def test_generate_session_token():
    """Test session token generation."""
    token1 = generate_session_token()
    token2 = generate_session_token()

    assert len(token1) == 32
    assert len(token2) == 32
    assert token1 != token2


def test_should_rotate_session_token():
    """Test session token rotation check."""
    settings = Settings(
        secret_key="test-secret-key-minimum-32-characters-long",
        session_token_rotation_days=7,
    )

    # Recent token should not rotate
    recent = datetime.now(UTC) - timedelta(days=3)
    assert not should_rotate_session_token(recent, settings)

    # Old token should rotate
    old = datetime.now(UTC) - timedelta(days=10)
    assert should_rotate_session_token(old, settings)


def test_is_session_token_expired():
    """Test session token expiration check."""
    settings = Settings(
        secret_key="test-secret-key-minimum-32-characters-long",
        session_token_expire_days=14,
    )

    # Recent token should not be expired
    recent = datetime.now(UTC) - timedelta(days=7)
    assert not is_session_token_expired(recent, settings)

    # Old token should be expired
    old = datetime.now(UTC) - timedelta(days=20)
    assert is_session_token_expired(old, settings)
