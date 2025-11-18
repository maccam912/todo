"""Security utilities for password hashing and token generation."""

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext

from todo.config import Settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_random_token(num_bytes: int = 32) -> bytes:
    """Generate a random token of specified byte length."""
    return secrets.token_bytes(num_bytes)


def generate_access_token() -> tuple[str, bytes, str]:
    """
    Generate an API access token.

    Returns:
        tuple: (plaintext_token, token_hash, token_prefix)
            - plaintext_token: Base64URL encoded token (shown once)
            - token_hash: SHA256 hash of plaintext (stored in DB)
            - token_prefix: First 8 chars for display
    """
    # Generate 32 random bytes
    token_bytes = generate_random_token(32)

    # Encode as Base64URL (no padding)
    plaintext_token = base64.urlsafe_b64encode(token_bytes).decode("utf-8").rstrip("=")

    # Compute SHA256 hash for storage
    token_hash = hashlib.sha256(plaintext_token.encode("utf-8")).digest()

    # Extract prefix for display
    token_prefix = plaintext_token[:8]

    return plaintext_token, token_hash, token_prefix


def hash_access_token(token: str) -> bytes:
    """Hash an access token using SHA256."""
    return hashlib.sha256(token.encode("utf-8")).digest()


def generate_session_token() -> bytes:
    """Generate a session token."""
    return generate_random_token(32)


def should_rotate_session_token(token_created_at: datetime, settings: Settings) -> bool:
    """Check if a session token should be rotated."""
    rotation_threshold = timedelta(days=settings.session_token_rotation_days)
    age = datetime.now(UTC) - token_created_at.replace(tzinfo=UTC)
    return age > rotation_threshold


def is_session_token_expired(token_created_at: datetime, settings: Settings) -> bool:
    """Check if a session token has expired."""
    expiration_threshold = timedelta(days=settings.session_token_expire_days)
    age = datetime.now(UTC) - token_created_at.replace(tzinfo=UTC)
    return age > expiration_threshold
